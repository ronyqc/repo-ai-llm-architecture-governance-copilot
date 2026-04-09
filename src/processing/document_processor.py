from __future__ import annotations

import re
import sys
import uuid
import json
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

    content = path.read_text(encoding="utf-8")
    chunks = chunk_text(content)
    updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    document_name = path.name
    metadata = json.dumps(
        {
            "document_id": path.stem,
            "document_version": "",
            "section": "",
            "uploaded_by": "",
            "source_system": "offline_document_processor",
        }
    )

    records = [
        {
            "id": str(uuid.uuid4()),
            "chunk_id": f"{document_name}#chunk-{chunk_order}",
            "chunk_order": chunk_order,
            "content": chunk,
            "title": document_name,
            "knowledge_domain": knowledge_domain,
            "source_type": source_type,
            "source_url": None,
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
