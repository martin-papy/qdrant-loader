from __future__ import annotations

from typing import Any

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency at this phase
    OpenAI = None  # type: ignore

from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter


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

    async def chat(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        if not self._client:
            raise NotImplementedError("OpenAI client not available")

        # Normalize kwargs to OpenAI python client parameters
        create_kwargs: dict[str, Any] = {}
        for key in ("temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop", "seed", "response_format"):
            if key in kwargs and kwargs[key] is not None:
                create_kwargs[key] = kwargs[key]

        # Allow model override per-call
        model_name = kwargs.pop("model", self._model)

        import asyncio

        # The OpenAI python client call is sync for chat.completions
        response = await asyncio.to_thread(
            self._client.chat.completions.create,
            model=model_name,
            messages=messages,
            **create_kwargs,
        )

        # Normalize to provider-agnostic dict
        choice0 = response.choices[0] if getattr(response, "choices", None) else None
        text = ""
        if choice0 is not None:
            message = getattr(choice0, "message", None)
            if message is not None:
                text = getattr(message, "content", "") or ""

        usage = getattr(response, "usage", None)
        normalized_usage = None
        if usage is not None:
            normalized_usage = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }

        return {
            "text": text,
            "raw": response,
            "usage": normalized_usage,
            "model": getattr(response, "model", model_name),
        }


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
