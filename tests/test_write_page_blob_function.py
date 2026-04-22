from __future__ import annotations

import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


APP_DIR = Path.cwd() / "apps" / "document_processor_function"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if "azure.functions" not in sys.modules:
    azure_module = sys.modules.setdefault("azure", types.ModuleType("azure"))
    core_module = sys.modules.setdefault("azure.core", types.ModuleType("azure.core"))
    core_credentials_module = types.ModuleType("azure.core.credentials")
    functions_module = types.ModuleType("azure.functions")
    search_module = sys.modules.setdefault(
        "azure.search",
        types.ModuleType("azure.search"),
    )
    search_documents_module = types.ModuleType("azure.search.documents")
    storage_module = sys.modules.setdefault(
        "azure.storage",
        types.ModuleType("azure.storage"),
    )
    blob_module = types.ModuleType("azure.storage.blob")

    class _AuthLevel:
        ANONYMOUS = "anonymous"

    class _FunctionApp:
        def __init__(self, http_auth_level: object | None = None) -> None:
            self.http_auth_level = http_auth_level

        def route(self, *args: object, **kwargs: object):
            def decorator(func: object) -> object:
                return func

            return decorator

        def function_name(self, *args: object, **kwargs: object):
            def decorator(func: object) -> object:
                return func

            return decorator

        def blob_trigger(self, *args: object, **kwargs: object):
            def decorator(func: object) -> object:
                return func

            return decorator

    class _HttpRequest:
        def __init__(
            self,
            *,
            method: str,
            url: str,
            body: bytes,
            headers: dict[str, str] | None = None,
        ) -> None:
            self.method = method
            self.url = url
            self._body = body
            self.headers = headers or {}

        def get_json(self) -> object:
            return json.loads(self._body.decode("utf-8"))

    class _HttpResponse:
        def __init__(self, *, body: str, status_code: int, mimetype: str) -> None:
            self._body = body.encode("utf-8")
            self.status_code = status_code
            self.mimetype = mimetype

        def get_body(self) -> bytes:
            return self._body

    class _InputStream:
        pass

    class _FakeContentSettings:
        def __init__(self, *, content_type: str) -> None:
            self.content_type = content_type

    class _FakeBlobServiceClient:
        @classmethod
        def from_connection_string(cls, connection_string: str) -> "_FakeBlobServiceClient":
            raise AssertionError("Unexpected BlobServiceClient.from_connection_string call.")

    class _FakeAzureKeyCredential:
        def __init__(self, key: str) -> None:
            self.key = key

    class _FakeSearchClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args
            self.kwargs = kwargs

        def upload_documents(self, *, documents: list[dict]) -> list[object]:
            return []

    openai_module = types.ModuleType("openai")

    class _FakeAzureOpenAI:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args
            self.kwargs = kwargs

    functions_module.AuthLevel = _AuthLevel
    functions_module.FunctionApp = _FunctionApp
    functions_module.HttpRequest = _HttpRequest
    functions_module.HttpResponse = _HttpResponse
    functions_module.InputStream = _InputStream
    core_credentials_module.AzureKeyCredential = _FakeAzureKeyCredential
    search_documents_module.SearchClient = _FakeSearchClient
    blob_module.ContentSettings = _FakeContentSettings
    blob_module.BlobServiceClient = _FakeBlobServiceClient
    openai_module.AzureOpenAI = _FakeAzureOpenAI

    sys.modules["azure.functions"] = functions_module
    sys.modules["azure.core.credentials"] = core_credentials_module
    sys.modules["azure.search.documents"] = search_documents_module
    sys.modules["azure.storage.blob"] = blob_module
    sys.modules["openai"] = openai_module
    azure_module.functions = functions_module
    azure_module.core = core_module
    azure_module.search = search_module
    azure_module.storage = storage_module
    core_module.credentials = core_credentials_module
    search_module.documents = search_documents_module
    storage_module.blob = blob_module

import azure.functions as func

import function_app  # type: ignore  # noqa: E402
from processing.blob_writer import BlobWriteResult  # type: ignore  # noqa: E402


class WritePageBlobFunctionTests(unittest.TestCase):
    def test_write_page_to_blob_returns_created_response(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="http://localhost/api/write-page-to-blob",
            body=json.dumps(
                {
                    "container": "pages-container",
                    "directory": "confluence/architecture",
                    "fileName": "payments-page",
                    "content": {"title": "Payments", "content": "Normalized content"},
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        with patch.object(
            function_app,
            "write_page_json_blob",
            return_value=BlobWriteResult(
                container_name="pages-container",
                blob_name="confluence/architecture/payments-page.json",
                blob_url=(
                    "https://account.blob.core.windows.net/"
                    "pages-container/confluence/architecture/payments-page.json"
                ),
                file_name="payments-page.json",
            ),
        ) as write_blob_mock:
            response = function_app.write_page_to_blob_http(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")
        response_body = json.loads(response.get_body().decode("utf-8"))
        self.assertEqual(response_body["status"], "success")
        self.assertEqual(response_body["blob_name"], "confluence/architecture/payments-page.json")
        write_blob_mock.assert_called_once_with(
            container_name="pages-container",
            directory="confluence/architecture",
            file_name="payments-page",
            content={"title": "Payments", "content": "Normalized content"},
        )

    def test_write_page_to_blob_rejects_missing_fields(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="http://localhost/api/write-page-to-blob",
            body=json.dumps(
                {
                    "container": "pages-container",
                    "fileName": "payments-page",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        response = function_app.write_page_to_blob_http(request)

        self.assertEqual(response.status_code, 400)
        response_body = json.loads(response.get_body().decode("utf-8"))
        self.assertEqual(
            response_body["message"],
            "Missing required fields: directory, content",
        )

    def test_write_page_to_blob_rejects_invalid_json_body(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="http://localhost/api/write-page-to-blob",
            body=b"not-json",
            headers={"Content-Type": "application/json"},
        )

        response = function_app.write_page_to_blob_http(request)

        self.assertEqual(response.status_code, 400)
        response_body = json.loads(response.get_body().decode("utf-8"))
        self.assertEqual(
            response_body["message"],
            "Request body must be valid JSON.",
        )


if __name__ == "__main__":
    unittest.main()
