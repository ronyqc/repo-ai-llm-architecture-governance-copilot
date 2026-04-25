from __future__ import annotations

import unittest
from unittest.mock import patch

from src.api.main import _get_cors_allowed_origins


class CorsConfigTests(unittest.TestCase):
    def test_cors_allowed_origins_defaults_to_local_frontend(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            origins = _get_cors_allowed_origins()

        self.assertEqual(
            origins,
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
        )

    def test_cors_allowed_origins_reads_csv_from_environment(self) -> None:
        with patch.dict(
            "os.environ",
            {"CORS_ALLOWED_ORIGINS": "https://app.example.com, https://admin.example.com"},
        ):
            origins = _get_cors_allowed_origins()

        self.assertEqual(
            origins,
            [
                "https://app.example.com",
                "https://admin.example.com",
            ],
        )


if __name__ == "__main__":
    unittest.main()
