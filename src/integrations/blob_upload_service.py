from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath, PureWindowsPath
from typing import Callable, Protocol

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

from src.core.config import Settings, settings


_ALLOWED_UPLOAD_EXTENSIONS = {
    ".md",
    ".txt",
    ".html",
    ".htm",
    ".pdf",
    ".docx",
}


@dataclass(frozen=True)
class UploadUrlResult:
    upload_url: str
    blob_url: str
    blob_name: str
    expires_in_seconds: int


class BlobClientProtocol(Protocol):
    url: str


class BlobServiceClientProtocol(Protocol):
    def get_blob_client(self, *, container: str, blob: str) -> BlobClientProtocol:
        ...


class UploadUrlServiceError(Exception):
    status_code = 400


class UploadUrlValidationError(UploadUrlServiceError):
    status_code = 400


class UploadUrlConfigurationError(UploadUrlServiceError):
    status_code = 500


class BlobUploadUrlService:
    def __init__(
        self,
        *,
        blob_service_client: BlobServiceClientProtocol,
        raw_container_name: str,
        expires_in_seconds: int,
        account_name: str,
        account_key: str,
        sas_generator: Callable[..., str] = generate_blob_sas,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._blob_service_client = blob_service_client
        self._raw_container_name = raw_container_name.strip()
        self._expires_in_seconds = expires_in_seconds
        self._account_name = account_name.strip()
        self._account_key = account_key.strip()
        self._sas_generator = sas_generator
        self._clock = clock or (lambda: datetime.now(UTC))

        if not self._raw_container_name:
            raise UploadUrlConfigurationError(
                "RAW_UPLOAD_CONTAINER_NAME debe estar configurado."
            )
        if self._expires_in_seconds <= 0:
            raise UploadUrlConfigurationError(
                "UPLOAD_URL_EXPIRATION_SECONDS debe ser mayor que cero."
            )
        if not self._account_name or not self._account_key:
            raise UploadUrlConfigurationError(
                "La configuración de Azure Blob Storage no incluye credenciales válidas para generar SAS."
            )

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "BlobUploadUrlService":
        account_name, account_key = _extract_storage_account_credentials(
            app_settings.AZURE_STORAGE_CONNECTION_STRING
        )
        return cls(
            blob_service_client=BlobServiceClient.from_connection_string(
                app_settings.AZURE_STORAGE_CONNECTION_STRING
            ),
            raw_container_name=app_settings.RAW_UPLOAD_CONTAINER_NAME,
            expires_in_seconds=app_settings.UPLOAD_URL_EXPIRATION_SECONDS,
            account_name=account_name,
            account_key=account_key,
        )

    def generate_upload_url(self, *, file_name: str) -> UploadUrlResult:
        normalized_file_name = self._validate_file_name(file_name)
        blob_client = self._blob_service_client.get_blob_client(
            container=self._raw_container_name,
            blob=normalized_file_name,
        )
        expires_on = self._clock() + timedelta(seconds=self._expires_in_seconds)
        sas_token = self._sas_generator(
            account_name=self._account_name,
            account_key=self._account_key,
            container_name=self._raw_container_name,
            blob_name=normalized_file_name,
            permission=BlobSasPermissions(create=True, write=True),
            expiry=expires_on,
            protocol="https",
        )

        return UploadUrlResult(
            upload_url=f"{blob_client.url}?{sas_token}",
            blob_url=blob_client.url,
            blob_name=normalized_file_name,
            expires_in_seconds=self._expires_in_seconds,
        )

    @staticmethod
    def _validate_file_name(file_name: str) -> str:
        normalized = file_name.strip()
        if not normalized:
            raise UploadUrlValidationError("file_name es obligatorio.")

        if (
            PurePosixPath(normalized).name != normalized
            or PureWindowsPath(normalized).name != normalized
            or normalized in {".", ".."}
        ):
            raise UploadUrlValidationError(
                "file_name no debe contener rutas ni segmentos inválidos."
            )

        suffix = PurePosixPath(normalized).suffix.lower()
        if suffix not in _ALLOWED_UPLOAD_EXTENSIONS:
            allowed = ", ".join(sorted(_ALLOWED_UPLOAD_EXTENSIONS))
            raise UploadUrlValidationError(
                "La extensión del archivo no está permitida para subida directa. "
                f"Extensiones permitidas: {allowed}."
            )

        return normalized


def _extract_storage_account_credentials(connection_string: str) -> tuple[str, str]:
    values: dict[str, str] = {}
    for segment in connection_string.split(";"):
        if "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        values[key.strip().lower()] = value.strip()

    account_name = values.get("accountname", "")
    account_key = values.get("accountkey", "")
    return account_name, account_key
