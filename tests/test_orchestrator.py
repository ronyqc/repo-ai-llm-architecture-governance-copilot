from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.core.llm_client import LLMGenerationResult
from src.core.orchestrator import (
    BasicQueryOrchestrator,
    ConversationContextTurn,
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
from src.integrations.confluence_client import ConfluencePage
from src.rag.vector_store import SearchChunk


class BasicQueryOrchestratorTests(unittest.TestCase):
    def test_answer_retrieves_rag_context_and_returns_llm_output(self) -> None:
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
            confluence_client=Mock(),
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
        self.assertIn("Azure AI Search y/o de paginas internas de Confluence", system_prompt)
        self.assertIn("Trace ID: trace-123", prompt)
        self.assertIn("Use a centralized authentication gateway.", prompt)

    def test_answer_includes_recent_conversation_history_in_final_prompt(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = [
            SearchChunk(
                source_id="doc-1",
                source_type="pdf",
                title="Architecture Guide",
                content="Use a centralized authentication gateway.",
                score=0.87,
                knowledge_domain="building_blocks",
                source_url=None,
                document_name="guide.pdf",
                chunk_order=1,
                metadata=None,
                chunk_id="guide#1",
                updated_at=None,
            )
        ]
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="## 1. Resumen del caso\n\nRespuesta con continuidad.",
            tokens_used=120,
            finish_reason="stop",
        )
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.RAG_ONLY,
            reason="La consulta busca building blocks del corpus indexado.",
            tokens_used=21,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=autentic",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            confluence_client=Mock(),
            query_router=query_router,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        orchestrator.answer(
            QueryOrchestrationRequest(
                query="Y para autorizacion?",
                trace_id="trace-history",
                conversation_history=[
                    ConversationContextTurn(
                        user_query="Que building blocks aplican para autenticacion?",
                        assistant_answer="Se recomienda un gateway centralizado.",
                        created_at="2026-04-20T12:00:00Z",
                    )
                ],
            )
        )

        prompt = llm_client.generate_answer.call_args.args[0].user_prompt
        self.assertIn("Historial conversacional reciente para continuidad", prompt)
        self.assertIn("Que building blocks aplican para autenticacion?", prompt)
        self.assertIn("Se recomienda un gateway centralizado.", prompt)

    def test_answer_returns_structured_fallback_without_final_llm_when_no_context_is_found(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = []
        confluence_client = Mock()
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
            confluence_client=confluence_client,
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
        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 22)
        llm_client.generate_answer.assert_not_called()
        retriever.retrieve.assert_called_once()
        confluence_client.search.assert_not_called()

    def test_answer_returns_out_of_scope_message_without_router_retrieval_or_llm_call(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        confluence_client = Mock()
        query_router = Mock(spec=QueryRouter)
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.OUT_OF_SCOPE,
            reason="negative_hints=clima",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            confluence_client=confluence_client,
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
        confluence_client.search.assert_not_called()
        llm_client.generate_answer.assert_not_called()

    def test_answer_returns_out_of_scope_when_router_marks_query_out_of_scope(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        confluence_client = Mock()
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
            confluence_client=confluence_client,
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

        self.assertEqual(result.sources, [])
        self.assertEqual(result.tokens_used, 17)
        query_router.route.assert_called_once()
        retriever.retrieve.assert_not_called()
        confluence_client.search.assert_not_called()
        llm_client.generate_answer.assert_not_called()

    def test_answer_uses_confluence_only_when_router_requests_it(self) -> None:
        retriever = Mock()
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="## 1. Resumen del caso\n\nSe identifico una decision interna reciente.",
            tokens_used=120,
            finish_reason="stop",
        )
        confluence_client = Mock()
        confluence_client.search.return_value = [
            ConfluencePage(
                page_id="123",
                title="Decision de Orquestacion de Pagos",
                content="El equipo acuerdo centralizar la orquestacion de pagos en un servicio dedicado.",
                url="https://acme.atlassian.net/wiki/spaces/AGC/pages/123",
                space_key="AGC",
                score=1.0,
            )
        ]
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.CONFLUENCE_ONLY,
            reason="La consulta apunta a decisiones internas recientes.",
            confluence_query="orquestacion de pagos decisiones internas",
            space_key="AGC",
            tokens_used=18,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.AMBIGUOUS,
            reason="no_local_scope_hints",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            confluence_client=confluence_client,
            query_router=query_router,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Existe alguna decision interna reciente sobre orquestacion de pagos?",
                trace_id="trace-confluence",
            )
        )

        self.assertIn("decision interna reciente", result.answer.lower())
        self.assertEqual(result.tokens_used, 138)
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0].source_type, "confluence_page")
        retriever.retrieve.assert_not_called()
        confluence_client.search.assert_called_once()
        self.assertEqual(
            confluence_client.search.call_args.args[0].query,
            "orquestacion de pagos decisiones internas",
        )
        self.assertEqual(
            confluence_client.search.call_args.args[0].space_key,
            "AGC",
        )
        user_prompt = llm_client.generate_answer.call_args.args[0].user_prompt
        self.assertIn("Decision de Orquestacion de Pagos", user_prompt)
        self.assertIn("Confluence", llm_client.generate_answer.call_args.args[0].system_prompt)

    def test_answer_combines_rag_and_confluence_when_router_requests_both(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = [
            SearchChunk(
                source_id="doc-1",
                source_type="pdf",
                title="Institutional Guideline",
                content="Aplicar un gateway de autenticacion centralizado.",
                score=0.86,
                knowledge_domain="guidelines_patterns",
                source_url=None,
                document_name="guideline.pdf",
                chunk_order=1,
                metadata=None,
                chunk_id="guide#1",
                updated_at=None,
            )
        ]
        confluence_client = Mock()
        confluence_client.search.return_value = [
            ConfluencePage(
                page_id="456",
                title="Acuerdo Interno Integraciones",
                content="El equipo acordo reutilizar el gateway institucional para este escenario.",
                url="https://acme.atlassian.net/wiki/spaces/AGC/pages/456",
                space_key="AGC",
                score=0.9,
            )
        ]
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="## 1. Resumen del caso\n\nSe consolidaron lineamientos institucionales y acuerdos internos.",
            tokens_used=140,
            finish_reason="stop",
        )
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.BOTH,
            reason="La consulta combina lineamientos institucionales y acuerdos internos recientes.",
            confluence_query="acuerdos internos integraciones recientes",
            space_key="AGC",
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
            confluence_client=confluence_client,
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

        self.assertIn("consolidaron", result.answer.lower())
        self.assertEqual(result.tokens_used, 164)
        self.assertEqual(len(result.sources), 2)
        retriever.retrieve.assert_called_once()
        confluence_client.search.assert_called_once()
        user_prompt = llm_client.generate_answer.call_args.args[0].user_prompt
        self.assertIn("Institutional Guideline", user_prompt)
        self.assertIn("Acuerdo Interno Integraciones", user_prompt)

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
            confluence_client=Mock(),
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

    def test_answer_uses_safe_fallback_when_final_llm_output_is_empty(self) -> None:
        retriever = Mock()
        retriever.retrieve.return_value = [
            SearchChunk(
                source_id="doc-1",
                source_type="pdf",
                title="Architecture Guide",
                content="Use a centralized authentication gateway.",
                score=0.87,
                knowledge_domain="building_blocks",
                source_url=None,
                document_name="guide.pdf",
                chunk_order=1,
                metadata=None,
                chunk_id="guide#1",
                updated_at=None,
            )
        ]
        llm_client = Mock()
        llm_client.generate_answer.return_value = LLMGenerationResult(
            answer="   ",
            tokens_used=120,
            finish_reason="stop",
        )
        query_router = Mock(spec=QueryRouter)
        query_router.route.return_value = RoutingDecision(
            strategy=RetrievalStrategy.RAG_ONLY,
            reason="La consulta busca building blocks del corpus indexado.",
            tokens_used=18,
        )
        scope_classifier = Mock(spec=QueryScopeClassifier)
        scope_classifier.assess.return_value = ScopeAssessment(
            decision=ScopeDecision.IN_SCOPE,
            reason="positive_hints=autentic",
        )

        orchestrator = BasicQueryOrchestrator(
            retriever=retriever,
            llm_client=llm_client,
            confluence_client=Mock(),
            query_router=query_router,
            scope_classifier=scope_classifier,
            precheck_top_k=1,
            precheck_score_threshold=0.6,
        )

        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query="Que se recomienda para autenticacion?",
                trace_id="trace-empty-output",
            )
        )

        self.assertIn(
            "No cuento con suficiente contexto confiable para emitir una recomendacion fundamentada.",
            result.answer,
        )
        self.assertEqual(result.tokens_used, 138)


if __name__ == "__main__":
    unittest.main()
