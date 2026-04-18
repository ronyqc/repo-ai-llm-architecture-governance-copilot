from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from src.core.config import Settings, settings
from src.core.llm_client import (
    AzureOpenAILLMClient,
    AzureOpenAILLMConfigurationError,
    AzureOpenAILLMError,
)
from src.integrations.confluence_client import (
    ConfluenceCloudClient,
    ConfluenceConfigurationError,
    ConfluenceError,
)
from src.rag.vector_store import (
    AzureSearchConfigurationError,
    AzureSearchQueryError,
    AzureSearchVectorStore,
)
from src.utils.logger import get_logger


logger = get_logger(__name__)

HealthCheckCallable = Callable[[float], None]


@dataclass(frozen=True)
class HealthReport:
    """Normalized health report returned by the health endpoint."""

    status: str
    components: dict[str, str]
    timestamp: str


class SystemHealthService:
    """Runs lightweight dependency checks without blocking the full endpoint unnecessarily."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        azure_openai_check: HealthCheckCallable | None = None,
        azure_search_check: HealthCheckCallable | None = None,
        confluence_check: HealthCheckCallable | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._azure_openai_check = azure_openai_check or self._check_azure_openai
        self._azure_search_check = azure_search_check or self._check_azure_search
        self._confluence_check = confluence_check or self._check_confluence

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "SystemHealthService":
        return cls(timeout_seconds=app_settings.HEALTHCHECK_TIMEOUT_SECONDS)

    def check(self) -> HealthReport:
        timestamp = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        components: dict[str, str] = {"backend": "healthy"}
        checks = {
            "azure_openai": self._azure_openai_check,
            "azure_ai_search": self._azure_search_check,
            "confluence": self._confluence_check,
        }

        logger.info(
            "Health check started. timeout_seconds=%s components=%s",
            self._timeout_seconds,
            ",".join(checks.keys()),
        )
        with ThreadPoolExecutor(max_workers=len(checks)) as executor:
            futures = {
                name: executor.submit(checker, self._timeout_seconds)
                for name, checker in checks.items()
            }
            for name, future in futures.items():
                try:
                    future.result(timeout=self._timeout_seconds)
                    components[name] = "healthy"
                    logger.info("Health check passed. component=%s", name)
                except TimeoutError:
                    components[name] = "unhealthy"
                    logger.warning(
                        "Health check timed out. component=%s timeout_seconds=%s",
                        name,
                        self._timeout_seconds,
                    )
                except Exception as exc:
                    components[name] = "unhealthy"
                    logger.warning(
                        "Health check failed. component=%s error=%s",
                        name,
                        str(exc),
                    )

        overall_status = (
            "healthy"
            if all(status == "healthy" for status in components.values())
            else "degraded"
        )
        logger.info(
            "Health check completed. status=%s components=%s",
            overall_status,
            components,
        )
        return HealthReport(
            status=overall_status,
            components=components,
            timestamp=timestamp,
        )

    @staticmethod
    def _check_azure_openai(timeout_seconds: float) -> None:
        client = AzureOpenAILLMClient.from_settings()
        client.check_health(timeout_seconds)

    @staticmethod
    def _check_azure_search(timeout_seconds: float) -> None:
        vector_store = AzureSearchVectorStore.from_settings()
        vector_store.check_health(timeout_seconds)

    @staticmethod
    def _check_confluence(timeout_seconds: float) -> None:
        client = ConfluenceCloudClient.from_settings()
        client.check_health(timeout_seconds)


__all__ = [
    "AzureOpenAILLMConfigurationError",
    "AzureOpenAILLMError",
    "AzureSearchConfigurationError",
    "AzureSearchQueryError",
    "ConfluenceConfigurationError",
    "ConfluenceError",
    "HealthReport",
    "SystemHealthService",
]
