from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol

from src.core.config import Settings, settings
from src.core.llm_client import (
    AzureOpenAILLMClient,
    LLMGenerationRequest,
)
from src.rag.retriever import AzureSearchRetriever, RetrievalRequest
from src.rag.vector_store import SearchChunk


@dataclass(frozen=True)
class QuerySource:
    """Normalized source returned to the API layer."""

    source_id: str
    source_type: str
    title: str
    score: float


@dataclass(frozen=True)
class QueryOrchestrationRequest:
    """Stable input contract for the basic query orchestration flow."""

    query: str
    trace_id: str


@dataclass(frozen=True)
class QueryOrchestrationResult:
    """Stable output contract for the basic query orchestration flow."""

    answer: str
    sources: list[QuerySource]
    tokens_used: int


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
    )
    _NEGATIVE_HINTS = (
        "clima",
        "temperatura",
        "pronostico",
        "pronóstico",
        "lluvia",
        "hora",
        "fecha",
        "cumpleaños",
        "cumpleanos",
        "cumpleaños",
        "receta",
        "cocina",
        "futbol",
        "fútbol",
        "partido",
        "deporte",
        "noticias",
        "farandula",
        "farándula",
        "pelicula",
        "película",
        "musica",
        "música",
        "trafico",
        "tráfico",
    )

    def assess(self, query: str) -> ScopeAssessment:
        normalized_query = re.sub(r"\s+", " ", query).strip().lower()
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


