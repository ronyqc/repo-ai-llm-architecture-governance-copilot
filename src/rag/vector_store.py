from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import AzureError
    from azure.search.documents import SearchClient
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal local envs
    AzureKeyCredential = None
    SearchClient = Any

    class AzureError(Exception):
        """Fallback Azure SDK base exception when azure-core is unavailable."""

from src.core.config import Settings, settings
from src.utils.logger import get_logger


logger = get_logger(__name__)

ALLOWED_KNOWLEDGE_DOMAINS = {
    "bian",
    "building_blocks",
    "guidelines_patterns",
}

class AzureSearchConfigurationError(ValueError):
    """Raised when Azure AI Search settings are incomplete or invalid."""


class AzureSearchQueryError(RuntimeError):
    """Raised when Azure AI Search query execution fails."""


@dataclass(frozen=True)
class SearchChunk:
    """Normalized chunk retrieved from Azure AI Search."""

    source_id: str
    source_type: str
    title: str
    content: str
    score: float
    knowledge_domain: str
    source_url: str | None
    document_name: str
    chunk_order: int | None
    metadata: str | None
    chunk_id: str | None
    updated_at: str | None


@dataclass(frozen=True)
class SearchQuery:
    """Input parameters for a retrieval operation."""

    text: str
    top_k: int
    score_threshold: float = 0.0
    knowledge_domain: str | None = None


class AzureSearchVectorStore:
    """Small wrapper around Azure AI Search used by the backend retriever."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        index_name: str,
        client: SearchClient | None = None,
    ) -> None:
        self._endpoint = endpoint.strip()
        self._api_key = api_key.strip()
        self._index_name = index_name.strip()
        self._validate_configuration()
        if client is None and AzureKeyCredential is None:
            raise AzureSearchConfigurationError(
                "azure-search-documents and azure-core must be installed to use "
                "AzureSearchVectorStore without an injected client."
            )
        self._client = client or SearchClient(
            endpoint=self._endpoint,
            index_name=self._index_name,
            credential=AzureKeyCredential(self._api_key),
        )

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "AzureSearchVectorStore":
        return cls(
            endpoint=app_settings.AZURE_SEARCH_ENDPOINT,
            api_key=app_settings.AZURE_SEARCH_KEY,
            index_name=app_settings.AZURE_SEARCH_INDEX,
        )

    def search(self, query: SearchQuery) -> list[SearchChunk]:
        self._validate_query(query)
        filter_expression = self._build_filter(knowledge_domain=query.knowledge_domain)

        logger.info(
            "Executing Azure AI Search query against index '%s' with top_k=%s and knowledge_domain=%s",
            self._index_name,
            query.top_k,
            query.knowledge_domain or "*",
        )

        try:
            # T31 keeps retrieval in the simplest functional mode: keyword search.
            # T32 will introduce query embeddings so this call can evolve to vector search.
            # Later iterations can combine both into hybrid search and add semantic ranking.
            results = self._client.search(
                search_text=query.text,
                filter=filter_expression,
                top=query.top_k,
            )
        except AzureError as exc:
            logger.exception("Azure AI Search query failed")
            raise AzureSearchQueryError(
                "Azure AI Search query execution failed."
            ) from exc

        normalized_results: list[SearchChunk] = []
        for result in results:
            normalized_chunk = self._normalize_result(result)
            if normalized_chunk.score >= query.score_threshold:
                normalized_results.append(normalized_chunk)

        logger.info(
            "Azure AI Search returned %s chunks after applying score_threshold=%s",
            len(normalized_results),
            query.score_threshold,
        )
        return normalized_results

    def _validate_configuration(self) -> None:
        missing = []
        if not self._endpoint:
            missing.append("AZURE_SEARCH_ENDPOINT")
        if not self._api_key:
            missing.append("AZURE_SEARCH_KEY")
        if not self._index_name:
            missing.append("AZURE_SEARCH_INDEX")

        if missing:
            raise AzureSearchConfigurationError(
                "Missing Azure AI Search configuration: "
                + ", ".join(sorted(missing))
            )

    @staticmethod
    def _validate_query(query: SearchQuery) -> None:
        if not query.text or not query.text.strip():
            raise ValueError("Query text must be a non-empty string.")
        if query.top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        if query.score_threshold < 0:
            raise ValueError("score_threshold must be greater than or equal to zero.")
        if query.knowledge_domain:
            AzureSearchVectorStore._validate_knowledge_domain(query.knowledge_domain)

    @staticmethod
    def _validate_knowledge_domain(knowledge_domain: str) -> None:
        if knowledge_domain not in ALLOWED_KNOWLEDGE_DOMAINS:
            raise ValueError(
                "Invalid knowledge_domain "
                f"'{knowledge_domain}'. Allowed values: "
                f"{', '.join(sorted(ALLOWED_KNOWLEDGE_DOMAINS))}."
            )

    @classmethod
    def _build_filter(cls, *, knowledge_domain: str | None) -> str | None:
        if not knowledge_domain:
            return None

        cls._validate_knowledge_domain(knowledge_domain)
        escaped_value = knowledge_domain.replace("'", "''")
        return f"knowledge_domain eq '{escaped_value}'"

    @staticmethod
    def _normalize_result(result: dict) -> SearchChunk:
        score = float(result.get("@search.score") or 0.0)
        return SearchChunk(
            source_id=str(result.get("id") or result.get("chunk_id") or ""),
            source_type=str(result.get("source_type") or ""),
            title=str(result.get("title") or ""),
            content=str(result.get("content") or ""),
            score=score,
            knowledge_domain=str(result.get("knowledge_domain") or ""),
            source_url=result.get("source_url"),
            document_name=str(result.get("document_name") or ""),
            chunk_order=result.get("chunk_order"),
            metadata=result.get("metadata"),
            chunk_id=result.get("chunk_id"),
            updated_at=result.get("updated_at"),
        )
