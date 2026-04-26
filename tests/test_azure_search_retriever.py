from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.rag.embeddings import AzureOpenAIEmbeddingClient
from src.rag.retriever import AzureSearchRetriever, RetrievalRequest
from src.rag.vector_store import AzureSearchVectorStore, SearchQuery


class AzureOpenAIEmbeddingClientTests(unittest.TestCase):
    def test_embed_query_calls_azure_openai_with_expected_dimensions(self) -> None:
        sdk_client = Mock()
        sdk_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1, 0.2, 0.3])]
        )

        client = AzureOpenAIEmbeddingClient(
            endpoint="https://example.openai.azure.com",
            api_key="secret",
            api_version="2024-02-01",
            deployment="text-embedding-3-large",
            dimensions=3,
            client=sdk_client,
        )

        result = client.embed_query("architecture principles")

        self.assertEqual(result, [0.1, 0.2, 0.3])
        sdk_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-large",
            input="architecture principles",
            dimensions=3,
        )


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
            vector_field="content_vector",
            vector_dimensions=3,
            client=client,
        )

        results = store.search(
            SearchQuery(
                text="architecture principles",
                top_k=3,
                score_threshold=0.5,
                knowledge_domain="bian",
                vector=[0.1, 0.2, 0.3],
            )
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_id, "doc-1")
        self.assertEqual(results[0].knowledge_domain, "bian")
        client.search.assert_called_once()
        call_kwargs = client.search.call_args.kwargs
        self.assertIsNone(call_kwargs["search_text"])
        self.assertEqual(call_kwargs["filter"], "knowledge_domain eq 'bian'")
        self.assertEqual(call_kwargs["top"], 3)
        self.assertEqual(len(call_kwargs["vector_queries"]), 1)

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
            vector_field="content_vector",
            vector_dimensions=3,
            client=client,
        )

        results = store.search(
            SearchQuery(
                text="architecture principles",
                top_k=3,
                score_threshold=0.5,
                vector=[0.1, 0.2, 0.3],
            )
        )

        self.assertEqual(results, [])

    def test_invalid_knowledge_domain_raises_error(self) -> None:
        store = AzureSearchVectorStore(
            endpoint="https://example.search.windows.net",
            api_key="secret",
            index_name="idx-agc-knowledge-dev",
            vector_field="content_vector",
            vector_dimensions=3,
            client=Mock(),
        )

        with self.assertRaises(ValueError):
            store.search(
                SearchQuery(
                    text="architecture principles",
                    top_k=3,
                    knowledge_domain="invalid",
                    vector=[0.1, 0.2, 0.3],
                )
            )


class AzureSearchRetrieverTests(unittest.TestCase):
    def test_retrieve_uses_default_settings_values_and_embeds_query(self) -> None:
        vector_store = Mock()
        vector_store.search.return_value = []
        embedding_client = Mock()
        embedding_client.embed_query.return_value = [0.1, 0.2, 0.3]

        retriever = AzureSearchRetriever(
            vector_store=vector_store,
            embedding_client=embedding_client,
            default_top_k=5,
            default_score_threshold=0.4,
        )

        retriever.retrieve(RetrievalRequest(query="target operating model"))

        embedding_client.embed_query.assert_called_once_with("target operating model")
        vector_store.search.assert_called_once()
        search_query = vector_store.search.call_args.args[0]
        self.assertEqual(search_query.text, "target operating model")
        self.assertEqual(search_query.top_k, 5)
        self.assertEqual(search_query.score_threshold, 0.4)
        self.assertIsNone(search_query.knowledge_domain)
        self.assertEqual(search_query.vector, [0.1, 0.2, 0.3])


if __name__ == "__main__":
    unittest.main()
