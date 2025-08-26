from __future__ import annotations

from dataclasses import dataclass

from ...components.search_result_models import HybridSearchResult
from ...models import SearchResult
from .interfaces import (
    Clusterer,
    ConflictDetector,
    EntityExtractor,
    GraphBuilder,
    Ranker,
    Recommender,
    RelationExtractor,
    SimilarityComputer,
)
from .models import (
    ClusteringStrategy,
    ComplementaryContent,
    ConflictAnalysis,
    DocumentCluster,
    DocumentSimilarity,
)


@dataclass
class CrossDocumentPipeline:
    """Composable pipeline skeleton for CDI.

    This is a non-functional scaffold to define typed extension points.
    """

    entity_extractor: EntityExtractor | None = None
    relation_extractor: RelationExtractor | None = None
    graph_builder: GraphBuilder | None = None
    ranker: Ranker | None = None
    clusterer: Clusterer | None = None
    similarity_computer: SimilarityComputer | None = None
    recommender: Recommender | None = None
    conflict_detector: ConflictDetector | None = None

    # Methods below intentionally do not implement logic yet.
    def compute_similarity(
        self, a: SearchResult, b: SearchResult
    ) -> DocumentSimilarity:
        if self.similarity_computer is None:
            raise RuntimeError("similarity_computer not configured")
        return self.similarity_computer.compute(a, b)

    def cluster(self, results: list[SearchResult]) -> list[DocumentCluster]:
        if self.clusterer is None:
            raise RuntimeError("clusterer not configured")
        return self.clusterer.cluster(
            results, strategy=ClusteringStrategy.MIXED_FEATURES
        )

    def recommend(
        self, target: SearchResult, pool: list[SearchResult]
    ) -> ComplementaryContent:
        if self.recommender is None:
            raise RuntimeError("recommender not configured")
        return self.recommender.recommend(target, pool)

    def detect_conflicts(self, results: list[SearchResult]) -> ConflictAnalysis:
        if self.conflict_detector is None:
            raise RuntimeError("conflict_detector not configured")
        # Support both sync and async detector implementations transparently
        detector = self.conflict_detector
        try:
            result = detector.detect(results)
        except TypeError:
            # In case the detector requires awaitable invocation but was called incorrectly
            # defer to a clear runtime error rather than silently failing
            raise
        # If the detector returns an awaitable (legacy async implementation), run it to completion
        try:
            import inspect

            if inspect.isawaitable(result):
                import asyncio

                return asyncio.run(result)  # type: ignore[no-any-return]
        except RuntimeError:
            # If we're already in an event loop, create a new loop to run the task
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(result)  # type: ignore[no-any-return]
            finally:
                loop.close()
        return result  # type: ignore[return-value]

    def rank(self, results: list[HybridSearchResult]) -> list[HybridSearchResult]:
        if self.ranker is None:
            raise RuntimeError("ranker not configured")
        return self.ranker.rank(results)
