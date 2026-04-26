from __future__ import annotations

import io
import logging
import unittest

from src.api.schemas import IngestRequest
from src.integrations.blob_ingest_service import (
    BlobDocumentIngestService,
    IngestConflictError,
    IngestNotFoundError,
    IngestValidationError,
    ResourceExistsError,
    ResourceNotFoundError,
    logger as ingest_logger,
)
from src.security.auth import AuthenticatedUser


class _FakeDownloadStream:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def readall(self) -> bytes:
        return self._payload


class _FakeBlobClient:
    def __init__(
        self,
        *,
        url: str,
        payload: bytes | None = None,
        exists: bool = True,
        fail_on_upload: Exception | None = None,
    ) -> None:
        self.url = url
        self._payload = payload or b""
        self._exists = exists
        self._fail_on_upload = fail_on_upload
        self.upload_calls: list[dict[str, object]] = []

    def get_blob_properties(self) -> object:
        if not self._exists:
            raise ResourceNotFoundError("missing")
        return {"etag": "fake"}

    def download_blob(self) -> _FakeDownloadStream:
        if not self._exists:
            raise ResourceNotFoundError("missing")
        return _FakeDownloadStream(self._payload)

    def upload_blob(
        self,
        data: bytes,
        *,
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> object:
        if self._fail_on_upload is not None:
            raise self._fail_on_upload
        self.upload_calls.append(
            {
                "data": data,
                "overwrite": overwrite,
                "metadata": metadata,
            }
        )
        return {"etag": "uploaded"}


class _FakeBlobServiceClient:
    def __init__(self) -> None:
        self._blob_clients: dict[tuple[str, str], _FakeBlobClient] = {}

    def add_blob_client(
        self,
        *,
        container: str,
        blob: str,
        client: _FakeBlobClient,
    ) -> None:
        self._blob_clients[(container, blob)] = client

    def get_blob_client(self, *, container: str, blob: str) -> _FakeBlobClient:
        try:
            return self._blob_clients[(container, blob)]
        except KeyError as exc:
            raise AssertionError(
                f"Unexpected blob client request for {container}/{blob}"
            ) from exc


class BlobDocumentIngestServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.blob_service = _FakeBlobServiceClient()
        self.service = BlobDocumentIngestService(
            blob_service_client=self.blob_service,
            destination_container="documents-processed",
            destination_prefix="admin-ingest",
            allowed_knowledge_domains=("bian", "building_blocks", "guidelines_patterns"),
            allowed_source_containers=("documents-raw",),
        )
        self.user = AuthenticatedUser(
            user_id="user-123",
            roles=["admin"],
            claims={"scp": []},
        )

    def _payload(self, **overrides: object) -> IngestRequest:
        values: dict[str, object] = {
            "file_name": "architecture-guidelines.md",
            "file_url": "blob://documents-raw/guidelines/architecture-guidelines.md",
            "knowledge_domain": "guidelines_patterns",
            "metadata": {
                "source_system": "sharepoint",
                "owner": "enterprise-architecture",
            },
        }
        values.update(overrides)
        return IngestRequest(**values)

    def _capture_logs(self) -> tuple[io.StringIO, logging.Handler]:
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ingest_logger.handlers[0].formatter
        if formatter is not None:
            handler.setFormatter(formatter)
        ingest_logger.addHandler(handler)
        return stream, handler

    def test_ingest_copies_existing_blob_to_trigger_container(self) -> None:
        source_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-raw/guidelines/architecture-guidelines.md",
            payload=b"# Architecture Guidelines",
        )
        destination_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-processed/admin-ingest/architecture-guidelines.md"
        )
        self.blob_service.add_blob_client(
            container="documents-raw",
            blob="guidelines/architecture-guidelines.md",
            client=source_blob,
        )
        self.blob_service.add_blob_client(
            container="documents-processed",
            blob="admin-ingest/architecture-guidelines.md",
            client=destination_blob,
        )

        result = self.service.ingest(
            payload=self._payload(),
            user=self.user,
            trace_id="trace-123",
        )

        self.assertEqual(
            result.destination_blob_name,
            "admin-ingest/architecture-guidelines.md",
        )
        self.assertEqual(len(destination_blob.upload_calls), 1)
        upload_call = destination_blob.upload_calls[0]
        self.assertEqual(upload_call["data"], b"# Architecture Guidelines")
        self.assertFalse(upload_call["overwrite"])
        self.assertEqual(
            upload_call["metadata"],
            {
                "agc_trace_id": "trace-123",
                "agc_ingest_mode": "admin_api_copy",
                "agc_requested_by": "user-123",
                "agc_requested_domain": "guidelines_patterns",
            },
        )

    def test_ingest_logs_dispatch_with_structured_metadata(self) -> None:
        source_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-raw/guidelines/architecture-guidelines.md",
            payload=b"# Architecture Guidelines",
        )
        destination_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-processed/admin-ingest/architecture-guidelines.md"
        )
        self.blob_service.add_blob_client(
            container="documents-raw",
            blob="guidelines/architecture-guidelines.md",
            client=source_blob,
        )
        self.blob_service.add_blob_client(
            container="documents-processed",
            blob="admin-ingest/architecture-guidelines.md",
            client=destination_blob,
        )
        stream, handler = self._capture_logs()

        try:
            self.service.ingest(
                payload=self._payload(),
                user=self.user,
                trace_id="trace-123",
            )
        finally:
            ingest_logger.removeHandler(handler)

        output = stream.getvalue()
        self.assertIn("ingest.request.dispatched", output)
        self.assertIn('"trace_id": "trace-123"', output)
        self.assertIn('"user_id": "user-123"', output)
        self.assertIn('"knowledge_domain": "guidelines_patterns"', output)
        self.assertIn('"destination_blob_name": "admin-ingest/architecture-guidelines.md"', output)

    def test_ingest_rejects_invalid_knowledge_domain(self) -> None:
        with self.assertRaises(IngestValidationError) as context:
            self.service.ingest(
                payload=self._payload(knowledge_domain="invalid"),
                user=self.user,
                trace_id="trace-123",
            )

        self.assertIn("knowledge_domain no es", str(context.exception))

    def test_ingest_rejects_nonexistent_blob(self) -> None:
        missing_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-raw/guidelines/architecture-guidelines.md",
            exists=False,
        )
        destination_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-processed/admin-ingest/architecture-guidelines.md"
        )
        self.blob_service.add_blob_client(
            container="documents-raw",
            blob="guidelines/architecture-guidelines.md",
            client=missing_blob,
        )
        self.blob_service.add_blob_client(
            container="documents-processed",
            blob="admin-ingest/architecture-guidelines.md",
            client=destination_blob,
        )

        with self.assertRaises(IngestNotFoundError) as context:
            self.service.ingest(
                payload=self._payload(),
                user=self.user,
                trace_id="trace-123",
            )

        self.assertEqual(
            str(context.exception),
            "El archivo referenciado no fue encontrado en Azure Blob Storage.",
        )

    def test_ingest_rejects_mismatched_file_name(self) -> None:
        with self.assertRaises(IngestValidationError) as context:
            self.service.ingest(
                payload=self._payload(file_name="other-name.md"),
                user=self.user,
                trace_id="trace-123",
            )

        self.assertEqual(
            str(context.exception),
            "file_name debe coincidir con el archivo referenciado por file_url.",
        )

    def test_ingest_accepts_pdf_extension(self) -> None:
        source_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-raw/guidelines/architecture-guidelines.pdf",
            payload=b"%PDF-1.4 fake",
        )
        destination_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-processed/admin-ingest/architecture-guidelines.pdf"
        )
        self.blob_service.add_blob_client(
            container="documents-raw",
            blob="guidelines/architecture-guidelines.pdf",
            client=source_blob,
        )
        self.blob_service.add_blob_client(
            container="documents-processed",
            blob="admin-ingest/architecture-guidelines.pdf",
            client=destination_blob,
        )

        result = self.service.ingest(
            payload=self._payload(
                file_name="architecture-guidelines.pdf",
                file_url="blob://documents-raw/guidelines/architecture-guidelines.pdf",
            ),
            user=self.user,
            trace_id="trace-123",
        )

        self.assertEqual(result.destination_blob_name, "admin-ingest/architecture-guidelines.pdf")

    def test_ingest_rejects_unsupported_file_extension(self) -> None:
        with self.assertRaises(IngestValidationError) as context:
            self.service.ingest(
                payload=self._payload(
                    file_name="architecture-guidelines.xlsx",
                    file_url="blob://documents-raw/guidelines/architecture-guidelines.xlsx",
                ),
                user=self.user,
                trace_id="trace-123",
            )

        self.assertIn("no está soportado", str(context.exception))

    def test_ingest_raises_conflict_when_destination_blob_already_exists(self) -> None:
        source_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-raw/guidelines/architecture-guidelines.md",
            payload=b"# Architecture Guidelines",
        )
        destination_blob = _FakeBlobClient(
            url="https://account.blob.core.windows.net/documents-processed/admin-ingest/architecture-guidelines.md",
            fail_on_upload=ResourceExistsError("already exists"),
        )
        self.blob_service.add_blob_client(
            container="documents-raw",
            blob="guidelines/architecture-guidelines.md",
            client=source_blob,
        )
        self.blob_service.add_blob_client(
            container="documents-processed",
            blob="admin-ingest/architecture-guidelines.md",
            client=destination_blob,
        )

        with self.assertRaises(IngestConflictError):
            self.service.ingest(
                payload=self._payload(),
                user=self.user,
                trace_id="trace-123",
            )


if __name__ == "__main__":
    unittest.main()
