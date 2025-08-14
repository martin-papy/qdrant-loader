from __future__ import annotations

from typing import Any

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency at this phase
    OpenAI = None  # type: ignore

from ..settings import LLMSettings
from ..types import EmbeddingsClient, ChatClient, TokenCounter, LLMProvider


class _OpenAITokenCounter(TokenCounter):
    def __init__(self, tokenizer: str):
        self._tokenizer = tokenizer

    def count(self, text: str) -> int:
        # Phase 0: fallback to naive length; real tiktoken impl to come later
        return len(text)


class OpenAIEmbeddings(EmbeddingsClient):
    def __init__(self, client: Any, model: str):
        self._client = client
        self._model = model

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        if not self._client:
            raise NotImplementedError("OpenAI client not available")
        # Use thread offloading to keep async interface consistent with sync client
        import asyncio

        response = await asyncio.to_thread(
            self._client.embeddings.create, model=self._model, input=inputs
        )
        return [item.embedding for item in response.data]


class OpenAIChat(ChatClient):
    def __init__(self, client: Any, model: str):
        self._client = client
        self._model = model

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: LLMSettings):
        self._settings = settings
        if OpenAI is None:
            self._client = None
        else:
            kwargs: dict[str, Any] = {}
            if settings.base_url:
                kwargs["base_url"] = settings.base_url
            if settings.api_key:
                kwargs["api_key"] = settings.api_key
            self._client = OpenAI(**kwargs)

    def embeddings(self) -> EmbeddingsClient:
        model = self._settings.models.get("embeddings", "")
        return OpenAIEmbeddings(self._client, model)

    def chat(self) -> ChatClient:
        model = self._settings.models.get("chat", "")
        return OpenAIChat(self._client, model)

    def tokenizer(self) -> TokenCounter:
        return _OpenAITokenCounter(self._settings.tokenizer)


