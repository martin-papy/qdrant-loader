from __future__ import annotations

# Thin adapters that reference legacy classes from cross_document_intelligence.
# This allows us to compose new pipeline components without changing behavior.

from ..cross_document_intelligence import DocumentSimilarityCalculator as LegacyDocumentSimilarityCalculator

__all__ = [
    "LegacyDocumentSimilarityCalculator",
]


