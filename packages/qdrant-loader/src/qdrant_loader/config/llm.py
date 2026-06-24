"""Configuration for embedding generation."""

from typing import Any

from pydantic import Field

from qdrant_loader.config.base import BaseConfig
from qdrant_loader.config.embedding import EmbeddingConfig


class LLMConfig(BaseConfig):
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    tokenizer: str = "none"

    models: dict[str, str] = Field(default_factory=dict)
    embeddings: EmbeddingConfig = Field(default_factory=EmbeddingConfig)

    headers: dict[str, str] = Field(default_factory=dict)
    provider_options: dict[str, Any] = Field(default_factory=dict)
