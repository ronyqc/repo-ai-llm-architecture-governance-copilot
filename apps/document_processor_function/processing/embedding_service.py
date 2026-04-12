from __future__ import annotations

import json
import os
from typing import Any

from openai import AzureOpenAI


EMBEDDING_MODEL_NAME = "text-embedding-3-large"


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the provided text using Azure OpenAI."""
    if not text or not text.strip():
        raise ValueError("Cannot generate an embedding for empty text.")

    endpoint = _get_required_env("AZURE_OPENAI_ENDPOINT")
    api_key = _get_required_env("AZURE_OPENAI_API_KEY")
    api_version = _get_required_env("AZURE_OPENAI_API_VERSION")
    deployment = _get_required_env("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")
    dimensions = _get_dimensions()

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    try:
        response = client.embeddings.create(
            model=deployment,
            input=text,
            dimensions=dimensions,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to generate embedding: {exc}") from exc

    embedding = response.data[0].embedding
    if len(embedding) != dimensions:
        raise RuntimeError(
            "Embedding dimension mismatch: "
            f"expected {dimensions}, received {len(embedding)}."
        )

    return embedding


def vectorize_chunks(chunks: list[dict]) -> list[dict]:
    """Enrich chunk records with embeddings and embedding metadata."""
    enriched_chunks: list[dict] = []
    dimensions = _get_dimensions()

    for chunk in chunks:
        content = chunk.get("content")
        if not isinstance(content, str) or not content.strip():
            chunk_id = chunk.get("chunk_id") or chunk.get("id") or "unknown"
            raise ValueError(f"Chunk '{chunk_id}' does not contain valid content.")

        enriched_chunk = dict(chunk)
        enriched_chunk["content_vector"] = generate_embedding(content)
        enriched_chunk["metadata"] = json.dumps(
            _enrich_metadata(enriched_chunk.get("metadata"), dimensions),
            ensure_ascii=False,
        )
        enriched_chunks.append(enriched_chunk)

    return enriched_chunks


def _enrich_metadata(metadata: Any, dimensions: int) -> dict[str, Any]:
    if metadata is None:
        metadata_dict: dict[str, Any] = {}
    elif isinstance(metadata, str):
        try:
            loaded_metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise ValueError("Chunk metadata must contain valid JSON.") from exc
        if not isinstance(loaded_metadata, dict):
            raise ValueError("Chunk metadata JSON must deserialize to an object.")
        metadata_dict = loaded_metadata
    elif isinstance(metadata, dict):
        metadata_dict = dict(metadata)
    else:
        raise ValueError("Chunk metadata must be a JSON string or a dictionary.")

    metadata_dict["embedding_model"] = EMBEDDING_MODEL_NAME
    metadata_dict["embedding_dimensions"] = dimensions
    return metadata_dict


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable '{name}' is required.")
    return value


def _get_dimensions() -> int:
    raw_dimensions = _get_required_env("AZURE_OPENAI_EMBEDDINGS_DIMENSIONS")
    try:
        dimensions = int(raw_dimensions)
    except ValueError as exc:
        raise ValueError(
            "Environment variable 'AZURE_OPENAI_EMBEDDINGS_DIMENSIONS' must be an integer."
        ) from exc

    if dimensions <= 0:
        raise ValueError(
            "Environment variable 'AZURE_OPENAI_EMBEDDINGS_DIMENSIONS' must be greater than zero."
        )

    return dimensions
