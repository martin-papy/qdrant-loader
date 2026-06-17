"""Regression locks for the config -> docling option mapping.

These assert the *options we hand docling* — no conversion, no models — so they
are fast and pin the five "footgun fixes" from doc 05 §5. If a docling upgrade
or a refactor silently changes one of these defaults, these tests catch it.
"""

from __future__ import annotations

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.docling_parse_v4_backend import DoclingParseV4DocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PictureDescriptionApiOptions,
    RapidOcrOptions,
    TableFormerMode,
)
from qdrant_loader.core.conversion import (
    ConversionConfig,
    ConversionProfile,
    PictureDescriptionConfig,
)
from qdrant_loader.core.conversion.options import DoclingOptionsBuilder


def _pdf_options(config: ConversionConfig):
    builder = DoclingOptionsBuilder(config)
    return builder.build_format_options()[InputFormat.PDF].pipeline_options


def test_fast_profile_disables_ocr_and_uses_fast_tables():
    pdf = _pdf_options(ConversionConfig.from_profile(ConversionProfile.FAST))
    assert pdf.do_ocr is False
    assert pdf.table_structure_options.mode is TableFormerMode.FAST


def test_fast_profile_pins_non_deprecated_pdf_backend():
    """Pin the non-deprecated docling-parse backend.

    docling 2.74.0 turned ``DoclingParseV4DocumentBackend`` into a deprecation
    shim: it now merely emits a ``FutureWarning`` and delegates to its parent,
    ``DoclingParseDocumentBackend`` (the real docling-parse v6 implementation).
    Pinning the parent directly preserves behaviour while killing the warning,
    which becomes a hard error in a future docling release.
    """
    config = ConversionConfig.from_profile(ConversionProfile.FAST)
    pdf_option = DoclingOptionsBuilder(config).build_format_options()[InputFormat.PDF]
    assert pdf_option.backend is DoclingParseDocumentBackend
    # Must not regress to the deprecated v4 shim (the source of the FutureWarning).
    assert pdf_option.backend is not DoclingParseV4DocumentBackend


def test_scanned_profile_pins_rapidocr_english_never_auto():
    """Canary: docling's OCR default auto-resolves to a *chinese* model in this
    venv. We must always pin RapidOcrOptions(lang=['english']). This is the guard
    against the chinese-default footgun reappearing on a docling upgrade."""
    pdf = _pdf_options(ConversionConfig.from_profile(ConversionProfile.SCANNED))
    assert pdf.do_ocr is True
    assert isinstance(pdf.ocr_options, RapidOcrOptions)
    assert pdf.ocr_options.lang == ["english"]
    assert pdf.ocr_options.force_full_page_ocr is True


def test_picture_description_off_by_default_keeps_remote_services_disabled():
    pdf = _pdf_options(ConversionConfig.from_profile(ConversionProfile.FAST))
    assert pdf.do_picture_description is False
    assert pdf.enable_remote_services is False


def test_picture_description_enabled_generates_picture_images():
    """do_picture_description is inert without rendered picture crops: docling's
    enrichment stage only captions pictures whose images were generated, and
    generate_picture_images defaults to False. Docs call for scale >= 2."""
    config = ConversionConfig.from_profile(
        ConversionProfile.FAST,
        picture=PictureDescriptionConfig(enabled=True, api_key="sk-test"),
    )
    pdf = _pdf_options(config)
    assert pdf.generate_picture_images is True
    assert pdf.images_scale >= 2.0


def test_no_picture_images_generated_when_description_disabled():
    """Image generation costs memory per page; keep it off when nothing consumes it."""
    pdf = _pdf_options(ConversionConfig.from_profile(ConversionProfile.FAST))
    assert pdf.generate_picture_images is False


def test_picture_description_enabled_builds_api_options_with_auth():
    config = ConversionConfig.from_profile(
        ConversionProfile.FAST,
        picture=PictureDescriptionConfig(
            enabled=True, api_key="sk-test", model="gpt-4o-mini"
        ),
    )
    pdf = _pdf_options(config)
    assert pdf.enable_remote_services is True
    assert pdf.do_picture_description is True
    options = pdf.picture_description_options
    assert isinstance(options, PictureDescriptionApiOptions)
    assert options.params["model"] == "gpt-4o-mini"
    assert options.headers["Authorization"] == "Bearer sk-test"
