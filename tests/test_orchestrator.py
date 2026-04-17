from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.core.llm_client import LLMGenerationResult
from src.core.orchestrator import (
    BasicQueryOrchestrator,
    QueryOrchestrationRequest,
    QueryScopeClassifier,
    ScopeAssessment,
    ScopeDecision,
)
from src.rag.vector_store import SearchChunk


class BasicQueryOrchestratorTests(unittest.TestCase):
    def test_answer_retrieves_context_builds_sources_and_returns_llm_output(self) -> None:
        retriever = Mock()
        precheck_chunk = SearchChunk(
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
        retriever.retrieve.side_effect = [[precheck_chunk], [
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
        ]]
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="Se recomienda un gateway de autenticacion centralizado.",
            tokens_used=210,
            finish_reason="stop",
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=autentic",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
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
        self.assertEqual(retriever.retrieve.call_count, 2)
        precheck_request = retriever.retrieve.call_args_list[0].args[0]
        full_request = retriever.retrieve.call_args_list[1].args[0]
        self.assertEqual(precheck_request.top_k, 1)
        self.assertEqual(precheck_request.score_threshold, 0.6)
        self.assertIsNone(full_request.top_k)
        system_prompt = llm_client.generate_answer.call_args.args[0].system_prompt
        prompt = llm_client.generate_answer.call_args.args[0].user_prompt
        self.assertIn("gobierno de arquitectura de soluciones", system_prompt)
        self.assertIn("## 1. Resumen del caso", system_prompt)
        self.assertIn("Trace ID: trace-123", prompt)
        self.assertIn("Use a centralized authentication gateway.", prompt)
        self.assertIn("Contexto recuperado y autorizado para grounding", prompt)
        self.assertIn("Fuentes deduplicadas disponibles para sustento", prompt)
        self.assertIn("strong", prompt)

    def test_answer_returns_structured_fallback_without_llm_when_precheck_fails_for_in_scope_query(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = []
        llm_client = Mock()
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=bian",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Que recomienda BIAN?",
                trace_id="trace-empty",
            )
        )

        self.assertIn(
            "No cuento con suficiente contexto confiable para emitir una recomendación fundamentada.",
            result.answer,
        )
        self.assertIn("## 1. Resumen del caso", result.answer)
        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 0)
        llm_client.generate_answer.assert_not_called()
        retriever.retrieve.assert_called_once()

    def test_answer_returns_out_of_scope_message_without_retrieval_or_llm_call(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.OUT_OF_SCOPE,
            reason="negative_hints=clima",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Cual es el clima en Lima hoy?",
                trace_id="trace-out-of-scope",
            )
        )

        self.assertEqual(
            result.answer,
            "La consulta se encuentra fuera del alcance del Architecture Governance Copilot.",
        )
        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 0)
        retriever.retrieve.assert_not_called()
        llm_client.generate_answer.assert_not_called()

    def test_answer_returns_out_of_scope_when_query_is_ambiguous_and_precheck_fails(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = []
        llm_client = Mock()
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.AMBIGUOUS,
            reason="no_local_scope_hints",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Que patron aplicaria para esto?",
                trace_id="trace-ambiguous",
            )
        )

        self.assertEqual(
            result.answer,
            "La consulta se encuentra fuera del alcance del Architecture Governance Copilot.",
        )
        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 0)
        retriever.retrieve.assert_called_once()
        llm_client.generate_answer.assert_not_called()

    def test_answer_deduplicates_sources_by_title_and_document_name(self) -> None:
        retriever = Mock()
        precheck_chunk = SearchChunk(
            source_id="doc-1",
            source_type="pdf",
            title="Authentication Gateway",
            content="Centralize authentication.",
            score=0.75,
            knowledge_domain="building_blocks",
            source_url=None,
            document_name="auth-gateway.pdf",
            chunk_order=1,
            metadata=None,
            chunk_id="doc-1#1",
            updated_at=None,
        )
        retriever.retrieve.side_effect = [[precheck_chunk], [
            precheck_chunk,
            SearchChunk(
                source_id="doc-2",
                source_type="pdf",
                title="Authentication Gateway",
                content="Validate tokens.",
                score=0.82,
                knowledge_domain="building_blocks",
                source_url=None,
                document_name="auth-gateway.pdf",
                chunk_order=2,
                metadata=None,
                chunk_id="doc-2#2",
                updated_at=None,
            ),
            SearchChunk(
                source_id="doc-3",
                source_type="wiki",
                title="API Governance Guideline",
                content="Document APIs.",
                score=0.79,
                knowledge_domain="guidelines_patterns",
                source_url=None,
                document_name="api-governance.md",
                chunk_order=1,
                metadata=None,
                chunk_id="doc-3#1",
                updated_at=None,
            ),
        ]]
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="## 1. Resumen del caso\n\nTexto",
            tokens_used=180,
            finish_reason="stop",
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=autentic",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Que building blocks aplicar para autenticacion?",
                trace_id="trace-dedupe",
            )
        )

        self.assertEqual(len(result.sources), 2)
        self.assertEqual(result.sources[0].title, "Authentication Gateway")
        self.assertEqual(result.sources[0].score, 0.82)
        self.assertEqual(result.sources[1].title, "API Governance Guideline")


if __name__ == "__main__":
    unittest.main()
