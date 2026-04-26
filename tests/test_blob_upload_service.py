from __future__ import annotations

from datetime import UTC, datetime
import unittest

from src.integrations.blob_upload_service import (
    BlobUploadUrlService,
    UploadUrlConfigurationError,
    UploadUrlValidationError,
)


class _FakeBlobClient:
    def __init__(self, url: str) -> None:
        self.url = url


class _FakeBlobServiceClient:
    def get_blob_client(self, *, container: str, blob: str) -> _FakeBlobClient:
        return _FakeBlobClient(
            f"https://account.blob.core.windows.net/{container}/{blob}"
        )


class BlobUploadUrlServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sas_calls: list[dict[str, object]] = []
        self.service = BlobUploadUrlService(
            blob_service_client=_FakeBlobServiceClient(),
            raw_container_name="raw-corpus",
            expires_in_seconds=900,
            account_name="account",
            account_key="secret-key",
            sas_generator=self._fake_sas_generator,
            clock=lambda: datetime(2026, 4, 19, 18, 0, 0, tzinfo=UTC),
        )

    def _fake_sas_generator(self, **kwargs: object) -> str:
        self.sas_calls.append(kwargs)
        return "sig=fake"

    def test_generates_upload_url_successfully(self) -> None:
        result = self.service.generate_upload_url(file_name="guide.pdf")

        self.assertEqual(
            result.upload_url,
            "https://account.blob.core.windows.net/raw-corpus/guide.pdf?sig=fake",
        )
        self.assertEqual(
            result.blob_url,
            "https://account.blob.core.windows.net/raw-corpus/guide.pdf",
        )
        self.assertEqual(result.blob_name, "guide.pdf")
        self.assertEqual(result.expires_in_seconds, 900)
        self.assertEqual(self.sas_calls[0]["container_name"], "raw-corpus")
        self.assertEqual(self.sas_calls[0]["blob_name"], "guide.pdf")

    def test_rejects_invalid_file_name_with_path_traversal(self) -> None:
        with self.assertRaises(UploadUrlValidationError) as context:
            self.service.generate_upload_url(file_name="../guide.pdf")

        self.assertEqual(
            str(context.exception),
            "file_name no debe contener rutas ni segmentos inválidos.",
        )

    def test_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(UploadUrlValidationError) as context:
            self.service.generate_upload_url(file_name="guide.exe")

        self.assertIn("no está permitida", str(context.exception))

    def test_rejects_empty_file_name(self) -> None:
        with self.assertRaises(UploadUrlValidationError) as context:
            self.service.generate_upload_url(file_name="   ")

        self.assertEqual(str(context.exception), "file_name es obligatorio.")

    def test_requires_valid_storage_credentials(self) -> None:
        with self.assertRaises(UploadUrlConfigurationError):
            BlobUploadUrlService(
                blob_service_client=_FakeBlobServiceClient(),
                raw_container_name="raw-corpus",
                expires_in_seconds=900,
                account_name="",
                account_key="",
            )


if __name__ == "__main__":
    unittest.main()
