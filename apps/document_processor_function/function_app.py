from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import azure.functions as func

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

from processing.blob_reader import read_blob_bytes
from processing.content_extractors import (
    SUPPORTED_FILE_SOURCE_TYPES,
    extract_text_from_bytes,
    infer_source_type_from_file_name,
)
from processing.document_processor import process_normalized_document
from processing.embedding_service import vectorize_chunks
from processing.search_indexer import index_chunks as upload_chunks_to_search
from processing.source_normalizer import normalize_source


if load_dotenv is not None:
    load_dotenv(Path(__file__).resolve().parent / ".env")


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

LOCAL_MODE_REQUIRED_FIELDS = ("file_path", "knowledge_domain", "source_type")
BLOB_MODE_REQUIRED_FIELDS = (
    "container_name",
    "blob_name",
    "knowledge_domain",
    "source_type",
)
BLOB_TRIGGER_PATH = "%DOCUMENTS_CONTAINER_NAME%/{name}"
DEFAULT_BLOB_SOURCE_SYSTEM = "azure_blob_trigger"
DEFAULT_BLOB_UPLOADED_BY = "system"
SUPPORTED_SOURCE_TYPES = set(SUPPORTED_FILE_SOURCE_TYPES.values())


@app.route(route="processDocument", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def process_document_http(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return _json_response(
            {"status": "error", "message": "Request body must be valid JSON."},
            status_code=400,
        )

    if not isinstance(payload, dict):
        return _json_response(
            {
                "status": "error",
                "message": "Request body must be a JSON object.",
            },
            status_code=400,
        )

    try:
        should_index_chunks = _parse_boolean_flag(
            payload.get("index_chunks", True),
            field_name="index_chunks",
        )
    except ValueError as exc:
        return _json_response(
            {"status": "error", "message": str(exc)},
            status_code=400,
        )

    try:
        source_input = _resolve_source_input(payload)
        extracted_source = extract_text_from_bytes(
            source_input["content_bytes"],
            file_name=source_input["document_name"],
        )
        resolved_source_type = _resolve_http_source_type(
            requested_source_type=payload["source_type"],
            inferred_source_type=extracted_source["source_type"],
        )
        pipeline_result = _run_document_pipeline(
            raw_content=extracted_source["content"],
            knowledge_domain=payload["knowledge_domain"],
            source_type=resolved_source_type,
            document_name=source_input["document_name"],
            source_url=source_input.get("source_url"),
            document_metadata=None,
            should_index_chunks=should_index_chunks,
        )
    except (ValueError, FileNotFoundError) as exc:
        return _json_response(
            {"status": "error", "message": str(exc)},
            status_code=400,
        )
    except Exception as exc:
        return _json_response(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )

    normalized_document = pipeline_result["normalized_document"]
    return _json_response(
        {
            "status": "success",
            "chunks_count": pipeline_result["chunks_count"],
            "indexed_count": pipeline_result["indexed_count"],
            "failed_count": pipeline_result["failed_count"],
            "document_name": normalized_document["document_name"],
            "source_type": normalized_document["source_type"],
            "knowledge_domain": normalized_document["knowledge_domain"],
        }
    )


@app.function_name(name="processDocumentBlob")
@app.blob_trigger(
    arg_name="input_blob",
    path=BLOB_TRIGGER_PATH,
    connection="AzureWebJobsStorage",
    source="EventGrid",
)
def process_document_blob(input_blob: func.InputStream) -> None:
    blob_name = _extract_blob_name(input_blob)
    container_name = _extract_container_name(input_blob)
    document_name = _extract_document_name(blob_name)
    source_url = _build_blob_source_url(
        container_name=container_name,
        blob_name=blob_name,
        input_blob=input_blob,
    )

    logging.info(
        "Blob trigger started for blob '%s' in container '%s'.",
        blob_name,
        container_name,
    )

    try:
        blob_bytes = _read_trigger_blob_bytes(input_blob)
        extracted_source = extract_text_from_bytes(
            blob_bytes,
            file_name=document_name,
        )
        knowledge_domain, source_type = _resolve_blob_source_metadata(
            blob_name=blob_name,
            raw_content=extracted_source["content"],
            inferred_source_type=extracted_source["source_type"],
        )
        logging.info(
            "Resolved blob metadata -> domain=%s, source_type=%s, blob_name=%s",
            knowledge_domain,
            source_type,
            blob_name,
        )
        pipeline_result = _run_document_pipeline(
            raw_content=extracted_source["content"],
            knowledge_domain=knowledge_domain,
            source_type=source_type,
            document_name=document_name,
            source_url=source_url,
            document_metadata=_build_blob_trigger_metadata(
                container_name=container_name,
                blob_name=blob_name,
            ),
            should_index_chunks=True,
        )
    except Exception:
        logging.exception(
            "Blob trigger failed for blob '%s' in container '%s'.",
            blob_name,
            container_name,
        )
        raise

    logging.info(
        "Blob trigger completed for blob '%s'. chunks=%s indexed=%s failed=%s",
        blob_name,
        pipeline_result["chunks_count"],
        pipeline_result["indexed_count"],
        pipeline_result["failed_count"],
    )


def _run_document_pipeline(
    raw_content: str,
    knowledge_domain: str,
    source_type: str,
    document_name: str,
    source_url: str | None,
    document_metadata: dict | None,
    should_index_chunks: bool,
) -> dict:
    normalized_document = normalize_source(
        raw_content=raw_content,
        source_type=source_type,
        knowledge_domain=knowledge_domain,
        document_name=document_name,
        source_url=source_url,
    )
    normalized_document = _merge_document_metadata(normalized_document, document_metadata)
    chunks = process_normalized_document(normalized_document)
    vectorized_chunks = vectorize_chunks(chunks)

    indexed_count = 0
    failed_count = 0

    if should_index_chunks:
        indexing_summary = upload_chunks_to_search(vectorized_chunks)
        indexed_count = indexing_summary["indexed_count"]
        failed_count = indexing_summary["failed_count"]

    return {
        "normalized_document": normalized_document,
        "chunks_count": len(vectorized_chunks),
        "indexed_count": indexed_count,
        "failed_count": failed_count,
    }


def _merge_document_metadata(normalized_document: dict, extra_metadata: dict | None) -> dict:
    if not extra_metadata:
        return normalized_document

    merged_document = dict(normalized_document)
    metadata = _load_metadata_dict(merged_document.get("metadata"))
    metadata.update(extra_metadata)
    merged_document["metadata"] = json.dumps(metadata, ensure_ascii=False)
    return merged_document


def _load_metadata_dict(metadata: object) -> dict:
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return dict(metadata)
    if isinstance(metadata, str):
        if not metadata.strip():
            return {}
        try:
            loaded = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise ValueError("Document metadata must contain valid JSON.") from exc
        if not isinstance(loaded, dict):
            raise ValueError("Document metadata JSON must deserialize to an object.")
        return loaded

    raise ValueError("Document metadata must be a JSON string, a dictionary or None.")


def _build_blob_trigger_metadata(container_name: str, blob_name: str) -> dict:
    return {
        "document_id": Path(blob_name).stem,
        "document_version": "",
        "section": "",
        "uploaded_by": os.getenv("DEFAULT_UPLOADED_BY", DEFAULT_BLOB_UPLOADED_BY),
        "source_system": os.getenv(
            "DEFAULT_SOURCE_SYSTEM",
            DEFAULT_BLOB_SOURCE_SYSTEM,
        ),
        "blob_container": container_name,
        "blob_name": blob_name,
        "ingestion_mode": "blob_trigger",
    }


def _read_trigger_blob_bytes(input_blob: func.InputStream) -> bytes:
    try:
        return input_blob.read()
    except Exception as exc:
        raise RuntimeError("Failed to read blob content from trigger input.") from exc


def _resolve_blob_source_metadata(
    blob_name: str,
    raw_content: str,
    inferred_source_type: str | None,
) -> tuple[str, str]:
    yaml_metadata = _extract_yaml_metadata(raw_content)
    yaml_knowledge_domain = yaml_metadata.get("knowledge_domain", "").strip()
    yaml_source_type = yaml_metadata.get("source_type", "").strip()

    if yaml_knowledge_domain and yaml_source_type in SUPPORTED_SOURCE_TYPES:
        return yaml_knowledge_domain, yaml_source_type

    if yaml_source_type and yaml_source_type not in SUPPORTED_SOURCE_TYPES:
        logging.warning(
            "Ignoring unsupported YAML source_type '%s' for blob '%s'.",
            yaml_source_type,
            blob_name,
        )

    inferred_knowledge_domain = _infer_knowledge_domain_from_blob_name(blob_name)
    blob_name_source_type = _infer_source_type_from_blob_name(blob_name)

    knowledge_domain = (
        yaml_knowledge_domain
        or inferred_knowledge_domain
        or os.getenv("DEFAULT_KNOWLEDGE_DOMAIN", "general").strip()
        or "general"
    )
    source_type = (
        yaml_source_type if yaml_source_type in SUPPORTED_SOURCE_TYPES else ""
        or inferred_source_type
        or blob_name_source_type
        or os.getenv("DEFAULT_SOURCE_TYPE", "plain_text").strip()
        or "plain_text"
    )

    return knowledge_domain, source_type


def _extract_yaml_metadata(raw_content: str) -> dict[str, str]:
    normalized_content = raw_content.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized_content.startswith("---\n"):
        return {}

    end_marker = normalized_content.find("\n---\n", 4)
    if end_marker == -1:
        return {}

    metadata: dict[str, str] = {}
    front_matter_block = normalized_content[4:end_marker]

    for raw_line in front_matter_block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue

        key, value = line.split(":", 1)
        parsed_key = key.strip()
        parsed_value = value.strip().strip("\"'")
        if parsed_key and parsed_value:
            metadata[parsed_key] = parsed_value

    return metadata


def _infer_source_type_from_blob_name(blob_name: str) -> str | None:
    return infer_source_type_from_file_name(Path(blob_name).name)


def _infer_knowledge_domain_from_blob_name(blob_name: str) -> str | None:
    normalized_blob_name = blob_name.lower()

    if "guidelines" in normalized_blob_name or "patterns" in normalized_blob_name:
        return "guidelines_patterns"
    if "building" in normalized_blob_name or "blocks" in normalized_blob_name:
        return "building_blocks"
    if "bian" in normalized_blob_name:
        return "bian"

    return None


def _extract_blob_name(input_blob: func.InputStream) -> str:
    blob_path = getattr(input_blob, "name", "") or ""
    if not blob_path.strip():
        raise ValueError("Blob trigger input does not include a blob name.")

    parts = blob_path.split("/", 1)
    if len(parts) == 2:
        return parts[1]
    return parts[0]


def _extract_container_name(input_blob: func.InputStream) -> str:
    blob_path = getattr(input_blob, "name", "") or ""
    if not blob_path.strip():
        configured_container = os.getenv("DOCUMENTS_CONTAINER_NAME", "").strip()
        if configured_container:
            return configured_container
        raise ValueError("Blob trigger input does not include a container name.")

    return blob_path.split("/", 1)[0]


def _extract_document_name(blob_name: str) -> str:
    return Path(blob_name).name or blob_name


def _build_blob_source_url(
    container_name: str,
    blob_name: str,
    input_blob: func.InputStream,
) -> str:
    uri = getattr(input_blob, "uri", None)
    if isinstance(uri, str) and uri.strip():
        return uri
    return f"blob://{container_name}/{blob_name}"


def _json_response(body: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(body, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json",
    )


def _parse_boolean_flag(value: object, field_name: str) -> bool:
    """Parse an optional boolean flag from the request payload."""
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False

    raise ValueError(f"Field '{field_name}' must be a boolean value if provided.")


def _resolve_source_input(payload: dict) -> dict:
    """Resolve request payload to a raw content source from local disk or Blob Storage."""
    is_local_mode = bool(payload.get("file_path"))
    is_blob_mode = bool(payload.get("container_name")) or bool(payload.get("blob_name"))

    if is_local_mode and is_blob_mode:
        raise ValueError(
            "Provide either local mode fields ('file_path') or blob mode fields "
            "('container_name' and 'blob_name'), but not both."
        )
    if is_local_mode:
        _validate_required_fields(payload, LOCAL_MODE_REQUIRED_FIELDS)
        return _read_local_text(payload["file_path"])

    _validate_required_fields(payload, BLOB_MODE_REQUIRED_FIELDS)
    return read_blob_bytes(
        container_name=payload["container_name"],
        blob_name=payload["blob_name"],
    )


def _resolve_http_source_type(
    *,
    requested_source_type: str,
    inferred_source_type: str,
) -> str:
    if requested_source_type == inferred_source_type:
        return requested_source_type

    return inferred_source_type


def _validate_required_fields(payload: dict, required_fields: tuple[str, ...]) -> None:
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")


def _read_local_text(file_path: str) -> dict:
    """Read a local file and return canonical source input fields."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document not found: {file_path}")

    return {
        "document_name": path.name,
        "content_bytes": path.read_bytes(),
        "source_url": str(path),
    }


def _get_required_env(name: str, error_message: str | None = None) -> str:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()

    if error_message:
        raise ValueError(error_message)
    raise ValueError(f"Environment variable '{name}' is required.")
