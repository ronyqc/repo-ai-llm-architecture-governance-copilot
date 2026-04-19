from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from apps.document_processor_function.processing.content_extractors import (
    extract_text_from_bytes,
)
from apps.document_processor_function.processing.document_processor import (
    process_normalized_document,
)
from apps.document_processor_function.processing.source_normalizer import normalize_source


def _build_docx_bytes(*paragraphs: str) -> bytes:
    document_xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        "<w:body>",
    ]
    for paragraph in paragraphs:
        document_xml.append("<w:p><w:r><w:t>")
        document_xml.append(paragraph)
        document_xml.append("</w:t></w:r></w:p>")
    document_xml.extend(["</w:body>", "</w:document>"])

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "".join(document_xml))
    return buffer.getvalue()


class _FakePdfPage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdfReader:
    def __init__(self, pages: list[_FakePdfPage]) -> None:
        self.pages = pages


class ContentExtractorTests(unittest.TestCase):
    def test_extracts_html_content_successfully(self) -> None:
        result = extract_text_from_bytes(
            b"<html><body><h1>Architecture</h1><p>Guideline</p></body></html>",
            file_name="guide.html",
        )

        self.assertEqual(result["source_type"], "html_page")
        self.assertIn("Architecture", result["content"])
        self.assertIn("Guideline", result["content"])

    def test_extracts_plain_text_successfully(self) -> None:
        result = extract_text_from_bytes(
            b"Line one\nLine two",
            file_name="guide.txt",
        )

        self.assertEqual(result["source_type"], "plain_text")
        self.assertEqual(result["content"], "Line one\nLine two")

    def test_extracts_markdown_successfully(self) -> None:
        result = extract_text_from_bytes(
            b"# Title\n\n- Item",
            file_name="guide.md",
        )

        self.assertEqual(result["source_type"], "markdown_curated")
        self.assertIn("# Title", result["content"])

    @patch("apps.document_processor_function.processing.content_extractors._build_pdf_reader")
    def test_extracts_pdf_successfully(self, build_pdf_reader: object) -> None:
        build_pdf_reader.return_value = _FakePdfReader(
            [_FakePdfPage("PDF page 1"), _FakePdfPage("PDF page 2")]
        )

        result = extract_text_from_bytes(
            b"%PDF-1.4 fake",
            file_name="guide.pdf",
        )

        self.assertEqual(result["source_type"], "pdf_document")
        self.assertEqual(result["content"], "PDF page 1\n\nPDF page 2")

    def test_extracts_docx_successfully(self) -> None:
        docx_bytes = _build_docx_bytes("First paragraph", "Second paragraph")

        result = extract_text_from_bytes(
            docx_bytes,
            file_name="guide.docx",
        )

        self.assertEqual(result["source_type"], "docx_document")
        self.assertIn("First paragraph", result["content"])
        self.assertIn("Second paragraph", result["content"])

    def test_rejects_unsupported_format(self) -> None:
        with self.assertRaises(ValueError) as context:
            extract_text_from_bytes(b"binary", file_name="guide.xlsx")

        self.assertIn("Unsupported file format", str(context.exception))

    @patch("apps.document_processor_function.processing.content_extractors._build_pdf_reader")
    def test_normalized_pdf_content_still_uses_existing_chunking(self, build_pdf_reader: object) -> None:
        build_pdf_reader.return_value = _FakePdfReader(
            [_FakePdfPage("A" * 1200)]
        )
        extracted = extract_text_from_bytes(b"%PDF-1.4 fake", file_name="guide.pdf")
        normalized = normalize_source(
            raw_content=extracted["content"],
            source_type=extracted["source_type"],
            knowledge_domain="bian",
            document_name="guide.pdf",
            source_url="blob://documents/guide.pdf",
        )

        chunks = process_normalized_document(normalized)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["source_type"], "pdf_document")
        self.assertEqual(chunks[0]["document_name"], "guide.pdf")


if __name__ == "__main__":
    unittest.main()
