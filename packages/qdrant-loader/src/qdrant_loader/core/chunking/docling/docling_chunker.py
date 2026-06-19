"""The docling chunker — the one module that touches ``HybridChunker`` directly.

:class:`DoclingChunker` is a thin facade over a single docling ``HybridChunker``.
It owns construction *once* via ``cached_property`` (class-enforced lazy-once, not a
lazy-null singleton) and composes the pure :class:`~.tokenizer.TokenizerFactory` and
:class:`~.structure.StructureProjector` rather than inlining their logic.

It structurally satisfies :class:`~.chunker.DocumentChunker` — no base class, no
registration. It runs HybridChunker's two-pass split/merge, maps ``contextualize``
output to ``embed_text``, and surfaces the post-context budget check via
``_warn_if_over_budget``.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from qdrant_loader.utils.logging import LoggingConfig

from .config import ChunkingConfig, TableSerialization
from .exceptions import EmptyDocumentError
from .outcome import Chunk
from .structure import StructureProjector
from .tokenizer import TokenizerFactory

if TYPE_CHECKING:
    from docling_core.transforms.chunker import BaseChunk, HybridChunker

    from ...conversion import ConvertedDocument

logger = LoggingConfig.get_logger(__name__)


class DoclingChunker:
    """ConvertedDocument -> list[Chunk] via docling's HybridChunker."""

    def __init__(self, config: ChunkingConfig) -> None:
        self._config = config
        self._tokenizer_factory = TokenizerFactory(config.tokenizer)
        self._projector = StructureProjector()

    @cached_property
    def _chunker(self) -> HybridChunker:
        """Construct the docling ``HybridChunker`` once, then reuse it.

        The tokenizer (built from our config) carries the token budget; ``merge_peers``
        and ``delim`` come from the config, and ``table_serialization`` selects the
        serializer provider. Built lazily so the budget/tokenizer cost is paid on
        first chunk, not at import.
        """
        from docling_core.transforms.chunker import HybridChunker

        return HybridChunker(
            tokenizer=self._tokenizer_factory.build(),
            merge_peers=self._config.merge_peers,
            delim=self._config.delim,
            serializer_provider=self._serializer_provider(),
        )

    def warm_up(self) -> None:
        """Build the docling ``HybridChunker`` + tokenizer eagerly.

        Used at pipeline startup so the first document's chunking timeout never
        covers the tokenizer build (HuggingFaceTokenizer.from_pretrained / tiktoken
        load). Touching the ``_chunker`` cached_property triggers and caches the
        one-time construction — mirroring :meth:`GlinerEntityExtractor.warm_up`.
        """
        _ = self._chunker

    def _serializer_provider(self):
        """Map the table-serialization knob onto a docling serializer provider.

        TRIPLETS is docling's own chunking default; MARKDOWN swaps in the
        GitHub-table serializer while keeping the rest of the chunking
        serialization (picture descriptions, code fences) unchanged.
        """
        from docling_core.transforms.chunker.hierarchical_chunker import (
            ChunkingDocSerializer,
            ChunkingSerializerProvider,
        )

        if self._config.table_serialization is not TableSerialization.MARKDOWN:
            return ChunkingSerializerProvider()

        from docling_core.transforms.serializer.markdown import MarkdownTableSerializer

        class _MarkdownTableProvider(ChunkingSerializerProvider):
            def get_serializer(self, doc):
                return ChunkingDocSerializer(
                    doc=doc, table_serializer=MarkdownTableSerializer()
                )

        return _MarkdownTableProvider()

    def chunk(self, document: ConvertedDocument) -> list[Chunk]:
        """Chunk a converted document into engine-neutral chunks.

        Runs ``HybridChunker.chunk`` over the structured ``DoclingDocument``, projects
        each chunk's ``meta`` via :class:`StructureProjector`, and counts tokens on the
        embedded text. A contentless document fails loud with
        :class:`EmptyDocumentError` rather than emitting a fake empty chunk.

        ``embed_text`` mirrors the body while contextual embedding is disabled (the
        deferred toggle); once enabled it becomes ``contextualize`` output and the
        ``enforce_token_budget`` check (which HybridChunker cannot guarantee for
        prepended context) becomes reachable.
        """
        chunker = self._chunker
        chunks = []
        for doc_chunk in chunker.chunk(document.document):
            chunk = self._to_chunk(doc_chunk, chunker)
            self._warn_if_over_budget(chunk)
            chunks.append(chunk)
        if not chunks:
            raise EmptyDocumentError(
                f"converted {document.source_format!r} document produced no chunks"
            )
        return chunks

    def _warn_if_over_budget(self, chunk: Chunk) -> None:
        """Surface — but do not raise on — a chunk that exceeds the token budget.

        HybridChunker only guarantees the budget for the bare body; ``contextualize``
        (when ``include_context_in_embed`` is on) and atomic oversized doc items can
        push a chunk over. The overflow is allowed; when
        ``enforce_token_budget`` is set we log it, because the embedder may silently
        truncate or reject oversized input.
        """
        max_tokens = self._config.tokenizer.max_tokens
        if (
            self._config.enforce_token_budget
            and chunk.token_count is not None
            and chunk.token_count > max_tokens
        ):
            logger.warning(
                "docling chunk exceeds token budget; embedder may truncate it",
                token_count=chunk.token_count,
                max_tokens=max_tokens,
                heading_path=list(chunk.structure.heading_path),
            )

    def _to_chunk(self, doc_chunk: BaseChunk, chunker: HybridChunker) -> Chunk:
        """Project one docling chunk into our engine-neutral :class:`Chunk`."""
        embed_text = (
            chunker.contextualize(doc_chunk)
            if self._config.include_context_in_embed
            else doc_chunk.text
        )
        return Chunk(
            text=doc_chunk.text,
            embed_text=embed_text,
            structure=self._projector.project(doc_chunk),
            token_count=chunker.tokenizer.count_tokens(embed_text),
        )
