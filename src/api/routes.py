import logging
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceReference,
    UploadUrlRequest,
    UploadUrlResponse,
)
from src.core.health import SystemHealthService
from src.core.llm_client import (
    AzureOpenAIContentFilterError,
    AzureOpenAILLMConfigurationError,
    AzureOpenAILLMError,
)
from src.core.orchestrator import (
    BasicQueryOrchestrator,
    ConversationContextTurn,
    QueryOrchestrationRequest,
)
from src.core.routing import QueryRoutingError
from src.integrations.blob_ingest_service import (
    BlobDocumentIngestService,
    IngestServiceError,
)
from src.integrations.blob_upload_service import (
    BlobUploadUrlService,
    UploadUrlServiceError,
)
from src.integrations.confluence_client import (
    ConfluenceConfigurationError,
    ConfluenceError,
)
from src.integrations.conversation_store import (
    AzureTableConversationStore,
    ConversationStoreConfigurationError,
    ConversationStoreError,
    ConversationTurnRecord,
    NoOpConversationStore,
    build_created_at_timestamp,
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
    require_ingest_user,
)
from src.security.guardrails import (
    GuardrailService,
    GuardrailViolation,
)
from src.utils.logger import get_logger, log_event


router = APIRouter()
logger = get_logger(__name__)
_GUARDRAIL_SERVICE = GuardrailService.from_settings()


def get_query_orchestrator() -> BasicQueryOrchestrator:
    return BasicQueryOrchestrator.from_settings()


def get_health_service() -> SystemHealthService:
    return SystemHealthService.from_settings()


def get_guardrail_service() -> GuardrailService:
    return _GUARDRAIL_SERVICE


def get_ingest_service() -> BlobDocumentIngestService:
    return BlobDocumentIngestService.from_settings()


def get_blob_upload_service() -> BlobUploadUrlService:
    return BlobUploadUrlService.from_settings()


