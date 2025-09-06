from __future__ import annotations

from urllib.parse import urlparse

from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider

try:
    from .providers.azure_openai import AzureOpenAIProvider  # type: ignore
except Exception:  # pragma: no cover - optional dependency surface
    AzureOpenAIProvider = None  # type: ignore
from .settings import LLMSettings
from .types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter


class _NoopEmbeddings(EmbeddingsClient):
    async def embed(self, inputs: list[str]) -> list[list[float]]:
        raise NotImplementedError("Embeddings provider not implemented")


class _NoopChat(ChatClient):
    async def chat(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError("Chat provider not implemented")


class _NoopTokenizer(TokenCounter):
    def count(self, text: str) -> int:  # naive char-count fallback
        return len(text)


class _NoopProvider(LLMProvider):
    def embeddings(self) -> EmbeddingsClient:
        return _NoopEmbeddings()

    def chat(self) -> ChatClient:
        return _NoopChat()

    def tokenizer(self) -> TokenCounter:
        return _NoopTokenizer()


def _safe_hostname(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).hostname
        return host.lower() if host else None
    except Exception:
        return None


def create_provider(settings: LLMSettings) -> LLMProvider:
    """Create a provider by settings.

    Phase 0: route OpenAI/OpenAI-compatible to OpenAIProvider when available; otherwise return a noop provider.
    Ollama returns a stub provider for now.
    """
    provider_name = (settings.provider or "").lower()
    base_url = settings.base_url or ""
    base_host = _safe_hostname(base_url)

    # Route Azure before generic OpenAI routing
    is_azure = "azure" in provider_name or (
        base_host is not None
        and (
            base_host == "openai.azure.com"
            or base_host.endswith(".openai.azure.com")
            or base_host == "cognitiveservices.azure.com"
            or base_host.endswith(".cognitiveservices.azure.com")
        )
    )
    if is_azure and AzureOpenAIProvider is not None:  # type: ignore[truthy-bool]
        try:
            return AzureOpenAIProvider(settings)  # type: ignore[misc]
        except Exception:
            return _NoopProvider()

    if "openai" in provider_name or "openai" in base_url.lower():
        try:
            return OpenAIProvider(settings)
        except Exception:
            return _NoopProvider()

    if provider_name == "ollama" or (base_host in ("localhost", "127.0.0.1")):
        return OllamaProvider(settings)

    return _NoopProvider()
