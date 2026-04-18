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
    def test_route_returns_structured_decision_with_confluence_hints(self) -> None:
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer=(
                '{"strategy":"CONFLUENCE_ONLY","reason":"La consulta apunta a decisiones internas recientes.",'
                '"confluence_query":"orquestacion de pagos decisiones internas","space_key":"AGC"}'
            ),
            tokens_used=14,
            finish_reason="stop",
        )
        router = LLMQueryRouter(
            llm_client=llm_client,
            temperature=0.0,
            max_tokens=120,
        )

        decision = router.route("Existe alguna decision interna reciente sobre orquestacion de pagos?")

        self.assertEqual(decision.strategy, RetrievalStrategy.CONFLUENCE_ONLY)
        self.assertEqual(
            decision.reason,
            "La consulta apunta a decisiones internas recientes.",
        )
        self.assertEqual(
            decision.confluence_query,
            "orquestacion de pagos decisiones internas",
        )
        self.assertEqual(decision.space_key, "AGC")
        self.assertEqual(decision.tokens_used, 14)

    def test_route_raises_when_llm_returns_invalid_json(self) -> None:
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="CONFLUENCE_ONLY",
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
