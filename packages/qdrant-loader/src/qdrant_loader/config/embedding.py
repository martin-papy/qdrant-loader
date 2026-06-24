"""Configuration for embedding generation."""

from pydantic import Field

from qdrant_loader.config.base import BaseConfig


class EmbeddingConfig(BaseConfig):
    """Configuration for embedding generation."""

    batch_size: int = Field(
        default=100, description="Number of texts to embed in a single batch"
    )
    max_tokens_per_request: int = Field(
        default=8000,
        description="Maximum total tokens allowed per embedding API request (leave buffer below model limit)",
    )
    max_tokens_per_chunk: int = Field(
        default=8000,
        description="Maximum tokens allowed for a single chunk (should match or be below model's context limit)",
    )
