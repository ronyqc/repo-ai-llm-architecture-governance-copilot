from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.rag.retriever import AzureSearchRetriever, RetrievalRequest
from src.rag.vector_store import AzureSearchVectorStore, SearchQuery


class AzureSearchVectorStoreTests(unittest.TestCase):
    def test_search_builds_filter_and_normalizes_results(self) -> None:
        client = Mock()
        client.search.return_value = [
            {
                "id": "doc-1",
                "content": "chunk content",
                "title": "Architecture Guide",
                "knowledge_domain": "bian",
                "source_type": "pdf",
                "source_url": "https://example.com/doc-1",
                "document_name": "guide.pdf",
                "chunk_order": 2,
                "metadata": "{\"section\":\"intro\"}",
                "updated_at": "2026-04-13T22:00:00Z",
                "chunk_id": "guide.pdf#chunk-2",
                "@search.score": 1.23,
            }
        ]

        store = AzureSearchVectorStore(
            endpoint="https://example.search.windows.net",
            api_key="secret",
            index_name="idx-agc-knowledge-dev",
            client=client,
        )

        results = store.search(
            SearchQuery(
                text="architecture principles",
                top_k=3,
                score_threshold=0.5,
                knowledge_domain="bian",
            )
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_id, "doc-1")
        self.assertEqual(results[0].knowledge_domain, "bian")
        client.search.assert_called_once_with(
            search_text="architecture principles",
            filter="knowledge_domain eq 'bian'",
            top=3,
        )

    def test_search_applies_score_threshold(self) -> None:
        client = Mock()
        client.search.return_value = [
            {
                "id": "doc-1",
                "content": "chunk content",
                "title": "Architecture Guide",
                "knowledge_domain": "bian",
                "source_type": "pdf",
                "@search.score": 0.2,
            }
        ]

        store = AzureSearchVectorStore(
            endpoint="https://example.search.windows.net",
            api_key="secret",
            index_name="idx-agc-knowledge-dev",
            client=client,
        )

        results = store.search(
            SearchQuery(
                text="architecture principles",
                top_k=3,
                score_threshold=0.5,
            )
        )

        self.assertEqual(results, [])

    def test_invalid_knowledge_domain_raises_error(self) -> None:
        store = AzureSearchVectorStore(
            endpoint="https://example.search.windows.net",
            api_key="secret",
            index_name="idx-agc-knowledge-dev",
            client=Mock(),
        )

        with self.assertRaises(ValueError):
            store.search(
                SearchQuery(
                    text="architecture principles",
                    top_k=3,
                    knowledge_domain="invalid",
                )
            )


class AzureSearchRetrieverTests(unittest.TestCase):
    def test_retrieve_uses_default_settings_values(self) -> None:
        vector_store = Mock()
        vector_store.search.return_value = []

        retriever = AzureSearchRetriever(
            vector_store=vector_store,
            default_top_k=5,
            default_score_threshold=0.4,
        )

        retriever.retrieve(RetrievalRequest(query="target operating model"))

        vector_store.search.assert_called_once()
        search_query = vector_store.search.call_args.args[0]
        self.assertEqual(search_query.text, "target operating model")
        self.assertEqual(search_query.top_k, 5)
        self.assertEqual(search_query.score_threshold, 0.4)
        self.assertIsNone(search_query.knowledge_domain)


if __name__ == "__main__":
    unittest.main()
