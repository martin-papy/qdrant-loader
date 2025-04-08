"""Configuration for embedding generation."""

from pydantic import Field
from .base import BaseConfig


class EmbeddingConfig(BaseConfig):
    """Configuration for embedding generation."""
    model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model to use"
    )
    batch_size: int = Field(
        default=100,
        description="Number of texts to embed in a single batch"
    ) 