"""Configuration for embedding generation."""

from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""
    model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model to use"
    )
    batch_size: int = Field(
        default=100,
        description="Number of texts to embed in a single batch"
    ) 