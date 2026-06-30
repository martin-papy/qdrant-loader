"""Tests for the ConversionService composition root (config-driven engine selection).

The markitdown branch is exercised with an injected fake converter: the real
markitdown library is heavy (and currently broken in this environment), and these
tests are about ConversionService's *orchestration* — which engine it picks, how it
maps success/failure onto the metadata contract — not about markitdown itself. The
docling branch is exercised with a stub engine returning pre-canned outcomes, so the
status -> ConvertedFile projection (success / partial / failure) is pinned without
running real docling over a fixture.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from qdrant_loader.core.conversion.outcome import (
    ConversionOutcome,
    ConversionStatus,
)
from qdrant_loader.core.conversion.service import ConversionService, ConvertedFile
from qdrant_loader.core.file_conversion.conversion_config import FileConversionConfig
from qdrant_loader.core.file_conversion.exceptions import FileConversionError

try:
    import docling as _docling  # noqa: F401
    _docling_available = True
except ModuleNotFoundError:
    _docling_available = False

_skip_no_docling = pytest.mark.skipif(
    not _docling_available,
    reason="docling optional dependency is not installed",
)


class _StubConvertedDocument:
    """Minimal stand-in for ConvertedDocument: just the ``to_markdown`` contract."""

    def __init__(self, markdown: str):
        self._markdown = markdown

    def to_markdown(self) -> str:
        return self._markdown


class _FakeDoclingEngine:
    """Returns a pre-canned ConversionOutcome, so the docling branch is exercised
    without running real docling over a fixture."""

    def __init__(self, outcome: ConversionOutcome):
        self._outcome = outcome

    def convert(self, source) -> ConversionOutcome:
        return self._outcome


def _docling_service(outcome: ConversionOutcome) -> ConversionService:
    config = FileConversionConfig(engine="docling")
    service = ConversionService(config)
    # cached_property stores on the instance __dict__; pre-seed the fake engine.
    service._docling_engine = _FakeDoclingEngine(outcome)
    return service


class _FakeMarkitdownConverter:
    """Stand-in for FileConverter; drives the markitdown branch without markitdown."""

    def __init__(self, *, text: str | None = None, error: Exception | None = None):
        self._text = text
        self._error = error
        self.fallback_calls: list[tuple[str, Exception]] = []

    def convert_file(self, file_path: str) -> str:
        if self._error is not None:
            raise self._error
        assert self._text is not None
        return self._text

    def create_fallback_document(self, file_path: str, error: Exception) -> str:
        self.fallback_calls.append((file_path, error))
        return f"# fallback for {file_path}"


def _markitdown_service(converter: _FakeMarkitdownConverter) -> ConversionService:
    config = FileConversionConfig(engine="markitdown")
    return ConversionService(config, markitdown_converter=converter)


def test_markitdown_success_returns_markdown_with_markitdown_method():
    converter = _FakeMarkitdownConverter(text="# Report\n\nbody text")
    service = _markitdown_service(converter)

    result = service.convert("/docs/report.docx")

    assert isinstance(result, ConvertedFile)
    assert result.content == "# Report\n\nbody text"
    assert result.conversion_method == "markitdown"
    assert result.conversion_failed is False
    assert result.converted_document is None
    assert result.original_file_type == "docx"


def test_markitdown_failure_uses_fallback_document_and_fallback_method():
    boom = FileConversionError("kaboom", file_path="/docs/broken.pdf")
    converter = _FakeMarkitdownConverter(error=boom)
    service = _markitdown_service(converter)

    result = service.convert("/docs/broken.pdf")

    assert result.conversion_method == "markitdown_fallback"
    assert result.conversion_failed is True
    assert result.content == "# fallback for /docs/broken.pdf"
    assert result.converted_document is None
    assert result.original_file_type == "pdf"
    assert converter.fallback_calls == [("/docs/broken.pdf", boom)]


# -- docling path: PARTIAL is usable but must be flagged -------------------------
def test_docling_success_returns_docling_content_without_warning():
    import qdrant_loader.core.conversion.service as conv_module

    doc = _StubConvertedDocument("# Full document\n\nall content present")
    outcome = ConversionOutcome(status=ConversionStatus.SUCCESS, document=doc)
    service = _docling_service(outcome)

    with patch.object(conv_module, "logger") as mock_logger:
        result = service.convert("/docs/report.pdf")

    assert result.content == "# Full document\n\nall content present"
    assert result.conversion_method == "docling"
    assert result.conversion_failed is False
    assert result.converted_document is doc
    assert mock_logger.warning.call_count == 0  # a clean SUCCESS must not warn


def test_docling_partial_logs_warning_but_still_returns_usable_content():
    """A PARTIAL outcome (e.g. document_timeout mid-document -> truncated content) is
    still usable, so we index it as docling content — but it must NOT pass silently:
    a distinct warning naming the file + that content is truncated/partial fires."""
    import qdrant_loader.core.conversion.service as conv_module

    doc = _StubConvertedDocument("# Truncated document\n\npartial content")
    outcome = ConversionOutcome(status=ConversionStatus.PARTIAL, document=doc)
    service = _docling_service(outcome)

    with patch.object(conv_module, "logger") as mock_logger:
        result = service.convert("/docs/huge.pdf")

    # content is still usable docling output, indexed as a real (not fallback) doc
    assert result.content == "# Truncated document\n\npartial content"
    assert result.conversion_method == "docling"
    assert result.conversion_failed is False
    assert result.converted_document is doc

    # but a distinct warning must have fired, naming the file
    assert mock_logger.warning.call_count == 1
    call_args = mock_logger.warning.call_args
    event_msg = call_args[0][0]  # first positional arg is the event string
    assert "/docs/huge.pdf" in str(call_args)
    assert "partial" in event_msg.lower() or "truncat" in event_msg.lower()


def test_docling_failure_uses_canonical_fallback_document():
    """The docling FAILURE path must reuse FileConverter's canonical
    create_fallback_document, not a divergent local stub."""
    outcome = ConversionOutcome(
        status=ConversionStatus.FAILED, error="docling exploded"
    )
    service = _docling_service(outcome)

    fallback_calls: list[tuple[str, Exception]] = []

    class _FakeMarkitdown:
        def convert_file(self, file_path: str) -> str:  # pragma: no cover
            raise AssertionError("convert_file must not be called on the docling path")

        def create_fallback_document(self, file_path: str, error: Exception) -> str:
            fallback_calls.append((file_path, error))
            return f"# canonical fallback for {file_path}"

    service._markitdown_converter = _FakeMarkitdown()

    result = service.convert("/docs/broken.pdf")

    assert result.conversion_method == "docling_fallback"
    assert result.conversion_failed is True
    assert result.converted_document is None
    assert result.content == "# canonical fallback for /docs/broken.pdf"
    # the canonical fallback was called with an Exception wrapping the outcome error
    assert len(fallback_calls) == 1
    called_path, called_error = fallback_calls[0]
    assert called_path == "/docs/broken.pdf"
    assert isinstance(called_error, Exception)
    assert "docling exploded" in str(called_error)


def test_docling_original_file_type_uses_filedetector_classification(tmp_path):
    """original_file_type on the docling path is FileDetector's normalized
    type (the same type the rest of the system stamps), not a raw suffix."""
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")
    doc = _StubConvertedDocument("# ok")
    outcome = ConversionOutcome(status=ConversionStatus.SUCCESS, document=doc)
    service = _docling_service(outcome)

    result = service.convert(str(pdf))

    assert result.original_file_type == "pdf"


# -- engine-aware is_supported gate ----------------------------------------------
def _service_for(engine: str) -> ConversionService:
    return ConversionService(FileConversionConfig(engine=engine))


def test_markitdown_is_supported_delegates_to_file_detector(tmp_path):
    """For markitdown, is_supported preserves today's behaviour: delegate to
    FileDetector.is_supported_for_conversion."""
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")
    md = tmp_path / "notes.md"  # markdown is handled natively, excluded
    md.write_text("# hello")

    service = _service_for("markitdown")
    assert service.is_supported(str(pdf)) is True
    assert service.is_supported(str(md)) is False


@_skip_no_docling
def test_docling_is_supported_true_for_pdf_within_policy(tmp_path):
    """For docling, a PDF is supported: FileDetector says convertible AND it falls
    within docling's FormatPolicy."""
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")

    service = _service_for("docling")
    assert service.is_supported(str(pdf)) is True


