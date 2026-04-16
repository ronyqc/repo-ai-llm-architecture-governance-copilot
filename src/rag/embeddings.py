from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from openai import AzureOpenAI
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal local envs
    AzureOpenAI = Any

from src.core.config import Settings, settings


class AzureOpenAIEmbeddingConfigurationError(ValueError):
    """Raised when Azure OpenAI embedding settings are incomplete or invalid."""


class AzureOpenAIEmbeddingError(RuntimeError):
    """Raised when Azure OpenAI fails to generate query embeddings."""


@dataclass(frozen=True)
class EmbeddingRequest:
    """Stable input contract for query embedding generation."""

    text: str


class AzureOpenAIEmbeddingClient:
    """Small Azure OpenAI wrapper dedicated to query embeddings for retrieval."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        api_version: str,
        deployment: str,
        dimensions: int,
        client: Any | None = None,
    ) -> None:
        self._endpoint = endpoint.strip()
        self._api_key = api_key.strip()
        self._api_version = api_version.strip()
        self._deployment = deployment.strip()
        self._dimensions = dimensions
        self._validate_configuration()
        if client is None and AzureOpenAI is Any:
            raise AzureOpenAIEmbeddingConfigurationError(
                "openai must be installed to use AzureOpenAIEmbeddingClient "
                "without an injected client."
            )
        self._client = client or AzureOpenAI(
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            api_version=self._api_version,
        )

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "AzureOpenAIEmbeddingClient":
        return cls(
            endpoint=app_settings.AZURE_OPENAI_ENDPOINT,
            api_key=app_settings.AZURE_OPENAI_API_KEY,
            api_version=app_settings.AZURE_OPENAI_API_VERSION,
            deployment=app_settings.AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT,
            dimensions=app_settings.AZURE_OPENAI_EMBEDDINGS_DIMENSIONS,
        )

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_query(self, request: EmbeddingRequest | str) -> list[float]:
        normalized_request = self._normalize_request(request)

        try:
            response = self._client.embeddings.create(
                model=self._deployment,
                input=normalized_request.text,
                dimensions=self._dimensions,
            )
        except Exception as exc:  # pragma: no cover - SDK-specific failures
            raise AzureOpenAIEmbeddingError(
                "Azure OpenAI embedding generation failed."
            ) from exc

        embedding = list(response.data[0].embedding)
        if len(embedding) != self._dimensions:
            raise AzureOpenAIEmbeddingError(
                "Embedding dimension mismatch: "
                f"expected {self._dimensions}, received {len(embedding)}."
            )

        return embedding

    def _validate_configuration(self) -> None:
        missing = []
        if not self._endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not self._api_key:
            missing.append("AZURE_OPENAI_API_KEY")
        if not self._api_version:
            missing.append("AZURE_OPENAI_API_VERSION")
        if not self._deployment:
            missing.append("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")
        if missing:
            raise AzureOpenAIEmbeddingConfigurationError(
                "Missing Azure OpenAI embedding configuration: "
                + ", ".join(sorted(missing))
            )
        if self._dimensions <= 0:
            raise AzureOpenAIEmbeddingConfigurationError(
                "AZURE_OPENAI_EMBEDDINGS_DIMENSIONS must be greater than zero."
            )

    @staticmethod
    def _normalize_request(request: EmbeddingRequest | str) -> EmbeddingRequest:
        if isinstance(request, str):
            request = EmbeddingRequest(text=request)

        if not request.text or not request.text.strip():
            raise ValueError("Embedding input text must be a non-empty string.")

        return EmbeddingRequest(text=request.text.strip())
