from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import re
from typing import Any, Iterable, Protocol

try:
    from azure.data.tables import TableServiceClient
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal local envs
    TableServiceClient = Any

from src.core.config import Settings, settings
from src.utils.logger import get_logger


logger = get_logger(__name__)
_ROW_KEY_PATTERN = re.compile(r"^turn_(\d{6,})$")


@dataclass(frozen=True)
class ConversationTurn:
    row_key: str
    user_query: str
    assistant_answer: str
    created_at: str
    trace_id: str
    knowledge_domain: str | None
    tokens_used: int
    latency_ms: float
    sources_json: str


@dataclass(frozen=True)
class ConversationTurnRecord:
    session_id: str
    user_query: str
    assistant_answer: str
    created_at: str
    trace_id: str
    knowledge_domain: str | None
    tokens_used: int
    latency_ms: float
    sources: list[dict[str, Any]]


class TableClientProtocol(Protocol):
    def query_entities(
        self,
        query_filter: str,
        *,
        parameters: dict[str, object] | None = None,
        select: list[str] | None = None,
    ) -> Iterable[dict[str, object]]:
        ...

    def create_entity(self, *, entity: dict[str, object]) -> object:
        ...


class TableServiceClientProtocol(Protocol):
    def get_table_client(self, table_name: str) -> TableClientProtocol:
        ...


class ConversationStoreError(RuntimeError):
    """Raised when conversation history cannot be read or written."""


class ConversationStoreConfigurationError(ValueError):
    """Raised when the conversation store is misconfigured."""


class NoOpConversationStore:
    """Fallback store used when conversation memory is unavailable."""

    def get_recent_history(
        self,
        *,
        session_id: str,
        limit: int | None = None,
    ) -> list[ConversationTurn]:
        return []

    def append_turn(self, record: ConversationTurnRecord) -> str:
        return ""


class AzureTableConversationStore:
    def __init__(
        self,
        *,
        table_client: TableClientProtocol,
        table_name: str,
        default_history_limit: int,
    ) -> None:
        self._table_client = table_client
        self._table_name = table_name.strip()
        self._default_history_limit = default_history_limit

        if not self._table_name:
            raise ConversationStoreConfigurationError(
                "AZURE_TABLE_CONVERSATION_TABLE_NAME debe estar configurado."
            )
        if self._default_history_limit <= 0:
            raise ConversationStoreConfigurationError(
                "QUERY_HISTORY_MAX_TURNS debe ser mayor que cero."
            )

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "AzureTableConversationStore":
        if TableServiceClient is Any:
            raise ConversationStoreConfigurationError(
                "azure-data-tables must be installed to use AzureTableConversationStore."
            )

        service_client = TableServiceClient.from_connection_string(
            app_settings.AZURE_STORAGE_CONNECTION_STRING
        )
        table_client = service_client.get_table_client(
            table_name=app_settings.AZURE_TABLE_CONVERSATION_TABLE_NAME
        )
        return cls(
            table_client=table_client,
            table_name=app_settings.AZURE_TABLE_CONVERSATION_TABLE_NAME,
            default_history_limit=app_settings.QUERY_HISTORY_MAX_TURNS,
        )

    def get_recent_history(
        self,
        *,
        session_id: str,
        limit: int | None = None,
    ) -> list[ConversationTurn]:
        normalized_session_id = session_id.strip()
        effective_limit = limit or self._default_history_limit
        if not normalized_session_id or effective_limit <= 0:
            return []

        try:
            entities = list(self._query_session_entities(session_id=normalized_session_id))
        except Exception as exc:  # pragma: no cover - SDK-specific failures
            logger.exception(
                "Conversation history retrieval failed. table=%s session_id=%s",
                self._table_name,
                normalized_session_id,
            )
            raise ConversationStoreError(
                "Conversation history retrieval failed."
            ) from exc

        ordered_entities = sorted(
            entities,
            key=lambda entity: str(entity.get("RowKey", "")),
        )
        return [
            self._to_turn(entity)
            for entity in ordered_entities[-effective_limit:]
        ]

    def append_turn(self, record: ConversationTurnRecord) -> str:
        normalized_session_id = record.session_id.strip()
        if not normalized_session_id:
            raise ConversationStoreError("session_id is required to persist conversation history.")

        try:
            existing_entities = list(
                self._query_session_entities(
                    session_id=normalized_session_id,
                    select=["RowKey"],
                )
            )
            row_key = self._build_next_row_key(existing_entities)
            entity = self._build_entity(record=record, row_key=row_key)
            self._table_client.create_entity(entity=entity)
            return row_key
        except Exception as exc:  # pragma: no cover - SDK-specific failures
            logger.exception(
                "Conversation history persistence failed. table=%s session_id=%s trace_id=%s",
                self._table_name,
                normalized_session_id,
                record.trace_id,
            )
            raise ConversationStoreError(
                "Conversation history persistence failed."
            ) from exc

    def _query_session_entities(
        self,
        *,
        session_id: str,
        select: list[str] | None = None,
    ) -> Iterable[dict[str, object]]:
        return self._table_client.query_entities(
            "PartitionKey eq @session_id",
            parameters={"session_id": session_id},
            select=select,
        )

    @staticmethod
    def _build_entity(
        *,
        record: ConversationTurnRecord,
        row_key: str,
    ) -> dict[str, object]:
        return {
            "PartitionKey": record.session_id.strip(),
            "RowKey": row_key,
            "user_query": record.user_query,
            "assistant_answer": record.assistant_answer,
            "created_at": record.created_at,
            "trace_id": record.trace_id,
            "knowledge_domain": (record.knowledge_domain or "").strip(),
            "tokens_used": int(record.tokens_used),
            "latency_ms": float(record.latency_ms),
            "sources_json": json.dumps(record.sources, ensure_ascii=False),
        }

    @staticmethod
    def _to_turn(entity: dict[str, object]) -> ConversationTurn:
        return ConversationTurn(
            row_key=str(entity.get("RowKey", "")),
            user_query=str(entity.get("user_query", "") or ""),
            assistant_answer=str(entity.get("assistant_answer", "") or ""),
            created_at=str(entity.get("created_at", "") or ""),
            trace_id=str(entity.get("trace_id", "") or ""),
            knowledge_domain=_normalize_optional_text(entity.get("knowledge_domain")),
            tokens_used=int(entity.get("tokens_used", 0) or 0),
            latency_ms=float(entity.get("latency_ms", 0.0) or 0.0),
            sources_json=str(entity.get("sources_json", "") or ""),
        )

    @staticmethod
    def _build_next_row_key(entities: list[dict[str, object]]) -> str:
        max_turn_index = 0
        for entity in entities:
            row_key = str(entity.get("RowKey", "") or "")
            match = _ROW_KEY_PATTERN.match(row_key)
            if match is None:
                continue
            max_turn_index = max(max_turn_index, int(match.group(1)))
        return f"turn_{max_turn_index + 1:06d}"


def build_created_at_timestamp(now: datetime | None = None) -> str:
    effective_now = now or datetime.now(UTC)
    return effective_now.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize_optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
