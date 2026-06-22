"""The conversion composition root: pick an engine from config, convert a file,
hand the connector one uniform result.

This is where the ``markitdown`` | ``docling`` choice is resolved (config-driven, not
a feature flag). Connectors depend on :class:`ConversionService` and
:class:`ConvertedFile`; they never branch on the engine themselves. The two engines
produce fundamentally different artifacts — markitdown a markdown string, docling a
structured ``DoclingDocument`` — and :class:`ConvertedFile` carries both shapes so a
single downstream contract works for either:

* ``content`` — markdown for *both* engines (docling exports its structure to markdown
  for display, state and the content hash), so existing consumers keep working.
* ``converted_document`` — the structured artifact, present only on the docling path.
  This is what the docling chunking strategy consumes for structure-aware chunking;
  it rides the in-process ``Document`` by reference to the chunker (never serialized).

Per-document engine failures are NOT raised here — docling reports them as a status on
its outcome, and this service projects that into a fallback ``ConvertedFile`` mirroring
today's ``conversion_method="*_fallback"`` behavior, so a connector never has to special
-case the engine. Policy/precondition errors (unsupported format, too large) remain the
caller's gate, exactly as today.

A docling ``PARTIAL_SUCCESS`` (e.g. a document_timeout truncating the document mid-parse)
yields usable-but-incomplete content: it is still indexed as ``conversion_method="docling"``
(content is real), but it is logged as a distinct warning so a truncated document never
passes silently as if it were complete. The fallback-document template and
``original_file_type`` classification are shared with the markitdown path (the canonical
:class:`FileConverter`/:class:`FileDetector`) so the two engines stamp identical metadata.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from qdrant_loader.utils.logging import LoggingConfig

from .engine import EngineKind, build_engine
from .formats import FormatPolicy
from .outcome import ConversionStatus

if TYPE_CHECKING:
    from qdrant_loader.core.file_conversion.conversion_config import (
        FileConversionConfig,
    )
    from qdrant_loader.core.file_conversion.file_detector import FileDetector

    from .engine import ConversionEngine
    from .outcome import ConvertedDocument

logger = LoggingConfig.get_logger(__name__)


class MarkitdownConverter(Protocol):
    """The slice of ``FileConverter`` the markitdown path depends on.

    Depending on this Protocol rather than the concrete ``FileConverter`` keeps the
    legacy engine injectable (and therefore testable without the markitdown library).
    """

    def convert_file(self, file_path: str) -> str: ...

    def create_fallback_document(self, file_path: str, error: Exception) -> str: ...


@dataclass(frozen=True, slots=True)
class ConvertedFile:
    """The uniform conversion result a connector turns into a ``Document``.

    ``conversion_method`` and ``conversion_failed`` map straight onto the existing
    metadata contract (``"markitdown"`` / ``"markitdown_fallback"`` / ``"docling"`` /
    ``"docling_fallback"``); ``converted_document`` is the structured artifact for the
    docling chunking path (``None`` for markitdown and for any fallback).
    """

    content: str
    conversion_method: str
    conversion_failed: bool
    original_file_type: str
    converted_document: ConvertedDocument | None = None


class ConversionService:
    """Selects the configured engine and converts files to a :class:`ConvertedFile`."""

    def __init__(
        self,
        config: FileConversionConfig,
        *,
        markitdown_converter: MarkitdownConverter | None = None,
    ) -> None:
        self._config = config
        self._injected_markitdown = markitdown_converter

    @cached_property
    def _docling_engine(self) -> ConversionEngine:
        """Build the docling engine once (it caches pipelines internally)."""
        return build_engine(EngineKind.DOCLING, self._config.docling.to_config())

    @cached_property
    def _markitdown_converter(self) -> MarkitdownConverter:
        """The injected converter, or a lazily-built ``FileConverter``.

        Imported lazily so the docling path never drags in markitdown.
        """
        if self._injected_markitdown is not None:
            return self._injected_markitdown
        from qdrant_loader.core.file_conversion.file_converter import FileConverter

        return FileConverter(self._config)

    @cached_property
    def _file_detector(self) -> FileDetector:
        """One shared ``FileDetector`` for ``original_file_type`` classification.

        Held lazily (built once, reused) so the docling path stamps the same type
        the rest of the system does, rather than a raw suffix.
        """
        from qdrant_loader.core.file_conversion.file_detector import FileDetector

        return FileDetector()

    def convert(self, file_path: str) -> ConvertedFile:
        """Convert ``file_path`` using the configured engine.

        The caller is responsible for the supported-type / size gate (via
        :meth:`is_supported`), so this dispatches purely on the configured engine.
        """
        match self._config.engine:
            case EngineKind.DOCLING:
                return self._convert_with_docling(file_path)
            case EngineKind.MARKITDOWN:
                return self._convert_with_markitdown(file_path)
        raise ValueError(f"unknown conversion engine: {self._config.engine!r}")

    def is_supported(self, file_path: str) -> bool:
        """Whether the configured engine can convert ``file_path`` — one gate.

        Connectors call this instead of reaching for ``FileDetector`` directly, so
        eligibility tracks the *active* engine rather than a single static MIME table:

        * ``markitdown`` — preserves today's behaviour exactly: delegate to
          ``FileDetector.is_supported_for_conversion``.
        * ``docling`` — supported only when the FileDetector says convertible (keeping
          the natively-handled exclusions like ``.md``/``.html``) AND the file falls
          within docling's own :class:`~.formats.FormatPolicy` (enabled format + size
          cap), so the two sources of truth can no longer disagree.
        """
        detector = self._file_detector
        if self._config.engine is EngineKind.MARKITDOWN:
            return detector.is_supported_for_conversion(file_path)

        if not detector.is_supported_for_conversion(file_path):
            return False
        policy = self._format_policy
        mime_type, _ = detector.detect_file_type(file_path)
        if mime_type not in policy.supported_mime_types():
            return False
        try:
            size_bytes = os.path.getsize(file_path)
        except OSError:
            return False
        return policy.is_within_size_limit(size_bytes)

    @cached_property
    def _format_policy(self) -> FormatPolicy:
        """docling's conversion-eligibility policy, built once from the engine config."""
        return FormatPolicy(self._config.docling.to_config())

    # ── docling path (full Option B) ────────────────────────────────────────────
    def _convert_with_docling(self, file_path: str) -> ConvertedFile:
        outcome = self._docling_engine.convert(file_path)
        original_file_type = self._file_type(file_path)

        if outcome.succeeded and outcome.document is not None:
            if outcome.status is ConversionStatus.PARTIAL:
                # PARTIAL_SUCCESS (e.g. document_timeout mid-document): content is
                # real and usable, so we still index it as a docling document — but
                # it is truncated/incomplete, so it must NOT pass silently.
                logger.warning(
                    "Docling conversion was partial; indexing truncated content",
                    file_path=file_path,
                    error=outcome.error,
                )
            return ConvertedFile(
                content=outcome.document.to_markdown(),
                conversion_method="docling",
                conversion_failed=False,
                original_file_type=original_file_type,
                converted_document=outcome.document,
            )

        # FAILED: fall back to the canonical document, mirroring markitdown_fallback.
        logger.warning(
            "Docling conversion did not succeed; emitting fallback document",
            file_path=file_path,
            status=str(outcome.status),
            error=outcome.error,
        )
        # Reuse FileConverter's canonical fallback so the docling and markitdown
        # paths emit identical fallback documents (no divergent local stub). This
        # lazily builds FileConverter, but only on a docling FAILURE (rare).
        error = Exception(outcome.error or "conversion failed")
        return ConvertedFile(
            content=self._markitdown_converter.create_fallback_document(
                file_path, error
            ),
            conversion_method="docling_fallback",
            conversion_failed=True,
            original_file_type=original_file_type,
            converted_document=None,
        )

    # ── markitdown path (legacy behavior, now behind the service) ────────────────
    def _convert_with_markitdown(self, file_path: str) -> ConvertedFile:
        """Delegate to the markitdown converter, mirroring the connectors' contract.

        Success -> ``conversion_method="markitdown"``; any ``FileConversionError``
        (including timeouts) -> a fallback document with ``"markitdown_fallback"`` and
        ``conversion_failed=True`` — exactly the three-way branch the connectors use
        today. There is no structured artifact on this path.
        """
        from qdrant_loader.core.file_conversion.exceptions import FileConversionError

        converter = self._markitdown_converter
        original_file_type = self._file_type(file_path)
        try:
            return ConvertedFile(
                content=converter.convert_file(file_path),
                conversion_method="markitdown",
                conversion_failed=False,
                original_file_type=original_file_type,
                converted_document=None,
            )
        except FileConversionError as error:
            return ConvertedFile(
                content=converter.create_fallback_document(file_path, error),
                conversion_method="markitdown_fallback",
                conversion_failed=True,
                original_file_type=original_file_type,
                converted_document=None,
            )

    def _file_type(self, file_path: str) -> str:
        """The ``original_file_type`` contract, via the shared FileDetector.

        Reuses ``FileDetector.get_file_type_info`` so both engines stamp the same
        normalized type the rest of the system uses, with a suffix-based fallback
        for files the detector can't classify (e.g. unknown extensions).
        """
        normalized = self._file_detector.get_file_type_info(file_path).get(
            "normalized_type"
        )
        return normalized or Path(file_path).suffix.lstrip(".").lower() or "unknown"
