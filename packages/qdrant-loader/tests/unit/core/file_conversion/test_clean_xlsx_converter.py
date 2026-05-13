import numpy as np
import pandas as pd

from qdrant_loader.core.file_conversion.clean_xlsx_converter import (
    _clean_dataframe,
)


def test_clean_dataframe_drops_fully_empty_rows():
    df = pd.DataFrame({"a": [1, np.nan, 3], "b": ["x", np.nan, "z"]})
    result = _clean_dataframe(df)
    assert list(result["a"]) == [1, 3]
    assert list(result["b"]) == ["x", "z"]


def test_clean_dataframe_drops_fully_empty_columns():
    df = pd.DataFrame(
        {"a": [1, 2, 3], "empty": [np.nan, np.nan, np.nan], "b": ["x", "y", "z"]}
    )
    result = _clean_dataframe(df)
    assert list(result.columns) == ["a", "b"]


def test_clean_dataframe_keeps_rows_with_partial_data():
    df = pd.DataFrame({"a": [1, np.nan, 3], "b": ["x", "y", np.nan]})
    result = _clean_dataframe(df)
    assert len(result) == 3


def test_clean_dataframe_handles_empty_input():
    assert _clean_dataframe(pd.DataFrame()).empty


def test_clean_dataframe_preserves_literal_na_strings():
    df = pd.DataFrame({"a": ["N/A", "real", "data"]})
    result = _clean_dataframe(df)
    assert list(result["a"]) == ["N/A", "real", "data"]


from qdrant_loader.core.file_conversion.clean_xlsx_converter import (
    _should_skip_sheet,
)


def test_should_skip_sheet_returns_true_for_empty_dataframe():
    assert _should_skip_sheet(pd.DataFrame()) is True


def test_should_skip_sheet_returns_true_for_all_nan_dataframe():
    df = pd.DataFrame({"a": [np.nan, np.nan], "b": [np.nan, np.nan]})
    assert _should_skip_sheet(df) is True


def test_should_skip_sheet_returns_false_for_dataframe_with_data():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    assert _should_skip_sheet(df) is False


def test_should_skip_sheet_returns_false_for_partial_data():
    df = pd.DataFrame({"a": [1, np.nan], "b": [np.nan, "y"]})
    assert _should_skip_sheet(df) is False


from markitdown._stream_info import StreamInfo

from qdrant_loader.core.file_conversion.clean_xlsx_converter import (
    CleanXlsxConverter,
)
from tests.unit.core.file_conversion._xlsx_fixtures import make_xlsx_bytes


def test_xlsx_converter_accepts_xlsx_extension():
    converter = CleanXlsxConverter()
    info = StreamInfo(extension=".xlsx")
    assert converter.accepts(make_xlsx_bytes({"S": [["a"], [1]]}), info) is True


def test_xlsx_converter_rejects_non_xlsx():
    converter = CleanXlsxConverter()
    info = StreamInfo(extension=".pdf")
    assert converter.accepts(make_xlsx_bytes({"S": [["a"], [1]]}), info) is False


def test_xlsx_converter_does_not_emit_nan():
    rows = [
        ["Name", "Age", "City"],
        ["Alice", 30, "NYC"],
        ["Bob", None, "LA"],
        ["Carol", 25, None],
    ]
    stream = make_xlsx_bytes({"Sheet1": rows})
    info = StreamInfo(extension=".xlsx")

    result = CleanXlsxConverter().convert(stream, info)

    assert "NaN" not in result.markdown
    assert "nan" not in result.markdown
    assert "NaT" not in result.markdown
    assert "Alice" in result.markdown
    assert "Bob" in result.markdown
    assert "Carol" in result.markdown


def test_xlsx_converter_skips_empty_sheets():
    sheets = {
        "Real": [["a", "b"], [1, 2]],
        "Empty": [[None, None], [None, None]],
    }
    info = StreamInfo(extension=".xlsx")

    result = CleanXlsxConverter().convert(make_xlsx_bytes(sheets), info)

    assert "## Sheet: Real" in result.markdown
    assert "## Sheet: Empty" not in result.markdown


def test_xlsx_converter_emits_one_heading_per_kept_sheet():
    sheets = {"First": [["a"], [1]], "Second": [["b"], [2]]}
    info = StreamInfo(extension=".xlsx")

    result = CleanXlsxConverter().convert(make_xlsx_bytes(sheets), info)

    assert result.markdown.count("## Sheet: First") == 1
    assert result.markdown.count("## Sheet: Second") == 1


from qdrant_loader.core.file_conversion.conversion_config import FileConversionConfig
from qdrant_loader.core.file_conversion.file_converter import FileConverter


