from __future__ import annotations

from collections.abc import Awaitable
from typing import Protocol

from ...components.search_result_models import HybridSearchResult
from ...models import SearchResult
from .models import (
    ClusteringStrategy,
    ComplementaryContent,
    ConflictAnalysis,
    DocumentCluster,
    DocumentSimilarity,
)


class EntityExtractor(Protocol):
    def extract(self, result: SearchResult) -> list[str]: ...


class RelationExtractor(Protocol):
    def extract(self, results: list[SearchResult]) -> list[tuple[str, str, str]]: ...


class GraphBuilder(Protocol):
    def build(self, results: list[SearchResult]) -> object: ...


class Ranker(Protocol):
    def rank(self, results: list[HybridSearchResult]) -> list[HybridSearchResult]: ...


class Clusterer(Protocol):
    def cluster(
        self,
        results: list[SearchResult],
        strategy: ClusteringStrategy | None = None,
        max_clusters: int | None = None,
        min_cluster_size: int | None = None,
    ) -> list[DocumentCluster]: ...


class SimilarityComputer(Protocol):
    def compute(self, a: SearchResult, b: SearchResult) -> DocumentSimilarity: ...


class Recommender(Protocol):
    def recommend(
        self, target: SearchResult, pool: list[SearchResult]
    ) -> ComplementaryContent: ...


class ConflictDetector(Protocol):
    def detect(
        self, results: list[SearchResult]
    ) -> ConflictAnalysis | Awaitable[ConflictAnalysis]: ...
