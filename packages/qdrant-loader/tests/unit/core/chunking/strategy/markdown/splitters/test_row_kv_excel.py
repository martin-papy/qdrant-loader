from unittest.mock import MagicMock

from qdrant_loader.core.chunking.strategy.markdown.section_splitter import (
    SectionSplitter,
)
from qdrant_loader.core.chunking.strategy.markdown.splitters.row_kv_excel import (
    MarkdownTableParser,
    RowChunkContextualizer,
    RowKVChunker,
    RowKVExcelSplitter,
    _SubTableContext,
)


def test_parses_heading_with_subtable_index():
    content = (
        "## Sheet: Inventory / Subtable: 2\n"
        "| SKU | Qty |\n"
        "|-----|-----|\n"
        "| A1  | 10  |\n"
        "| A2  | 20  |\n"
    )
    parsed = MarkdownTableParser().parse(content)
    assert len(parsed) == 1
    ctx, rows = parsed[0]
    assert ctx == _SubTableContext(
        sheet="Inventory", subtable=2, columns=("SKU", "Qty")
    )
    assert rows == [{"SKU": "A1", "Qty": "10"}, {"SKU": "A2", "Qty": "20"}]


def test_parses_heading_without_subtable_index():
    content = "## Sheet: Solo\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    parsed = MarkdownTableParser().parse(content)
    ctx, rows = parsed[0]
    assert ctx.sheet == "Solo"
    assert ctx.subtable is None
    assert rows == [{"a": "1", "b": "2"}]


def test_parses_multiple_sections_in_one_blob():
    content = (
        "## Sheet: A / Subtable: 1\n"
        "| x |\n"
        "|---|\n"
        "| 1 |\n"
        "\n"
        "## Sheet: A / Subtable: 2\n"
        "| y |\n"
        "|---|\n"
        "| 2 |\n"
    )
    parsed = MarkdownTableParser().parse(content)
    assert [ctx.subtable for ctx, _ in parsed] == [1, 2]
    assert parsed[0][1] == [{"x": "1"}]
    assert parsed[1][1] == [{"y": "2"}]


def test_returns_empty_when_no_matching_heading():
    content = "Just some prose without a sheet heading.\n"
    assert MarkdownTableParser().parse(content) == []


def test_parser_unescapes_pipe_characters_in_cells():
    """Cells containing literal `\\|` (escaped pipe) round-trip back to `|`.

    The converter escapes literal pipes in cell values; the parser must split
    on UNESCAPED pipes and unescape each cell so the original value survives.
    """
    content = (
        "## Sheet: S\n"
        "| URL | Note |\n"
        "|-----|------|\n"
        r"| http://x.com?a=1\|b=2 | with pipe |"
        "\n"
    )
    parsed = MarkdownTableParser().parse(content)
    assert len(parsed) == 1
    _ctx, rows = parsed[0]
    assert rows == [{"URL": "http://x.com?a=1|b=2", "Note": "with pipe"}]


def test_contextualizer_emits_preamble_and_rows():
    ctx = _SubTableContext(sheet="Inventory", subtable=1, columns=("SKU", "Qty"))
    rows = [{"SKU": "A1", "Qty": "10"}, {"SKU": "A2", "Qty": "20"}]
    text = RowChunkContextualizer().build(ctx, rows)

    assert text.startswith("Sheet: Inventory")
    assert "Subtable: 1" in text
    assert "Columns: SKU, Qty" in text
    assert "Row:\n  SKU: A1\n  Qty: 10" in text
    assert "Row:\n  SKU: A2\n  Qty: 20" in text


def test_contextualizer_omits_subtable_line_when_absent():
    ctx = _SubTableContext(sheet="Solo", subtable=None, columns=("a",))
    text = RowChunkContextualizer().build(ctx, [{"a": "1"}])

    assert "Subtable" not in text
    assert "Sheet: Solo" in text


def test_contextualizer_skips_empty_cells_in_kv_block():
    """Per the STC paper: only non-empty cells are encoded as KV pairs."""
    ctx = _SubTableContext(sheet="S", subtable=None, columns=("a", "b", "c"))
    text = RowChunkContextualizer().build(ctx, [{"a": "1", "b": "", "c": "3"}])

    assert "a: 1" in text
    assert "c: 3" in text
    assert "b:" not in text


