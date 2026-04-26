from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser


SUPPORTED_SOURCE_TYPES = {
    "markdown_curated",
    "plain_text",
    "html_page",
    "pdf_document",
    "docx_document",
}


def normalize_source(
    raw_content: str,
    source_type: str,
    knowledge_domain: str,
    document_name: str,
    source_url: str | None = None,
) -> dict:
    """Normalize raw document content into the canonical document structure."""
    if not isinstance(raw_content, str):
        raise ValueError("raw_content must be a string.")
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(
            f"Unsupported source_type '{source_type}'. Supported values: "
            f"{', '.join(sorted(SUPPORTED_SOURCE_TYPES))}."
        )
    if not knowledge_domain or not knowledge_domain.strip():
        raise ValueError("knowledge_domain is required.")
    if not document_name or not document_name.strip():
        raise ValueError("document_name is required.")

    if source_type == "markdown_curated":
        normalized = _normalize_markdown_curated(
            raw_content=raw_content,
            knowledge_domain=knowledge_domain,
            document_name=document_name,
            source_url=source_url,
        )
    elif source_type == "plain_text":
        normalized = _normalize_plain_text(
            raw_content=raw_content,
            knowledge_domain=knowledge_domain,
            document_name=document_name,
            source_url=source_url,
        )
    elif source_type == "pdf_document":
        normalized = _normalize_text_document(
            raw_content=raw_content,
            knowledge_domain=knowledge_domain,
            document_name=document_name,
            source_url=source_url,
            source_type="pdf_document",
        )
    elif source_type == "docx_document":
        normalized = _normalize_text_document(
            raw_content=raw_content,
            knowledge_domain=knowledge_domain,
            document_name=document_name,
            source_url=source_url,
            source_type="docx_document",
        )
    else:
        normalized = _normalize_html_page(
            raw_content=raw_content,
            knowledge_domain=knowledge_domain,
            document_name=document_name,
            source_url=source_url,
        )

    return normalized


def _normalize_markdown_curated(
    raw_content: str,
    knowledge_domain: str,
    document_name: str,
    source_url: str | None,
) -> dict:
    front_matter, markdown_body = _extract_front_matter(raw_content)
    title = _first_non_empty_string(
        front_matter.get("title"),
        document_name,
    )

    metadata = dict(front_matter)

    return {
        "title": title,
        "knowledge_domain": _first_non_empty_string(
            front_matter.get("knowledge_domain"),
            knowledge_domain,
        ),
        "source_type": "markdown_curated",
        "document_name": document_name,
        "source_url": source_url,
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "content": _markdown_to_text(markdown_body),
    }


def _normalize_plain_text(
    raw_content: str,
    knowledge_domain: str,
    document_name: str,
    source_url: str | None,
) -> dict:
    return _normalize_text_document(
        raw_content=raw_content,
        knowledge_domain=knowledge_domain,
        document_name=document_name,
        source_url=source_url,
        source_type="plain_text",
    )


def _normalize_text_document(
    raw_content: str,
    knowledge_domain: str,
    document_name: str,
    source_url: str | None,
    source_type: str,
) -> dict:
    metadata = {
        "content_type": source_type,
    }
    if source_url:
        metadata["source_url"] = source_url

    return {
        "title": document_name,
        "knowledge_domain": knowledge_domain,
        "source_type": source_type,
        "document_name": document_name,
        "source_url": source_url,
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "content": raw_content,
    }


def _normalize_html_page(
    raw_content: str,
    knowledge_domain: str,
    document_name: str,
    source_url: str | None,
) -> dict:
    metadata = {
        "content_type": "html_page",
    }
    if source_url:
        metadata["source_url"] = source_url

    return {
        "title": document_name,
        "knowledge_domain": knowledge_domain,
        "source_type": "html_page",
        "document_name": document_name,
        "source_url": source_url,
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "content": _html_to_text(raw_content),
    }


def _extract_front_matter(raw_content: str) -> tuple[dict, str]:
    normalized = raw_content.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return {}, raw_content

    end_marker = normalized.find("\n---\n", 4)
    if end_marker == -1:
        return {}, raw_content

    front_matter_block = normalized[4:end_marker]
    body = normalized[end_marker + 5 :]
    return _parse_simple_yaml(front_matter_block), body


def _parse_simple_yaml(front_matter_block: str) -> dict:
    metadata: dict[str, object] = {}

    for raw_line in front_matter_block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue

        key, value = line.split(":", 1)
        parsed_key = key.strip()
        parsed_value = value.strip().strip("\"'")
        if parsed_key:
            metadata[parsed_key] = parsed_value

    return metadata


def _markdown_to_text(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__|\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return _normalize_whitespace(unescape(text))


def _html_to_text(html_content: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html_content)
    parser.close()
    return _normalize_whitespace(unescape(parser.get_text()))


def _normalize_whitespace(text: str) -> str:
    normalized = text.replace("\ufeff", "").replace("\u00a0", " ")
    normalized = re.sub(r"[^\S\n]+", " ", normalized)
    normalized = "\n".join(line.strip() for line in normalized.splitlines())
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _first_non_empty_string(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


class _HTMLTextExtractor(HTMLParser):
    """Collect textual HTML content while ignoring tags and noisy blocks."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._ignored_tag_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_tag_depth += 1
            return
        if self._ignored_tag_depth == 0 and tag in {"p", "div", "br", "li", "section"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_tag_depth > 0:
            self._ignored_tag_depth -= 1
            return
        if self._ignored_tag_depth == 0 and tag in {"p", "div", "li", "section"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_tag_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)
