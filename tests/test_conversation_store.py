from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from src.integrations.conversation_store import (
    AzureTableConversationStore,
    ConversationTurnRecord,
)


class AzureTableConversationStoreTests(unittest.TestCase):
    def test_get_recent_history_returns_last_n_turns_sorted_by_row_key(self) -> None:
        table_client = Mock()
        table_client.query_entities.return_value = [
            {
                "PartitionKey": "session-123",
                "RowKey": "turn_000002",
                "user_query": "Segundo turno",
                "assistant_answer": "Segunda respuesta",
                "created_at": "2026-04-20T12:01:00Z",
                "trace_id": "trace-2",
                "knowledge_domain": "guidelines_patterns",
                "tokens_used": 11,
                "latency_ms": 22.5,
                "sources_json": "[]",
            },
            {
                "PartitionKey": "session-123",
                "RowKey": "turn_000001",
                "user_query": "Primer turno",
                "assistant_answer": "Primera respuesta",
                "created_at": "2026-04-20T12:00:00Z",
                "trace_id": "trace-1",
                "knowledge_domain": "building_blocks",
                "tokens_used": 10,
                "latency_ms": 20.5,
                "sources_json": "[]",
            },
            {
                "PartitionKey": "session-123",
                "RowKey": "turn_000003",
                "user_query": "Tercer turno",
                "assistant_answer": "Tercera respuesta",
                "created_at": "2026-04-20T12:02:00Z",
                "trace_id": "trace-3",
                "knowledge_domain": "guidelines_patterns",
                "tokens_used": 12,
                "latency_ms": 24.5,
                "sources_json": "[]",
            },
        ]
        store = AzureTableConversationStore(
            table_client=table_client,
            table_name="ConversationHistory",
            default_history_limit=2,
        )

        history = store.get_recent_history(session_id="session-123")

        self.assertEqual([turn.row_key for turn in history], ["turn_000002", "turn_000003"])
        self.assertEqual(history[0].user_query, "Segundo turno")
        table_client.query_entities.assert_called_once_with(
            "PartitionKey eq @session_id",
            parameters={"session_id": "session-123"},
            select=None,
        )

    def test_append_turn_persists_expected_schema_and_next_row_key(self) -> None:
        table_client = Mock()
        table_client.query_entities.return_value = [
            {"RowKey": "turn_000001"},
            {"RowKey": "turn_000002"},
        ]
        store = AzureTableConversationStore(
            table_client=table_client,
            table_name="ConversationHistory",
            default_history_limit=3,
        )

        row_key = store.append_turn(
            ConversationTurnRecord(
                session_id="session-xyz",
                user_query="Que building blocks aplican?",
                assistant_answer="Se recomienda un gateway.",
                created_at="2026-04-20T12:10:00Z",
                trace_id="trace-123",
                knowledge_domain="building_blocks",
                tokens_used=123,
                latency_ms=45.6,
                sources=[
                    {
                        "source_id": "doc-1",
                        "source_type": "pdf",
                        "title": "Architecture Guide",
                        "score": 0.93,
                        "knowledge_domain": "building_blocks",
                    }
                ],
            )
        )

        self.assertEqual(row_key, "turn_000003")
        table_client.create_entity.assert_called_once()
        persisted_entity = table_client.create_entity.call_args.kwargs["entity"]
        self.assertEqual(persisted_entity["PartitionKey"], "session-xyz")
        self.assertEqual(persisted_entity["RowKey"], "turn_000003")
        self.assertEqual(persisted_entity["user_query"], "Que building blocks aplican?")
        self.assertEqual(persisted_entity["assistant_answer"], "Se recomienda un gateway.")
        self.assertEqual(persisted_entity["created_at"], "2026-04-20T12:10:00Z")
        self.assertEqual(persisted_entity["trace_id"], "trace-123")
        self.assertEqual(persisted_entity["knowledge_domain"], "building_blocks")
        self.assertEqual(persisted_entity["tokens_used"], 123)
        self.assertEqual(persisted_entity["latency_ms"], 45.6)
        self.assertEqual(
            json.loads(persisted_entity["sources_json"])[0]["source_id"],
            "doc-1",
        )


if __name__ == "__main__":
    unittest.main()
