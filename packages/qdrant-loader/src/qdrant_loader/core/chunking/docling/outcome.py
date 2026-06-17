"""The chunker -> mapper handoff type.

A :class:`Chunk` is the engine-neutral unit the chunker emits: the body text, the
heading-contextualised text that will actually be embedded (doc 03 §5.1), and the
projected :class:`~.structure.ChunkStructure`. It is the contract boundary between
the docling-touching :mod:`.docling_chunker` and the docling-free :mod:`.mapper`
that turns chunks into qdrant-loader ``Document`` chunks — so the mapper, and its
tests, never need docling.
"""

from __future__ import annotations

from dataclasses import dataclass

from .structure import ChunkStructure


@dataclass(frozen=True, slots=True)
class Chunk:
    """One chunk, before projection into the qdrant-loader ``Document`` contract."""

    text: str  # the chunk body — docling DocChunk.text
    # contextualize() output (§5.1). Contextual embedding is NOT YET IMPLEMENTED, so
    # this mirrors text while the toggle is off; it is the carrier for when it lands.
    embed_text: str
    structure: ChunkStructure
    token_count: int | None = None  # tokens in embed_text — drives the §3.3 budget check
