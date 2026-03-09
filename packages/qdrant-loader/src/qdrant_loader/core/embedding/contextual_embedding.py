"""Contextual embedding builder.

Prepends document-level context to a chunk's text before embedding.
The enriched text is sent to the embedding API only — chunk.content
stored in Qdrant remains unchanged.
"""

from __future__ import annotations

from qdrant_loader.config.embedding import ContextualEmbeddingConfig


def build_contextual_text(chunk, config: ContextualEmbeddingConfig) -> str:
    """Build embedding input text with optional document-level context prefix.

    Args:
        chunk: A chunk produced by ChunkingWorker. Must have
               chunk.metadata["parent_document"] set (a Document instance).
        config: Contextual embedding configuration.

    Returns:
        If config.enabled and parent document is available:
            "[Document: {title} | Source: {source_type}]\n\n{chunk.content}"
        Otherwise:
            chunk.content unchanged.
    """
    if not config.enabled:
        return chunk.content

    parent = chunk.metadata.get("parent_document")
    if parent is None:
        return chunk.content

    parts = []
    if config.include_title and parent.title:
        parts.append(f"Document: {parent.title}")
    if config.include_source_type and parent.source_type:
        parts.append(f"Source: {parent.source_type}")
    if config.include_source and parent.source:
        parts.append(f"Collection: {parent.source}")

    if not parts:
        return chunk.content

    context = "[" + " | ".join(parts) + "]"
    return f"{context}\n\n{chunk.content}"
