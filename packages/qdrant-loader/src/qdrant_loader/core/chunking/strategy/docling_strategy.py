"""Structure-aware chunking strategy backed by docling's ``HybridChunker``.

This is the chunking half of full Option B: instead of re-parsing a markdown string,
it consumes the structured ``DoclingDocument`` the docling conversion engine produced
(carried on :attr:`Document.converted_document`) and chunks it natively — so heading
paths, page spans, bounding boxes and element labels survive into the payload via the
engine-neutral ``metadata.structure`` block.

It composes the seam in :mod:`qdrant_loader.core.chunking.docling`:
``build_chunker`` (the docling ``HybridChunker`` facade) plus the docling-free
:class:`ChunkDocumentMapper` (chunks -> chunk ``Document``s). The chunk-size budget
and contextual-embedding toggle are read from ``chunking.strategies.docling`` (falling
back to the *embedding* settings), and the token counter is aligned to the embedding
model's tokenizer — see :meth:`DoclingChunkingStrategy._build_config`.

Remaining parity gap vs the markdown path: NLP enrichment keys (see the TODO below).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qdrant_loader.core.chunking.docling import (
    ChunkDocumentMapper,
    ChunkerKind,
    ChunkingConfig,
    ChunkingError,
    TableSerialization,
    build_chunker,
)
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

if TYPE_CHECKING:
    from qdrant_loader.config import Settings
    from qdrant_loader.config.chunking import DoclingStrategyConfig
    from qdrant_loader.config.embedding import EmbeddingConfig
    from qdrant_loader.core.chunking.docling import DocumentChunker
    from qdrant_loader.core.document import Document


class DoclingChunkingStrategy(BaseChunkingStrategy):
    """Chunks a docling-converted document via its structured ``DoclingDocument``."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._config: ChunkingConfig = self._build_config(
            settings.global_config.chunking.strategies.docling,
            settings.global_config.embedding,
        )
        self._chunker: DocumentChunker = build_chunker(
            ChunkerKind.DOCLING, self._config
        )
        self._mapper = ChunkDocumentMapper(self._config)

    @staticmethod
    def _build_config(
        docling: DoclingStrategyConfig, embedding: EmbeddingConfig
    ) -> ChunkingConfig:
        """Bridge the YAML knobs into the frozen engine config.

        The chunk-size budget is ``chunking.strategies.docling.max_tokens`` when set,
        otherwise the embedding model's ``max_tokens_per_chunk``. The tokenizer
        identity (how tokens are counted) always comes from ``embedding.tokenizer`` —
        the override changes the budget, never the counter.
        """
        max_tokens = (
            docling.max_tokens
            if docling.max_tokens is not None
            else embedding.max_tokens_per_chunk
        )
        return ChunkingConfig.from_embedding(
            tokenizer=embedding.tokenizer,
            max_tokens=max_tokens,
            include_context_in_embed=docling.include_context_in_embed,
            table_serialization=TableSerialization(docling.table_serialization),
        )

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk the structured artifact, then map chunks into chunk ``Document``s.

        Requires the structured ``DoclingDocument`` produced by the docling engine.
        Its absence is a wiring bug, not a soft-degrade case, so it fails loud rather
        than silently emitting one giant chunk.
        """
        converted = document.converted_document
        if converted is None:
            raise ChunkingError(
                "docling chunking requires a converted DoclingDocument, but "
                f"document {document.id!r} carries none — was it converted with the "
                "docling engine? (conversion_method="
                f"{document.metadata.get('conversion_method')!r})"
            )

        chunks = self._chunker.chunk(converted)

        # Configuration-driven safety limit, in parity with the other strategies: a
        # huge document must not emit unbounded chunks and overwhelm embedding/upsert.
        max_chunks = self.settings.global_config.chunking.max_chunks_per_document
        if len(chunks) > max_chunks:
            logger.warning(
                f"Docling chunking produced {len(chunks)} chunks, limiting to "
                f"{max_chunks} per max_chunks_per_document. Consider raising "
                f"max_chunks_per_document or the token budget. Document: {document.title}"
            )
            chunks = chunks[:max_chunks]

        return self._mapper.to_documents(chunks, document)

        # TODO: parity with the markdown path — NLP enrichment keys
        # (entities/pos_tags/topics) are not produced here; decide whether to run the
        # TextProcessor over chunk.content.
