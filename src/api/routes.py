from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter

from src.api.schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)


router = APIRouter()


@router.get("/api/v1/health")
def health_check() -> dict[str, object]:
    timestamp = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return {
        "status": "healthy",
        "components": {
            "backend": "healthy",
        },
        "timestamp": timestamp,
    }


@router.post("/api/v1/query", response_model=QueryResponse)
def query_copilot(payload: QueryRequest) -> QueryResponse:
    start_time = perf_counter()
    session_id = payload.session_id or str(uuid4())
    trace_id = str(uuid4())
    latency_ms = (perf_counter() - start_time) * 1000

    return QueryResponse(
        answer="Respuesta simulada para el copiloto de arquitectura",
        sources=[],
        tokens_used=0,
        latency_ms=latency_ms,
        trace_id=trace_id,
        session_id=session_id,
    )


@router.post("/api/v1/ingest", response_model=IngestResponse)
def ingest_document(payload: IngestRequest) -> IngestResponse:
    trace_id = str(uuid4())

    return IngestResponse(
        status="accepted",
        message="Ingesta registrada correctamente",
        trace_id=trace_id,
    )