def test_file_converter_registers_clean_xlsx_converters():
    fc = FileConverter(FileConversionConfig())
    md = fc._get_markitdown()

    types = [type(reg.converter).__name__ for reg in md._converters]
    assert "CleanXlsxConverter" in types
    assert "CleanXlsConverter" in types

    clean_priority = next(
        reg.priority for reg in md._converters
        if type(reg.converter).__name__ == "CleanXlsxConverter"
    )
    default_priority = next(
        reg.priority for reg in md._converters
        if type(reg.converter).__name__ == "XlsxConverter"
    )
    # MarkItDown sorts ascending — lower priority value is tried first
    assert clean_priority < default_priority


def test_xlsx_converter_emits_one_section_per_subtable():
    """A sheet with two sub-tables separated by a blank row produces two sections."""
    sheet = [
        ["Name", "Age"],
        ["Alice", 30],
        ["Bob", 25],
        [None, None],
        [None, None],
        ["Product", "Price"],
        ["Widget", 9.99],
        ["Gadget", 14.99],
    ]
    info = StreamInfo(extension=".xlsx")

    result = CleanXlsxConverter().convert(make_xlsx_bytes({"Mixed": sheet}), info)

    assert "## Sheet: Mixed / Subtable: 1" in result.markdown
    assert "## Sheet: Mixed / Subtable: 2" in result.markdown
    assert "Alice" in result.markdown
    assert "Widget" in result.markdown


def test_xlsx_converter_uses_simple_heading_when_only_one_subtable():
    """A clean single-table sheet keeps the simple `Sheet: X` heading (no Subtable suffix)."""
    sheet = [["a", "b"], [1, 2], [3, 4]]
    info = StreamInfo(extension=".xlsx")

    result = CleanXlsxConverter().convert(make_xlsx_bytes({"Solo": sheet}), info)

    assert "## Sheet: Solo\n" in result.markdown
    assert "Subtable" not in result.markdown


def test_xlsx_converter_raises_on_malformed_bytes():
    """A non-xlsx blob carrying an `.xlsx` extension surfaces as an exception.

    Documents the failure-mode contract: rather than silently returning
    garbage markdown, the converter raises (pandas / openpyxl emit a
    `BadZipFile`, `ValueError`, or similar). The specific exception type
    isn't load-bearing; the important thing is that callers get a clear
    failure signal.
    """
    import pytest
    from io import BytesIO

    info = StreamInfo(extension=".xlsx")
    bad_stream = BytesIO(b"not really an xlsx")

    with pytest.raises(Exception):
        CleanXlsxConverter().convert(bad_stream, info)


def test_xlsx_converter_pipe_round_trip_through_splitter():
    """A cell containing a literal `|` survives the converter -> splitter round-trip.

    Without escaping, `MarkdownTableParser._row_cells` over-splits the row,
    the cell count diverges from the header count, and the row is silently
    dropped. The fix is render-side `|` -> `\\|` escape plus an
    unescaped-pipe split in the parser.
    """
    from qdrant_loader.core.chunking.strategy.markdown.splitters.row_kv_excel import (
        MarkdownTableParser,
    )

    rows = [
        ["URL", "Description"],
        ["http://x.com?a=1|b=2", "pipe in url"],
        ["plain", "no pipe here"],
    ]
    info = StreamInfo(extension=".xlsx")

    md = CleanXlsxConverter().convert(make_xlsx_bytes({"Sheet1": rows}), info).markdown

    # Render-side: literal `|` in cell text is escaped as `\|`.
    assert r"http://x.com?a=1\|b=2" in md

    # Parser-side: the row survives, and the unescape is symmetric.
    parsed = MarkdownTableParser().parse(md)
    assert len(parsed) == 1
    _ctx, parsed_rows = parsed[0]
    assert len(parsed_rows) == 2
    assert parsed_rows[0] == {
        "URL": "http://x.com?a=1|b=2",
        "Description": "pipe in url",
    }
    assert parsed_rows[1] == {"URL": "plain", "Description": "no pipe here"}


def test_xlsx_converter_handles_nan_in_header_row():
    """A first-row cell that's empty must not crash header coercion.

    Reproduces a real failure on `Brief_Agency Partner_VLG.xlsx`: when a sheet's
    first row contains an empty cell, `Series.astype(str).tolist()` in this
    pandas version leaves the NaN as a Python float, so the header-escape
    comprehension blows up with
    `AttributeError: 'float' object has no attribute 'replace'`.

    Expected behavior: empty header cells render as empty strings (matching the
    body path, which already coerces NaN to "" via `to_html(na_rep="")`).
    """
    sheet = [
        ["Title cell", None],
        ["row1col1", "row1col2"],
        ["row2col1", "row2col2"],
    ]
    info = StreamInfo(extension=".xlsx")

    result = CleanXlsxConverter().convert(make_xlsx_bytes({"S": sheet}), info)

    assert "Title cell" in result.markdown
    assert "row1col1" in result.markdown
    assert "nan" not in result.markdown
    assert "NaN" not in result.markdown
