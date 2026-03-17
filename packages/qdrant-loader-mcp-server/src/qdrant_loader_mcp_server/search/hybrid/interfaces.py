"""
Interfaces for the hybrid search pipeline.
"""

from __future__ import annotations

from typing import Protocol

from ..components.search_result_models import HybridSearchResult


class VectorSearcher(Protocol):
    """
    Vector searcher interface for searching for vector results.
    Args:
        Protocol (_type_): _description_
    """

    async def search(
        self, query: str, limit: int, project_ids: list[str] | None
    ) -> list[dict]:
        """
        Search for vector results.
        """
        ...


class KeywordSearcher(Protocol):
    """
    Keyword searcher interface for searching for keyword results.
    Args:
        Protocol (_type_): _description_
    """

    async def search(
        self, query: str, limit: int, project_ids: list[str] | None
    ) -> list[dict]:
        """
        Search for keyword results.
        """
        ...


class ResultCombinerLike(Protocol):
    """
    Result combiner interface for combining search results.
    """

    async def combine_results(
        self,
        vector_results: list[dict],
        keyword_results: list[dict],
        query_context: dict,
        limit: int,
        source_types: list[str] | None,
        project_ids: list[str] | None,
    ) -> list[HybridSearchResult]:
        """
        Combine the search results.
        """
        ...


class Reranker(Protocol):
    """
    Reranker interface for reranking search results.
    """

    def rerank(
        self, query: str, results: list[HybridSearchResult]
    ) -> list[HybridSearchResult]:
        """
        Rerank the search results.
        """
        ...
