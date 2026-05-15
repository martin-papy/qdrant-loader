"""Custom MarkItDown converters that strip NaN/NaT noise from xlsx and xls output."""

from __future__ import annotations

from typing import Any, BinaryIO

import pandas as pd
from markitdown._base_converter import (
    DocumentConverter,
    DocumentConverterResult,
)
from markitdown._stream_info import StreamInfo
from markitdown.converters._html_converter import HtmlConverter

from qdrant_loader.core.file_conversion.sub_table_detector import SubTableDetector
from qdrant_loader.core.file_conversion.xlsx_markdown_format import (
    format_sheet_heading,
)


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows and columns that are entirely missing."""
    if df.empty:
        return df
    cleaned = df.dropna(axis=0, how="all")
    cleaned = cleaned.dropna(axis=1, how="all")
    return cleaned


def _is_blank_dataframe(df: pd.DataFrame) -> bool:
    """Return True for a DataFrame that holds no real data after cleaning.

    Used on per-subtable frames, not full sheets — the name avoids the older
    "_should_skip_sheet" misnomer.
    """
    if df.empty:
        return True
    return bool(df.isna().all().all())


def _cell_to_str(value: Any) -> str:
    """Coerce a header cell to a clean string, mapping NaN/None to ''.

    `Series.astype(str).tolist()` in current pandas can leak a Python `float`
    NaN through instead of the string "nan", which breaks downstream `.replace`
    calls on header values.
    """
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value)


def _escape_string_cell(value: Any) -> Any:
    """Escape `|` in string cells; pass non-strings through unchanged.

    Body cells use this rather than `_cell_to_str` so pandas' `to_html` can
    apply its smart numeric formatting (e.g. `1` not `1.0`, `0.5` not `0.50`).
    NaN survives this pass and is rendered as `""` by `to_html(na_rep="")`.
    """
    if isinstance(value, str):
        return value.replace("|", r"\|")
    return value


class _CleanSpreadsheetConverter(DocumentConverter):
    """Shared logic for cleaning xlsx/xls output before handing it to MarkItDown."""

    ENGINE: str = ""
    EXTENSIONS: tuple[str, ...] = ()
    MIME_PREFIXES: tuple[str, ...] = ()

    def __init__(self) -> None:
        super().__init__()
        self._html_converter = HtmlConverter()
        self._detector = SubTableDetector()

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        extension = (stream_info.extension or "").lower()
        if extension in self.EXTENSIONS:
            return True
        mimetype = (stream_info.mimetype or "").lower()
        return any(mimetype.startswith(prefix) for prefix in self.MIME_PREFIXES)

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        # Read header-less so SubTableDetector can decide where headers start.
        # keep_default_na=False preserves literal "N/A" strings; explicit
        # na_values=[""] still treats genuinely empty cells as NaN.
        sheets = pd.read_excel(
            file_stream,
            sheet_name=None,
            engine=self.ENGINE,
            header=None,
            keep_default_na=False,
            na_values=[""],
        )

        parts: list[str] = []
        for name, sheet_df in sheets.items():
            sub_tables = self._detector.detect(sheet_df)
            for idx, raw in enumerate(sub_tables, start=1):
                rendered = self._render_subtable(raw, **kwargs)
                if rendered is None:
                    continue
                heading = self._heading(name, idx, total=len(sub_tables))
                parts.append(f"{heading}\n{rendered}")

        return DocumentConverterResult(markdown="\n\n".join(parts).strip())

    @staticmethod
    def _heading(sheet_name: str, idx: int, total: int) -> str:
        return format_sheet_heading(
            sheet_name, subtable_idx=None if total <= 1 else idx
        )

    def _render_subtable(self, raw: pd.DataFrame, **kwargs: Any) -> str | None:
        """Promote first row to header, clean, render to markdown.

        Headers and body cells take different paths on purpose: headers are
        coerced to strings here (they become DataFrame column labels and feed
        `.replace`), but body cells stay typed so pandas' `to_html` can apply
        its native numeric formatting. Both paths escape `|` to survive the
        downstream markdown-table parser; `HtmlConverter` passes cell text
        through unchanged.
        """
        if raw.empty:
            return None
        header = [_cell_to_str(c).replace("|", r"\|") for c in raw.iloc[0].tolist()]
        body = raw.iloc[1:].reset_index(drop=True)
        body.columns = header
        cleaned = _clean_dataframe(body)
        if _is_blank_dataframe(cleaned):
            return None
        escaped = cleaned.map(_escape_string_cell)
        html = escaped.to_html(index=False, na_rep="")
        return self._html_converter.convert_string(html, **kwargs).markdown.strip()


class CleanXlsxConverter(_CleanSpreadsheetConverter):
    ENGINE = "openpyxl"
    EXTENSIONS = (".xlsx",)
    MIME_PREFIXES = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class CleanXlsConverter(_CleanSpreadsheetConverter):
    ENGINE = "xlrd"
    EXTENSIONS = (".xls",)
    MIME_PREFIXES = (
        "application/vnd.ms-excel",
        "application/excel",
    )
