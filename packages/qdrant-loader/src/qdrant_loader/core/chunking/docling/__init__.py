"""Docling-native, structure-aware chunking: DoclingDocument -> chunk Documents.

This is the public surface for the rest of qdrant-loader. Callers obtain a chunker
via :func:`build_chunker` and depend on the :class:`DocumentChunker` Protocol; the
docling implementation, its tokenizer factory and the structure projector stay
private behind the seam, so the chunking engine remains swappable. The contract
types (:class:`Chunk`, :class:`ChunkStructure`) and the docling-free
:class:`ChunkDocumentMapper` are public because the pipeline composes them.
"""

from __future__ import annotations

from .chunker import ChunkerKind, DocumentChunker, build_chunker
from .config import (
    ChunkingConfig,
    TableSerialization,
    TokenizerConfig,
    TokenizerKind,
)
from .exceptions import (
    ChunkingError,
    EmptyDocumentError,
    TokenizerUnavailableError,
)
from .mapper import ChunkDocumentMapper
from .outcome import Chunk
from .structure import BoundingBoxSpan, ChunkStructure

__all__ = [
    # config
    "ChunkingConfig",
    "TableSerialization",
    "TokenizerConfig",
    "TokenizerKind",
    # chunker seam
    "DocumentChunker",
    "ChunkerKind",
    "build_chunker",
    # contract types
    "Chunk",
    "ChunkStructure",
    "BoundingBoxSpan",
    "ChunkDocumentMapper",
    # errors
    "ChunkingError",
    "EmptyDocumentError",
    "TokenizerUnavailableError",
]
