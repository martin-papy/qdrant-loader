"""Configuration for embedding generation."""

from pydantic import Field

from qdrant_loader.config.base import BaseConfig


class EmbeddingConfig(BaseConfig):
    """Configuration for embedding generation."""

    model: str = Field(
        default="argus-ai/pplx-embed-context-v1-0.6b:fp32",
        description="Embedding model to use",
    )
    api_key: str | None = Field(
        default=None, description="API key for the embedding service"
    )
    batch_size: int = Field(
        default=100, description="Number of texts to embed in a single batch"
    )
    endpoint: str = Field(
        default="http://localhost:11434",
        description="Base URL for the embedding API endpoint",
    )
    tokenizer: str = Field(
        default="none",
        description="Tokenizer to use for token counting. Use 'none' for Ollama local models",
    )
    vector_size: int | None = Field(
        default=1024,
        description="Vector size for the embedding model (384 for BAAI/bge-small-en-v1.5, 1024 for argus-ai/pplx-embed-context-v1-0.6b:fp32)",
    )
    max_tokens_per_request: int = Field(
        default=8000,
        description="Maximum total tokens allowed per embedding API request (leave buffer below model limit)",
    )
    max_tokens_per_chunk: int = Field(
        default=8000,
        description="Maximum tokens allowed for a single chunk (should match or be below model's context limit)",
    )
