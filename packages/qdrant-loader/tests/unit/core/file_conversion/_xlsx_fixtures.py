# packages/qdrant-loader/tests/unit/core/file_conversion/_xlsx_fixtures.py
"""Shared programmatic xlsx fixture builders for converter and splitter tests.

Each function returns either a BytesIO or a Path so tests can choose between
in-memory streams (converter unit tests) and on-disk files (FileConverter e2e).
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook


def make_xlsx_bytes(sheets: dict[str, list[list]]) -> BytesIO:
    """Build an in-memory xlsx from {sheet_name: rows}."""
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def make_xlsx_file(tmp_path: Path, sheets: dict[str, list[list]], name: str = "test.xlsx") -> Path:
    """Persist an xlsx to disk for FileConverter end-to-end tests."""
    path = tmp_path / name
    path.write_bytes(make_xlsx_bytes(sheets).getvalue())
    return path