class BasicQueryOrchestrator:
    """Grounded query orchestrator for T34 final answer generation."""

    OUT_OF_SCOPE_MESSAGE = (
        "La consulta se encuentra fuera del alcance del Architecture Governance Copilot."
    )
    INSUFFICIENT_CONTEXT_MESSAGE = (
        "No cuento con suficiente contexto confiable para emitir una recomendación fundamentada."
    )

    def __init__(
        self,
        *,
        retriever: AzureSearchRetriever,
        llm_client: AzureOpenAILLMClient,
        scope_classifier: QueryScopeClassifier | None = None,
        precheck_top_k: int,
        precheck_score_threshold: float,
    ) -> None:
        self._retriever = retriever
        self._llm_client = llm_client
        self._scope_classifier = scope_classifier or KeywordQueryScopeClassifier()
        self._precheck_top_k = precheck_top_k
        self._precheck_score_threshold = precheck_score_threshold

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "BasicQueryOrchestrator":
        return cls(
            retriever=AzureSearchRetriever.from_settings(app_settings),
            llm_client=AzureOpenAILLMClient.from_settings(app_settings),
            precheck_top_k=app_settings.AZURE_SEARCH_PRECHECK_TOP_K,
            precheck_score_threshold=app_settings.AZURE_SEARCH_PRECHECK_SCORE_THRESHOLD,
        )

    def answer(self, request: QueryOrchestrationRequest) -> QueryOrchestrationResult:
        scope_assessment = self._scope_classifier.assess(request.query)
        if scope_assessment.decision is ScopeDecision.OUT_OF_SCOPE:
            return QueryOrchestrationResult(
                answer=self._build_out_of_scope_answer(),
                sources=[],
                tokens_used=0,
            )

        precheck_chunks = self._run_precheck(request.query)
        if not precheck_chunks:
            fallback_answer = (
                self._build_insufficient_context_answer()
                if scope_assessment.decision is ScopeDecision.IN_SCOPE
                else self._build_out_of_scope_answer()
            )
            return QueryOrchestrationResult(
                answer=fallback_answer,
                sources=[],
                tokens_used=0,
            )

        chunks = self._retriever.retrieve(RetrievalRequest(query=request.query))
        sources = self._build_sources(chunks)

        if not chunks:
            return QueryOrchestrationResult(
                answer=self._build_insufficient_context_answer(),
                sources=[],
                tokens_used=0,
            )

        context_block = self._build_context_block(chunks)
        context_strength = self._assess_context_strength(chunks)
        llm_result = self._llm_client.generate_answer(
            LLMGenerationRequest(
                system_prompt=self._build_system_prompt(),
                user_prompt=self._build_user_prompt(
                    query=request.query,
                    trace_id=request.trace_id,
                    context_block=context_block,
                    sources=sources,
                    context_strength=context_strength,
                ),
                temperature=0.0,
                max_tokens=900,
            )
        )
        return QueryOrchestrationResult(
            answer=llm_result.answer,
            sources=sources,
            tokens_used=llm_result.tokens_used,
        )

    def _run_precheck(self, query: str) -> list[SearchChunk]:
        return self._retriever.retrieve(
            RetrievalRequest(
                query=query,
                top_k=self._precheck_top_k,
                score_threshold=self._precheck_score_threshold,
            )
        )

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "Eres un copiloto experto en gobierno de arquitectura de soluciones para una "
            "organización del sector financiero.\n\n"
            "Tu función es analizar casos de uso y escenarios de negocio descritos en "
            "lenguaje natural, para asistir al equipo de arquitectura en la revisión "
            "conceptual de propuestas de solución.\n\n"
            "Debes apoyarte únicamente en el contexto recuperado por el sistema, el cual "
            "puede incluir building blocks arquitectónicos institucionales, lineamientos, "
            "patrones, buenas prácticas y referencias del marco BIAN.\n\n"
            "OBJETIVO DE LA RESPUESTA\n"
            "Debes ayudar a identificar:\n"
            "1. posibles building blocks reutilizables,\n"
            "2. lineamientos o patrones aplicables,\n"
            "3. posibles alineamientos con service domains de BIAN,\n"
            "4. observaciones y recomendaciones arquitectónicas.\n\n"
            "RESTRICCIONES\n"
            "- No inventes información.\n"
            "- No asumas decisiones no sustentadas por el contexto disponible.\n"
            "- Si no existe suficiente información, indícalo explícitamente.\n"
            "- No proporciones detalles técnicos de bajo nivel si no son relevantes para el análisis conceptual.\n"
            "- No expongas información sensible.\n\n"
            "MANEJO DE CONSULTAS FUERA DE ALCANCE\n"
            "Si la consulta no corresponde al dominio de arquitectura de soluciones, responde exactamente:\n"
            f"\"{BasicQueryOrchestrator.OUT_OF_SCOPE_MESSAGE}\"\n\n"
            "MANEJO DE FALTA DE CONTEXTO\n"
            "Si no existe suficiente información, responde exactamente:\n"
            f"\"{BasicQueryOrchestrator.INSUFFICIENT_CONTEXT_MESSAGE}\"\n\n"
            "FORMATO DE RESPUESTA\n"
            "Responde siempre en español usando Markdown claro con la siguiente estructura exacta:\n"
            "## 1. Resumen del caso\n"
            "## 2. Hallazgos relevantes\n"
            "## 3. Recomendaciones arquitectónicas\n"
            "## 4. Posible alineamiento BIAN\n"
            "## 5. Fuentes consultadas\n\n"
            "Dentro de las secciones 2, 3, 4 y 5 usa listas con viñetas `-` cuando corresponda.\n"
            "ESTILO\n"
            "- Profesional y técnico\n"
            "- Claro y estructurado\n"
            "- Enfocado en análisis conceptual\n"
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
    ) -> str:
        source_titles = "\n".join(
            f"- {source.title or source.source_id}"
            for source in sources
        )
        evidence_note = (
            "La evidencia recuperada es suficientemente directa para formular recomendaciones concretas, "
            "siempre que cada punto esté sustentado en el contexto."
            if context_strength is ContextStrength.STRONG
            else (
                "La evidencia recuperada es parcial o tangencial. No formules recomendaciones específicas "
                "como si fueran concluyentes. Explica explícitamente que el contexto encontrado es indirecto "
                "o insuficiente para una recomendación cerrada."
            )
        )
        return (
            f"Trace ID: {trace_id}\n\n"
            "Consulta del usuario:\n"
            f"{query}\n\n"
            "Nivel de confianza del contexto recuperado:\n"
            f"{context_strength.value}\n\n"
            "Interpretación operativa del nivel de confianza:\n"
            f"{evidence_note}\n\n"
            "Fuentes deduplicadas disponibles para sustento:\n"
            f"{source_titles}\n\n"
            "Contexto recuperado y autorizado para grounding:\n"
            f"{context_block}\n\n"
            "Instrucciones operativas:\n"
            "1. Usa solo el contexto recuperado.\n"
            "2. Si mencionas building blocks, patrones o referencias BIAN, deben aparecer en el contexto.\n"
            "3. Si un punto no está sustentado, indícalo como no confirmado.\n"
            "4. Si el contexto es parcial o tangencial, evita recomendar un patrón o building block específico con falsa certeza.\n"
            "5. En \"Fuentes consultadas\", cita por título las fuentes deduplicadas que realmente sustentan tu respuesta.\n"
            "6. Usa Markdown limpio con encabezados `##` y listas con `-`.\n"
            "7. Mantén el formato exacto solicitado en el system prompt."
        )

    @staticmethod
    def _build_context_block(chunks: list[SearchChunk]) -> str:
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
                "- No se recuperaron fragmentos confiables desde Azure AI Search para sustentar la consulta.",
                "## 3. Recomendaciones arquitectónicas",
                "- Reformular la consulta con más contexto de negocio o arquitectura.",
                "- Indicar building blocks, capability domains, patrones o service domains esperados si se conocen.",
                "## 4. Posible alineamiento BIAN",
                "- No es posible proponer un alineamiento BIAN sustentado con la evidencia recuperada.",
                "## 5. Fuentes consultadas",
                "- No se encontraron fuentes relevantes en el contexto recuperado.",
            ]
        )

    @staticmethod
    def _assess_context_strength(chunks: list[SearchChunk]) -> ContextStrength:
        top_score = max(chunk.score for chunk in chunks)
        return (
            ContextStrength.STRONG
            if top_score >= 0.72
            else ContextStrength.PARTIAL
        )

    @staticmethod
    def _build_sources(chunks: list[SearchChunk]) -> list[QuerySource]:
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
            )
            current = deduped.get(dedupe_key)
            if current is None or candidate.score > current.score:
                deduped[dedupe_key] = candidate

        return sorted(
            deduped.values(),
            key=lambda source: source.score,
            reverse=True,
        )
