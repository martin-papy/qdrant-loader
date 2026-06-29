"""DEPRECATED: Configuration for embedding generation.

WARNING: This module is deprecated and should not be used.
The EmbeddingConfig class is no longer part of the application configuration.

Migration required:
  OLD (deprecated):\n    global:
      embedding:
        model: text-embedding-3-small
        api_key: ${OPENAI_API_KEY}

  NEW (required):
    global:
      llm:
        provider: openai
        api_key: ${OPENAI_API_KEY}
        models:
          embeddings: text-embedding-3-small
        embeddings:
          vector_size: 1536

Please update your configuration.yaml to use global.llm instead of global.embedding.
"""

from pydantic import Field

from qdrant_loader.config.base import BaseConfig


class EmbeddingConfig(BaseConfig):
    """DEPRECATED: Configuration for embedding generation.

    This class is deprecated and retained only for reference.
    Use global.llm configuration instead.
    """

    batch_size: int = Field(
        default=100, description="Number of texts to embed in a single batch"
    )
    vector_size: int | None = Field(
        default=1024,
        description="Vector size for the embedding model (384 for BAAI/bge-small-en-v1.5, 1024 for argus-ai/pplx-embed-v1-0.6b:fp32)",
    )
    max_tokens_per_request: int = Field(
        default=8000,
        description="Maximum total tokens allowed per embedding API request (leave buffer below model limit)",
    )
    max_tokens_per_chunk: int = Field(
        default=8000,
        description="Maximum tokens allowed for a single chunk (should match or be below model's context limit)",
    )
