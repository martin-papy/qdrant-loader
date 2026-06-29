"""The conversion -> chunking handoff types, and the typed failure model.

Conversion produces a *structured* artifact — a ``DoclingDocument`` wrapped in
:class:`ConvertedDocument` — or a typed :class:`ConversionOutcome`. It never
returns a fake markdown stub carrying an error string: failure is a value the caller
inspects, not content that flows into embedding.

Per the conversion/chunking boundary, the structured document is the contract;
``to_markdown`` is a convenience for the prose path, and the chunker chooses its
own view (structured table traversal vs. markdown) per format.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docling.datamodel.document import ConversionResult
    from docling_core.types.doc import DoclingDocument


class ConversionStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"  # docling PARTIAL_SUCCESS (e.g. document_timeout mid-doc)
    FAILED = "failed"
    SKIPPED = "skipped"  # rejected by policy (format not enabled / too large)


@dataclass(frozen=True, slots=True)
class ConvertedDocument:
    """The canonical conversion artifact handed to the chunking layer.

    Holds the structured ``DoclingDocument`` so consumers can read cells/tables
    directly — no serialize-then-reparse round-trip.
    """

    document: DoclingDocument
    source_format: str  # the InputFormat value, e.g. "pdf"

    def to_markdown(self) -> str:
        """One-way serialization for the prose path. Not the primary contract."""
        return self.document.export_to_markdown()


@dataclass(frozen=True, slots=True)
class ConversionOutcome:
    """The result value of a conversion attempt; the caller owns skip-vs-stub policy."""

    status: ConversionStatus
    document: ConvertedDocument | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL)

    @classmethod
    def skipped(cls, reason: str) -> ConversionOutcome:
        """A source the policy declined to convert (format/size)."""
        return cls(status=ConversionStatus.SKIPPED, error=reason)

    @classmethod
    def failed(cls, error: str) -> ConversionOutcome:
        """The engine attempted conversion and failed."""
        return cls(status=ConversionStatus.FAILED, error=error)

    @classmethod
    def from_docling_result(cls, docling_result: ConversionResult) -> ConversionOutcome:
        """Translate a docling ``ConversionResult`` into our typed outcome."""
        from docling.datamodel.base_models import ConversionStatus as DoclingStatus

        if docling_result.status in (
            DoclingStatus.SUCCESS,
            DoclingStatus.PARTIAL_SUCCESS,
        ):
            status = (
                ConversionStatus.SUCCESS
                if docling_result.status is DoclingStatus.SUCCESS
                else ConversionStatus.PARTIAL
            )
            source_format = docling_result.input.format.value
            # Repair docling's XLSX defects (merged-cell duplication, dropped
            # sheet names) once on the structured document, before either the
            # markdown export or the chunker reads it. No-op for other formats.
            from .postprocess import postprocess_spreadsheet

            postprocess_spreadsheet(docling_result.document, source_format)
            document = ConvertedDocument(
                document=docling_result.document,
                source_format=source_format,
            )
            return cls(status=status, document=document)

        message = (
            "; ".join(error.error_message for error in docling_result.errors)
            or "conversion failed"
        )
        return cls(status=ConversionStatus.FAILED, error=message)
