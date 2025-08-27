from __future__ import annotations

from ..settings import LLMSettings
from ..types import ChatClient, EmbeddingsClient, LLMProvider, TokenCounter


class OllamaEmbeddings(EmbeddingsClient):
    async def embed(self, inputs: list[str]) -> list[list[float]]:
        raise NotImplementedError


class OllamaChat(ChatClient):
    async def chat(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError


class OllamaTokenizer(TokenCounter):
    def count(self, text: str) -> int:
        return len(text)


class OllamaProvider(LLMProvider):
    def __init__(self, settings: LLMSettings):
        self._settings = settings

    def embeddings(self) -> EmbeddingsClient:
        return OllamaEmbeddings()

    def chat(self) -> ChatClient:
        return OllamaChat()

    def tokenizer(self) -> TokenCounter:
        return OllamaTokenizer()
