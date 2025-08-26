from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingsClient(Protocol):
    async def embed(self, inputs: list[str]) -> list[list[float]]: ...


@runtime_checkable
class ChatClient(Protocol):
    async def chat(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]: ...


@runtime_checkable
class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


@runtime_checkable
class LLMProvider(Protocol):
    def embeddings(self) -> EmbeddingsClient: ...

    def chat(self) -> ChatClient: ...

    def tokenizer(self) -> TokenCounter: ...
