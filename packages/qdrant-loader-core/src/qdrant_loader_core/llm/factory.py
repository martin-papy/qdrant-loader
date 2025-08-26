from __future__ import annotations

from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider
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


def create_provider(settings: LLMSettings) -> LLMProvider:
    """Create a provider by settings.

    Phase 0: route OpenAI/OpenAI-compatible to OpenAIProvider when available; otherwise return a noop provider.
    Ollama returns a stub provider for now.
    """
    provider_name = (settings.provider or "").lower()
    base_url = (settings.base_url or "").lower()

    if "openai" in provider_name or "openai" in base_url:
        try:
            return OpenAIProvider(settings)
        except Exception:
            return _NoopProvider()

    if provider_name == "ollama" or "localhost" in base_url:
        return OllamaProvider(settings)

    return _NoopProvider()
