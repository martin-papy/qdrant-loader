"""Behaviour tests for the structure anti-corruption layer.

These assert that ``StructureProjector`` turns *real* docling chunk metadata into
our engine-neutral :class:`ChunkStructure` and, crucially,
that no docling type leaks across the boundary (labels become plain strings, the
coord-origin enum becomes a string, boxes become floats). They are not a re-test of
docling's own metadata extraction.
"""

from __future__ import annotations

from qdrant_loader.core.chunking.docling.structure import (
    BoundingBoxSpan,
    ChunkStructure,
    StructureProjector,
)


def test_projects_heading_path_from_real_docling_meta(header_doc_chunks):
    """The headline field: a chunk's heading path becomes heading_path, and
    heading_level reflects its nesting depth."""
    projector = StructureProjector()

    # chunk 0 sits under "Test Document" > "Section 1"
    shallow = projector.project(header_doc_chunks[0])
    assert shallow.heading_path == ("Test Document", "Section 1")
    assert shallow.heading_level == 2

    # a deeper chunk carries the full path; depth grows with it
    deep = next(c for c in header_doc_chunks if len(c.meta.headings or []) >= 3)
    projected_deep = projector.project(deep)
    assert projected_deep.heading_path == tuple(deep.meta.headings)
    assert projected_deep.heading_level == len(deep.meta.headings)


def test_heading_chunks_are_prose_not_tables(header_doc_chunks):
    """Prose chunks: text doc-items, no table/picture rollup, no page provenance
    (docx text carries none)."""
    structure = StructureProjector().project(header_doc_chunks[0])

    assert structure.is_table is False
    assert structure.is_picture is False
    assert structure.doc_items == ("text", "text")
    assert structure.page_start is None
    assert structure.page_end is None
    assert structure.bbox == ()
    assert structure.charspan is None


def test_projects_table_label_and_provenance_from_xlsx(xlsx_doc_chunks):
    """The xlsx chunk's TABLE items roll up to is_table and carry page + bbox."""
    structure = StructureProjector().project(xlsx_doc_chunks[0])

    assert structure.is_table is True
    assert "table" in structure.doc_items
    assert structure.page_start == 1
    assert structure.page_end == 1
    assert structure.bbox, "table provenance should yield bounding boxes"
    assert structure.charspan is not None and len(structure.charspan) == 2


def test_no_docling_types_leak_across_the_boundary(xlsx_doc_chunks):
    """The anti-corruption guarantee: labels are plain strings, bbox is floats + a
    string coord-origin (JSON-safe), never docling enums."""
    structure = StructureProjector().project(xlsx_doc_chunks[0])

    assert all(isinstance(label, str) for label in structure.doc_items)
    box = structure.bbox[0]
    assert isinstance(box, BoundingBoxSpan)
    assert isinstance(box.left, float) and isinstance(box.bottom, float)
    assert isinstance(box.coord_origin, str)  # not docling's CoordOrigin enum


def test_carries_docmeta_version_for_reproducibility(header_doc_chunks):
    structure = StructureProjector().project(header_doc_chunks[0])
    assert isinstance(structure.dl_meta_version, str)
    assert structure.dl_meta_version  # non-empty


def test_projection_returns_frozen_chunk_structure(header_doc_chunks):
    structure = StructureProjector().project(header_doc_chunks[0])
    assert isinstance(structure, ChunkStructure)
