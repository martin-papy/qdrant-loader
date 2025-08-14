from __future__ import annotations

from ....nlp.spacy_analyzer import SpaCyQueryAnalyzer
from ....models import SearchResult
from ..interfaces import SimilarityComputer
from ..models import (
    DocumentSimilarity,
    SimilarityMetric,
    RelationshipType,
)
from .....utils.logging import LoggingConfig
import time


class DefaultSimilarityComputer(SimilarityComputer):
    """Adapter around the legacy similarity logic."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)

    def compute(
        self,
        doc1: SearchResult,
        doc2: SearchResult,
    ) -> DocumentSimilarity:
        # Lightweight re-use: delegate to legacy calculator to avoid behavior change
        from ..legacy_adapters import LegacyDocumentSimilarityCalculator

        calc = LegacyDocumentSimilarityCalculator(self.spacy_analyzer)
        return calc.calculate_similarity(
            doc1,
            doc2,
            metrics=[
                SimilarityMetric.ENTITY_OVERLAP,
                SimilarityMetric.TOPIC_OVERLAP,
                SimilarityMetric.METADATA_SIMILARITY,
                SimilarityMetric.CONTENT_FEATURES,
            ],
        )


