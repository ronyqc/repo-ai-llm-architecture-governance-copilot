from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from src.core.config import Settings, settings
from src.rag.vector_store import AzureSearchVectorStore, SearchChunk, SearchQuery


@dataclass(frozen=True)
class RetrievalRequest:
    """Stable retrieval contract for the backend and future orchestrator."""

    query: str
    top_k: int | None = None
    score_threshold: float | None = None
    knowledge_domain: str | None = None


class AzureSearchRetriever:
    """Backend retrieval service backed by Azure AI Search."""

    def __init__(
        self,
        vector_store: AzureSearchVectorStore,
        *,
        default_top_k: int,
        default_score_threshold: float,
    ) -> None:
        self._vector_store = vector_store
        self._default_top_k = default_top_k
        self._default_score_threshold = default_score_threshold

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "AzureSearchRetriever":
        return cls(
            vector_store=AzureSearchVectorStore.from_settings(app_settings),
            default_top_k=app_settings.AZURE_SEARCH_TOP_K,
            default_score_threshold=app_settings.AZURE_SEARCH_SCORE_THRESHOLD,
        )

    def retrieve(self, request: RetrievalRequest) -> list[SearchChunk]:
        query = SearchQuery(
            text=request.query,
            top_k=request.top_k or self._default_top_k,
            score_threshold=(
                request.score_threshold
                if request.score_threshold is not None
                else self._default_score_threshold
            ),
            knowledge_domain=request.knowledge_domain,
        )
        return self._vector_store.search(query)

    def retrieve_as_dict(self, request: RetrievalRequest) -> list[dict]:
        return [asdict(chunk) for chunk in self.retrieve(request)]
