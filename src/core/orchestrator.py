from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol
import unicodedata

from src.core.config import Settings, settings
from src.core.llm_client import (
    AzureOpenAILLMClient,
    LLMGenerationRequest,
)
from src.core.routing import (
    LLMQueryRouter,
    QueryRouter,
    RetrievalStrategy,
    RoutingDecision,
)
from src.integrations.confluence_client import (
    ConfluenceClient,
    ConfluenceCloudClient,
    ConfluencePage,
    ConfluenceSearchRequest,
)
from src.rag.retriever import AzureSearchRetriever, RetrievalRequest
from src.rag.vector_store import SearchChunk
from src.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class QuerySource:
    """Normalized source returned to the API layer."""

    source_id: str
    source_type: str
    title: str
    score: float
    knowledge_domain: str | None = None


@dataclass(frozen=True)
class ConversationContextTurn:
    """Recent conversation turn recovered for continuity."""

    user_query: str
    assistant_answer: str
    created_at: str | None = None


@dataclass(frozen=True)
class QueryOrchestrationRequest:
    """Stable input contract for the basic query orchestration flow."""

    query: str
    trace_id: str
    conversation_history: list[ConversationContextTurn] | None = None


@dataclass(frozen=True)
class QueryOrchestrationResult:
    """Stable output contract for the basic query orchestration flow."""

    answer: str
    sources: list[QuerySource]
    tokens_used: int


@dataclass(frozen=True)
class ContextChunk:
    """Normalized chunk from any retrieval strategy before final prompting."""

    source_id: str
    source_type: str
    title: str
    content: str
    score: float
    source_url: str | None = None
    document_name: str | None = None
    knowledge_domain: str | None = None


class ContextStrength(str, Enum):
    """Strength of the retrieved evidence with respect to the query."""

    STRONG = "strong"
    PARTIAL = "partial"


