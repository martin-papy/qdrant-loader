from __future__ import annotations

from ....models import SearchResult
from ..interfaces import Clusterer
from ..models import ClusteringStrategy, DocumentCluster


class DefaultClusterer(Clusterer):
    """Adapter to legacy DocumentClusterAnalyzer for behavior parity."""

    def __init__(self, similarity_calculator):
        """Initialize the clusterer.

        The provided `similarity_calculator` is expected to expose a `spacy_analyzer`
        attribute compatible with the legacy `DocumentSimilarityCalculator`.

        - If `spacy_analyzer` is present, it will be used to construct the legacy
          similarity calculator and analyzer.
        - If absent, a clear ValueError is raised describing the missing attribute
          and expected type, rather than failing with an AttributeError later.
        """
        if not hasattr(similarity_calculator, "spacy_analyzer"):
            raise ValueError(
                "similarity_calculator must provide a 'spacy_analyzer' attribute compatible "
                "with the legacy DocumentSimilarityCalculator."
            )
        # Import from CDI modules directly to avoid cycles via re-export module
        from ..analyzers import (
            DocumentClusterAnalyzer as LegacyClusterAnalyzer,  # type: ignore[misc]
        )
        from ..calculators import (
            DocumentSimilarityCalculator as LegacySimilarityCalculator,  # type: ignore[misc]
        )

        self._legacy_similarity = LegacySimilarityCalculator(similarity_calculator.spacy_analyzer)  # type: ignore[attr-defined]
        self._legacy = LegacyClusterAnalyzer(self._legacy_similarity)

    def cluster(
        self,
        results: list[SearchResult],
        strategy: ClusteringStrategy | None = None,
        max_clusters: int | None = None,
        min_cluster_size: int | None = None,
    ) -> list[DocumentCluster]:
        return self._legacy.create_clusters(
            results,
            strategy=strategy or ClusteringStrategy.MIXED_FEATURES,
            max_clusters=max_clusters or 10,
            min_cluster_size=min_cluster_size or 2,
        )
