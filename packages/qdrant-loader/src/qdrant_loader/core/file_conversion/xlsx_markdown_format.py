"""Shared heading format for converted xlsx markdown.

The xlsx converter emits sheet/subtable headings; the row-KV splitter parses
them back to recover structure. Centralizing the format and regex here makes
that contract explicit — change the template and the regex breaks loudly at
import time instead of silently degrading ingestion at runtime.
"""

from __future__ import annotations

import re

SHEET_HEADING_RE = re.compile(
    r"^##\s+Sheet:\s+(?P<sheet>.+?)(?:\s+/\s+Subtable:\s+(?P<idx>\d+))?\s*$",
    re.MULTILINE,
)


def format_sheet_heading(sheet: str, subtable_idx: int | None) -> str:
    """Render the H2 heading for a sheet (and optional subtable index)."""
    if subtable_idx is None:
        return f"## Sheet: {sheet}"
    return f"## Sheet: {sheet} / Subtable: {subtable_idx}"
