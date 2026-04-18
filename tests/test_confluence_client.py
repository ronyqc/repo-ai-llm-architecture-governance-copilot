from __future__ import annotations

import json
import unittest

from src.integrations.confluence_client import (
    ConfluenceCloudClient,
    ConfluenceSearchRequest,
)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeOpener:
    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = list(payloads)
        self.requests = []

    def open(self, req):  # noqa: ANN001
        self.requests.append(req)
        return _FakeResponse(self._payloads.pop(0))


class ConfluenceCloudClientTests(unittest.TestCase):
    def test_search_executes_bounded_cql_and_normalizes_pages(self) -> None:
        opener = _FakeOpener(
            [
                {
                    "results": [
                        {
                            "content": {
                                "id": "123",
                                "title": "Decision de Orquestacion",
                            }
                        }
                    ]
                },
                {
                    "id": "123",
                    "title": "Decision de Orquestacion",
                    "body": {
                        "storage": {
                            "value": "<p>Se acordo centralizar pagos.</p>"
                        }
                    },
                    "space": {"key": "AGC"},
                    "_links": {
                        "base": "https://acme.atlassian.net",
                        "webui": "/wiki/spaces/AGC/pages/123",
                    },
                },
            ]
        )
        client = ConfluenceCloudClient(
            base_url="https://acme.atlassian.net",
            email="user@example.com",
            api_token="token",
            default_space_key="AGC",
            default_top_k=2,
            opener=opener,
        )

        pages = client.search(
            ConfluenceSearchRequest(
                query="orquestacion pagos decisiones internas",
            )
        )

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page_id, "123")
        self.assertEqual(pages[0].space_key, "AGC")
        self.assertEqual(pages[0].title, "Decision de Orquestacion")
        self.assertIn("Se acordo centralizar pagos.", pages[0].content)
        self.assertIn("cql=", opener.requests[0].full_url)
        self.assertIn('space+%3D+%22AGC%22', opener.requests[0].full_url)


if __name__ == "__main__":
    unittest.main()
