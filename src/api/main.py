import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router


DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _get_cors_allowed_origins() -> list[str]:
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS")
    if raw_value is None or not raw_value.strip():
        return list(DEFAULT_CORS_ALLOWED_ORIGINS)

    origins = [
        origin.strip()
        for origin in raw_value.split(",")
        if origin.strip()
    ]
    return origins or list(DEFAULT_CORS_ALLOWED_ORIGINS)


app = FastAPI(title="Architecture Governance Copilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
