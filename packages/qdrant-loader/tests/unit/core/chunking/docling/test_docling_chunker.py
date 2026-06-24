"""Behaviour tests for the docling chunker facade.

These chunk real converted documents through *our* DoclingChunker and assert its
contract: engine-neutral Chunk objects, the structure projection wired in, the
contextual-embedding toggle (off => embed_text mirrors body), token counting, the
build-once facade, and the loud empty-document failure. They are not a re-test of
HybridChunker's splitting.
"""

from __future__ import annotations

import pytest
from qdrant_loader.core.chunking.docling import (
    Chunk,
    ChunkerKind,
    ChunkingConfig,
    ChunkStructure,
    EmptyDocumentError,
    build_chunker,
)
from qdrant_loader.core.chunking.docling import docling_chunker as dc


def _chunker():
    # default config: cl100k_base @ 8000 tokens, contextual embedding OFF
    return build_chunker(ChunkerKind.DOCLING, ChunkingConfig())


def test_chunk_headers_yields_chunks_carrying_heading_path(converted_headers):
    """The headline: chunking a structured doc yields Chunk objects whose projected
    structure preserves the heading path (proving the projector is wired in)."""
    chunks = _chunker().chunk(converted_headers)

    assert chunks and all(isinstance(c, Chunk) for c in chunks)
    assert all(isinstance(c.structure, ChunkStructure) for c in chunks)
    paths = {c.structure.heading_path for c in chunks}
    assert any("Test Document" in path for path in paths), paths
    assert all(c.text for c in chunks), "no empty chunk bodies"


def test_chunk_xlsx_yields_table_structured_chunks(converted_xlsx):
    """The table promise: an xlsx chunk's projected structure is flagged is_table."""
    chunks = _chunker().chunk(converted_xlsx)

    assert chunks
    assert any(c.structure.is_table for c in chunks), "expected a table-typed chunk"


def test_embed_text_mirrors_body_while_contextual_embedding_disabled(converted_headers):
    """Contextual embedding is deferred (toggle off), so embed_text must equal the
    body text — no heading prefix sneaks into what gets embedded yet."""
    chunks = _chunker().chunk(converted_headers)

    assert all(c.embed_text == c.text for c in chunks)


def test_token_count_is_populated_within_budget(converted_headers):
    chunks = _chunker().chunk(converted_headers)

    assert all(isinstance(c.token_count, int) and c.token_count > 0 for c in chunks)
    assert all(c.token_count <= 8000 for c in chunks)


def test_chunker_is_built_once_and_reused(converted_headers, converted_xlsx):
    """Guards the build-once facade: the HybridChunker is constructed via
    cached_property and reused, never re-instantiated per call."""
    engine = _chunker()

    engine.chunk(converted_headers)
    chunker_after_first = engine._chunker
    engine.chunk(converted_xlsx)

    assert engine._chunker is chunker_after_first


def test_build_chunker_memoizes_per_config():
    """build_chunker returns the SAME DoclingChunker for equal configs (so the
    HybridChunker + tokenizer are built once process-wide, not per document) and a
    DIFFERENT instance for a different config — mirroring the NER _EXTRACTOR_REGISTRY.
    """
    config_a = ChunkingConfig()
    config_a_equal = ChunkingConfig()
    config_b = ChunkingConfig.from_embedding(tokenizer="cl100k_base", max_tokens=123)

    first = build_chunker(ChunkerKind.DOCLING, config_a)
    again = build_chunker(ChunkerKind.DOCLING, config_a_equal)
    other = build_chunker(ChunkerKind.DOCLING, config_b)

    assert first is again, "equal configs must share one cached chunker instance"
    assert first is not other, "a different config must yield a different chunker"


def test_warm_up_forces_chunker_construction(converted_headers):
    """warm_up() eagerly builds the HybridChunker + tokenizer so the cost is paid
    at pipeline startup, not inside the first document's chunking timeout. After
    warm_up the cached _chunker is already populated and is the one chunk() uses."""
    chunker = dc.DoclingChunker(ChunkingConfig())
    assert "_chunker" not in chunker.__dict__, "not built before warm_up"

    chunker.warm_up()

    assert "_chunker" in chunker.__dict__, "warm_up must build the HybridChunker"
    built = chunker.__dict__["_chunker"]
    chunker.chunk(converted_headers)
    assert chunker._chunker is built, "chunk() reuses the warmed instance"


def _budget_chunk(token_count: int) -> Chunk:
    return Chunk(
        text="body",
        embed_text="Heading\nbody",
        structure=ChunkStructure(
            heading_path=("Heading",), heading_level=1, doc_items=("text",)
        ),
        token_count=token_count,
    )


def _capture_warnings(monkeypatch) -> list:
    warnings: list = []
    monkeypatch.setattr(dc.logger, "warning", lambda *a, **k: warnings.append((a, k)))
    return warnings


def test_overflow_logs_warning_when_enforce_token_budget(monkeypatch):
    """A chunk over the budget surfaces a warning (overflow allowed, not raised)."""
    chunker = dc.DoclingChunker(
        ChunkingConfig.from_embedding(tokenizer="cl100k_base", max_tokens=10)
    )
    warnings = _capture_warnings(monkeypatch)

    chunker._warn_if_over_budget(_budget_chunk(50))

    assert warnings, "expected an overflow warning"


def test_no_warning_when_enforce_token_budget_disabled(monkeypatch):
    chunker = dc.DoclingChunker(
        ChunkingConfig.from_embedding(
            tokenizer="cl100k_base", max_tokens=10, enforce_token_budget=False
        )
    )
    warnings = _capture_warnings(monkeypatch)

    chunker._warn_if_over_budget(_budget_chunk(50))

    assert not warnings


def test_no_warning_when_within_budget(monkeypatch):
    chunker = dc.DoclingChunker(
        ChunkingConfig.from_embedding(tokenizer="cl100k_base", max_tokens=100)
    )
    warnings = _capture_warnings(monkeypatch)

    chunker._warn_if_over_budget(_budget_chunk(50))

    assert not warnings


def test_picture_descriptions_land_in_chunk_text():
    """Regression lock on the docling contract we rely on: a picture's description
    annotation (produced by the conversion engine's API captioning) is emitted into
    chunk text by the default chunking serializer. If a docling upgrade stops doing
    this, captioned images silently vanish from the index — fail here instead."""
    from docling_core.types.doc import DoclingDocument
    from docling_core.types.doc.document import PictureDescriptionData
    from qdrant_loader.core.conversion import ConvertedDocument

    doc = DoclingDocument(name="captioned")
    doc.add_text(label="section_header", text="Diagrams")
    picture = doc.add_picture()
    picture.annotations.append(
        PictureDescriptionData(
            text="A flowchart of the ingestion pipeline.", provenance="test"
        )
    )
    converted = ConvertedDocument(document=doc, source_format="pdf")

    chunks = _chunker().chunk(converted)

    assert any("flowchart of the ingestion pipeline" in c.text for c in chunks)
    assert any(c.structure.is_picture for c in chunks)


def test_empty_document_raises_loudly_not_a_fake_chunk():
    """A document with no chunkable content fails loud (EmptyDocumentError) rather
    than silently emitting a fake empty chunk."""
    from docling_core.types.doc import DoclingDocument
    from qdrant_loader.core.conversion import ConvertedDocument

    empty = ConvertedDocument(
        document=DoclingDocument(name="empty"), source_format="docx"
    )

    with pytest.raises(EmptyDocumentError):
        _chunker().chunk(empty)
