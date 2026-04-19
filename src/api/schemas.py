from typing import Literal

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    source_id: str = Field(..., description="Unique identifier of the source")
    source_type: str = Field(..., description="Type or category of the source")
    title: str = Field(..., description="Human-readable title of the source")
    score: float = Field(..., description="Relevance score assigned to the source")


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="User query text",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session identifier for conversation continuity",
    )
    stream: bool = Field(
        default=False,
        description="Whether the response should be streamed",
    )


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Generated answer for the query")
    sources: list[SourceReference] = Field(
        ...,
        description="Sources used to build the answer",
    )
    tokens_used: int = Field(..., description="Total tokens consumed")
    latency_ms: float = Field(..., description="Request latency in milliseconds")
    trace_id: str = Field(..., description="Trace identifier for observability")
    session_id: str = Field(..., description="Session identifier associated with the request")


class IngestRequest(BaseModel):
    file_name: str = Field(
        ...,
        min_length=1,
        description="Name of the file to ingest",
    )
    file_url: str = Field(
        ...,
        min_length=1,
        description="URL where the file can be retrieved",
    )
    knowledge_domain: str = Field(
        ...,
        min_length=1,
        description="Knowledge domain associated with the file",
    )
    metadata: dict[str, str] = Field(
        ...,
        min_length=1,
        description="Metadata associated with the ingestion request",
    )


class IngestResponse(BaseModel):
    status: Literal["accepted"] = Field(
        ...,
        description="Status of the ingestion request",
    )
    message: str = Field(..., description="Result message for the ingestion request")
    trace_id: str = Field(..., description="Trace identifier for observability")
