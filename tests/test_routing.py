from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.core.llm_client import LLMGenerationResult
from src.core.routing import (
    LLMQueryRouter,
    QueryRoutingError,
    RetrievalStrategy,
)


class LLMQueryRouterTests(unittest.TestCase):
    def test_route_returns_structured_decision(self) -> None:
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer='{"strategy":"RAG_ONLY","reason":"La consulta busca building blocks del corpus indexado."}',
            tokens_used=14,
            finish_reason="stop",
        )
        router = LLMQueryRouter(
            llm_client=llm_client,
            temperature=0.0,
            max_tokens=120,
        )

        decision = router.route("Que building blocks aplicar para autenticacion?")

        self.assertEqual(decision.strategy, RetrievalStrategy.RAG_ONLY)
        self.assertEqual(
            decision.reason,
            "La consulta busca building blocks del corpus indexado.",
        )
        self.assertEqual(decision.tokens_used, 14)

    def test_route_raises_when_llm_returns_invalid_json(self) -> None:
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="RAG_ONLY",
            tokens_used=9,
            finish_reason="stop",
        )
        router = LLMQueryRouter(
            llm_client=llm_client,
            temperature=0.0,
            max_tokens=120,
        )

        with self.assertRaises(QueryRoutingError):
            router.route("Que lineamientos aplicar?")


if __name__ == "__main__":
    unittest.main()
