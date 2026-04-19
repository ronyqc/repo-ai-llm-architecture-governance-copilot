from __future__ import annotations

import unittest
from unittest.mock import Mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import get_ingest_service
from src.integrations.blob_ingest_service import (
    IngestExecutionResult,
    IngestNotFoundError,
    IngestValidationError,
)
from src.security.auth import AuthenticatedUser, require_authenticated_user, require_ingest_user


class IngestEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.ingest_service = Mock()
        self.ingest_service.ingest.return_value = IngestExecutionResult(
            trace_id="trace-from-service",
            destination_blob_url="https://example.blob.core.windows.net/documents/admin-ingest/guidelines_patterns/trace/doc.md",
            destination_blob_name="admin-ingest/guidelines_patterns/trace/doc.md",
        )
        app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
            user_id="admin-user",
            roles=["admin"],
            claims={"scp": []},
        )
        app.dependency_overrides[get_ingest_service] = lambda: self.ingest_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _valid_payload(self) -> dict[str, object]:
        return {
            "file_name": "architecture-guidelines.md",
            "file_url": "blob://documents-raw/guidelines/architecture-guidelines.md",
            "knowledge_domain": "guidelines_patterns",
            "metadata": {
                "source_system": "sharepoint",
                "owner": "enterprise-architecture",
            },
        }

    def test_ingest_succeeds_for_admin_user(self) -> None:
        response = self.client.post("/api/v1/ingest", json=self._valid_payload())

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(
            body["message"],
            "Ingest accepted and dispatched to the blob-trigger pipeline.",
        )
        self.assertTrue(body["trace_id"])
        self.ingest_service.ingest.assert_called_once()
        call_kwargs = self.ingest_service.ingest.call_args.kwargs
        self.assertEqual(call_kwargs["user"].user_id, "admin-user")
        self.assertEqual(call_kwargs["payload"].knowledge_domain, "guidelines_patterns")
        self.assertTrue(call_kwargs["trace_id"])

    def test_ingest_rejects_non_admin_user(self) -> None:
        def _reject_non_admin() -> AuthenticatedUser:
            raise HTTPException(
                status_code=403,
                detail="Admin role or scope is required for this operation.",
            )

        app.dependency_overrides[require_ingest_user] = _reject_non_admin

        response = self.client.post("/api/v1/ingest", json=self._valid_payload())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Admin role or scope is required for this operation.",
        )
        self.ingest_service.ingest.assert_not_called()

    def test_ingest_rejects_invalid_payload(self) -> None:
        payload = self._valid_payload()
        payload.pop("metadata")

        response = self.client.post("/api/v1/ingest", json=payload)

        self.assertEqual(response.status_code, 422)
        self.ingest_service.ingest.assert_not_called()

    def test_ingest_rejects_invalid_knowledge_domain(self) -> None:
        self.ingest_service.ingest.side_effect = IngestValidationError(
            "Invalid knowledge_domain. Allowed values: bian, building_blocks, guidelines_patterns."
        )

        response = self.client.post("/api/v1/ingest", json=self._valid_payload())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid knowledge_domain", response.json()["detail"])

    def test_ingest_rejects_missing_blob_reference(self) -> None:
        self.ingest_service.ingest.side_effect = IngestNotFoundError(
            "Referenced file was not found in Azure Blob Storage."
        )

        response = self.client.post("/api/v1/ingest", json=self._valid_payload())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Referenced file was not found in Azure Blob Storage.",
        )

    def test_ingest_returns_accepted_with_valid_reference(self) -> None:
        response = self.client.post("/api/v1/ingest", json=self._valid_payload())

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
