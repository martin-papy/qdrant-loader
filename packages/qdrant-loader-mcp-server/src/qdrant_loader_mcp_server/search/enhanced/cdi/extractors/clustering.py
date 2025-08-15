from __future__ import annotations

from ..interfaces import Clusterer
from ....models import SearchResult
from ..models import DocumentCluster, ClusteringStrategy


class DefaultClusterer(Clusterer):
    """Adapter to legacy DocumentClusterAnalyzer for behavior parity."""

    def __init__(self, similarity_calculator):
        from ...cross_document_intelligence import (
            DocumentSimilarityCalculator as LegacySimilarityCalculator,  # type: ignore
            DocumentClusterAnalyzer as LegacyClusterAnalyzer,  # type: ignore
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


