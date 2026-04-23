from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Protocol

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal local envs
    BlobServiceClient = None

    class ContentSettings:  # type: ignore[override]
        def __init__(self, *, content_type: str) -> None:
            self.content_type = content_type


@dataclass(frozen=True)
class BlobWriteResult:
    container_name: str
    blob_name: str
    blob_url: str
    file_name: str


class BlobClientProtocol(Protocol):
    url: str

    def upload_blob(
        self,
        data: bytes,
        *,
        overwrite: bool = False,
        content_settings: object | None = None,
    ) -> object:
        ...


class BlobServiceClientProtocol(Protocol):
    def get_blob_client(self, *, container: str, blob: str) -> BlobClientProtocol:
        ...


def write_page_json_blob(
    *,
    container_name: str,
    directory: str,
    file_name: str,
    content: Any,
    blob_service_client: BlobServiceClientProtocol | None = None,
    overwrite: bool = True,
) -> BlobWriteResult:
    return write_page_text_blob(
        container_name=container_name,
        directory=directory,
        file_name=file_name,
        content=content,
        blob_service_client=blob_service_client,
        overwrite=overwrite,
    )


def write_page_text_blob(
    *,
    container_name: str,
    directory: str,
    file_name: str,
    content: Any,
    blob_service_client: BlobServiceClientProtocol | None = None,
    overwrite: bool = True,
) -> BlobWriteResult:
    normalized_container = _normalize_container_name(container_name)
    normalized_directory = _normalize_directory(directory)
    normalized_file_name = _normalize_file_name(file_name)
    blob_name = _build_blob_name(
        directory=normalized_directory,
        file_name=normalized_file_name,
    )
    payload_bytes = _serialize_page_payload(content)

    if blob_service_client is None:
        if BlobServiceClient is None:
            raise RuntimeError(
                "azure-storage-blob must be installed to write page blobs."
            )
        service_client = BlobServiceClient.from_connection_string(
            _get_storage_connection_string()
        )
    else:
        service_client = blob_service_client
    blob_client = service_client.get_blob_client(
        container=normalized_container,
        blob=blob_name,
    )

    try:
        blob_client.upload_blob(
            payload_bytes,
            overwrite=overwrite,
            content_settings=ContentSettings(
                content_type="text/plain; charset=utf-8"
            ),
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to write blob '{normalized_container}/{blob_name}': {exc}"
        ) from exc

    return BlobWriteResult(
        container_name=normalized_container,
        blob_name=blob_name,
        blob_url=blob_client.url,
        file_name=normalized_file_name,
    )


def _normalize_container_name(container_name: str) -> str:
    normalized = container_name.strip()
    if not normalized:
        raise ValueError("Field 'container' is required.")
    return normalized


def _normalize_directory(directory: str) -> str:
    normalized = directory.strip().replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("Field 'directory' is required.")

    parts = [part.strip() for part in normalized.split("/") if part.strip()]
    if not parts:
        raise ValueError("Field 'directory' is required.")
    if any(part in {".", ".."} for part in parts):
        raise ValueError("Field 'directory' contains invalid path segments.")

    return "/".join(parts)


def _normalize_file_name(file_name: str) -> str:
    normalized = file_name.strip()
    if not normalized:
        raise ValueError("Field 'fileName' is required.")

    if (
        PurePosixPath(normalized).name != normalized
        or PureWindowsPath(normalized).name != normalized
        or normalized in {".", ".."}
    ):
        raise ValueError("Field 'fileName' must not contain path segments.")

    lowered = normalized.lower()
    if lowered.endswith(".json"):
        normalized = normalized[:-5]
        lowered = normalized.lower()
    if not lowered.endswith(".txt"):
        normalized = f"{normalized}.txt"

    return normalized


def _build_blob_name(*, directory: str, file_name: str) -> str:
    return "/".join(
        segment
        for segment in (directory.strip("/"), file_name)
        if segment
    )


def _serialize_page_payload(content: Any) -> bytes:
    try:
        serialized = _render_plain_text(content)
    except (TypeError, ValueError) as exc:
        raise ValueError("Field 'content' must be serializable to plain text.") from exc

    if not serialized.strip():
        raise ValueError("Field 'content' must contain serializable text.")

    return serialized.encode("utf-8")


def _render_plain_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, bool):
        return "true" if content else "false"
    if isinstance(content, (int, float)):
        return str(content)
    if isinstance(content, dict):
        return _render_mapping(content)
    if isinstance(content, (list, tuple, set)):
        return _render_sequence(content)
    raise TypeError("Unsupported content type.")


def _render_mapping(content: dict[Any, Any]) -> str:
    parts: list[str] = []
    for raw_key, value in content.items():
        key = str(raw_key).strip()
        if not key:
            continue

        rendered_value = _render_plain_text(value).strip()
        if not rendered_value:
            continue

        if isinstance(value, dict):
            parts.append(f"{key}:\n{_indent_text(rendered_value)}")
            continue

        if isinstance(value, (list, tuple, set)):
            parts.append(f"{key}:\n{_indent_text(rendered_value)}")
            continue

        parts.append(f"{key}: {rendered_value}")

    return "\n\n".join(parts)


def _render_sequence(content: list[Any] | tuple[Any, ...] | set[Any]) -> str:
    parts: list[str] = []
    for item in content:
        rendered_item = _render_plain_text(item).strip()
        if not rendered_item:
            continue

        if "\n" in rendered_item:
            parts.append(f"-\n{_indent_text(rendered_item)}")
            continue

        parts.append(f"- {rendered_item}")

    return "\n".join(parts)


def _indent_text(value: str) -> str:
    lines = [line.rstrip() for line in value.splitlines()]
    non_empty_lines = [line for line in lines if line.strip()]
    return "\n".join(f"  {line}" for line in non_empty_lines)


def _get_storage_connection_string() -> str:
    for env_name in ("AZURE_STORAGE_CONNECTION_STRING", "AzureWebJobsStorage"):
        value = os.getenv(env_name)
        if value and value.strip():
            return value.strip()

    raise ValueError(
        "Environment variable 'AZURE_STORAGE_CONNECTION_STRING' or "
        "'AzureWebJobsStorage' is required."
    )