class ScopeDecision(str, Enum):
    """Routing decision produced by the local scope classifier."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class ScopeAssessment:
    """Result of the low-cost local scope assessment."""

    decision: ScopeDecision
    reason: str


class QueryScopeClassifier(Protocol):
    """Abstraction for deciding whether a query is in scope for the copilot."""

    def assess(self, query: str) -> ScopeAssessment:
        """Return a low-cost routing assessment for the incoming query."""


class KeywordQueryScopeClassifier:
    """Low-cost fallback classifier based on positive and negative domain hints."""

    _POSITIVE_HINTS = (
        "arquitect",
        "soluci",
        "gobierno",
        "building block",
        "building blocks",
        "patr",
        "lineamiento",
        "bian",
        "api",
        "integraci",
        "dominio de servicio",
        "service domain",
        "microserv",
        "seguridad",
        "autentic",
        "autoriz",
        "canal",
        "orquest",
        "servicio",
        "capabilidad",
        "capability",
        "decision interna",
        "acuerdo interno",
        "confluence",
        "documentacion interna",
    )
    _NEGATIVE_HINTS = (
        "clima",
        "temperatura",
        "pronostico",
        "lluvia",
        "hora",
        "fecha",
        "cumpleanos",
        "receta",
        "cocina",
        "futbol",
        "partido",
        "deporte",
        "noticias",
        "noticias generales",
        "farandula",
        "pelicula",
        "musica",
        "trafico",
    )

    def assess(self, query: str) -> ScopeAssessment:
        normalized_query = self._normalize_text(query)
        positive_matches = [
            hint for hint in self._POSITIVE_HINTS if hint in normalized_query
        ]
        negative_matches = [
            hint for hint in self._NEGATIVE_HINTS if hint in normalized_query
        ]

        if negative_matches and not positive_matches:
            return ScopeAssessment(
                decision=ScopeDecision.OUT_OF_SCOPE,
                reason=f"negative_hints={','.join(negative_matches)}",
            )

        if positive_matches:
            return ScopeAssessment(
                decision=ScopeDecision.IN_SCOPE,
                reason=f"positive_hints={','.join(positive_matches)}",
            )

        return ScopeAssessment(
            decision=ScopeDecision.AMBIGUOUS,
            reason="no_local_scope_hints",
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", ascii_only).strip().lower()


class BasicQueryOrchestrator:
    """Grounded query orchestrator with low-cost scope filter and runtime routing."""

    OUT_OF_SCOPE_MESSAGE = (
        "La consulta se encuentra fuera del alcance del Architecture Governance Copilot."
    )
    INSUFFICIENT_CONTEXT_MESSAGE = (
        "No cuento con suficiente contexto confiable para emitir una recomendacion fundamentada."
    )

    def __init__(
        self,
        *,
        retriever: AzureSearchRetriever,
        llm_client: AzureOpenAILLMClient,
        confluence_client: ConfluenceClient | None = None,
        query_router: QueryRouter | None = None,
        scope_classifier: QueryScopeClassifier | None = None,
        precheck_top_k: int,
        precheck_score_threshold: float,
    ) -> None:
        self._retriever = retriever
        self._llm_client = llm_client
        self._confluence_client = confluence_client
        self._query_router = query_router or LLMQueryRouter(
            llm_client=llm_client,
            temperature=0.0,
            max_tokens=160,
        )
        self._scope_classifier = scope_classifier or KeywordQueryScopeClassifier()
        # Kept only for constructor/settings backward compatibility.
        # Runtime routing no longer uses semantic precheck thresholds after T34A/T34B.
        self._precheck_top_k = precheck_top_k
        self._precheck_score_threshold = precheck_score_threshold

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "BasicQueryOrchestrator":
        return cls(
            retriever=AzureSearchRetriever.from_settings(app_settings),
            llm_client=AzureOpenAILLMClient.from_settings(app_settings),
            confluence_client=ConfluenceCloudClient.from_settings(app_settings),
            query_router=LLMQueryRouter.from_settings(app_settings),
            precheck_top_k=app_settings.AZURE_SEARCH_PRECHECK_TOP_K,
            precheck_score_threshold=app_settings.AZURE_SEARCH_PRECHECK_SCORE_THRESHOLD,
        )

    def answer(self, request: QueryOrchestrationRequest) -> QueryOrchestrationResult:
        logger.info(
            "Query orchestration started. trace_id=%s query_preview=%s",
            request.trace_id,
            _preview_text(request.query),
        )
        scope_assessment = self._scope_classifier.assess(request.query)
        logger.info(
            "Cheap scope filter result. trace_id=%s decision=%s reason=%s",
            request.trace_id,
            scope_assessment.decision.value,
            scope_assessment.reason,
        )
        if scope_assessment.decision is ScopeDecision.OUT_OF_SCOPE:
            logger.info(
                "Query rejected by cheap scope filter. trace_id=%s",
                request.trace_id,
            )
            return QueryOrchestrationResult(
                answer=self._build_out_of_scope_answer(),
                sources=[],
                tokens_used=0,
            )

        routing_decision = self._query_router.route(request.query)
        logger.info(
            "Routing decision accepted. trace_id=%s strategy=%s reason=%s confluence_query=%s space_key=%s router_tokens=%s",
            request.trace_id,
            routing_decision.strategy.value,
            routing_decision.reason,
            routing_decision.confluence_query,
            routing_decision.space_key,
            routing_decision.tokens_used,
        )
        if routing_decision.strategy is RetrievalStrategy.OUT_OF_SCOPE:
            logger.info(
                "Query marked out of scope by LLM router. trace_id=%s",
                request.trace_id,
            )
            return QueryOrchestrationResult(
                answer=self._build_out_of_scope_answer(),
                sources=[],
                tokens_used=routing_decision.tokens_used,
            )

        context_chunks = self._collect_context(request.query, routing_decision, request.trace_id)
        sources = self._build_sources(context_chunks)
        logger.info(
            "Context collection finished. trace_id=%s chunks=%s deduped_sources=%s",
            request.trace_id,
            len(context_chunks),
            len(sources),
        )

        if not context_chunks:
            logger.warning(
                "Query finished with insufficient context. trace_id=%s strategy=%s",
                request.trace_id,
                routing_decision.strategy.value,
            )
            return QueryOrchestrationResult(
                answer=self._build_insufficient_context_answer(),
                sources=[],
                tokens_used=routing_decision.tokens_used,
            )

        context_block = self._build_context_block(context_chunks)
        context_strength = self._assess_context_strength(context_chunks)
        logger.info(
            "Final answer generation starting. trace_id=%s context_strength=%s context_chars=%s",
            request.trace_id,
            context_strength.value,
            len(context_block),
        )
        llm_result = self._llm_client.generate_answer(
            LLMGenerationRequest(
                system_prompt=self._build_system_prompt(),
                user_prompt=self._build_user_prompt(
                    query=request.query,
                    trace_id=request.trace_id,
                    context_block=context_block,
                    sources=sources,
                    context_strength=context_strength,
                    conversation_history=request.conversation_history or [],
                ),
                temperature=0.0,
                max_tokens=900,
            )
        )
        guarded_answer = self._apply_output_guardrails(
            llm_result.answer,
            trace_id=request.trace_id,
        )
        result = QueryOrchestrationResult(
            answer=guarded_answer,
            sources=sources,
            tokens_used=routing_decision.tokens_used + llm_result.tokens_used,
        )
        logger.info(
            "Query orchestration completed. trace_id=%s final_tokens=%s sources=%s",
            request.trace_id,
            result.tokens_used,
            len(result.sources),
        )
        return result

    def _collect_context(
        self,
        query: str,
        routing_decision: RoutingDecision,
        trace_id: str,
    ) -> list[ContextChunk]:
        context_chunks: list[ContextChunk] = []

        if routing_decision.strategy in (
            RetrievalStrategy.RAG_ONLY,
            RetrievalStrategy.BOTH,
        ):
            logger.info(
                "RAG retrieval started. trace_id=%s query_preview=%s",
                trace_id,
                _preview_text(query),
            )
            rag_chunks = self._retriever.retrieve(RetrievalRequest(query=query))
            logger.info(
                "RAG retrieval completed. trace_id=%s chunks=%s",
                trace_id,
                len(rag_chunks),
            )
            if rag_chunks:
                logger.info(
                    "RAG top results. trace_id=%s items=%s",
                    trace_id,
                    _preview_rag_chunks(rag_chunks),
                )
            context_chunks.extend(self._from_rag_chunks(rag_chunks))

        if routing_decision.strategy in (
            RetrievalStrategy.CONFLUENCE_ONLY,
            RetrievalStrategy.BOTH,
        ):
            if self._confluence_client is None:
                raise ValueError(
                    "Confluence client is required for CONFLUENCE_ONLY or BOTH routing strategies."
                )

            effective_query = routing_decision.confluence_query or query
            logger.info(
                "Confluence retrieval started. trace_id=%s query=%s space_key=%s",
                trace_id,
                effective_query,
                routing_decision.space_key,
            )
            confluence_pages = self._confluence_client.search(
                ConfluenceSearchRequest(
                    query=effective_query,
                    space_key=routing_decision.space_key,
                )
            )
            logger.info(
                "Confluence retrieval completed. trace_id=%s pages=%s",
                trace_id,
                len(confluence_pages),
            )
            if confluence_pages:
                logger.info(
                    "Confluence top results. trace_id=%s items=%s",
                    trace_id,
                    _preview_confluence_pages(confluence_pages),
                )
            context_chunks.extend(self._from_confluence_pages(confluence_pages))

        return context_chunks

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "Eres un copiloto experto en gobierno de arquitectura de soluciones para una "
            "organizacion del sector financiero.\n\n"
            "Tu funcion es analizar casos de uso y escenarios de negocio descritos en "
            "lenguaje natural, para asistir al equipo de arquitectura en la revision "
            "conceptual de propuestas de solucion.\n\n"
            "Debes apoyarte unicamente en el contexto recuperado por el sistema. Ese contexto "
            "puede provenir del corpus indexado en Azure AI Search y/o de paginas internas de Confluence.\n\n"
            "OBJETIVO DE LA RESPUESTA\n"
            "Debes ayudar a identificar:\n"
            "1. posibles building blocks reutilizables,\n"
            "2. lineamientos o patrones aplicables,\n"
            "3. posibles alineamientos con service domains de BIAN,\n"
            "4. observaciones y recomendaciones arquitectonicas.\n\n"
            "RESTRICCIONES\n"
            "- No inventes informacion.\n"
            "- No asumas decisiones no sustentadas por el contexto disponible.\n"
            "- Si no existe suficiente informacion, indicalo explicitamente.\n"
            "- Distingue cuando una conclusion proviene de lineamientos institucionales versus acuerdos internos recientes.\n"
            "- No proporciones detalles tecnicos de bajo nivel si no son relevantes para el analisis conceptual.\n"
            "- No expongas informacion sensible.\n\n"
            "MANEJO DE CONSULTAS FUERA DE ALCANCE\n"
            "Si la consulta no corresponde al dominio de arquitectura de soluciones, responde exactamente:\n"
            f"\"{BasicQueryOrchestrator.OUT_OF_SCOPE_MESSAGE}\"\n\n"
            "MANEJO DE FALTA DE CONTEXTO\n"
            "Si no existe suficiente informacion, responde exactamente:\n"
            f"\"{BasicQueryOrchestrator.INSUFFICIENT_CONTEXT_MESSAGE}\"\n\n"
            "FORMATO DE RESPUESTA\n"
            "Responde siempre en espanol usando Markdown claro con la siguiente estructura exacta:\n"
            "## 1. Resumen del caso\n"
            "## 2. Hallazgos relevantes\n"
            "## 3. Recomendaciones arquitectonicas\n"
            "## 4. Posible alineamiento BIAN\n"
            "## 5. Fuentes consultadas\n\n"
            "Dentro de las secciones 2, 3, 4 y 5 usa listas con vinetas `-` cuando corresponda.\n"
            "ESTILO\n"
            "- Profesional y tecnico\n"
            "- Claro y estructurado\n"
            "- Enfocado en analisis conceptual\n"
            "- Sin contradicciones entre recomendaciones y falta de contexto\n"
        )

    def _build_user_prompt(
        self,
        *,
        query: str,
        trace_id: str,
        context_block: str,
        sources: list[QuerySource],
        context_strength: ContextStrength,
        conversation_history: list[ConversationContextTurn],
    ) -> str:
        source_titles = "\n".join(
            f"- {source.title or source.source_id}"
            for source in sources
        )
        history_block = self._build_conversation_history_block(conversation_history)
        evidence_note = (
            "La evidencia recuperada es suficientemente directa para formular recomendaciones concretas, "
            "siempre que cada punto este sustentado en el contexto."
            if context_strength is ContextStrength.STRONG
            else (
                "La evidencia recuperada es parcial o tangencial. No formules recomendaciones especificas "
                "como si fueran concluyentes. Explica explicitamente que el contexto encontrado es indirecto "
                "o insuficiente para una recomendacion cerrada."
            )
        )
        return (
            f"Trace ID: {trace_id}\n\n"
            "Consulta del usuario:\n"
            f"{query}\n\n"
            "Nivel de confianza del contexto recuperado:\n"
            f"{context_strength.value}\n\n"
            "Interpretacion operativa del nivel de confianza:\n"
            f"{evidence_note}\n\n"
            "Historial conversacional reciente para continuidad:\n"
            f"{history_block}\n\n"
            "Fuentes deduplicadas disponibles para sustento:\n"
            f"{source_titles}\n\n"
            "Contexto recuperado y autorizado para grounding:\n"
            f"{context_block}\n\n"
            "Instrucciones operativas:\n"
            "1. Usa solo el contexto recuperado.\n"
            "2. Usa el historial conversacional solo para resolver referencias del turno actual o mantener continuidad; el historial no reemplaza el grounding.\n"
            "3. Si mencionas building blocks, patrones o referencias BIAN, deben aparecer en el contexto.\n"
            "4. Si mencionas acuerdos internos recientes, deben aparecer en el contexto de Confluence recuperado.\n"
            "5. Si un punto no esta sustentado, indicalo como no confirmado.\n"
            "6. Si el contexto es parcial o tangencial, evita recomendar un patron o building block especifico con falsa certeza.\n"
            "7. En \"Fuentes consultadas\", cita por titulo las fuentes deduplicadas que realmente sustentan tu respuesta.\n"
            "8. Usa Markdown limpio con encabezados `##` y listas con `-`.\n"
            "9. Manten el formato exacto solicitado en el system prompt."
        )

    @staticmethod
    def _build_context_block(chunks: list[ContextChunk]) -> str:
        sections = []
        for index, chunk in enumerate(chunks, start=1):
            sections.append(
                "\n".join(
                    [
                        f"[Source {index}]",
                        f"source_id: {chunk.source_id or '(unknown)'}",
                        f"title: {chunk.title or '(untitled)'}",
                        f"knowledge_domain: {chunk.knowledge_domain or '(unknown)'}",
                        f"source_type: {chunk.source_type or '(unknown)'}",
                        f"document_name: {chunk.document_name or '(unknown)'}",
                        f"score: {chunk.score:.4f}",
                        f"content: {chunk.content}",
                    ]
                )
            )
        return "\n\n".join(sections)

    @staticmethod
    def _build_conversation_history_block(
        turns: list[ConversationContextTurn],
    ) -> str:
        if not turns:
            return "- Sin historial previo recuperado para esta sesion."

        sections = []
        for index, turn in enumerate(turns, start=1):
            created_at = (turn.created_at or "").strip() or "(unknown)"
            sections.append(
                "\n".join(
                    [
                        f"[Turno previo {index}]",
                        f"created_at: {created_at}",
                        f"user_query: {turn.user_query}",
                        f"assistant_answer: {turn.assistant_answer}",
                    ]
                )
            )
        return "\n\n".join(sections)

    @classmethod
    def _build_out_of_scope_answer(cls) -> str:
        return cls.OUT_OF_SCOPE_MESSAGE

    @classmethod
    def _build_insufficient_context_answer(cls) -> str:
        return "\n\n".join(
            [
                "## 1. Resumen del caso",
                cls.INSUFFICIENT_CONTEXT_MESSAGE,
                "## 2. Hallazgos relevantes",
                "- No se recuperaron fragmentos confiables desde las fuentes disponibles para sustentar la consulta.",
                "## 3. Recomendaciones arquitectonicas",
                "- Reformular la consulta con mas contexto de negocio o arquitectura.",
                "- Indicar building blocks, capability domains, decisiones internas o service domains esperados si se conocen.",
                "## 4. Posible alineamiento BIAN",
                "- No es posible proponer un alineamiento BIAN sustentado con la evidencia recuperada.",
                "## 5. Fuentes consultadas",
                "- No se encontraron fuentes relevantes en el contexto recuperado.",
            ]
        )

    @classmethod
    def _apply_output_guardrails(cls, answer: str, *, trace_id: str) -> str:
        normalized_answer = answer.strip()
        if not normalized_answer:
            logger.warning(
                "Output guardrail triggered: empty final answer. trace_id=%s",
                trace_id,
            )
            return cls._build_insufficient_context_answer()

        if any(character.isalnum() for character in normalized_answer):
            return normalized_answer

        logger.warning(
            "Output guardrail triggered: non-textual final answer. trace_id=%s answer_preview=%s",
            trace_id,
            _preview_text(normalized_answer),
        )
        return cls._build_insufficient_context_answer()

    @staticmethod
    def _assess_context_strength(chunks: list[ContextChunk]) -> ContextStrength:
        top_score = max(chunk.score for chunk in chunks)
        return ContextStrength.STRONG if top_score >= 0.72 else ContextStrength.PARTIAL

    @staticmethod
    def _build_sources(chunks: list[ContextChunk]) -> list[QuerySource]:
        deduped: dict[tuple[str, str, str], QuerySource] = {}
        for chunk in chunks:
            title = (chunk.title or "").strip()
            document_name = (chunk.document_name or "").strip()
            fallback_key = (chunk.source_id or "").strip()
            if title or document_name:
                dedupe_key = (
                    title.lower(),
                    document_name.lower(),
                    "",
                )
            else:
                dedupe_key = ("", "", fallback_key.lower())
            candidate = QuerySource(
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                title=title or document_name or chunk.source_id,
                score=chunk.score,
                knowledge_domain=chunk.knowledge_domain,
            )
            current = deduped.get(dedupe_key)
            if current is None or candidate.score > current.score:
                deduped[dedupe_key] = candidate

        return sorted(
            deduped.values(),
            key=lambda source: source.score,
            reverse=True,
        )

    @staticmethod
    def _from_rag_chunks(chunks: list[SearchChunk]) -> list[ContextChunk]:
        return [
            ContextChunk(
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                title=chunk.title or chunk.document_name or chunk.source_id,
                content=chunk.content,
                score=chunk.score,
                source_url=chunk.source_url,
                document_name=chunk.document_name,
                knowledge_domain=chunk.knowledge_domain,
            )
            for chunk in chunks
        ]

    @staticmethod
    def _from_confluence_pages(pages: list[ConfluencePage]) -> list[ContextChunk]:
        return [
            ContextChunk(
                source_id=page.page_id,
                source_type="confluence_page",
                title=page.title,
                content=page.content,
                score=page.score,
                source_url=page.url,
                document_name=page.title,
                knowledge_domain=(
                    f"confluence:{page.space_key.lower()}"
                    if page.space_key
                    else "confluence"
                ),
            )
            for page in pages
        ]


def _preview_text(value: str, limit: int = 120) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _preview_rag_chunks(chunks: list[SearchChunk], limit: int = 3) -> str:
    previews = []
    for chunk in chunks[:limit]:
        previews.append(
            f"{chunk.title or chunk.document_name or chunk.source_id} (score={chunk.score:.4f}, domain={chunk.knowledge_domain or 'n/a'})"
        )
    return " | ".join(previews)


def _preview_confluence_pages(pages: list[ConfluencePage], limit: int = 3) -> str:
    previews = []
    for page in pages[:limit]:
        previews.append(
            f"{page.title} (score={page.score:.4f}, space={page.space_key or 'n/a'})"
        )
    return " | ".join(previews)
