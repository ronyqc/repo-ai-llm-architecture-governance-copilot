from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Protocol

from src.core.config import Settings, settings
from src.core.llm_client import (
    AzureOpenAILLMClient,
    LLMGenerationRequest,
)
from src.utils.logger import get_logger


logger = get_logger(__name__)


class RetrievalStrategy(str, Enum):
    """Strategies available for query routing."""

    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    RAG_ONLY = "RAG_ONLY"
    CONFLUENCE_ONLY = "CONFLUENCE_ONLY"
    BOTH = "BOTH"


@dataclass(frozen=True)
class RoutingDecision:
    """Structured routing result returned by the router layer."""

    strategy: RetrievalStrategy
    reason: str
    confluence_query: str | None = None
    space_key: str | None = None
    tokens_used: int = 0


class QueryRoutingError(RuntimeError):
    """Raised when the router cannot produce a valid structured decision."""


class QueryRouter(Protocol):
    """Abstraction for deciding the retrieval strategy of a query."""

    def route(self, query: str) -> RoutingDecision:
        """Return a structured routing decision for the query."""


class LLMQueryRouter:
    """Small LLM-based router that classifies retrieval strategy only."""

    def __init__(
        self,
        *,
        llm_client: AzureOpenAILLMClient,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self._llm_client = llm_client
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "LLMQueryRouter":
        return cls(
            llm_client=AzureOpenAILLMClient.from_router_settings(app_settings),
            temperature=app_settings.AZURE_OPENAI_ROUTER_TEMPERATURE,
            max_tokens=app_settings.AZURE_OPENAI_ROUTER_MAX_TOKENS,
        )

    def route(self, query: str) -> RoutingDecision:
        logger.info(
            "LLM router invoked. query_preview=%s",
            _preview_text(query),
        )
        llm_result = self._llm_client.generate_answer(
            LLMGenerationRequest(
                system_prompt=self._build_system_prompt(),
                user_prompt=self._build_user_prompt(query),
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        )

        try:
            payload = json.loads(llm_result.answer)
        except json.JSONDecodeError as exc:
            raise QueryRoutingError("LLM router returned invalid JSON.") from exc

        strategy_value = str(payload.get("strategy", "")).strip().upper()
        reason = str(payload.get("reason", "")).strip()
        confluence_query = _normalize_optional_text(payload.get("confluence_query"))
        space_key = _normalize_optional_text(payload.get("space_key"))
        if not reason:
            raise QueryRoutingError("LLM router returned an empty reason.")

        try:
            strategy = RetrievalStrategy(strategy_value)
        except ValueError as exc:
            raise QueryRoutingError(
                f"LLM router returned unsupported strategy: {strategy_value or '(empty)'}.",
            ) from exc

        decision = RoutingDecision(
            strategy=strategy,
            reason=reason[:280],
            confluence_query=confluence_query,
            space_key=space_key,
            tokens_used=llm_result.tokens_used,
        )
        logger.info(
            "LLM router decision. strategy=%s reason=%s confluence_query=%s space_key=%s tokens_used=%s",
            decision.strategy.value,
            decision.reason,
            decision.confluence_query,
            decision.space_key,
            decision.tokens_used,
        )
        return decision

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "Eres un router de consultas para un copiloto de gobierno de arquitectura.\n"
            "No respondas la consulta del usuario. Solo clasifica la estrategia de recuperacion.\n\n"
            "Devuelve un objeto JSON valido con exactamente estas claves:\n"
            "{\"strategy\":\"OUT_OF_SCOPE|RAG_ONLY|CONFLUENCE_ONLY|BOTH\",\"reason\":\"...\","
            "\"confluence_query\":\"...\",\"space_key\":\"AGC\"}\n\n"
            "Definiciones:\n"
            "- OUT_OF_SCOPE: la consulta no pertenece al dominio de gobierno de arquitectura, "
            "building blocks, lineamientos, integraciones, BIAN o documentacion interna relevante.\n"
            "- RAG_ONLY: la consulta debe resolverse con el corpus indexado en Azure AI Search.\n"
            "- CONFLUENCE_ONLY: la consulta pide acuerdos internos recientes, decisiones del equipo, "
            "documentacion interna viva o conocimiento operativo que normalmente viviria en Confluence.\n"
            "- BOTH: la consulta requiere tanto corpus institucional/indexado como documentacion interna reciente.\n\n"
            "Reglas:\n"
            "- Prioriza RAG_ONLY para building blocks, lineamientos, patrones o BIAN.\n"
            "- Prioriza CONFLUENCE_ONLY para acuerdos internos recientes, decisiones del equipo o documentacion interna.\n"
            "- Usa BOTH solo cuando la consulta combine explicitamente ambos frentes.\n"
            "- Usa OUT_OF_SCOPE si la consulta no trata de arquitectura o documentacion interna del dominio.\n"
            "- La razon debe ser breve, concreta y en espanol.\n"
            "- Si la estrategia es CONFLUENCE_ONLY o BOTH, devuelve tambien confluence_query con terminos breves y utiles para CQL.\n"
            "- space_key es opcional y debe ir solo si tienes una pista razonable del espacio.\n"
            "- Si la estrategia es OUT_OF_SCOPE o RAG_ONLY, confluence_query y space_key pueden ser null.\n"
            "- No agregues texto fuera del JSON."
        )

    @staticmethod
    def _build_user_prompt(query: str) -> str:
        return "Clasifica la siguiente consulta.\n" f"Consulta: {query}"


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _preview_text(value: str, limit: int = 120) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
