"""Regression locks for the conversion eligibility policy.

FormatPolicy is our single source of truth for "should we convert this?". These
tests guard that we enable exactly the formats we intend (no silent regressions
or accidental opt-ins) and enforce the size cap.
"""

from __future__ import annotations

from docling.datamodel.base_models import InputFormat
from qdrant_loader.core.conversion import ConversionConfig, ConversionProfile
from qdrant_loader.core.conversion.formats import FormatPolicy


def _policy() -> FormatPolicy:
    return FormatPolicy(ConversionConfig.from_profile(ConversionProfile.FAST))


def test_only_enabled_formats_are_allowed():
    allowed = set(_policy().allowed_formats())
    # what we convert today
    for fmt in (
        InputFormat.PDF,
        InputFormat.IMAGE,
        InputFormat.XLSX,
        InputFormat.DOCX,
        InputFormat.PPTX,
        InputFormat.CSV,
    ):
        assert fmt in allowed
    # docling supports these, but they are chunked natively today — enabling them
    # would be a behaviour change, not the baseline.
    assert InputFormat.MD not in allowed
    assert InputFormat.HTML not in allowed


def test_supported_mime_types_are_derived_for_enabled_formats():
    accepted = _policy().supported_mime_types()
    assert "application/pdf" in accepted
    assert accepted, "policy should derive a non-empty mime set from docling"


def test_size_limit_policy_uses_configured_cap():
    policy = _policy()  # 50 MB default
    assert policy.is_within_size_limit(10 * 1024 * 1024) is True
    assert policy.is_within_size_limit(60 * 1024 * 1024) is False
