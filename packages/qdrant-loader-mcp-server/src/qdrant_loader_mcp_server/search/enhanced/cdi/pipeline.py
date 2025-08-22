from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ...components.search_result_models import HybridSearchResult
from ...models import SearchResult
from .interfaces import (
    EntityExtractor,
    RelationExtractor,
    GraphBuilder,
    Ranker,
    Clusterer,
    SimilarityComputer,
    Recommender,
    ConflictDetector,
)
from .models import (
    DocumentCluster,
    DocumentSimilarity,
    ComplementaryContent,
    ConflictAnalysis,
    ClusteringStrategy,
)


@dataclass
class CrossDocumentPipeline:
    """Composable pipeline skeleton for CDI.

    This is a non-functional scaffold to define typed extension points.
    """

    entity_extractor: Optional[EntityExtractor] = None
    relation_extractor: Optional[RelationExtractor] = None
    graph_builder: Optional[GraphBuilder] = None
    ranker: Optional[Ranker] = None
    clusterer: Optional[Clusterer] = None
    similarity_computer: Optional[SimilarityComputer] = None
    recommender: Optional[Recommender] = None
    conflict_detector: Optional[ConflictDetector] = None

    # Methods below intentionally do not implement logic yet.
    def compute_similarity(self, a: SearchResult, b: SearchResult) -> DocumentSimilarity:
        if self.similarity_computer is None:
            raise RuntimeError("similarity_computer not configured")
        return self.similarity_computer.compute(a, b)

    def cluster(self, results: list[SearchResult]) -> list[DocumentCluster]:
        if self.clusterer is None:
            raise RuntimeError("clusterer not configured")
        return self.clusterer.cluster(results, strategy=ClusteringStrategy.MIXED_FEATURES)

    def recommend(self, target: SearchResult, pool: list[SearchResult]) -> ComplementaryContent:
        if self.recommender is None:
            raise RuntimeError("recommender not configured")
        return self.recommender.recommend(target, pool)

    async def detect_conflicts(self, results: list[SearchResult]) -> ConflictAnalysis:
        if self.conflict_detector is None:
            raise RuntimeError("conflict_detector not configured")
        return await self.conflict_detector.detect(results)

    def rank(self, results: list[HybridSearchResult]) -> list[HybridSearchResult]:
        if self.ranker is None:
            raise RuntimeError("ranker not configured")
        return self.ranker.rank(results)


