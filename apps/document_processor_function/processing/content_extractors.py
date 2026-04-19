from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
import zipfile
from xml.etree import ElementTree


SUPPORTED_FILE_SOURCE_TYPES = {
    ".md": "markdown_curated",
    ".txt": "plain_text",
    ".html": "html_page",
    ".htm": "html_page",
    ".pdf": "pdf_document",
    ".docx": "docx_document",
}


def infer_source_type_from_file_name(file_name: str) -> str | None:
    suffix = PurePosixPath(file_name).suffix.lower()
    return SUPPORTED_FILE_SOURCE_TYPES.get(suffix)


def extract_text_from_bytes(blob_bytes: bytes, *, file_name: str) -> dict[str, str]:
    if not file_name or not file_name.strip():
        raise ValueError("file_name is required.")
    if not isinstance(blob_bytes, bytes):
        raise ValueError("blob_bytes must be bytes.")

    source_type = infer_source_type_from_file_name(file_name)
    if source_type is None:
        allowed = ", ".join(sorted(SUPPORTED_FILE_SOURCE_TYPES))
        raise ValueError(
            "Unsupported file format for document processing. "
            f"Allowed extensions: {allowed}."
        )

    if source_type in {"markdown_curated", "plain_text", "html_page"}:
        return {
            "source_type": source_type,
            "content": _decode_utf8_text(blob_bytes),
        }
    if source_type == "pdf_document":
        return {
            "source_type": source_type,
            "content": _extract_pdf_text(blob_bytes),
        }

    return {
        "source_type": source_type,
        "content": _extract_docx_text(blob_bytes),
    }


def _decode_utf8_text(blob_bytes: bytes) -> str:
    try:
        return blob_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Blob content could not be decoded as UTF-8.") from exc


def _extract_pdf_text(blob_bytes: bytes) -> str:
    try:
        reader = _build_pdf_reader(BytesIO(blob_bytes))
    except Exception as exc:
        raise ValueError("Failed to open PDF document for text extraction.") from exc

    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        normalized_text = page_text.strip()
        if normalized_text:
            parts.append(normalized_text)

    if not parts:
        raise ValueError("No readable text could be extracted from the PDF document.")

    return "\n\n".join(parts)


def _build_pdf_reader(stream: BytesIO) -> object:
    from pypdf import PdfReader

    return PdfReader(stream)


def _extract_docx_text(blob_bytes: bytes) -> str:
    try:
        archive = zipfile.ZipFile(BytesIO(blob_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("Failed to open DOCX document for text extraction.") from exc

    with archive:
        xml_names = [
            "word/document.xml",
            *sorted(
                name
                for name in archive.namelist()
                if name.startswith("word/header") or name.startswith("word/footer")
            ),
        ]
        xml_payloads = []
        for name in xml_names:
            if name in archive.namelist():
                xml_payloads.append(archive.read(name))

    if not xml_payloads:
        raise ValueError("The DOCX document does not contain readable XML content.")

    text_parts: list[str] = []
    for xml_payload in xml_payloads:
        text_parts.extend(_extract_docx_xml_text(xml_payload))

    extracted_text = "".join(text_parts).strip()
    if not extracted_text:
        raise ValueError("No readable text could be extracted from the DOCX document.")

    return extracted_text


def _extract_docx_xml_text(xml_payload: bytes) -> list[str]:
    root = ElementTree.fromstring(xml_payload)
    parts: list[str] = []

    for element in root.iter():
        tag = _local_name(element.tag)
        if tag == "t" and element.text:
            parts.append(element.text)
        elif tag == "tab":
            parts.append("\t")
        elif tag in {"br", "cr"}:
            parts.append("\n")
        elif tag == "p":
            parts.append("\n")

    return parts


def _local_name(tag: str) -> str:
    if "}" not in tag:
        return tag
    return tag.rsplit("}", 1)[-1]
