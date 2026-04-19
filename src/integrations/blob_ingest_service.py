from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import unquote, urlparse

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from src.api.schemas import IngestRequest
from src.core.config import Settings, settings
from src.security.auth import AuthenticatedUser
from src.utils.logger import get_logger


logger = get_logger(__name__)

_SUPPORTED_SOURCE_TYPES = {
    ".md": "markdown_curated",
    ".txt": "plain_text",
    ".html": "html_page",
    ".htm": "html_page",
    ".pdf": "pdf_document",
    ".docx": "docx_document",
}


@dataclass(frozen=True)
class BlobReference:
    container_name: str
    blob_name: str

    @property
    def file_name(self) -> str:
        return PurePosixPath(self.blob_name).name


@dataclass(frozen=True)
class IngestExecutionResult:
    trace_id: str
    destination_blob_url: str
    destination_blob_name: str


class BlobClientProtocol(Protocol):
    url: str

    def get_blob_properties(self) -> object:
        ...

    def download_blob(self) -> object:
        ...

    def upload_blob(
        self,
        data: bytes,
        *,
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> object:
        ...


class BlobServiceClientProtocol(Protocol):
    def get_blob_client(self, *, container: str, blob: str) -> BlobClientProtocol:
        ...


class IngestServiceError(Exception):
    status_code = 400


class IngestValidationError(IngestServiceError):
    status_code = 400


class IngestNotFoundError(IngestServiceError):
    status_code = 404


class IngestConflictError(IngestServiceError):
    status_code = 409


class BlobDocumentIngestService:
    def __init__(
        self,
        *,
        blob_service_client: BlobServiceClientProtocol,
        destination_container: str,
        destination_prefix: str,
        allowed_knowledge_domains: tuple[str, ...],
        allowed_source_containers: tuple[str, ...],
    ) -> None:
        self._blob_service_client = blob_service_client
        self._destination_container = destination_container.strip()
        self._destination_prefix = destination_prefix.strip().strip("/")
        self._allowed_knowledge_domains = {
            domain.strip().lower()
            for domain in allowed_knowledge_domains
            if domain.strip()
        }
        self._allowed_source_containers = {
            container.strip().lower()
            for container in allowed_source_containers
            if container.strip()
        }

        if not self._destination_container:
            raise IngestValidationError(
                "DOCUMENTS_CONTAINER_NAME debe estar configurado para /api/v1/ingest."
            )

        if not self._allowed_knowledge_domains:
            raise IngestValidationError(
                "INGEST_ALLOWED_KNOWLEDGE_DOMAINS debe definir al menos un valor."
            )

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "BlobDocumentIngestService":
        return cls(
            blob_service_client=BlobServiceClient.from_connection_string(
                app_settings.AZURE_STORAGE_CONNECTION_STRING
            ),
            destination_container=app_settings.DOCUMENTS_CONTAINER_NAME,
            destination_prefix=app_settings.INGEST_DESTINATION_PREFIX,
            allowed_knowledge_domains=app_settings.INGEST_ALLOWED_KNOWLEDGE_DOMAINS,
            allowed_source_containers=app_settings.INGEST_ALLOWED_SOURCE_CONTAINERS,
        )

    def ingest(
        self,
        payload: IngestRequest,
        *,
        user: AuthenticatedUser,
        trace_id: str,
    ) -> IngestExecutionResult:
        normalized_domain = payload.knowledge_domain.strip().lower()
        self._validate_knowledge_domain(normalized_domain)

        source_reference = self._parse_blob_reference(payload.file_url)
        self._validate_source_container(source_reference.container_name)
        self._validate_file_name(payload.file_name, source_reference.file_name)
        self._validate_supported_source_type(source_reference.file_name)

        source_blob = self._blob_service_client.get_blob_client(
            container=source_reference.container_name,
            blob=source_reference.blob_name,
        )
        destination_blob_name = self._build_destination_blob_name(
            knowledge_domain=normalized_domain,
            file_name=source_reference.file_name,
            trace_id=trace_id,
        )
        destination_blob = self._blob_service_client.get_blob_client(
            container=self._destination_container,
            blob=destination_blob_name,
        )

        try:
            source_blob.get_blob_properties()
        except ResourceNotFoundError as exc:
            raise IngestNotFoundError(
                "El archivo referenciado no fue encontrado en Azure Blob Storage."
            ) from exc

        try:
            blob_payload = source_blob.download_blob().readall()
        except ResourceNotFoundError as exc:
            raise IngestNotFoundError(
                "El archivo referenciado no fue encontrado en Azure Blob Storage."
            ) from exc
        except Exception as exc:
            logger.exception(
                "Failed to download source blob for ingest. trace_id=%s source=%s/%s",
                trace_id,
                source_reference.container_name,
                source_reference.blob_name,
            )
            raise IngestValidationError(
                "No se pudo leer el archivo referenciado desde Azure Blob Storage."
            ) from exc

        metadata = {
            "agc_trace_id": trace_id,
            "agc_ingest_mode": "admin_api_copy",
            "agc_requested_by": self._slugify(user.user_id),
            "agc_requested_domain": normalized_domain,
        }

        try:
            destination_blob.upload_blob(
                blob_payload,
                overwrite=False,
                metadata=metadata,
            )
        except ResourceExistsError as exc:
            raise IngestConflictError(
                "Ya existe un blob de ingesta con la misma ruta de destino."
            ) from exc
        except Exception as exc:
            logger.exception(
                "Failed to upload destination blob for ingest. trace_id=%s destination=%s/%s",
                trace_id,
                self._destination_container,
                destination_blob_name,
            )
            raise IngestValidationError(
                "No se pudo despachar la solicitud de ingesta al contenedor que activa el Blob Trigger."
            ) from exc

        logger.info(
            "Ingest request dispatched to blob trigger container. trace_id=%s source=%s/%s destination=%s/%s user_id=%s",
            trace_id,
            source_reference.container_name,
            source_reference.blob_name,
            self._destination_container,
            destination_blob_name,
            user.user_id,
        )
        return IngestExecutionResult(
            trace_id=trace_id,
            destination_blob_url=destination_blob.url,
            destination_blob_name=destination_blob_name,
        )

    def _validate_knowledge_domain(self, knowledge_domain: str) -> None:
        if knowledge_domain not in self._allowed_knowledge_domains:
            allowed = ", ".join(sorted(self._allowed_knowledge_domains))
            raise IngestValidationError(
                "knowledge_domain no es válido. "
                f"Valores permitidos: {allowed}."
            )

    def _validate_source_container(self, container_name: str) -> None:
        if not self._allowed_source_containers:
            return

        if container_name.strip().lower() not in self._allowed_source_containers:
            allowed = ", ".join(sorted(self._allowed_source_containers))
            raise IngestValidationError(
                "El contenedor del blob referenciado no está permitido para la ingesta administrativa. "
                f"Valores permitidos: {allowed}."
            )

    @staticmethod
    def _validate_file_name(payload_file_name: str, referenced_file_name: str) -> None:
        normalized_payload = payload_file_name.strip()
        if normalized_payload != referenced_file_name:
            raise IngestValidationError(
                "file_name debe coincidir con el archivo referenciado por file_url."
            )

    @staticmethod
    def _validate_supported_source_type(file_name: str) -> None:
        suffix = PurePosixPath(file_name).suffix.lower()
        if suffix not in _SUPPORTED_SOURCE_TYPES:
            allowed = ", ".join(sorted(_SUPPORTED_SOURCE_TYPES))
            raise IngestValidationError(
                "El tipo de archivo no está soportado por el pipeline de ingesta actual. "
                f"Extensiones permitidas: {allowed}."
            )

    def _build_destination_blob_name(
        self,
        *,
        knowledge_domain: str,
        file_name: str,
        trace_id: str,
    ) -> str:
        path_segments = [
            segment
            for segment in (
                self._destination_prefix,
                file_name,
            )
            if segment
        ]
        return "/".join(path_segments)

    @staticmethod
    def _parse_blob_reference(file_url: str) -> BlobReference:
        parsed = urlparse(file_url.strip())
        scheme = parsed.scheme.lower()

        if scheme == "blob":
            container_name = parsed.netloc.strip()
            blob_name = parsed.path.lstrip("/")
            return BlobDocumentIngestService._build_blob_reference(
                container_name=container_name,
                blob_name=blob_name,
            )

        if scheme == "https" and parsed.netloc:
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) < 2:
                raise IngestValidationError(
                    "file_url debe incluir tanto el contenedor del blob como la ruta del blob."
                )
            return BlobDocumentIngestService._build_blob_reference(
                container_name=path_parts[0],
                blob_name="/".join(path_parts[1:]),
            )

        raise IngestValidationError(
            "file_url debe referenciar un objeto de Azure Blob Storage usando blob:// o https://."
        )

    @staticmethod
    def _build_blob_reference(*, container_name: str, blob_name: str) -> BlobReference:
        normalized_container = container_name.strip()
        normalized_blob_name = unquote(blob_name.strip().lstrip("/"))
        if not normalized_container or not normalized_blob_name:
            raise IngestValidationError(
                "file_url debe referenciar un contenedor de blob existente y una ruta de blob válida."
            )
        return BlobReference(
            container_name=normalized_container,
            blob_name=normalized_blob_name,
        )

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = "".join(
            character.lower()
            if character.isalnum()
            else "-"
            for character in value.strip()
        )
        compact = "-".join(part for part in normalized.split("-") if part)
        return compact or "unknown"
