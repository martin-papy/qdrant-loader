"""Contextual embedding builder.

Prepends document-level context to a chunk's text before embedding.
The enriched text is sent to the embedding API AND stored in Qdrant as
``contextual_content`` so callers can display it alongside the chunk.
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
            "[Document: {title} | Path: {breadcrumb} | Section: {section} | Source: {source_type}]\\n\\n{chunk.content}"
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

    # Document-level hierarchy path (e.g. Confluence space > parent page > page)
    if config.include_path:
        breadcrumb_text = parent.get_breadcrumb_text()
        if breadcrumb_text:
            parts.append(f"Path: {breadcrumb_text}")

    # Chunk-level section path from markdown/HTML headings (e.g. "Setup > Docker > Volumes")
    if config.include_section:
        section_breadcrumb = chunk.metadata.get("breadcrumb")
        if section_breadcrumb:
            if isinstance(section_breadcrumb, list):
                section_path = " > ".join(str(s) for s in section_breadcrumb)
            else:
                section_path = str(section_breadcrumb)
            parts.append(f"Section: {section_path}")
        elif chunk.metadata.get("parent_title"):
            parts.append(f"Section: {chunk.metadata['parent_title']}")

    if config.include_source_type and parent.source_type:
        parts.append(f"Source: {parent.source_type}")

    if config.include_source and parent.source:
        parts.append(f"Collection: {parent.source}")

    if not parts:
        return chunk.content

    context = "[" + " | ".join(parts) + "]"
    return f"{context}\n\n{chunk.content}"
