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
from src.core.routing import (
    QueryRouter,
    RetrievalStrategy,
    RoutingDecision,
)
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
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.RAG_ONLY,
            reason="La consulta busca building blocks del corpus indexado.",
            tokens_used=31,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=autentic",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            query_router=query_router,
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
        self.assertEqual(result.tokens_used, 241)
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0].source_id, "doc-1")
        query_router.route.assert_called_once_with("Que se recomienda para autenticacion?")
        llm_client.generate_answer.assert_called_once()
        retriever.retrieve.assert_called_once()
        full_request = retriever.retrieve.call_args.args[0]
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

    def test_answer_returns_structured_fallback_without_final_llm_when_rag_has_no_results(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = []
        llm_client = Mock()
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.RAG_ONLY,
            reason="La consulta apunta al corpus de arquitectura.",
            tokens_used=22,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=bian",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            query_router=query_router,
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
            "No cuento con suficiente contexto confiable para emitir una recomendacion fundamentada.",
            result.answer,
        )
        self.assertIn("## 1. Resumen del caso", result.answer)
        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 22)
        query_router.route.assert_called_once()
        llm_client.generate_answer.assert_not_called()
        retriever.retrieve.assert_called_once()

    def test_answer_returns_out_of_scope_message_without_router_retrieval_or_llm_call(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        query_router = Mock(spec=QueryRouter)
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.OUT_OF_SCOPE,
            reason="negative_hints=clima",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            query_router=query_router,
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
        query_router.route.assert_not_called()
        retriever.retrieve.assert_not_called()
        llm_client.generate_answer.assert_not_called()

    def test_answer_returns_out_of_scope_when_router_marks_query_out_of_scope(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.OUT_OF_SCOPE,
            reason="La consulta no pertenece al dominio.",
            tokens_used=17,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.AMBIGUOUS,
            reason="no_local_scope_hints",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            query_router=query_router,
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
        self.assertEqual(result.tokens_used, 17)
        query_router.route.assert_called_once()
        retriever.retrieve.assert_not_called()
        llm_client.generate_answer.assert_not_called()

    def test_answer_deduplicates_sources_by_title_and_document_name(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = [
            SearchChunk(
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
            ),
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
        ]
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="## 1. Resumen del caso\n\nTexto",
            tokens_used=180,
            finish_reason="stop",
        )
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.RAG_ONLY,
            reason="La consulta busca building blocks y lineamientos del corpus indexado.",
            tokens_used=28,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=autentic",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            query_router=query_router,
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

    def test_answer_returns_controlled_message_for_confluence_only_strategy(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.CONFLUENCE_ONLY,
            reason="La consulta pide acuerdos internos recientes del equipo.",
            tokens_used=19,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.AMBIGUOUS,
            reason="no_local_scope_hints",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            query_router=query_router,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Existe algun acuerdo interno reciente del equipo sobre esta integracion?",
                trace_id="trace-confluence",
            )
        )

        self.assertIn("CONFLUENCE_ONLY", result.answer)
        self.assertIn("Razon del router", result.answer)
        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 19)
        retriever.retrieve.assert_not_called()
        llm_client.generate_answer.assert_not_called()

    def test_answer_returns_controlled_message_for_both_strategy(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.BOTH,
            reason="La consulta combina lineamientos institucionales y acuerdos internos recientes.",
            tokens_used=24,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=lineamiento,integraci",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            query_router=query_router,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Que lineamientos institucionales y acuerdos internos recientes aplican?",
                trace_id="trace-both",
            )
        )

        self.assertIn("BOTH", result.answer)
        self.assertIn("Confluence", result.answer)
        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 24)
        retriever.retrieve.assert_not_called()
        llm_client.generate_answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