def get_conversation_store() -> AzureTableConversationStore | NoOpConversationStore:
    try:
        return AzureTableConversationStore.from_settings()
    except ConversationStoreConfigurationError:
        logger.warning("Conversation store configuration is unavailable. Falling back to no-op store.")
        return NoOpConversationStore()


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
    conversation_store: AzureTableConversationStore = Depends(get_conversation_store),
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> QueryResponse:
    start_time = perf_counter()
    session_id = payload.session_id or str(uuid4())
    trace_id = str(uuid4())
    conversation_history: list[ConversationContextTurn] = []
    query_preview = _build_query_preview(payload.query)

    if payload.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is not supported in the current /query implementation.",
        )

    try:
        client_host = request.client.host if request.client is not None else "unknown"
        log_event(
            logger,
            logging.INFO,
            "query.request.started",
            trace_id=trace_id,
            session_id=session_id,
            user_id=user.user_id,
            query_preview=query_preview,
        )
        validated_query = guardrail_service.protect_query(
            query=payload.query,
            identity=f"{user.user_id}:{client_host}",
        )
    except GuardrailViolation as exc:
        log_event(
            logger,
            logging.WARNING,
            "query.request.blocked_guardrails",
            trace_id=trace_id,
            session_id=session_id,
            user_id=user.user_id,
            status_code=exc.status_code,
            reason=str(exc),
            query_preview=query_preview,
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    if payload.session_id:
        try:
            persisted_turns = conversation_store.get_recent_history(session_id=session_id)
            conversation_history = [
                ConversationContextTurn(
                    user_query=turn.user_query,
                    assistant_answer=turn.assistant_answer,
                    created_at=turn.created_at,
                )
                for turn in persisted_turns
            ]
        except ConversationStoreError:
            log_event(
                logger,
                logging.ERROR,
                "query.history.retrieval_failed",
                trace_id=trace_id,
                session_id=session_id,
                user_id=user.user_id,
                exc_info=True,
            )

    try:
        result = orchestrator.answer(
            QueryOrchestrationRequest(
                query=validated_query.sanitized_query,
                trace_id=trace_id,
                conversation_history=conversation_history,
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
    primary_knowledge_domain = _resolve_primary_knowledge_domain(result.sources)
    log_event(
        logger,
        logging.INFO,
        "query.request.completed",
        trace_id=trace_id,
        session_id=session_id,
        user_id=user.user_id,
        latency_ms=round(latency_ms, 2),
        tokens_used=result.tokens_used,
        sources_count=len(result.sources),
        knowledge_domain=primary_knowledge_domain,
    )

    try:
        conversation_store.append_turn(
            ConversationTurnRecord(
                session_id=session_id,
                user_query=validated_query.sanitized_query,
                assistant_answer=result.answer,
                created_at=build_created_at_timestamp(),
                trace_id=trace_id,
                knowledge_domain=primary_knowledge_domain,
                tokens_used=result.tokens_used,
                latency_ms=latency_ms,
                sources=[
                    {
                        "source_id": source.source_id,
                        "source_type": source.source_type,
                        "title": source.title,
                        "score": source.score,
                        "knowledge_domain": source.knowledge_domain,
                    }
                    for source in result.sources
                ],
            )
        )
    except ConversationStoreError:
        log_event(
            logger,
            logging.ERROR,
            "query.history.persistence_failed",
            trace_id=trace_id,
            session_id=session_id,
            user_id=user.user_id,
            latency_ms=round(latency_ms, 2),
            tokens_used=result.tokens_used,
            sources_count=len(result.sources),
            knowledge_domain=primary_knowledge_domain,
            exc_info=True,
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


def _resolve_primary_knowledge_domain(sources: list[object]) -> str:
    for source in sources:
        knowledge_domain = getattr(source, "knowledge_domain", None)
        if isinstance(knowledge_domain, str) and knowledge_domain.strip():
            return knowledge_domain.strip()
    return ""


def _build_query_preview(query: str, limit: int = 120) -> str:
    compact = " ".join(query.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


@router.post(
    "/api/v1/upload-url",
    response_model=UploadUrlResponse,
)
def create_upload_url(
    payload: UploadUrlRequest,
    upload_service: BlobUploadUrlService = Depends(get_blob_upload_service),
    user: AuthenticatedUser = Depends(require_admin_user),
) -> UploadUrlResponse:
    try:
        result = upload_service.generate_upload_url(file_name=payload.file_name)
    except UploadUrlServiceError as exc:
        log_event(
            logger,
            logging.WARNING,
            "upload_url.request.rejected",
            user_id=user.user_id,
            file_name=payload.file_name,
            error=str(exc),
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    log_event(
        logger,
        logging.INFO,
        "upload_url.sas.generated",
        user_id=user.user_id,
        file_name=payload.file_name,
        blob_name=result.blob_name,
        expires_in_seconds=result.expires_in_seconds,
    )

    return UploadUrlResponse(
        upload_url=result.upload_url,
        blob_url=result.blob_url,
        blob_name=result.blob_name,
        expires_in_seconds=result.expires_in_seconds,
    )


@router.post(
    "/api/v1/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_document(
    payload: IngestRequest,
    ingest_service: BlobDocumentIngestService = Depends(get_ingest_service),
    user: AuthenticatedUser = Depends(require_ingest_user),
) -> IngestResponse:
    trace_id = str(uuid4())

    try:
        ingest_service.ingest(
            payload=payload,
            user=user,
            trace_id=trace_id,
        )
    except IngestServiceError as exc:
        log_event(
            logger,
            logging.WARNING,
            "ingest.request.rejected",
            trace_id=trace_id,
            user_id=user.user_id,
            knowledge_domain=payload.knowledge_domain,
            file_name=payload.file_name,
            error=str(exc),
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    return IngestResponse(
        status="accepted",
        message="Ingest accepted and dispatched to the blob-trigger pipeline.",
        trace_id=trace_id,
    )
