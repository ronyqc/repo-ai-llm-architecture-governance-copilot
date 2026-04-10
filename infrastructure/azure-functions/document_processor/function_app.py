from __future__ import annotations

import json
import sys
from pathlib import Path

import azure.functions as func
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.processing.document_processor import process_document
from src.processing.embedding_service import vectorize_chunks
from src.processing.search_indexer import index_chunks as upload_chunks_to_search


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

REQUIRED_FIELDS = ("file_path", "knowledge_domain", "source_type")


@app.route(route="processDocument", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def process_document_http(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return _json_response(
            {"status": "error", "message": "Request body must be valid JSON."},
            status_code=400,
        )

    missing_fields = [field for field in REQUIRED_FIELDS if not payload.get(field)]
    if missing_fields:
        return _json_response(
            {
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing_fields)}",
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
        chunks = process_document(
            file_path=payload["file_path"],
            knowledge_domain=payload["knowledge_domain"],
            source_type=payload["source_type"],
        )
    except (ValueError, FileNotFoundError) as exc:
        return _json_response(
            {"status": "error", "message": str(exc)},
            status_code=400,
        )

    try:
        chunks = vectorize_chunks(chunks)
    except ValueError as exc:
        return _json_response(
            {"status": "error", "message": str(exc)},
            status_code=400,
        )
    except Exception as exc:
        return _json_response(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )

    indexed_count = 0
    failed_count = 0

    if should_index_chunks:
        try:
            indexing_summary = upload_chunks_to_search(chunks)
        except ValueError as exc:
            return _json_response(
                {"status": "error", "message": str(exc)},
                status_code=400,
            )
        except Exception as exc:
            return _json_response(
                {"status": "error", "message": str(exc)},
                status_code=500,
            )

        indexed_count = indexing_summary["indexed_count"]
        failed_count = indexing_summary["failed_count"]

    return _json_response(
        {
            "status": "success",
            "chunks_count": len(chunks),
            "indexed_count": indexed_count,
            "failed_count": failed_count,
        }
    )


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
