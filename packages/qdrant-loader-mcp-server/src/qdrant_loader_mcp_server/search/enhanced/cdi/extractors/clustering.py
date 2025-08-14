from __future__ import annotations

from ..interfaces import Clusterer
from ....models import SearchResult
from ..models import DocumentCluster, ClusteringStrategy


class DefaultClusterer(Clusterer):
    """Adapter to legacy DocumentClusterAnalyzer for behavior parity."""

    def __init__(self, similarity_calculator):
        from ..legacy_adapters import LegacyDocumentSimilarityCalculator
        from ...cross_document_intelligence import DocumentClusterAnalyzer as LegacyClusterAnalyzer  # type: ignore

        self._legacy_similarity = LegacyDocumentSimilarityCalculator(similarity_calculator.spacy_analyzer)  # type: ignore[attr-defined]
        self._legacy = LegacyClusterAnalyzer(self._legacy_similarity)

    def cluster(
        self,
        results: list[SearchResult],
        strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
    ) -> list[DocumentCluster]:
        return self._legacy.create_clusters(results, strategy=strategy)


