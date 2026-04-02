from datetime import datetime, timezone

from fastapi import APIRouter


router = APIRouter()


@router.get("/api/v1/health")
def health_check() -> dict[str, object]:
    timestamp = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return {
        "status": "healthy",
        "components": {
            "backend": "healthy",
        },
        "timestamp": timestamp,
    }
