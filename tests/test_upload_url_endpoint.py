from __future__ import annotations

import unittest
from unittest.mock import Mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import get_blob_upload_service
from src.integrations.blob_upload_service import (
    UploadUrlResult,
    UploadUrlValidationError,
)
from src.security.auth import (
    AuthenticatedUser,
    require_admin_user,
    require_authenticated_user,
)


class UploadUrlEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.upload_service = Mock()
        self.upload_service.generate_upload_url.return_value = UploadUrlResult(
            upload_url="https://account.blob.core.windows.net/raw-corpus/guide.pdf?sig=fake",
            blob_url="https://account.blob.core.windows.net/raw-corpus/guide.pdf",
            blob_name="guide.pdf",
            expires_in_seconds=900,
        )
        app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
            user_id="admin-user",
            roles=["admin"],
            claims={"scp": []},
        )
        app.dependency_overrides[get_blob_upload_service] = lambda: self.upload_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_generates_sas_successfully_for_admin(self) -> None:
        response = self.client.post(
            "/api/v1/upload-url",
            json={"file_name": "guide.pdf"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("upload_url", body)
        self.assertEqual(body["blob_name"], "guide.pdf")
        self.assertEqual(body["expires_in_seconds"], 900)
        self.upload_service.generate_upload_url.assert_called_once_with(
            file_name="guide.pdf"
        )

    def test_rejects_non_admin_user(self) -> None:
        def _reject_non_admin() -> AuthenticatedUser:
            raise HTTPException(
                status_code=403,
                detail="Admin role or scope is required for this operation.",
            )

        app.dependency_overrides[require_admin_user] = _reject_non_admin

        response = self.client.post(
            "/api/v1/upload-url",
            json={"file_name": "guide.pdf"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Admin role or scope is required for this operation.",
        )
        self.upload_service.generate_upload_url.assert_not_called()

    def test_rejects_invalid_payload(self) -> None:
        response = self.client.post(
            "/api/v1/upload-url",
            json={},
        )

        self.assertEqual(response.status_code, 422)
        self.upload_service.generate_upload_url.assert_not_called()

    def test_rejects_invalid_file_name(self) -> None:
        self.upload_service.generate_upload_url.side_effect = UploadUrlValidationError(
            "file_name no debe contener rutas ni segmentos inválidos."
        )

        response = self.client.post(
            "/api/v1/upload-url",
            json={"file_name": "../guide.pdf"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "file_name no debe contener rutas ni segmentos inválidos.",
        )

    def test_response_contains_upload_url_and_expiration(self) -> None:
        response = self.client.post(
            "/api/v1/upload-url",
            json={"file_name": "guide.docx"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["upload_url"])
        self.assertTrue(body["blob_url"])
        self.assertEqual(body["expires_in_seconds"], 900)


if __name__ == "__main__":
    unittest.main()
