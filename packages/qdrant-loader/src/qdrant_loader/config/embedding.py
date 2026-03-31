"""Configuration for embedding generation."""

from pydantic import Field

from qdrant_loader.config.base import BaseConfig


class ContextualEmbeddingConfig(BaseConfig):
    """Configuration for contextual embedding enrichment."""

    enabled: bool = Field(
        default=True,
        description="Enable contextual enrichment before generating embeddings",
    )
    include_title: bool = Field(
        default=True,
        description="Include the parent document title in the contextual prefix",
    )
    include_source_type: bool = Field(
        default=True,
        description="Include the parent document source type in the contextual prefix",
    )
    include_source: bool = Field(
        default=False,
        description="Include the parent document source identifier in the contextual prefix",
    )
    include_path: bool = Field(
        default=True,
        description="Include the parent document breadcrumb/hierarchy path in the contextual prefix",
    )
    include_section: bool = Field(
        default=True,
        description="Include the chunk's section path (from markdown headings) in the contextual prefix",
    )


class EmbeddingConfig(BaseConfig):
    """Configuration for embedding generation."""

    model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model to use"
    )
    api_key: str | None = Field(
        default=None, description="API key for the embedding service"
    )
    batch_size: int = Field(
        default=100, description="Number of texts to embed in a single batch"
    )
    endpoint: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for the embedding API endpoint",
    )
    tokenizer: str = Field(
        default="cl100k_base",  # Default OpenAI tokenizer
        description="Tokenizer to use for token counting. Use 'cl100k_base' for OpenAI models or 'none' for other models",
    )
    vector_size: int | None = Field(
        default=1536,
        description="Vector size for the embedding model (384 for BAAI/bge-small-en-v1.5, 1536 for OpenAI models)",
    )
    max_tokens_per_request: int = Field(
        default=8000,
        description="Maximum total tokens allowed per embedding API request (leave buffer below model limit)",
    )
    max_tokens_per_chunk: int = Field(
        default=8000,
        description="Maximum tokens allowed for a single chunk (should match or be below model's context limit)",
    )
