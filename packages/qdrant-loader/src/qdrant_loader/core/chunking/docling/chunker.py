"""The chunker seam: the abstraction the rest of the codebase depends on.

A :class:`DocumentChunker` turns a converted document into engine-neutral
:class:`~.outcome.Chunk` objects. The codebase depends on this Protocol, not on
docling's ``HybridChunker`` — the same swappability discipline the conversion layer
uses in its ``engine.py``. :func:`build_chunker` is the composition root that
selects and constructs the implementation, importing docling lazily.

This consumes the :class:`~..conversion.ConvertedDocument` the conversion layer
produces — the structured ``DoclingDocument``, never a re-parsed markdown string —
which is what makes Option B (structure-aware chunking, doc 03 §5–6) possible.
"""

from __future__ import annotations

import threading
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...conversion import ConvertedDocument
    from .config import ChunkingConfig
    from .outcome import Chunk


@runtime_checkable
class DocumentChunker(Protocol):
    """ConvertedDocument -> list[Chunk]. The codebase depends on this, not docling."""

    def chunk(self, document: ConvertedDocument) -> list[Chunk]: ...


class ChunkerKind(StrEnum):
    DOCLING = "docling"


# One chunker (and thus one HybridChunker + tokenizer) per distinct config for the
# whole process, mirroring entity_extraction's _EXTRACTOR_REGISTRY: ChunkingService
# builds a fresh DoclingChunkingStrategy per document, and without this the docling
# HybridChunker and its tokenizer (HuggingFaceTokenizer.from_pretrained / tiktoken)
# would be rebuilt for every document. ChunkingConfig is a frozen, hashable
# dataclass, so equal configs key the same cached instance.
_CHUNKER_REGISTRY: dict[tuple[ChunkerKind, ChunkingConfig], DocumentChunker] = {}
_REGISTRY_LOCK = threading.Lock()


def build_chunker(kind: ChunkerKind, config: ChunkingConfig) -> DocumentChunker:
    """Composition root: select and construct the chunker.

    Memoized per ``(kind, config)`` so the same config shares one chunker instance
    process-wide — the per-document strategy construction in ChunkingService thus
    reuses one already-built (and pre-warmed) HybridChunker + tokenizer instead of
    rebuilding it every document. docling is imported lazily so importing this
    package never drags in the chunker stack, and so the import also breaks the
    chunker <-> docling_chunker cycle.
    """
    key = (kind, config)
    with _REGISTRY_LOCK:
        chunker = _CHUNKER_REGISTRY.get(key)
        if chunker is None:
            chunker = _build_chunker(kind, config)
            _CHUNKER_REGISTRY[key] = chunker
    return chunker


def _build_chunker(kind: ChunkerKind, config: ChunkingConfig) -> DocumentChunker:
    match kind:
        case ChunkerKind.DOCLING:
            from .docling_chunker import DoclingChunker

            return DoclingChunker(config)
    raise ValueError(f"unknown chunker kind: {kind!r}")