def test_docling_is_supported_false_when_file_detector_rejects(tmp_path):
    """A file the FileDetector excludes (markdown, handled natively) is not supported
    by the docling engine either."""
    md = tmp_path / "notes.md"
    md.write_text("# hello")

    service = _service_for("docling")
    assert service.is_supported(str(md)) is False


@_skip_no_docling
def test_docling_is_supported_false_when_outside_format_policy(tmp_path):
    """A file the FileDetector accepts but whose format is NOT in docling's
    FormatPolicy (e.g. epub — MarkItDown-supported, not a docling enabled format)
    is rejected by the engine-aware gate."""
    epub = tmp_path / "book.epub"
    epub.write_bytes(b"PK\x03\x04 epub stub")

    service = _service_for("docling")
    # FileDetector treats epub as convertible (MarkItDown table) ...
    assert service._file_detector.is_supported_for_conversion(str(epub)) is True
    # ... but docling's FormatPolicy does not enable it, so the engine-aware gate rejects.
    assert service.is_supported(str(epub)) is False


@_skip_no_docling
def test_docling_is_supported_false_when_over_size_limit(tmp_path):
    """A convertible, in-policy file that exceeds docling's max_file_size is rejected."""
    big = tmp_path / "huge.pdf"
    big.write_bytes(b"%PDF-1.4 ")

    config = FileConversionConfig(engine="docling")
    # shrink docling's size cap so our small stub exceeds it
    config.docling.max_file_size = 4
    service = ConversionService(config)

    assert service.is_supported(str(big)) is False
