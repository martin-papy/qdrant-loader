"""Behaviour tests for how DoclingChunkingStrategy resolves its chunking config.

The strategy bridges two YAML layers into the frozen engine ``ChunkingConfig``:
the docling-specific knobs (``chunking.strategies.docling``) and the embedding
settings. These pin the bridge rules — the chunk-size budget override/inherit and
the contextual-embedding flag — without needing a full Settings tree or docling.
"""

from __future__ import annotations

from types import SimpleNamespace

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


# -- max_chunks_per_document safety cap (parity with the other strategies) --------
class _FakeChunker:
    """Returns a fixed number of opaque chunks, so chunk_document's cap logic is
    exercised without running the real HybridChunker over a fixture."""

    def __init__(self, count: int) -> None:
        self._chunks = [f"chunk-{i}" for i in range(count)]

    def chunk(self, converted):
        return list(self._chunks)


class _FakeDoc:
    """Document-shaped enough for the enrichment loop: content, id, metadata dict."""

    def __init__(self, content: str, doc_id: str) -> None:
        self.content = content
        self.id = doc_id
        self.metadata: dict = {}


class _EchoMapper:
    """Maps each chunk 1:1 into a _FakeDoc, recording what it received so the cap can
    be asserted on the mapper's input as well as the returned list."""

    def __init__(self) -> None:
        self.received: list | None = None

    def to_documents(self, chunks, document):
        self.received = list(chunks)
        return [
            _FakeDoc(content=str(c), doc_id=f"{document.id}_{i}")
            for i, c in enumerate(self.received)
        ]


class _DocStub:
    """Minimal Document for chunk_document: a non-None converted_document passes the
    wiring guard; title feeds the cap warning."""

    def __init__(self) -> None:
        self.id = "doc-1"
        self.title = "huge.pdf"
        self.metadata: dict = {}
        self.converted_document = object()


class _NoopEnricher:
    """Returns no enrichment keys; used where the cap logic is what's under test."""

    def enrich(self, content, doc_id):
        return {}


def _capped_strategy(
    chunker, mapper, max_chunks: int, enricher=None
) -> DoclingChunkingStrategy:
    """A strategy with collaborators injected, bypassing the heavy __init__
    (HybridChunker + tokenizer + spaCy). Mirrors test_service.py pre-seeding a fake
    engine: we drive chunk_document's real cap + enrichment logic, not the chunker."""
    strategy = object.__new__(DoclingChunkingStrategy)
    strategy._chunker = chunker
    strategy._mapper = mapper
    strategy._enricher = enricher if enricher is not None else _NoopEnricher()
    strategy.settings = SimpleNamespace(
        global_config=SimpleNamespace(
            chunking=SimpleNamespace(max_chunks_per_document=max_chunks)
        )
    )
    return strategy


def test_chunk_document_caps_at_max_chunks_per_document(caplog):
    """Like every other strategy, docling caps output at max_chunks_per_document so a
    huge document cannot emit unbounded chunks — and the drop is logged, not silent."""
    mapper = _EchoMapper()
    strategy = _capped_strategy(_FakeChunker(count=10), mapper, max_chunks=3)

    with caplog.at_level("WARNING"):
        result = strategy.chunk_document(_DocStub())

    assert len(result) == 3
    assert mapper.received is not None and len(mapper.received) == 3
    assert any("max_chunks_per_document" in r.getMessage() for r in caplog.records)


def test_chunk_document_keeps_all_chunks_when_under_cap(caplog):
    """Under the cap, every chunk is mapped and nothing is logged about limiting."""
    mapper = _EchoMapper()
    strategy = _capped_strategy(_FakeChunker(count=2), mapper, max_chunks=500)

    with caplog.at_level("WARNING"):
        result = strategy.chunk_document(_DocStub())

    assert len(result) == 2
    assert not any(
        "max_chunks_per_document" in r.getMessage() for r in caplog.records
    )


class _RecordingEnricher:
    """Records each enrich() call and returns a fixed payload."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[tuple[str, str]] = []

    def enrich(self, content, doc_id):
        self.calls.append((content, doc_id))
        return dict(self._payload)


def test_chunk_document_enriches_each_chunk_metadata():
    """Every chunk Document gets the enrichment keys merged into its metadata."""
    mapper = _EchoMapper()
    enricher = _RecordingEnricher(
        {"entities": [{"text": "X"}], "topics": [], "key_phrases": []}
    )
    strategy = _capped_strategy(
        _FakeChunker(count=2), mapper, max_chunks=500, enricher=enricher
    )

    result = strategy.chunk_document(_DocStub())

    assert len(result) == 2
    assert all(d.metadata["entities"] == [{"text": "X"}] for d in result)
    assert all(d.metadata["key_phrases"] == [] for d in result)
    # enrich receives each chunk's content (the mapper echoed "chunk-0"/"chunk-1")
    assert [content for content, _ in enricher.calls] == ["chunk-0", "chunk-1"]


def test_chunk_document_attaches_empty_shape_when_enrichment_disabled():
    """Parity with markdown: disabled enrichment still yields the empty-shape keys."""
    mapper = _EchoMapper()
    enricher = _RecordingEnricher(
        {"entities": [], "topics": [], "key_phrases": []}
    )
    strategy = _capped_strategy(
        _FakeChunker(count=1), mapper, max_chunks=500, enricher=enricher
    )

    result = strategy.chunk_document(_DocStub())

    assert result[0].metadata["entities"] == []
    assert result[0].metadata["topics"] == []
    assert result[0].metadata["key_phrases"] == []