def test_chunker_packs_all_rows_into_one_chunk_when_under_budget():
    ctx = _SubTableContext(sheet="S", subtable=None, columns=("a",))
    rows = [{"a": str(i)} for i in range(3)]
    chunks = RowKVChunker().chunk(ctx, rows, max_size=10_000)
    assert len(chunks) == 1
    assert chunks[0].count("Row:") == 3


def test_chunker_splits_when_rows_exceed_budget():
    ctx = _SubTableContext(sheet="S", subtable=None, columns=("a",))
    rows = [{"a": "x" * 100} for _ in range(5)]
    chunks = RowKVChunker().chunk(ctx, rows, max_size=300)
    assert len(chunks) >= 2
    # Every chunk re-emits the context preamble for retrieval-time grounding.
    for chunk in chunks:
        assert chunk.startswith("Sheet: S")


def test_chunker_emits_oversized_row_as_its_own_chunk():
    ctx = _SubTableContext(sheet="S", subtable=None, columns=("a",))
    rows = [{"a": "y" * 1000}]
    chunks = RowKVChunker().chunk(ctx, rows, max_size=200)
    # One row that exceeds the budget is still emitted (truncation is a separate concern).
    assert len(chunks) == 1


def test_chunker_returns_empty_for_no_rows():
    ctx = _SubTableContext(sheet="S", subtable=None, columns=("a",))
    assert RowKVChunker().chunk(ctx, [], max_size=1000) == []


def _settings_with_chunk_overlap(overlap: int = 0) -> MagicMock:
    settings = MagicMock()
    settings.global_config.chunking.chunk_overlap = overlap
    settings.global_config.chunking.max_chunks_per_document = 10_000
    settings.global_config.chunking.strategies.markdown.max_chunks_per_section = 10_000
    return settings


def test_splitter_emits_one_chunk_per_row_group():
    content = (
        "## Sheet: Inventory / Subtable: 1\n"
        "| SKU | Qty |\n"
        "|-----|-----|\n"
        "| A1  | 10  |\n"
        "| A2  | 20  |\n"
    )
    splitter = RowKVExcelSplitter(_settings_with_chunk_overlap())
    chunks = splitter.split_content(content, max_size=10_000)
    assert len(chunks) == 1
    assert "Sheet: Inventory" in chunks[0]
    assert "SKU: A1" in chunks[0]
    assert "SKU: A2" in chunks[0]


def test_splitter_falls_back_to_passthrough_when_no_heading():
    """If content lacks the structured heading, return it unchanged in one chunk.

    This preserves the BaseSplitter contract for non-xlsx markdown that may
    transit through this splitter due to mis-classification upstream.
    """
    content = "Just prose, no table heading."
    splitter = RowKVExcelSplitter(_settings_with_chunk_overlap())
    chunks = splitter.split_content(content, max_size=10_000)
    assert chunks == [content]


def test_splitter_handles_multi_subtable_content():
    content = (
        "## Sheet: A / Subtable: 1\n"
        "| x |\n|---|\n| 1 |\n\n"
        "## Sheet: A / Subtable: 2\n"
        "| y |\n|---|\n| 2 |\n"
    )
    splitter = RowKVExcelSplitter(_settings_with_chunk_overlap())
    chunks = splitter.split_content(content, max_size=10_000)
    assert len(chunks) == 2
    assert "x: 1" in chunks[0]
    assert "y: 2" in chunks[1]


def test_splitter_truncates_at_max_chunks_per_section_cap():
    """Match legacy ExcelSplitter: stop producing chunks once the per-section
    cap (or half the per-document cap) is reached. A 50k-row sheet must not
    silently produce 50k chunks just because the budget allows it."""
    settings = MagicMock()
    settings.global_config.chunking.chunk_overlap = 0
    settings.global_config.chunking.max_chunks_per_document = 10
    settings.global_config.chunking.strategies.markdown.max_chunks_per_section = 3
    # 10 rows in one subtable, tight budget so each row becomes its own chunk.
    rows_md = "\n".join(f"| {i} |" for i in range(10))
    content = f"## Sheet: Big\n| n |\n|---|\n{rows_md}\n"

    splitter = RowKVExcelSplitter(settings)
    chunks = splitter.split_content(content, max_size=40)

    expected_cap = min(3, 10 // 2)  # min(per_section, per_doc // 2) = 3
    assert len(chunks) == expected_cap


def test_section_splitter_uses_row_kv_excel_splitter():
    settings = _settings_with_chunk_overlap()
    splitter = SectionSplitter(settings)
    assert type(splitter.excel_splitter).__name__ == "RowKVExcelSplitter"
