"""Projects engine-neutral chunks into the qdrant-loader ``Document`` contract.

:class:`ChunkDocumentMapper` is the docling-free half of the layer: it takes the
:class:`~.outcome.Chunk` objects the chunker emits plus the parent ``Document`` and
produces the chunk ``Document`` list the rest of the pipeline already consumes. Two
contracts meet here:

* the new ``metadata.structure`` block (engine-neutral provenance), plus
  ``chunk_schema_version`` so a future re-index is detectable; and
* the legacy ``metadata.*`` keys other subsystems still read
  (``chunk_index``/``total_chunks``, ``section_breadcrumb``, ``parent_document_id``,
  ``conversion_method``, …) — populated *from* the structured block for back-compat.

Because it touches no docling type, this class and its tests run fast and offline.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from qdrant_loader.core.document import Document

from .config import ChunkingConfig

if TYPE_CHECKING:
    from .outcome import Chunk
    from .structure import ChunkStructure


class ChunkDocumentMapper:
    """Chunk + parent Document -> chunk Documents (the stable payload contract)."""

    def __init__(self, config: ChunkingConfig) -> None:
        self._config = config

    def to_documents(self, chunks: list[Chunk], parent: Document) -> list[Document]:
        """Map chunks into chunk ``Document``s carrying the chunk payload contract.

        Per chunk: a deterministic id via ``Document.generate_chunk_id``; the
        ``metadata.structure`` block flattened from :class:`~.structure.ChunkStructure`
        plus ``chunk_schema_version``; and the back-compat ``metadata.*`` keys derived
        from it. ``content`` is the chunk body — contextual embedding is deferred, so
        no heading prefix is folded into the embedded text yet.
        """
        total = len(chunks)
        return [
            self._to_document(chunk, parent, index, total)
            for index, chunk in enumerate(chunks)
        ]

    def _to_document(
        self, chunk: Chunk, parent: Document, index: int, total: int
    ) -> Document:
        structure = chunk.structure
        metadata = dict(parent.metadata)  # preserve parent scoping (project_id, ...)
        metadata.update(
            {
                "chunk_index": index,
                "total_chunks": total,
                "chunking_strategy": "docling",
                "chunk_schema_version": self._config.chunk_schema_version,
                "parent_document_id": parent.id,
                "parent_document_title": parent.title,
                "parent_document_url": parent.url,
                "structure": self._structure_block(structure),
                # legacy-compat hierarchy keys, derived from the structured block
                "section_breadcrumb": " > ".join(structure.heading_path),
                "section_depth": structure.heading_level,
                "section_title": (
                    structure.heading_path[-1] if structure.heading_path else None
                ),
            }
        )
        # Contextual embedding: when enabled, the contextualized embed text (heading
        # breadcrumb + body) becomes the stored content, so it flows into both the payload
        # and the vector (the embedder embeds Document.content). Off => the bare body.
        content = (
            chunk.embed_text if self._config.include_context_in_embed else chunk.text
        )
        return Document(
            id=Document.generate_chunk_id(parent.id, index),
            title=parent.title,
            content_type=parent.content_type,
            content=content,
            source_type=parent.source_type,
            source=parent.source,
            url=parent.url,
            metadata=metadata,
        )

    @staticmethod
    def _structure_block(structure: ChunkStructure) -> dict[str, Any]:
        """Flatten :class:`ChunkStructure` into a JSON-safe payload block.

        Tuples become lists and the bbox dataclasses become dicts so the payload is
        plain JSON — no docling objects, no dataclasses reach Qdrant.
        """
        return {
            "heading_path": list(structure.heading_path),
            "heading_level": structure.heading_level,
            "doc_items": list(structure.doc_items),
            "is_table": structure.is_table,
            "is_picture": structure.is_picture,
            "page_start": structure.page_start,
            "page_end": structure.page_end,
            "bbox": [dataclasses.asdict(box) for box in structure.bbox],
            "charspan": list(structure.charspan) if structure.charspan else None,
            "caption": structure.caption,
            "dl_meta_version": structure.dl_meta_version,
        }
