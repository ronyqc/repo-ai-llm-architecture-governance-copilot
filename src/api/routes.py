from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceReference,
)
from src.core.config import settings
from src.core.health import SystemHealthService
from src.core.llm_client import (
    AzureOpenAIContentFilterError,
    AzureOpenAILLMConfigurationError,
    AzureOpenAILLMError,
)
from src.core.orchestrator import BasicQueryOrchestrator, QueryOrchestrationRequest
from src.core.routing import QueryRoutingError
from src.integrations.confluence_client import (
    ConfluenceConfigurationError,
    ConfluenceError,
)
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
from src.security.guardrails import (
    GuardrailService,
    GuardrailViolation,
)
from src.utils.logger import get_logger


router = APIRouter()
logger = get_logger(__name__)
_GUARDRAIL_SERVICE = GuardrailService.from_settings()
ingest_dependency = (
    require_admin_user
    if settings.REQUIRE_ADMIN_FOR_INGEST
    else require_authenticated_user
)


def get_query_orchestrator() -> BasicQueryOrchestrator:
    return BasicQueryOrchestrator.from_settings()


def get_health_service() -> SystemHealthService:
    return SystemHealthService.from_settings()


def get_guardrail_service() -> GuardrailService:
    return _GUARDRAIL_SERVICE


@router.get("/api/v1/health")
def health_check(
    health_service: SystemHealthService = Depends(get_health_service),
) -> dict[str, object]:
    report = health_service.check()
    return {
        "status": report.status,
        "components": report.components,
        "timestamp": report.timestamp,
    }


@router.post("/api/v1/query", response_model=QueryResponse)
def query_copilot(
    request: Request,
    payload: QueryRequest,
    orchestrator: BasicQueryOrchestrator = Depends(get_query_orchestrator),
    guardrail_service: GuardrailService = Depends(get_guardrail_service),
    user: AuthenticatedUser = Depends(require_authenticated_user),
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
        client_host = request.client.host if request.client is not None else "unknown"
        validated_query = guardrail_service.protect_query(
            query=payload.query,
            identity=f"{user.user_id}:{client_host}",
        )
    except GuardrailViolation as exc:
        logger.warning(
            "Query blocked by guardrails. trace_id=%s user_id=%s status_code=%s reason=%s",
            trace_id,
            user.user_id,
            exc.status_code,
            str(exc),
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    logger.info(
        "Query request received. trace_id=%s session_id=%s query_preview=%s",
        trace_id,
        session_id,
        validated_query.sanitized_query[:120],
    )

    try:
        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query=validated_query.sanitized_query,
                trace_id=trace_id,
            )
        )
    except (
        AzureOpenAIEmbeddingConfigurationError,
        AzureSearchConfigurationError,
        AzureOpenAILLMConfigurationError,
        ConfluenceConfigurationError,
    ) as exc:
        logger.exception("Query endpoint misconfigured. trace_id=%s", trace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (
        AzureOpenAIEmbeddingError,
        AzureSearchQueryError,
        QueryRoutingError,
        ConfluenceError,
    ) as exc:
        logger.exception("Query execution failed. trace_id=%s", trace_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Query processing is temporarily unavailable.",
        ) from exc
    except AzureOpenAIContentFilterError as exc:
        logger.warning(
            "Query blocked by Azure OpenAI content filter. trace_id=%s error=%s",
            trace_id,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AzureOpenAILLMError as exc:
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
    logger.info(
        "Query request completed. trace_id=%s session_id=%s tokens_used=%s sources=%s latency_ms=%.2f",
        trace_id,
        session_id,
        result.tokens_used,
        len(result.sources),
        latency_ms,
    )

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
