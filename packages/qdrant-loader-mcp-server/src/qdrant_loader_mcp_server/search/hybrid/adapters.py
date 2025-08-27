from __future__ import annotations

from ..components.keyword_search_service import KeywordSearchService
from ..components.result_combiner import ResultCombiner
from ..components.vector_search_service import VectorSearchService
from .interfaces import KeywordSearcher, ResultCombinerLike, VectorSearcher


class VectorSearcherAdapter(VectorSearcher):
    def __init__(self, service: VectorSearchService):
        self._service = service

    async def search(self, query: str, limit: int, project_ids: list[str] | None):  # type: ignore[override]
        return await self._service.vector_search(query, limit, project_ids)


class KeywordSearcherAdapter(KeywordSearcher):
    def __init__(self, service: KeywordSearchService):
        self._service = service

    async def search(self, query: str, limit: int, project_ids: list[str] | None):  # type: ignore[override]
        return await self._service.keyword_search(query, limit, project_ids)


class ResultCombinerAdapter(ResultCombinerLike):
    def __init__(self, combiner: ResultCombiner):
        self._combiner = combiner

    async def combine_results(  # type: ignore[override]
        self,
        vector_results: list[dict],
        keyword_results: list[dict],
        query_context: dict,
        limit: int,
        source_types: list[str] | None,
        project_ids: list[str] | None,
    ):
        return await self._combiner.combine_results(
            vector_results,
            keyword_results,
            query_context,
            limit,
            source_types,
            project_ids,
        )
