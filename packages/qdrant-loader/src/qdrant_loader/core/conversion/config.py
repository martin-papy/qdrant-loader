"""Engine-agnostic conversion configuration.

Frozen dataclasses describing *our* conversion knobs — never docling types. The
option builder in :mod:`.options` is the single place that translates this into
docling objects, which keeps the config swappable and the engine behind a seam.

The defaults below ARE the ``fast`` profile (CPU-only, born-digital corpus,
conversion opt-in per source); each field documents its own rationale inline.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


@dataclass(frozen=True, slots=True)
class OcrConfig:
    """OCR settings. Off in the baseline — the corpus is born-digital."""

    enabled: bool = False
    backend: str = (
        "torch"  # the only rapidocr backend in the slim image (no onnxruntime)
    )
    languages: tuple[str, ...] = ("english",)  # rapidocr supports english | chinese
    full_page: bool = False


@dataclass(frozen=True, slots=True)
class TableConfig:
    """Table-structure recognition settings."""

    enabled: bool = True
    mode: str = "fast"  # FAST on CPU; the "accurate" profile flips this
    cell_matching: bool = True


@dataclass(frozen=True, slots=True)
class PictureDescriptionConfig:
    """API image-captioning. Off by default but fully wired (matches today)."""

    enabled: bool = False
    url: str = "https://api.openai.com/v1/chat/completions"
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    prompt: str = "Describe this image in a few sentences."
    timeout: float = 60.0
    concurrency: int = 1
    scale: float = 2.0  # docling's own picture-description default scale


@dataclass(frozen=True, slots=True)
class ExcelConfig:
    """Excel backend tuning. docling's defaults already handle merged cells."""

    gap_tolerance: int = 0
    singleton_as_text: bool = False
    sheet_names: tuple[str, ...] | None = None


class ConversionProfile(StrEnum):
    """Named bundles of the three cost axes (OCR / table fidelity / captioning).

    Operators choose one profile instead of reasoning about a dozen interacting
    knobs. The string values are what a connector config carries in YAML, so the
    enum doubles as the type-safe parse target for that string.
    """

    FAST = "fast"
    ACCURATE = "accurate"
    SCANNED = "scanned"


@dataclass(frozen=True, slots=True)
class ConversionConfig:
    """The complete, immutable conversion configuration for one engine instance."""

    # ── policy / ops ──
    max_file_size: int = 50 * 1024 * 1024
    document_timeout: float | None = 300.0  # wall-clock; docling default is None
    enabled_formats: tuple[str, ...] = ("pdf", "docx", "pptx", "xlsx", "image", "csv")

    # ── hardware ──
    device: str = "auto"
    num_threads: int = 4
    compile_models: bool = False  # disable torch.compile warm-up cost on CPU
    artifacts_path: str | None = None  # offline model dir; None = fetch-on-first-run

    # ── pdf / image quality ──
    ocr: OcrConfig = field(default_factory=OcrConfig)
    table: TableConfig = field(default_factory=TableConfig)
    code_formula_enrichment: bool = False

    # ── enrichment / office ──
    picture: PictureDescriptionConfig = field(default_factory=PictureDescriptionConfig)
    excel: ExcelConfig = field(default_factory=ExcelConfig)

    @classmethod
    def from_profile(
        cls, profile: ConversionProfile, **overrides: Any
    ) -> ConversionConfig:
        """Build the baseline config for ``profile``, then apply top-level overrides.

        Overrides replace top-level fields only; nested sub-configs (``ocr=...``,
        ``table=...``) are passed as whole frozen objects, not field-by-field.
        """
        baseline = cls._baseline_for(profile)
        return dataclasses.replace(baseline, **overrides) if overrides else baseline

    @classmethod
    def _baseline_for(cls, profile: ConversionProfile) -> ConversionConfig:
        """The unmodified config for each profile. Replaces the old _PROFILES dict."""
        match profile:
            case ConversionProfile.FAST:
                return cls()  # the schema defaults are the fast profile
            case ConversionProfile.ACCURATE:
                return cls(table=TableConfig(mode="accurate"))
            case ConversionProfile.SCANNED:
                return cls(
                    ocr=OcrConfig(enabled=True, full_page=True),
                    table=TableConfig(mode="accurate"),
                    document_timeout=600.0,
                )
        raise ValueError(f"unknown conversion profile: {profile!r}")
