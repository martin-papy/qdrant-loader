"""Row-level KV chunking for converted xlsx documents.

Implements the structure-aware chunking technique from arXiv 2605.00318
("Structure-Aware Chunking for Tabular Data in Retrieval-Augmented Generation"):
each row becomes a key-value block, prefixed with sheet/subtable/column context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from qdrant_loader.core.chunking.strategy.markdown.splitters.base import BaseSplitter
from qdrant_loader.core.file_conversion.xlsx_markdown_format import SHEET_HEADING_RE

# Split on `|` only when it is NOT preceded by a backslash (escaped pipe).
_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")


@dataclass(frozen=True)
class _SubTableContext:
    sheet: str
    subtable: int | None
    columns: tuple[str, ...]


class MarkdownTableParser:
    """Parse `## Sheet: ... / Subtable: N` sections back into structured rows."""

    def parse(self, content: str) -> list[tuple[_SubTableContext, list[dict[str, str]]]]:
        sections: list[tuple[_SubTableContext, list[dict[str, str]]]] = []
        matches = list(SHEET_HEADING_RE.finditer(content))
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            block = content[start:end]
            columns, rows = self._parse_table(block)
            if not columns:
                continue
            ctx = _SubTableContext(
                sheet=m.group("sheet").strip(),
                subtable=int(m.group("idx")) if m.group("idx") else None,
                columns=columns,
            )
            sections.append((ctx, rows))
        return sections

    @staticmethod
    def _parse_table(block: str) -> tuple[tuple[str, ...], list[dict[str, str]]]:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip().startswith("|")]
        if len(lines) < 2:
            return (), []
        header_cells = MarkdownTableParser._row_cells(lines[0])
        body: list[dict[str, str]] = []
        # lines[1] is the separator (`|---|---|`); skip it.
        for line in lines[2:]:
            cells = MarkdownTableParser._row_cells(line)
            if len(cells) != len(header_cells):
                continue
            body.append(dict(zip(header_cells, cells)))
        return tuple(header_cells), body

    @staticmethod
    def _row_cells(line: str) -> list[str]:
        # Strip the leading and trailing pipe before splitting on UNESCAPED
        # pipes (the converter escapes literal `|` in cell values as `\|` so
        # they don't break this split). After splitting, unescape each cell.
        inner = line.strip().strip("|")
        cells = _UNESCAPED_PIPE_RE.split(inner)
        return [c.strip().replace(r"\|", "|") for c in cells]


class RowChunkContextualizer:
    """Render a slice of rows with contextual preamble for embedding."""

    def build(self, ctx: _SubTableContext, rows: Iterable[dict[str, str]]) -> str:
        lines: list[str] = [f"Sheet: {ctx.sheet}"]
        if ctx.subtable is not None:
            lines.append(f"Subtable: {ctx.subtable}")
        lines.append(f"Columns: {', '.join(ctx.columns)}")
        lines.append("")
        for row in rows:
            lines.append("Row:")
            for col in ctx.columns:
                value = row.get(col, "")
                if value == "":
                    continue
                lines.append(f"  {col}: {value}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


class RowKVChunker:
    """Pack rows into chunks under a character budget, re-emitting context per chunk."""

    def __init__(self) -> None:
        self._renderer = RowChunkContextualizer()

    def chunk(
        self,
        ctx: _SubTableContext,
        rows: list[dict[str, str]],
        max_size: int,
    ) -> list[str]:
        if not rows:
            return []
        chunks: list[str] = []
        current: list[dict[str, str]] = []
        for row in rows:
            candidate = current + [row]
            if current and len(self._renderer.build(ctx, candidate)) > max_size:
                chunks.append(self._renderer.build(ctx, current))
                current = [row]
            else:
                current = candidate
        if current:
            chunks.append(self._renderer.build(ctx, current))
        return chunks


class RowKVExcelSplitter(BaseSplitter):
    """BaseSplitter that emits row-level KV chunks for converted xlsx content.

    Type-substitutable for the legacy ExcelSplitter at the BaseSplitter
    interface — same `split_content(content, max_size) -> list[str]` signature
    and the same dispatch site at section_splitter.py:104. The output shape is
    materially different, however: ExcelSplitter emits markdown-table fragments,
    while RowKVExcelSplitter emits prose-like context-prefixed KV blocks (the
    STC technique from arXiv 2605.00318). Downstream consumers that re-parsed
    chunks as markdown tables need updating; in-tree consumers (embedding,
    reranking, retrieval) treat chunks as opaque text.
    """

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self._parser = MarkdownTableParser()
        self._chunker = RowKVChunker()

    def split_content(self, content: str, max_size: int) -> list[str]:
        sections = self._parser.parse(content)
        if not sections:
            # No structured heading — preserve content as a single chunk so
            # upstream mis-classification doesn't drop content.
            return [content]
        chunks: list[str] = []
        for ctx, rows in sections:
            chunks.extend(self._chunker.chunk(ctx, rows, max_size=max_size))
        return chunks
