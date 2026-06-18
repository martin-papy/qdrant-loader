"""Behaviour tests for the chunk -> Document mapper.

The mapper is the docling-free half of the layer, so these are fully offline: we
hand-build engine-neutral Chunks and assert the produced chunk Documents carry the
chunk payload contract — the structure block, the back-compat metadata keys derived
from it, deterministic ids, and JSON-safe payloads.
"""

from __future__ import annotations

import json

from qdrant_loader.core.chunking.docling import (
    Chunk,
    ChunkDocumentMapper,
    ChunkingConfig,
    ChunkStructure,
)
from qdrant_loader.core.chunking.docling.structure import BoundingBoxSpan
from qdrant_loader.core.document import Document


def _parent() -> Document:
    return Document(
        id="",
        title="Quarterly Report",
        content_type="docx",
        content="full body",
        source_type="localfile",
        source="reports",
        url="http://example.test/report.docx",
        metadata={"project_id": "proj-1", "original_file_type": "docx"},
    )


def _chunks() -> list[Chunk]:
    prose = Chunk(
        text="Revenue grew.",
        embed_text="Revenue grew.",
        structure=ChunkStructure(
            heading_path=("Quarterly Report", "Section 1"),
            heading_level=2,
            doc_items=("text",),
        ),
        token_count=3,
    )
    table = Chunk(
        text="Q1 | 100",
        embed_text="Q1 | 100",
        structure=ChunkStructure(
            doc_items=("table",),
            is_table=True,
            page_start=1,
            page_end=1,
            bbox=(BoundingBoxSpan(1.0, 1.0, 2.0, 2.0, "TOPLEFT"),),
            charspan=(0, 0),
            dl_meta_version="1.0.0",
        ),
        token_count=5,
    )
    return [prose, table]


def _map(chunks=None, parent=None) -> list[Document]:
    return ChunkDocumentMapper(ChunkingConfig()).to_documents(
        chunks or _chunks(), parent or _parent()
    )


def test_one_document_per_chunk_with_ordered_indices():
    docs = _map()
    assert len(docs) == 2
    assert [d.metadata["chunk_index"] for d in docs] == [0, 1]
    assert all(d.metadata["total_chunks"] == 2 for d in docs)


def test_chunk_ids_are_deterministic():
    parent = _parent()
    chunks = _chunks()
    first = ChunkDocumentMapper(ChunkingConfig()).to_documents(chunks, parent)
    second = ChunkDocumentMapper(ChunkingConfig()).to_documents(chunks, parent)

    assert [d.id for d in first] == [d.id for d in second]  # stable across runs
    assert first[0].id == Document.generate_chunk_id(parent.id, 0)
    assert first[1].id == Document.generate_chunk_id(parent.id, 1)
    assert first[0].id != first[1].id


def test_content_is_the_chunk_body():
    docs = _map()
    assert docs[0].content == "Revenue grew."
    assert docs[1].content == "Q1 | 100"


def _contextual_chunk() -> Chunk:
    """A chunk whose embed_text carries a heading breadcrumb its body does not."""
    return Chunk(
        text="Revenue grew.",
        embed_text="Quarterly Report > Section 1\nRevenue grew.",
        structure=ChunkStructure(
            heading_path=("Quarterly Report", "Section 1"),
            heading_level=2,
            doc_items=("text",),
        ),
        token_count=8,
    )


def test_content_is_contextualized_when_include_context_in_embed():
    """With the flag on, the stored content becomes the contextualized embed text —
    so the heading breadcrumb lands in both the payload and (via content) the vector."""
    mapper = ChunkDocumentMapper(ChunkingConfig(include_context_in_embed=True))
    docs = mapper.to_documents([_contextual_chunk()], _parent())
    assert docs[0].content == "Quarterly Report > Section 1\nRevenue grew."


def test_content_is_bare_body_when_context_disabled():
    """With the flag off (default), content stays the bare body, no breadcrumb."""
    mapper = ChunkDocumentMapper(ChunkingConfig())
    docs = mapper.to_documents([_contextual_chunk()], _parent())
    assert docs[0].content == "Revenue grew."


def test_structure_block_is_projected_engine_neutral():
    docs = _map()
    prose_structure = docs[0].metadata["structure"]
    assert prose_structure["heading_path"] == ["Quarterly Report", "Section 1"]
    assert prose_structure["is_table"] is False

    table_structure = docs[1].metadata["structure"]
    assert table_structure["is_table"] is True
    assert table_structure["page_start"] == 1
    assert table_structure["bbox"] == [
        {
            "left": 1.0,
            "top": 1.0,
            "right": 2.0,
            "bottom": 2.0,
            "coord_origin": "TOPLEFT",
        }
    ]


def test_payload_metadata_is_json_serialisable():
    """The whole point of the anti-corruption layer: the payload is JSON-safe (no
    tuples-as-keys, no docling objects, no dataclasses)."""
    docs = _map()
    for doc in docs:
        json.dumps(doc.metadata)  # must not raise


def test_legacy_compat_keys_derived_from_structure():
    docs = _map()
    assert docs[0].metadata["section_breadcrumb"] == "Quarterly Report > Section 1"
    assert docs[0].metadata["section_depth"] == 2
    assert docs[0].metadata["section_title"] == "Section 1"
    assert all(d.metadata["chunking_strategy"] == "docling" for d in docs)


def test_parent_linkage_and_parent_metadata_preserved():
    parent = _parent()
    docs = _map(parent=parent)
    assert all(d.metadata["parent_document_id"] == parent.id for d in docs)
    assert all(d.metadata["parent_document_title"] == "Quarterly Report" for d in docs)
    # parent's own metadata survives (e.g. project scoping)
    assert all(d.metadata["project_id"] == "proj-1" for d in docs)


def test_chunk_schema_version_is_stamped():
    docs = _map()
    assert all(d.metadata["chunk_schema_version"] == "1" for d in docs)
