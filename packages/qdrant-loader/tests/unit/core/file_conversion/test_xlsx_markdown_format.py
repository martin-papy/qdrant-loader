"""Tests for the shared xlsx heading format used by the converter and splitter.

The converter and splitter previously held two independent string/regex
representations of `## Sheet: X / Subtable: N`. This module centralizes the
contract; these tests pin the round-trip so future renames break loudly at
import time, not silently at runtime.
"""

from __future__ import annotations

from qdrant_loader.core.file_conversion.xlsx_markdown_format import (
    SHEET_HEADING_RE,
    format_sheet_heading,
)


def test_format_heading_single_subtable_omits_index():
    """When a sheet has only one subtable, the heading drops the suffix."""
    assert format_sheet_heading("Solo", subtable_idx=None) == "## Sheet: Solo"


def test_format_heading_with_index_includes_subtable_suffix():
    assert (
        format_sheet_heading("Inventory", subtable_idx=2)
        == "## Sheet: Inventory / Subtable: 2"
    )


def test_regex_matches_simple_heading():
    m = SHEET_HEADING_RE.match("## Sheet: Solo")
    assert m is not None
    assert m.group("sheet") == "Solo"
    assert m.group("idx") is None


def test_regex_matches_heading_with_subtable_index():
    m = SHEET_HEADING_RE.match("## Sheet: Inventory / Subtable: 2")
    assert m is not None
    assert m.group("sheet") == "Inventory"
    assert m.group("idx") == "2"


def test_regex_tolerates_sheet_name_with_spaces_and_punctuation():
    """Real xlsx sheets have names like '6. Core Banking System ' (note trailing space)."""
    m = SHEET_HEADING_RE.match("## Sheet: 6. Core Banking System  / Subtable: 3")
    assert m is not None
    assert m.group("sheet").strip() == "6. Core Banking System"
    assert m.group("idx") == "3"


def test_round_trip_format_then_parse():
    """format -> regex round-trip recovers the original sheet name and index."""
    for sheet, idx in [("Solo", None), ("Inventory", 2), ("A B C", 10)]:
        rendered = format_sheet_heading(sheet, idx)
        m = SHEET_HEADING_RE.match(rendered)
        assert m is not None, f"regex failed to match: {rendered!r}"
        assert m.group("sheet") == sheet
        parsed_idx = int(m.group("idx")) if m.group("idx") else None
        assert parsed_idx == idx
