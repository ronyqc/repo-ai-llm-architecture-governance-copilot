from __future__ import annotations

import json
import sys
from pathlib import Path

import azure.functions as func


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.document_processor import process_document


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
    except Exception:
        return _json_response(
            {"status": "error", "message": "Internal server error."},
            status_code=500,
        )

    return _json_response(
        {
            "status": "success",
            "chunks_count": len(chunks),
            "chunks": chunks,
        }
    )


def _json_response(body: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(body, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json",
    )
