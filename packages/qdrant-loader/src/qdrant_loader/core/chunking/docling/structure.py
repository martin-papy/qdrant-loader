"""The anti-corruption layer: docling chunk metadata -> engine-neutral structure.

Docling computes layout/provenance during conversion (heading paths, page numbers,
bounding boxes, char spans, element labels). The legacy chunker throws this away and
*re-derives* a thin version with regex over markdown. This module projects docling's
typed metadata into a small, frozen, JSON-serialisable :class:`ChunkStructure` so
docling classes never reach the Qdrant payload schema and the engine stays swappable
(the same boundary discipline the conversion engine uses).

Docling types are confined to this module and :mod:`.docling_chunker`; everything
downstream (the mapper, the payload) sees only :class:`ChunkStructure`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from docling_core.transforms.chunker import BaseChunk, DocMeta
    from docling_core.types.doc.base import BoundingBox


@dataclass(frozen=True, slots=True)
class BoundingBoxSpan:
    """An element's bounding box, projected off docling's ``BoundingBox``.

    ``coord_origin`` is carried verbatim (``TOPLEFT`` / ``BOTTOMLEFT``) so a
    citation overlay can interpret the coordinates without guessing.
    """

    left: float
    top: float
    right: float
    bottom: float
    coord_origin: str


@dataclass(frozen=True, slots=True)
class ChunkStructure:
    """Engine-neutral structure/provenance for one chunk.

    Every field maps to a docling metadata source (noted inline below). Defaults are
    the "absent" case (native markdown, no layout) so a chunk with no provenance is
    representable without ``None``-checking each field at the call site.
    """

    heading_path: tuple[str, ...] = ()  # meta.headings — also the embed-time prefix
    heading_level: int | None = None  # SectionHeaderItem.level (depth)
    doc_items: tuple[str, ...] = ()  # doc_items[].label values
    is_table: bool = False  # label rollup — element-type filter
    is_picture: bool = False
    page_start: int | None = None  # min(prov.page_no) — page-scoped filter / citation
    page_end: int | None = None  # max(prov.page_no)
    bbox: tuple[
        BoundingBoxSpan, ...
    ] = ()  # prov.bbox — payload-only (high cardinality)
    charspan: tuple[int, int] | None = None  # prov.charspan — source-span citation
    caption: str | None = None  # Table/PictureItem.captions (best-effort)
    dl_meta_version: str | None = None  # DocMeta.version — reproducibility


class StructureProjector:
    """Projects a docling chunk's ``meta`` into a :class:`ChunkStructure`.

    Stateless — it holds no docling object, only the projection rules, so one
    instance is shared across all chunks of a document. ``project`` performs the
    field-by-field translation (headings, ``SectionHeaderItem.level``, the
    ``doc_items[].label`` rollup, the ``prov`` page/bbox/charspan aggregation).
    """

    def project(self, chunk: BaseChunk) -> ChunkStructure:
        # HybridChunker always yields DocChunks; narrow BaseMeta -> DocMeta so the
        # headings/doc_items/version fields it actually carries are visible.
        meta = cast("DocMeta", chunk.meta)
        heading_path = tuple(meta.headings or ())
        doc_items = tuple(item.label.value for item in meta.doc_items)
        provenances = [prov for item in meta.doc_items for prov in (item.prov or ())]
        pages = [prov.page_no for prov in provenances if prov.page_no is not None]
        return ChunkStructure(
            heading_path=heading_path,
            heading_level=len(heading_path) or None,
            doc_items=doc_items,
            is_table="table" in doc_items,
            is_picture="picture" in doc_items,
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            bbox=tuple(
                self._to_box(prov.bbox) for prov in provenances if prov.bbox is not None
            ),
            charspan=self._cover_spans(
                [prov.charspan for prov in provenances if prov.charspan is not None]
            ),
            # caption is deferred: DocMeta.captions is deprecated and not carried
            # through merge paths. Populate from picture/table captions if/when that
            # enrichment lands; until then it stays best-effort-absent.
            caption=None,
            dl_meta_version=str(meta.version) if meta.version else None,
        )

    @staticmethod
    def _to_box(bbox: BoundingBox) -> BoundingBoxSpan:
        """Project docling's ``BoundingBox`` to floats + a string coord-origin."""
        return BoundingBoxSpan(
            left=float(bbox.l),
            top=float(bbox.t),
            right=float(bbox.r),
            bottom=float(bbox.b),
            coord_origin=bbox.coord_origin.value,
        )

    @staticmethod
    def _cover_spans(spans: list[tuple[int, int]]) -> tuple[int, int] | None:
        """The char range covering every item's span: (min start, max end)."""
        if not spans:
            return None
        return (min(start for start, _ in spans), max(end for _, end in spans))
