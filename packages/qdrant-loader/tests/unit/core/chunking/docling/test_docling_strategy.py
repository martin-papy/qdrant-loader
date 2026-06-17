"""Behaviour tests for how DoclingChunkingStrategy resolves its chunking config.

The strategy bridges two YAML layers into the frozen engine ``ChunkingConfig``:
the docling-specific knobs (``chunking.strategies.docling``) and the embedding
settings. These pin the bridge rules — the chunk-size budget override/inherit and
the contextual-embedding flag — without needing a full Settings tree or docling.
"""

from __future__ import annotations

from qdrant_loader.config.chunking import DoclingStrategyConfig
from qdrant_loader.config.embedding import EmbeddingConfig
from qdrant_loader.core.chunking.docling import TokenizerKind
from qdrant_loader.core.chunking.strategy.docling_strategy import (
    DoclingChunkingStrategy,
)


def test_docling_max_tokens_override_wins_over_embedding():
    """A set chunking.strategies.docling.max_tokens is the chunk-size budget."""
    config = DoclingChunkingStrategy._build_config(
        DoclingStrategyConfig(max_tokens=256),
        EmbeddingConfig(tokenizer="cl100k_base", max_tokens_per_chunk=512),
    )
    assert config.tokenizer.max_tokens == 256


def test_docling_max_tokens_inherits_embedding_when_unset():
    """Unset docling.max_tokens falls back to embedding.max_tokens_per_chunk."""
    config = DoclingChunkingStrategy._build_config(
        DoclingStrategyConfig(),
        EmbeddingConfig(tokenizer="cl100k_base", max_tokens_per_chunk=777),
    )
    assert config.tokenizer.max_tokens == 777


def test_include_context_in_embed_threads_through():
    """The flag flows from YAML config into the frozen ChunkingConfig."""
    on = DoclingChunkingStrategy._build_config(
        DoclingStrategyConfig(include_context_in_embed=True), EmbeddingConfig()
    )
    off = DoclingChunkingStrategy._build_config(
        DoclingStrategyConfig(), EmbeddingConfig()
    )
    assert on.include_context_in_embed is True
    assert off.include_context_in_embed is False


def test_table_serialization_threads_through():
    """The YAML table_serialization string maps onto the engine enum."""
    from qdrant_loader.core.chunking.docling import TableSerialization

    markdown = DoclingChunkingStrategy._build_config(
        DoclingStrategyConfig(table_serialization="markdown"), EmbeddingConfig()
    )
    default = DoclingChunkingStrategy._build_config(
        DoclingStrategyConfig(), EmbeddingConfig()
    )
    assert markdown.table_serialization is TableSerialization.MARKDOWN
    assert default.table_serialization is TableSerialization.TRIPLETS


def test_tokenizer_identity_comes_from_embedding():
    """The counter is always the embedding model's tokenizer, never the override."""
    config = DoclingChunkingStrategy._build_config(
        DoclingStrategyConfig(max_tokens=256),
        EmbeddingConfig(tokenizer="cl100k_base", max_tokens_per_chunk=512),
    )
    assert config.tokenizer.kind == TokenizerKind.OPENAI
    assert config.tokenizer.model == "cl100k_base"
