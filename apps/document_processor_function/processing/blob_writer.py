from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Protocol

from azure.storage.blob import BlobServiceClient, ContentSettings


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
    normalized_container = _normalize_container_name(container_name)
    normalized_directory = _normalize_directory(directory)
    normalized_file_name = _normalize_file_name(file_name)
    blob_name = _build_blob_name(
        directory=normalized_directory,
        file_name=normalized_file_name,
    )
    payload_bytes = _serialize_page_payload(content)

    service_client = blob_service_client or BlobServiceClient.from_connection_string(
        _get_storage_connection_string()
    )
    blob_client = service_client.get_blob_client(
        container=normalized_container,
        blob=blob_name,
    )

    try:
        blob_client.upload_blob(
            payload_bytes,
            overwrite=overwrite,
            content_settings=ContentSettings(
                content_type="application/json; charset=utf-8"
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

    if not normalized.lower().endswith(".json"):
        normalized = f"{normalized}.json"

    return normalized


def _build_blob_name(*, directory: str, file_name: str) -> str:
    return "/".join(
        segment
        for segment in (directory.strip("/"), file_name)
        if segment
    )


def _serialize_page_payload(content: Any) -> bytes:
    payload = content if isinstance(content, dict) else {"content": content}
    try:
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    except TypeError as exc:
        raise ValueError("Field 'content' must be JSON-serializable.") from exc
    return serialized.encode("utf-8")


def _get_storage_connection_string() -> str:
    for env_name in ("AZURE_STORAGE_CONNECTION_STRING", "AzureWebJobsStorage"):
        value = os.getenv(env_name)
        if value and value.strip():
            return value.strip()

    raise ValueError(
        "Environment variable 'AZURE_STORAGE_CONNECTION_STRING' or "
        "'AzureWebJobsStorage' is required."
    )
