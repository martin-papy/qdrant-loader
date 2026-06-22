"""Engine-agnostic file conversion: bytes -> structured document -> typed outcome.

This is the public surface for the rest of qdrant-loader. Callers obtain an engine
via :func:`build_engine` and depend on the :class:`ConversionEngine` Protocol; the
docling implementation and its option builders stay private behind the seam, so the
conversion engine remains swappable.
"""

from __future__ import annotations

from .config import (
    ConversionConfig,
    ConversionProfile,
    ExcelConfig,
    OcrConfig,
    PictureDescriptionConfig,
    TableConfig,
)
from .engine import ConversionEngine, ConversionSource, EngineKind, build_engine
from .outcome import ConversionOutcome, ConversionStatus, ConvertedDocument

__all__ = [
    # config
    "ConversionConfig",
    "ConversionProfile",
    "OcrConfig",
    "TableConfig",
    "ExcelConfig",
    "PictureDescriptionConfig",
    # engine seam
    "ConversionEngine",
    "ConversionSource",
    "EngineKind",
    "build_engine",
    # outcomes
    "ConversionStatus",
    "ConvertedDocument",
    "ConversionOutcome",
]
