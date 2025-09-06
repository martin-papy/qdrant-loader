from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

try:
    from openai import AzureOpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency surface
    AzureOpenAI = None  # type: ignore

from ...logging import LoggingConfig
from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter
from .openai import OpenAIChat, OpenAIEmbeddings, _OpenAITokenCounter

logger = LoggingConfig.get_logger(__name__)


def _host_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).hostname or None
    except Exception:
        return None


def _validate_azure_settings(settings: LLMSettings) -> None:
    base_url = settings.base_url or ""
    if "/openai/deployments" in base_url:
        raise ValueError(
            "Azure OpenAI base_url must be the resource root (e.g. https://<resource>.openai.azure.com). Do not include /openai/deployments/... in base_url."
        )
    if not (settings.api_version and isinstance(settings.api_version, str)):
        raise ValueError(
            "Azure OpenAI requires api_version (e.g. '2024-05-01-preview') in global.llm.api_version"
        )


class AzureOpenAIProvider(LLMProvider):
    def __init__(self, settings: LLMSettings):
        self._settings = settings
        _validate_azure_settings(settings)

        self._base_host = _host_of(settings.base_url)
        if AzureOpenAI is None:
            self._client = None
        else:
            # Prefer explicit azure_endpoint in provider_options; fallback to base_url
            provider_opts = settings.provider_options or {}
            endpoint = provider_opts.get("azure_endpoint") or settings.base_url
            kwargs: dict[str, Any] = {
                "api_key": settings.api_key,
                "api_version": settings.api_version,
            }
            if endpoint:
                kwargs["azure_endpoint"] = endpoint
            self._client = AzureOpenAI(
                **{k: v for k, v in kwargs.items() if v is not None}
            )

    def embeddings(self) -> EmbeddingsClient:
        model = self._settings.models.get("embeddings", "")
        return OpenAIEmbeddings(
            self._client, model, self._base_host, provider_label="azure_openai"
        )

    def chat(self) -> ChatClient:
        model = self._settings.models.get("chat", "")
        return OpenAIChat(
            self._client, model, self._base_host, provider_label="azure_openai"
        )

    def tokenizer(self) -> TokenCounter:
        return _OpenAITokenCounter(self._settings.tokenizer)
