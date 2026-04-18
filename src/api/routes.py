from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceReference,
)
from src.core.config import settings
from src.core.llm_client import (
    AzureOpenAILLMConfigurationError,
    AzureOpenAILLMError,
)
from src.core.orchestrator import BasicQueryOrchestrator, QueryOrchestrationRequest
from src.core.routing import QueryRoutingError
from src.rag.embeddings import (
    AzureOpenAIEmbeddingConfigurationError,
    AzureOpenAIEmbeddingError,
)
from src.rag.vector_store import (
    AzureSearchConfigurationError,
    AzureSearchQueryError,
)
from src.security.auth import (
    AuthenticatedUser,
    require_admin_user,
    require_authenticated_user,
)
from src.utils.logger import get_logger


router = APIRouter()
logger = get_logger(__name__)
ingest_dependency = (
    require_admin_user
    if settings.REQUIRE_ADMIN_FOR_INGEST
    else require_authenticated_user
)


def get_query_orchestrator() -> BasicQueryOrchestrator:
    return BasicQueryOrchestrator.from_settings()


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
def query_copilot(
    payload: QueryRequest,
    orchestrator: BasicQueryOrchestrator = Depends(get_query_orchestrator),
    _user: AuthenticatedUser = Depends(require_authenticated_user),
) -> QueryResponse:
    start_time = perf_counter()
    session_id = payload.session_id or str(uuid4())
    trace_id = str(uuid4())

    if payload.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is not supported in the current /query implementation.",
        )

    try:
        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query=payload.query,
                trace_id=trace_id,
            )
        )
    except (
        AzureOpenAIEmbeddingConfigurationError,
        AzureSearchConfigurationError,
        AzureOpenAILLMConfigurationError,
    ) as exc:
        logger.exception("Query endpoint misconfigured. trace_id=%s", trace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (
        AzureOpenAIEmbeddingError,
        AzureSearchQueryError,
        AzureOpenAILLMError,
        QueryRoutingError,
    ) as exc:
        logger.exception("Query execution failed. trace_id=%s", trace_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Query processing is temporarily unavailable.",
        ) from exc
    except ValueError as exc:
        logger.warning("Invalid query request. trace_id=%s error=%s", trace_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    latency_ms = (perf_counter() - start_time) * 1000

    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceReference(
                source_id=source.source_id,
                source_type=source.source_type,
                title=source.title,
                score=source.score,
            )
            for source in result.sources
        ],
        tokens_used=result.tokens_used,
        latency_ms=latency_ms,
        trace_id=trace_id,
        session_id=session_id,
    )


@router.post("/api/v1/ingest", response_model=IngestResponse)
def ingest_document(
    payload: IngestRequest,
    _user: AuthenticatedUser = Depends(ingest_dependency),
) -> IngestResponse:
    trace_id = str(uuid4())

    return IngestResponse(
        status="accepted",
        message="Ingesta registrada correctamente",
        trace_id=trace_id,
    )
