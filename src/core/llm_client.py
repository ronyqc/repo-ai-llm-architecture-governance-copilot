from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from openai import AzureOpenAI
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal local envs
    AzureOpenAI = Any

from src.core.config import Settings, settings


class AzureOpenAILLMConfigurationError(ValueError):
    """Raised when Azure OpenAI LLM settings are incomplete or invalid."""


class AzureOpenAILLMError(RuntimeError):
    """Raised when Azure OpenAI fails to generate an answer."""


@dataclass(frozen=True)
class LLMGenerationRequest:
    """Stable input contract for the LLM answer generation step."""

    system_prompt: str
    user_prompt: str
    temperature: float = 0.1
    max_tokens: int = 800


@dataclass(frozen=True)
class LLMGenerationResult:
    """Normalized result returned by the Azure OpenAI LLM wrapper."""

    answer: str
    tokens_used: int
    finish_reason: str | None


class AzureOpenAILLMClient:
    """Small Azure OpenAI wrapper for text generation tasks."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        api_version: str,
        deployment: str,
        client: Any | None = None,
    ) -> None:
        self._endpoint = endpoint.strip()
        self._api_key = api_key.strip()
        self._api_version = api_version.strip()
        self._deployment = deployment.strip()
        self._validate_configuration()
        if client is None and AzureOpenAI is Any:
            raise AzureOpenAILLMConfigurationError(
                "openai must be installed to use AzureOpenAILLMClient "
                "without an injected client."
            )
        self._client = client or AzureOpenAI(
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            api_version=self._api_version,
        )

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "AzureOpenAILLMClient":
        return cls(
            endpoint=app_settings.AZURE_OPENAI_ENDPOINT,
            api_key=app_settings.AZURE_OPENAI_API_KEY,
            api_version=app_settings.AZURE_OPENAI_API_VERSION,
            deployment=app_settings.AZURE_OPENAI_DEPLOYMENT,
        )

    @classmethod
    def from_router_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "AzureOpenAILLMClient":
        return cls(
            endpoint=app_settings.AZURE_OPENAI_ENDPOINT,
            api_key=app_settings.AZURE_OPENAI_API_KEY,
            api_version=app_settings.AZURE_OPENAI_API_VERSION,
            deployment=app_settings.AZURE_OPENAI_ROUTER_DEPLOYMENT,
        )

    def generate_answer(
        self,
        request: LLMGenerationRequest,
    ) -> LLMGenerationResult:
        normalized_request = self._normalize_request(request)

        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": normalized_request.system_prompt},
                    {"role": "user", "content": normalized_request.user_prompt},
                ],
                temperature=normalized_request.temperature,
                max_tokens=normalized_request.max_tokens,
            )
        except Exception as exc:  # pragma: no cover - SDK-specific failures
            raise AzureOpenAILLMError(
                "Azure OpenAI answer generation failed."
            ) from exc

        choice = response.choices[0]
        answer = (choice.message.content or "").strip()
        if not answer:
            raise AzureOpenAILLMError("Azure OpenAI returned an empty answer.")

        usage = getattr(response, "usage", None)
        tokens_used = int(getattr(usage, "total_tokens", 0) or 0)

        return LLMGenerationResult(
            answer=answer,
            tokens_used=tokens_used,
            finish_reason=getattr(choice, "finish_reason", None),
        )

    def _validate_configuration(self) -> None:
        missing = []
        if not self._endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not self._api_key:
            missing.append("AZURE_OPENAI_API_KEY")
        if not self._api_version:
            missing.append("AZURE_OPENAI_API_VERSION")
        if not self._deployment:
            missing.append("AZURE_OPENAI_DEPLOYMENT")
        if missing:
            raise AzureOpenAILLMConfigurationError(
                "Missing Azure OpenAI LLM configuration: "
                + ", ".join(sorted(missing))
            )

    @staticmethod
    def _normalize_request(request: LLMGenerationRequest) -> LLMGenerationRequest:
        if not request.system_prompt or not request.system_prompt.strip():
            raise ValueError("System prompt must be a non-empty string.")
        if not request.user_prompt or not request.user_prompt.strip():
            raise ValueError("User prompt must be a non-empty string.")
        if request.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")
        if request.temperature < 0:
            raise ValueError("temperature must be greater than or equal to zero.")

        return LLMGenerationRequest(
            system_prompt=request.system_prompt.strip(),
            user_prompt=request.user_prompt.strip(),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
