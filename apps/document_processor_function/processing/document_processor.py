from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200


def clean_text(text: str) -> str:
    """Apply basic text cleanup without summarizing or reinterpreting content."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "").replace("\u00a0", " ")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]", "", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def recursive_split(text: str) -> list[str]:
    """Split text recursively by paragraphs, sentences and character boundaries."""
    return _recursive_split(text, DEFAULT_CHUNK_SIZE)


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Create coherent chunks with a sliding window overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to zero")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    cleaned_text = clean_text(text)
    if not cleaned_text:
        return []

    fragments = _recursive_split(cleaned_text, chunk_size)
    chunks: list[str] = []
    current = ""

    for fragment in fragments:
        candidate = _join_fragments(current, fragment)

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = _overlap_prefix(current, overlap)
            candidate = _join_fragments(current, fragment)

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        current = fragment

    if current:
        chunks.append(current)

    return chunks


def process_document(
    file_path: str,
    knowledge_domain: str,
    source_type: str,
) -> list[dict]:
    """Process a local .txt document into chunk records for later ingestion."""
    path = Path(file_path)

    if path.suffix.lower() != ".txt":
        raise ValueError("Only .txt files are supported at this stage")
    if not path.is_file():
        raise FileNotFoundError(f"Document not found: {file_path}")

    normalized_document = {
        "title": path.name,
        "knowledge_domain": knowledge_domain,
        "source_type": source_type,
        "document_name": path.name,
        "source_url": None,
        "metadata": json.dumps(
            {
                "document_id": path.stem,
                "document_version": "",
                "section": "",
                "uploaded_by": "",
                "source_system": "offline_document_processor",
            }
        ),
        "content": path.read_text(encoding="utf-8"),
    }
    return process_normalized_document(normalized_document)


def process_normalized_document(normalized_document: dict) -> list[dict]:
    """Process normalized content into chunk records for embedding and indexing."""
    required_fields = (
        "title",
        "knowledge_domain",
        "source_type",
        "document_name",
        "metadata",
        "content",
    )

    if not isinstance(normalized_document, dict):
        raise ValueError("normalized_document must be a dictionary.")

    missing_fields = [
        field for field in required_fields if field not in normalized_document
    ]
    if missing_fields:
        raise ValueError(
            "normalized_document is missing required fields: "
            f"{', '.join(missing_fields)}"
        )

    content = normalized_document["content"]
    if not isinstance(content, str):
        raise ValueError("normalized_document['content'] must be a string.")

    title = normalized_document["title"]
    knowledge_domain = normalized_document["knowledge_domain"]
    source_type = normalized_document["source_type"]
    document_name = normalized_document["document_name"]
    source_url = normalized_document.get("source_url")
    metadata = normalized_document["metadata"]

    if not isinstance(title, str) or not title.strip():
        raise ValueError("normalized_document['title'] must be a non-empty string.")
    if not isinstance(knowledge_domain, str) or not knowledge_domain.strip():
        raise ValueError(
            "normalized_document['knowledge_domain'] must be a non-empty string."
        )
    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError(
            "normalized_document['source_type'] must be a non-empty string."
        )
    if not isinstance(document_name, str) or not document_name.strip():
        raise ValueError(
            "normalized_document['document_name'] must be a non-empty string."
        )
    if source_url is not None and not isinstance(source_url, str):
        raise ValueError("normalized_document['source_url'] must be a string or None.")
    if not isinstance(metadata, str):
        raise ValueError("normalized_document['metadata'] must be a JSON string.")

    chunks = chunk_text(content)
    updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = [
        {
            "id": str(uuid.uuid4()),
            "chunk_id": f"{document_name}#chunk-{chunk_order}",
            "chunk_order": chunk_order,
            "content": chunk,
            "title": title,
            "knowledge_domain": knowledge_domain,
            "source_type": source_type,
            "source_url": source_url,
            "document_name": document_name,
            "metadata": metadata,
            "updated_at": updated_at,
        }
        for chunk_order, chunk in enumerate(chunks, start=1)
    ]

    average_size = (
        sum(len(record["content"]) for record in records) / len(records)
        if records
        else 0
    )
    print(f"Chunks generated: {len(records)}")
    print(f"Average chunk size: {average_size:.2f} characters")
    return records


def _recursive_split(text: str, chunk_size: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    if len(paragraphs) > 1:
        return _split_parts(paragraphs, chunk_size)

    sentences = [part.strip() for part in re.split(r"(?<=\.)\s+", text) if part.strip()]
    if len(sentences) > 1:
        return _split_parts(sentences, chunk_size)

    return _split_by_characters(text, chunk_size)


def _split_parts(parts: list[str], chunk_size: int) -> list[str]:
    fragments: list[str] = []
    for part in parts:
        fragments.extend(_recursive_split(part, chunk_size))
    return fragments


def _split_by_characters(text: str, chunk_size: int) -> list[str]:
    fragments: list[str] = []
    remaining = text.strip()

    while len(remaining) > chunk_size:
        split_at = remaining.rfind(" ", 0, chunk_size + 1)
        if split_at <= 0:
            split_at = chunk_size

        fragments.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        fragments.append(remaining)

    return fragments


def _join_fragments(current: str, fragment: str) -> str:
    if not current:
        return fragment
    if not fragment:
        return current
    return f"{current}\n\n{fragment}"


def _overlap_prefix(text: str, overlap: int) -> str:
    if overlap == 0 or len(text) <= overlap:
        return text if overlap else ""

    prefix = text[-overlap:]
    split_at = prefix.find(" ")
    if split_at > 0:
        prefix = prefix[split_at + 1 :]

    return prefix.strip()


if __name__ == "__main__":
    processor_dir = Path(__file__).resolve().parent
    sample_file = Path(sys.argv[1]) if len(sys.argv) > 1 else processor_dir / "sample.txt"
    if not sample_file.exists() and not sample_file.is_absolute():
        sample_file = processor_dir / sample_file

    processed_chunks = process_document(
        file_path=str(sample_file),
        knowledge_domain="bian",
        source_type="txt",
    )

    for chunk in processed_chunks:
        print(chunk)
