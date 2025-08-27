from __future__ import annotations

from .....utils.logging import LoggingConfig
from ....models import SearchResult
from ....nlp.spacy_analyzer import SpaCyQueryAnalyzer
from ..interfaces import SimilarityComputer
from ..models import (
    DocumentSimilarity,
    SimilarityMetric,
)


class DefaultSimilarityComputer(SimilarityComputer):
    """Adapter around the legacy similarity logic."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        # Import directly from CDI calculators to avoid cyclic import via
        # cross_document_intelligence re-export module.
        from ..calculators import (
            DocumentSimilarityCalculator as LegacySimilarityCalculator,  # type: ignore[misc]
        )

        self._legacy = LegacySimilarityCalculator(spacy_analyzer)
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)

    def compute(
        self,
        doc1: SearchResult,
        doc2: SearchResult,
    ) -> DocumentSimilarity:
        # Delegate to the embedded legacy calculator to avoid behavior change
        return self._legacy.calculate_similarity(
            doc1,
            doc2,
            metrics=[
                SimilarityMetric.ENTITY_OVERLAP,
                SimilarityMetric.TOPIC_OVERLAP,
                SimilarityMetric.METADATA_SIMILARITY,
                SimilarityMetric.CONTENT_FEATURES,
            ],
        )
