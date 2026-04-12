"""Compatibility imports for the document processing pipeline."""

from apps.document_processor_function.processing.blob_reader import read_blob_text
from apps.document_processor_function.processing.document_processor import (
    chunk_text,
    clean_text,
    process_document,
    process_normalized_document,
    recursive_split,
)
from apps.document_processor_function.processing.embedding_service import (
    generate_embedding,
    vectorize_chunks,
)
from apps.document_processor_function.processing.search_indexer import index_chunks
from apps.document_processor_function.processing.source_normalizer import normalize_source

__all__ = [
    "chunk_text",
    "clean_text",
    "generate_embedding",
    "index_chunks",
    "normalize_source",
    "process_document",
    "process_normalized_document",
    "read_blob_text",
    "recursive_split",
    "vectorize_chunks",
]
