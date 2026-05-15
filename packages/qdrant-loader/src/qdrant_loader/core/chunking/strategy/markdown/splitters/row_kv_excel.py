"""Row-level KV chunking for converted xlsx documents.

Implements the structure-aware chunking technique from arXiv 2605.00318
("Structure-Aware Chunking for Tabular Data in Retrieval-Augmented Generation"):
each row becomes a key-value block, prefixed with sheet/subtable/column context.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

import structlog

from qdrant_loader.core.chunking.strategy.markdown.splitters.base import BaseSplitter
from qdrant_loader.core.file_conversion.xlsx_markdown_format import SHEET_HEADING_RE

logger = structlog.get_logger(__name__)

# Split on `|` only when it is NOT preceded by a backslash (escaped pipe).
_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")

# Separator between row blocks within a chunk body — a blank line.
_ROW_SEP = "\n\n"


@dataclass(frozen=True)
class _SubTableContext:
    sheet: str
    subtable: int | None
    columns: tuple[str, ...]


class MarkdownTableParser:
    """Parse `## Sheet: ... / Subtable: N` sections back into structured rows."""

    def parse(
        self, content: str
    ) -> list[tuple[_SubTableContext, list[dict[str, str]]]]:
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
        dropped = 0
        # lines[1] is the separator (`|---|---|`); skip it.
        for line in lines[2:]:
            cells = MarkdownTableParser._row_cells(line)
            if len(cells) != len(header_cells):
                dropped += 1
                continue
            body.append(dict(zip(header_cells, cells, strict=True)))
        if dropped:
            logger.debug(
                "row_kv_excel: parser dropped rows whose cell count != header count",
                dropped=dropped,
                kept=len(body),
                header_cells=len(header_cells),
            )
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

    def preamble(self, ctx: _SubTableContext) -> str:
        """Render the sheet/subtable/columns header that prefixes every chunk."""
        lines: list[str] = [f"Sheet: {ctx.sheet}"]
        if ctx.subtable is not None:
            lines.append(f"Subtable: {ctx.subtable}")
        lines.append(f"Columns: {', '.join(ctx.columns)}")
        return "\n".join(lines)

    def row_block(self, ctx: _SubTableContext, row: dict[str, str]) -> str:
        """Render one row as a KV block (no trailing separator)."""
        lines: list[str] = ["Row:"]
        for col in ctx.columns:
            value = row.get(col, "")
            if value == "":
                continue
            lines.append(f"  {col}: {value}")
        return "\n".join(lines)

    def build(self, ctx: _SubTableContext, rows: Iterable[dict[str, str]]) -> str:
        """Render preamble + body for the given rows. Compatible output format."""
        preamble = self.preamble(ctx)
        blocks = [self.row_block(ctx, r) for r in rows]
        if not blocks:
            return f"{preamble}\n"
        return f"{preamble}\n\n{_ROW_SEP.join(blocks)}\n"


class RowKVChunker:
    """Pack rows into chunks under a character budget, re-emitting context per chunk.

    Single-pass O(N): pre-renders each row block once, then walks them while
    tracking the projected chunk length. Only assembles the full chunk string
    at emit time, not on every probe.
    """

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
        preamble = self._renderer.preamble(ctx)
        blocks = [self._renderer.row_block(ctx, r) for r in rows]
        # Chunk shape: "{preamble}\n\n{block}{_ROW_SEP}{block}...\n"
        # — preamble + "\n\n" + (N blocks joined by _ROW_SEP) + trailing "\n".
        overhead = len(preamble) + 2 + 1  # "\n\n" after preamble + trailing "\n"
        sep_len = len(_ROW_SEP)

        chunks: list[str] = []
        current: list[str] = []
        current_body_len = 0
        for block in blocks:
            addition = len(block) if not current else len(block) + sep_len
            if current and overhead + current_body_len + addition > max_size:
                chunks.append(f"{preamble}\n\n{_ROW_SEP.join(current)}\n")
                current = [block]
                current_body_len = len(block)
            else:
                current.append(block)
                current_body_len += addition
        if current:
            chunks.append(f"{preamble}\n\n{_ROW_SEP.join(current)}\n")
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

        # Match legacy ExcelSplitter: bound per-section output so a 50k-row
        # sheet doesn't silently emit 50k chunks.
        md_cfg = self.settings.global_config.chunking.strategies.markdown
        per_section_cap = min(
            md_cfg.max_chunks_per_section,
            self.settings.global_config.chunking.max_chunks_per_document // 2,
        )

        chunks: list[str] = []
        for ctx, rows in sections:
            section_chunks = self._chunker.chunk(ctx, rows, max_size=max_size)
            if len(section_chunks) > per_section_cap:
                logger.warning(
                    "row_kv_excel: section reached max_chunks_per_section cap, truncating",
                    sheet=ctx.sheet,
                    subtable=ctx.subtable,
                    produced=len(section_chunks),
                    cap=per_section_cap,
                    rows_dropped=len(rows)
                    - sum(c.count("Row:") for c in section_chunks[:per_section_cap]),
                )
                section_chunks = section_chunks[:per_section_cap]
            chunks.extend(section_chunks)
        return chunks
