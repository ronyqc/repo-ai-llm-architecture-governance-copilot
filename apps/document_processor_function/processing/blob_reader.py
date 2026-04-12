from __future__ import annotations

import os

from azure.storage.blob import BlobServiceClient


def read_blob_text(container_name: str, blob_name: str) -> dict:
    """Read a UTF-8 text blob from Azure Blob Storage and return canonical fields."""
    if not container_name or not container_name.strip():
        raise ValueError("container_name is required.")
    if not blob_name or not blob_name.strip():
        raise ValueError("blob_name is required.")

    connection_string = _get_required_env("AZURE_STORAGE_CONNECTION_STRING")
    service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = service_client.get_blob_client(
        container=container_name.strip(),
        blob=blob_name.strip(),
    )

    try:
        blob_bytes = blob_client.download_blob().readall()
        content = blob_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Blob content could not be decoded as UTF-8.") from exc
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read blob '{container_name}/{blob_name}': {exc}"
        ) from exc

    return {
        "document_name": blob_name.strip().rsplit("/", 1)[-1],
        "content": content,
        "source_url": f"blob://{container_name.strip()}/{blob_name.strip()}",
    }


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable '{name}' is required.")
    return value
