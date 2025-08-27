from __future__ import annotations

from typing import Protocol

from ..components.search_result_models import HybridSearchResult


class VectorSearcher(Protocol):
    async def search(
        self, query: str, limit: int, project_ids: list[str] | None
    ) -> list[dict]: ...


class KeywordSearcher(Protocol):
    async def search(
        self, query: str, limit: int, project_ids: list[str] | None
    ) -> list[dict]: ...


class ResultCombinerLike(Protocol):
    async def combine_results(
        self,
        vector_results: list[dict],
        keyword_results: list[dict],
        query_context: dict,
        limit: int,
        source_types: list[str] | None,
        project_ids: list[str] | None,
    ) -> list[HybridSearchResult]: ...


class Reranker(Protocol):
    def rerank(self, results: list[HybridSearchResult]) -> list[HybridSearchResult]: ...
