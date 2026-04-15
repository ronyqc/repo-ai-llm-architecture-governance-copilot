from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return int(raw_value.strip())


def _get_env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return float(raw_value.strip())


@dataclass(frozen=True)
class Settings:
    ENVIRONMENT: str = _get_env("ENVIRONMENT", "development")
    LOG_LEVEL: str = _get_env("LOG_LEVEL", "INFO")
    AZURE_OPENAI_ENDPOINT: str = _get_env(
        "AZURE_OPENAI_ENDPOINT",
        "https://localhost-openai.openai.azure.com/",
    )
    AZURE_OPENAI_API_KEY: str = _get_env(
        "AZURE_OPENAI_API_KEY",
        "dev-openai-api-key",
    )
    AZURE_OPENAI_DEPLOYMENT: str = _get_env(
        "AZURE_OPENAI_DEPLOYMENT",
        "gpt-4o-mini",
    )
    AZURE_SEARCH_ENDPOINT: str = _get_env(
        "AZURE_SEARCH_ENDPOINT",
        "https://localhost-search.search.windows.net",
    )
    AZURE_SEARCH_KEY: str = _get_env("AZURE_SEARCH_KEY", "dev-search-key")
    AZURE_SEARCH_INDEX: str = _get_env(
        "AZURE_SEARCH_INDEX",
        "idx-agc-knowledge-dev",
    )
    AZURE_SEARCH_TOP_K: int = _get_env_int("AZURE_SEARCH_TOP_K", 5)
    AZURE_SEARCH_SCORE_THRESHOLD: float = _get_env_float(
        "AZURE_SEARCH_SCORE_THRESHOLD",
        0.2,  # Avoid 0.0 so low-signal keyword matches do not pass by default.
    )
    AZURE_STORAGE_CONNECTION_STRING: str = _get_env(
        "AZURE_STORAGE_CONNECTION_STRING",
        "UseDevelopmentStorage=true",
    )
    AZURE_TENANT_ID: str = _get_env("AZURE_TENANT_ID")
    AZURE_CLIENT_ID: str = _get_env("AZURE_CLIENT_ID")
    AZURE_API_AUDIENCE: str = _get_env("AZURE_API_AUDIENCE")
    AZURE_JWKS_URL: str = _get_env("AZURE_JWKS_URL")
    REQUIRE_ADMIN_FOR_INGEST: bool = _get_env_bool(
        "REQUIRE_ADMIN_FOR_INGEST",
        False,
    )

    @property
    def azure_jwks_url(self) -> str:
        if self.AZURE_JWKS_URL:
            return self.AZURE_JWKS_URL

        if not self.AZURE_TENANT_ID:
            return ""

        return (
            f"https://login.microsoftonline.com/"
            f"{self.AZURE_TENANT_ID}/discovery/v2.0/keys"
        )

    @property
    def azure_issuer(self) -> str:
        if not self.AZURE_TENANT_ID:
            return ""

        return f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}/v2.0"

    @property
    def azure_issuers(self) -> tuple[str, ...]:
        if not self.AZURE_TENANT_ID:
            return ()

        return (
            f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}/v2.0",
            f"https://sts.windows.net/{self.AZURE_TENANT_ID}/",
        )


settings = Settings()
