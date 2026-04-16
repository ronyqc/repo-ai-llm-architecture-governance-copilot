from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.core.llm_client import LLMGenerationResult
from src.core.orchestrator import BasicQueryOrchestrator, QueryOrchestrationRequest
from src.rag.vector_store import SearchChunk


class BasicQueryOrchestratorTests(unittest.TestCase):
    def test_answer_retrieves_context_builds_sources_and_returns_llm_output(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = [
            SearchChunk(
                source_id="doc-1",
                source_type="pdf",
                title="Architecture Guide",
                content="Use a centralized authentication gateway.",
                score=0.87,
                knowledge_domain="building_blocks",
                source_url="https://example.com/doc-1",
                document_name="guide.pdf",
                chunk_order=1,
                metadata=None,
                chunk_id="guide#1",
                updated_at="2026-04-16T00:00:00Z",
            )
        ]
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="Se recomienda un gateway de autenticacion centralizado.",
            tokens_used=210,
            finish_reason="stop",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Que se recomienda para autenticacion?",
                trace_id="trace-123",
            )
        )

        self.assertEqual(
            result.answer,
            "Se recomienda un gateway de autenticacion centralizado.",
        )
        self.assertEqual(result.tokens_used, 210)
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0].source_id, "doc-1")
        llm_client.generate_answer.assert_called_once()
        prompt = llm_client.generate_answer.call_args.args[0].user_prompt
        self.assertIn("Trace ID: trace-123", prompt)
        self.assertIn("Use a centralized authentication gateway.", prompt)

    def test_answer_handles_empty_context(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = []
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="No hay suficiente contexto recuperado.",
            tokens_used=55,
            finish_reason="stop",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Que recomienda BIAN?",
                trace_id="trace-empty",
            )
        )

        self.assertEqual(result.answer, "No hay suficiente contexto recuperado.")
        self.assertEqual(result.sources, [])
        prompt = llm_client.generate_answer.call_args.args[0].user_prompt
        self.assertIn("No relevant knowledge chunks were retrieved", prompt)


if __name__ == "__main__":
    unittest.main()
