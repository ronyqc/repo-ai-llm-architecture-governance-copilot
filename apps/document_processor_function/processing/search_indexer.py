from __future__ import annotations

import os

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal local envs
    AzureKeyCredential = None
    SearchClient = None


ALLOWED_KNOWLEDGE_DOMAINS = {
    "bian",
    "building_blocks",
    "guidelines_patterns",
}

REQUIRED_CHUNK_FIELDS = (
    "id",
    "chunk_id",
    "chunk_order",
    "content",
    "title",
    "knowledge_domain",
    "source_type",
    "source_url",
    "document_name",
    "metadata",
    "updated_at",
    "content_vector",
)


def index_chunks(chunks: list[dict]) -> dict:
    """Upload vectorized chunks to Azure AI Search and return an indexing summary."""
    endpoint = _get_required_env("AZURE_SEARCH_ENDPOINT")
    api_key = _get_required_env("AZURE_SEARCH_KEY")
    index_name = _get_required_env("AZURE_SEARCH_INDEX")

    _validate_chunks(chunks)
    if SearchClient is None or AzureKeyCredential is None:
        raise RuntimeError(
            "azure-search-documents and azure-core must be installed to index chunks."
        )

    client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(api_key),
    )

    try:
        results = client.upload_documents(documents=chunks)
    except Exception as exc:
        raise RuntimeError(f"Failed to index chunks in Azure AI Search: {exc}") from exc

    indexed_count = sum(1 for result in results if result.succeeded)
    failed_count = len(results) - indexed_count
    return {
        "indexed_count": indexed_count,
        "failed_count": failed_count,
    }


def _validate_chunks(chunks: list[dict]) -> None:
    if not isinstance(chunks, list):
        raise ValueError("Chunks must be provided as a list.")

    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ValueError("Each chunk must be a dictionary.")

        chunk_id = chunk.get("chunk_id") or chunk.get("id") or "unknown"

        for field in REQUIRED_CHUNK_FIELDS:
            if field not in chunk:
                raise ValueError(
                    f"Chunk '{chunk_id}' is missing required field '{field}'."
                )

        content_vector = chunk["content_vector"]
        if not isinstance(content_vector, list):
            raise ValueError(
                f"Chunk '{chunk_id}' has an invalid 'content_vector'; expected a list."
            )

        knowledge_domain = chunk["knowledge_domain"]
        if knowledge_domain not in ALLOWED_KNOWLEDGE_DOMAINS:
            raise ValueError(
                f"Chunk '{chunk_id}' has invalid knowledge_domain "
                f"'{knowledge_domain}'. Allowed values: "
                f"{', '.join(sorted(ALLOWED_KNOWLEDGE_DOMAINS))}."
            )


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable '{name}' is required.")
    return value
