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

NLP enrichment parity with the markdown path is provided by the shared
:class:`~qdrant_loader.core.text_processing.chunk_enricher.ChunkEnricher`, which writes
the entities/topics/key_phrases (+ enhanced) keys onto each chunk ``Document``. One
intentional divergence: this path front-loads a per-*document* LDA topic model
(``ChunkEnricher.fit_topics``) before enriching, whereas markdown still trains a
per-*chunk* model — see :meth:`chunk_document`. Parity is the floor; docling is allowed
to exceed it on topic quality.
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
from qdrant_loader.core.text_processing.chunk_enricher import ChunkEnricher
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

if TYPE_CHECKING:
    from qdrant_loader.config import Settings
    from qdrant_loader.config.chunking import DoclingStrategyConfig
    from qdrant_loader.core.chunking.docling import DocumentChunker
    from qdrant_loader.core.document import Document


class DoclingChunkingStrategy(BaseChunkingStrategy):
    """Chunks a docling-converted document via its structured ``DoclingDocument``."""

    # This strategy enriches via ChunkEnricher (SemanticAnalyzer), not the base
    # TextProcessor — so don't let BaseChunkingStrategy load a second spaCy model.
    _uses_base_text_processor = False

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._config: ChunkingConfig = self._build_config(
            settings.global_config.chunking.strategies.docling,
            settings.llm_settings.tokenizer,
            settings.llm_settings.embeddings.max_tokens_per_chunk,
        )
        self._chunker: DocumentChunker = build_chunker(
            ChunkerKind.DOCLING, self._config
        )
        self._mapper = ChunkDocumentMapper(self._config)
        self._enricher = ChunkEnricher(settings)

    @staticmethod
    def _build_config(
        docling: DoclingStrategyConfig,
        llm_tokenizer: str,
        llm_max_tokens_per_chunk: int,
    ) -> ChunkingConfig:
        """Bridge the YAML knobs into the frozen engine config.

        The chunk-size budget is ``chunking.strategies.docling.max_tokens`` when set,
        otherwise ``global.llm.embeddings.max_tokens_per_chunk``. The tokenizer
        identity (how tokens are counted) always comes from ``global.llm.tokenizer`` —
        the override changes the budget, never the counter.
        """
        max_tokens = (
            docling.max_tokens
            if docling.max_tokens is not None
            else llm_max_tokens_per_chunk
        )
        return ChunkingConfig.from_embedding(
            tokenizer=llm_tokenizer,
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

        documents = self._mapper.to_documents(chunks, document)

        # Front-load the topic model on this document's chunks, so each chunk's
        # topics are inferred against one model instead of a degenerate per-chunk
        # single-document LDA. Must run before the enrich loop below.
        #
        # NOTE: this intentionally diverges from the markdown path, which still
        # trains a per-chunk LDA.
        self._enricher.fit_topics([chunk_doc.content for chunk_doc in documents])

        # NLP enrichment parity with the markdown path: the shared ChunkEnricher
        # writes entities/topics/key_phrases (+ enhanced when enabled), or the
        # empty-shape keys when disabled. Runs on the stored chunk content.
        for chunk_doc in documents:
            chunk_doc.metadata.update(
                self._enricher.enrich(chunk_doc.content, doc_id=chunk_doc.id)
            )

        return documents

    def shutdown(self) -> None:
        """Release the enricher's analyzer resources (spaCy/LDA)."""
        if getattr(self, "_enricher", None) is not None:
            self._enricher.shutdown()

    def __del__(self) -> None:
        """Release per-document NLP resources on GC.

        The service builds a fresh strategy per document (see
        ``ChunkingService._get_strategy``), so without this the spaCy/LDA model
        each instance loads would linger until GC ran its finalizer-free path.
        Mirrors the markdown strategy's ``__del__`` so both paths free the
        enricher the same way.
        """
        self.shutdown()
