from __future__ import annotations

from dataclasses import dataclass

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


class BasicQueryOrchestrator:
    """Minimal orchestrator for T33: retrieve, consolidate context and answer."""

    def __init__(
        self,
        *,
        retriever: AzureSearchRetriever,
        llm_client: AzureOpenAILLMClient,
    ) -> None:
        self._retriever = retriever
        self._llm_client = llm_client

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "BasicQueryOrchestrator":
        return cls(
            retriever=AzureSearchRetriever.from_settings(app_settings),
            llm_client=AzureOpenAILLMClient.from_settings(app_settings),
        )

    def answer(self, request: QueryOrchestrationRequest) -> QueryOrchestrationResult:
        chunks = self._retriever.retrieve(RetrievalRequest(query=request.query))
        context_block = self._build_context_block(chunks)
        llm_result = self._llm_client.generate_answer(
            LLMGenerationRequest(
                system_prompt=self._build_system_prompt(),
                user_prompt=self._build_user_prompt(
                    query=request.query,
                    trace_id=request.trace_id,
                    context_block=context_block,
                ),
            )
        )
        return QueryOrchestrationResult(
            answer=llm_result.answer,
            sources=self._build_sources(chunks),
            tokens_used=llm_result.tokens_used,
        )

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "You are the Architecture Governance Copilot. "
            "Answer using only the provided context. "
            "Prioritize architecture guidance, building blocks, BIAN references and governance recommendations. "
            "If the retrieved context is insufficient, say so explicitly and avoid inventing facts."
        )

    def _build_user_prompt(
        self,
        *,
        query: str,
        trace_id: str,
        context_block: str,
    ) -> str:
        return (
            f"Trace ID: {trace_id}\n"
            "Task: Answer the user's architecture governance question using the retrieved context.\n\n"
            f"User question:\n{query}\n\n"
            f"Retrieved context:\n{context_block}\n\n"
            "Instructions:\n"
            "1. Provide a direct answer in Spanish.\n"
            "2. Base the answer on the retrieved context only.\n"
            "3. If the context is insufficient, say what is missing.\n"
            "4. Keep the answer concise but useful for an architecture review."
        )

    @staticmethod
    def _build_context_block(chunks: list[SearchChunk]) -> str:
        if not chunks:
            return "No relevant knowledge chunks were retrieved from Azure AI Search."

        sections = []
        for index, chunk in enumerate(chunks, start=1):
            sections.append(
                "\n".join(
                    [
                        f"[Source {index}]",
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
    def _build_sources(chunks: list[SearchChunk]) -> list[QuerySource]:
        return [
            QuerySource(
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                title=chunk.title,
                score=chunk.score,
            )
            for chunk in chunks
        ]
