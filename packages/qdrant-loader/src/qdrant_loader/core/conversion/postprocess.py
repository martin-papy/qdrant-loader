"""Post-processing of the docling ``DoclingDocument`` for spreadsheet inputs.

docling's Excel backend has two defects that hurt every downstream consumer
(markdown export *and* the HybridChunker, since both read the same structured
document). We repair them once, immediately after parsing, at the single choke
point where the :class:`~.outcome.ConvertedDocument` is built — so there is no
serialize/reparse round-trip and both views see the fix.

Defect 1 — merged-cell duplication
    A merged cell is stored *once* in ``table.data.table_cells`` with correct
    span info, but ``TableData.grid`` (a computed property) — and every
    serializer that reads it — expands that one cell into *every* position it
    spans. A title merged across N columns becomes the same text N times. We
    keep the anchor cell (and its span metadata) intact and append explicit
    empty 1x1 filler cells for the non-anchor positions; because ``grid``
    derives itself by overwriting positions in ``table_cells`` order, the
    later fillers blank the vacated positions while the anchor survives.

    NOTE on object identity: ``grid`` is a ``@computed_field`` rebuilt on every
    access, and within it all spanned positions are the *same* ``TableCell``
    object as the anchor. Mutating a grid position is therefore both futile
    (not persisted) and dangerous (would mutate the anchor). The repair has to
    live in ``table_cells``, which is what this does.

Defect 2 — sheet names dropped
    Each sheet survives as a body group whose ``name`` is ``"sheet: <name>"``,
    but neither markdown export nor chunk contextualization surfaces it
    (markitdown emitted ``## Sheet: <name>`` headings). We insert a
    ``SECTION_HEADER`` text item as the first child of each sheet group, so the
    name becomes a markdown heading and rides into each chunk's heading path.

Both repairs are strictly-better, default-on, and apply *only* to spreadsheet
inputs — prose formats (PDF/DOCX) are untouched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docling_core.types.doc import DoclingDocument

# docling's InputFormat.value for spreadsheets, and the prefix its Excel backend
# stamps onto each sheet group's name.
_XLSX_FORMAT = "xlsx"
_SHEET_PREFIX = "sheet:"


def postprocess_spreadsheet(document: DoclingDocument, source_format: str) -> None:
    """Repair the two XLSX defects in place. No-op for non-spreadsheet formats.

    ``source_format`` is the ``ConvertedDocument.source_format`` (the docling
    ``InputFormat.value``); we gate on it so PDFs/DOCX are never touched.
    """
    if source_format.lower() != _XLSX_FORMAT:
        return

    _dedupe_merged_cells(document)
    _surface_sheet_headings(document)


def _dedupe_merged_cells(document: DoclingDocument) -> None:
    """Stop merged cells from being serialized once per spanned position.

    For every multi-row/col cell, append empty 1x1 filler cells covering all
    non-anchor positions. ``TableData.grid`` rebuilds itself by writing each
    ``table_cells`` entry over its offset range in list order, so the fillers
    (added last) overwrite the duplicate positions while leaving the anchor —
    at ``(start_row_offset_idx, start_col_offset_idx)`` — and its span intact.
    """
    from docling_core.types.doc.document import TableCell

    for table in document.tables:
        data = table.data
        fillers: list[TableCell] = []
        for cell in data.table_cells:
            if cell.col_span <= 1 and cell.row_span <= 1:
                continue
            anchor_row = cell.start_row_offset_idx
            anchor_col = cell.start_col_offset_idx
            for row in range(cell.start_row_offset_idx, cell.end_row_offset_idx):
                for col in range(cell.start_col_offset_idx, cell.end_col_offset_idx):
                    if row == anchor_row and col == anchor_col:
                        continue  # keep the anchor's text exactly once
                    fillers.append(
                        TableCell(
                            text="",
                            row_span=1,
                            col_span=1,
                            start_row_offset_idx=row,
                            end_row_offset_idx=row + 1,
                            start_col_offset_idx=col,
                            end_col_offset_idx=col + 1,
                        )
                    )
        if fillers:
            data.table_cells.extend(fillers)


def _surface_sheet_headings(document: DoclingDocument) -> None:
    """Insert a SECTION_HEADER as the first child of each sheet group.

    The docling Excel backend names each body group ``"sheet: <name>"``; we lift
    that name into a heading so it shows up in the markdown export and in each
    chunk's heading path. Inserting before the group's current first child (with
    ``after=False``) parents the header on the group and makes it lead the sheet.
    """
    from docling_core.types.doc import DocItemLabel

    for group in document.groups:
        name = group.name or ""
        if not name.lower().startswith(_SHEET_PREFIX) or not group.children:
            continue
        sheet_name = name.split(":", 1)[1].strip()
        first_child = group.children[0].resolve(document)
        document.insert_text(
            sibling=first_child,
            label=DocItemLabel.SECTION_HEADER,
            text=f"Sheet: {sheet_name}",
            after=False,
        )
