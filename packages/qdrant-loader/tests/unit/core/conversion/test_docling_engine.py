"""Behaviour tests for the docling conversion engine.

These convert real files and assert on *our* contract: the typed outcome, the
structured-document handoff, the failure model, and the build-once facade. They
are not a re-test of docling's own backends.
"""

from __future__ import annotations

from qdrant_loader.core.conversion import (
    ConversionConfig,
    ConversionProfile,
    ConversionStatus,
    EngineKind,
    build_engine,
)


def _fast_engine():
    config = ConversionConfig.from_profile(ConversionProfile.FAST)
    return build_engine(EngineKind.DOCLING, config)


def test_convert_xlsx_yields_success_outcome_with_structured_tables(xlsx_path):
    """The migration's core promise: tables survive as structured cell grids,
    not as a markdown string we would have to re-parse (the A1 round-trip)."""
    outcome = _fast_engine().convert(xlsx_path)

    assert outcome.status is ConversionStatus.SUCCESS
    assert outcome.document is not None
    assert outcome.document.source_format == "xlsx"

    tables = outcome.document.document.tables
    assert tables, "expected at least one structured table"
    grid = tables[0].data.grid
    assert grid and grid[0], "expected a 2-D grid of cells"
    assert any(
        cell.text for row in grid for cell in row
    ), "expected non-empty cell text"


def test_convert_corrupt_file_yields_failed_outcome_not_a_fake_document(
    corrupt_xlsx_path,
):
    """Errors are values, not content (A7): a broken file produces a FAILED
    outcome with no document — never a stub doc carrying the error as text."""
    outcome = _fast_engine().convert(corrupt_xlsx_path)

    assert outcome.status is ConversionStatus.FAILED
    assert outcome.document is None
    assert outcome.error, "a failure must carry an explanation"


def test_to_markdown_renders_prose_document(docx_path):
    """The prose path: a converted document serializes to markdown on demand,
    without us re-deriving structure from that markdown."""
    outcome = _fast_engine().convert(docx_path)

    assert outcome.status is ConversionStatus.SUCCESS
    markdown = outcome.document.to_markdown()
    assert isinstance(markdown, str)
    assert markdown.strip(), "expected non-empty markdown"
    assert "lorem" in markdown.lower()  # the fixture is lorem-ipsum prose


def test_converter_is_built_once_and_reused_across_conversions(xlsx_path, csv_path):
    """Guards the A4 fix: the docling converter is constructed once (cached_property)
    and reused, never re-instantiated per call."""
    engine = _fast_engine()

    engine.convert(xlsx_path)
    converter_after_first = engine._converter
    engine.convert(csv_path)

    assert engine._converter is converter_after_first
