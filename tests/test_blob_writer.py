from __future__ import annotations

import json
from pathlib import Path
import sys
import types
import unittest


APP_DIR = Path.cwd() / "apps" / "document_processor_function"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if "azure.storage.blob" not in sys.modules:
    azure_module = sys.modules.setdefault("azure", types.ModuleType("azure"))
    storage_module = sys.modules.setdefault(
        "azure.storage",
        types.ModuleType("azure.storage"),
    )
    blob_module = types.ModuleType("azure.storage.blob")

    class _FakeContentSettings:
        def __init__(self, *, content_type: str) -> None:
            self.content_type = content_type

    class _FakeBlobServiceClient:
        @classmethod
        def from_connection_string(cls, connection_string: str) -> "_FakeBlobServiceClient":
            raise AssertionError("Unexpected BlobServiceClient.from_connection_string call.")

    blob_module.ContentSettings = _FakeContentSettings
    blob_module.BlobServiceClient = _FakeBlobServiceClient
    sys.modules["azure.storage.blob"] = blob_module
    azure_module.storage = storage_module
    storage_module.blob = blob_module

from processing.blob_writer import write_page_json_blob  # type: ignore  # noqa: E402


class _FakeBlobClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.upload_calls: list[dict[str, object]] = []

    def upload_blob(
        self,
        data: bytes,
        *,
        overwrite: bool = False,
        content_settings: object | None = None,
    ) -> object:
        self.upload_calls.append(
            {
                "data": data,
                "overwrite": overwrite,
                "content_settings": content_settings,
            }
        )
        return {"etag": "fake"}


class _FakeBlobServiceClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str]] = []
        self.clients: dict[tuple[str, str], _FakeBlobClient] = {}

    def get_blob_client(self, *, container: str, blob: str) -> _FakeBlobClient:
        self.requests.append((container, blob))
        client = _FakeBlobClient(
            url=f"https://account.blob.core.windows.net/{container}/{blob}"
        )
        self.clients[(container, blob)] = client
        return client


class BlobWriterTests(unittest.TestCase):
    def test_write_page_json_blob_writes_json_file_to_requested_path(self) -> None:
        blob_service_client = _FakeBlobServiceClient()

        result = write_page_json_blob(
            container_name="pages-container",
            directory="confluence/architecture",
            file_name="payments-page",
            content="Normalized page content",
            blob_service_client=blob_service_client,
        )

        self.assertEqual(
            blob_service_client.requests,
            [("pages-container", "confluence/architecture/payments-page.json")],
        )
        self.assertEqual(result.file_name, "payments-page.json")
        self.assertEqual(
            result.blob_name,
            "confluence/architecture/payments-page.json",
        )

        upload_call = blob_service_client.clients[
            ("pages-container", "confluence/architecture/payments-page.json")
        ].upload_calls[0]
        self.assertTrue(upload_call["overwrite"])
        self.assertEqual(
            json.loads(upload_call["data"].decode("utf-8")),
            {"content": "Normalized page content"},
        )

    def test_write_page_json_blob_preserves_dictionary_content(self) -> None:
        blob_service_client = _FakeBlobServiceClient()

        write_page_json_blob(
            container_name="pages-container",
            directory="confluence/architecture",
            file_name="payments-page.json",
            content={"title": "Payments", "content": "Normalized page content"},
            blob_service_client=blob_service_client,
        )

        upload_call = blob_service_client.clients[
            ("pages-container", "confluence/architecture/payments-page.json")
        ].upload_calls[0]
        self.assertEqual(
            json.loads(upload_call["data"].decode("utf-8")),
            {"title": "Payments", "content": "Normalized page content"},
        )

    def test_write_page_json_blob_rejects_file_name_with_path_segments(self) -> None:
        blob_service_client = _FakeBlobServiceClient()

        with self.assertRaises(ValueError) as context:
            write_page_json_blob(
                container_name="pages-container",
                directory="confluence/architecture",
                file_name="../payments-page",
                content="Normalized page content",
                blob_service_client=blob_service_client,
            )

        self.assertEqual(
            str(context.exception),
            "Field 'fileName' must not contain path segments.",
        )

    def test_write_page_json_blob_rejects_invalid_directory_segments(self) -> None:
        blob_service_client = _FakeBlobServiceClient()

        with self.assertRaises(ValueError) as context:
            write_page_json_blob(
                container_name="pages-container",
                directory="../confluence",
                file_name="payments-page",
                content="Normalized page content",
                blob_service_client=blob_service_client,
            )

        self.assertEqual(
            str(context.exception),
            "Field 'directory' contains invalid path segments.",
        )


if __name__ == "__main__":
    unittest.main()
