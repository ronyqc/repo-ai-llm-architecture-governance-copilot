from __future__ import annotations

import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import get_query_orchestrator
from src.core.orchestrator import (
    QueryOrchestrationResult,
    QuerySource,
)
from src.security.auth import AuthenticatedUser, require_authenticated_user


class QueryEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        default_orchestrator = Mock()
        default_orchestrator.answer.return_value = QueryOrchestrationResult(
            answer="Respuesta por defecto",
            sources=[],
            tokens_used=0,
        )

        app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
            user_id="test-user",
            roles=["user"],
            claims={},
        )
        app.dependency_overrides[get_query_orchestrator] = lambda: default_orchestrator

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_query_endpoint_returns_structured_response(self) -> None:
        orchestrator = Mock()
        orchestrator.answer.return_value = QueryOrchestrationResult(
            answer="Respuesta basada en contexto",
            sources=[
                QuerySource(
                    source_id="doc-1",
                    source_type="pdf",
                    title="Architecture Guide",
                    score=0.93,
                )
            ],
            tokens_used=321,
        )
        app.dependency_overrides[get_query_orchestrator] = lambda: orchestrator

        response = self.client.post(
            "/api/v1/query",
            json={
                "query": "Que building blocks aplican para autenticacion?",
                "stream": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], "Respuesta basada en contexto")
        self.assertEqual(body["tokens_used"], 321)
        self.assertEqual(len(body["sources"]), 1)
        self.assertEqual(body["sources"][0]["source_id"], "doc-1")
        self.assertTrue(body["trace_id"])
        self.assertTrue(body["session_id"])

    def test_query_endpoint_rejects_streaming_for_now(self) -> None:
        response = self.client.post(
            "/api/v1/query",
            json={
                "query": "Que building blocks aplican para autenticacion?",
                "stream": True,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Streaming is not supported in the current /query implementation.",
        )

    def test_query_endpoint_requires_authentication(self) -> None:
        app.dependency_overrides.pop(require_authenticated_user, None)

        response = self.client.post(
            "/api/v1/query",
            json={"query": "Que building blocks aplican para autenticacion?"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Authorization token is required.",
        )


if __name__ == "__main__":
    unittest.main()
