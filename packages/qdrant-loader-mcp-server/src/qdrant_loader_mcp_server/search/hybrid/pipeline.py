from __future__ import annotations

from dataclasses import dataclass

from .interfaces import VectorSearcher, KeywordSearcher, ResultCombinerLike
from ..components.search_result_models import HybridSearchResult


@dataclass
class HybridPipeline:
    vector_searcher: VectorSearcher
    keyword_searcher: KeywordSearcher
    result_combiner: ResultCombinerLike

    async def run(
        self,
        query: str,
        limit: int,
        query_context: dict,
        source_types: list[str] | None,
        project_ids: list[str] | None,
        *,
        vector_query: str | None = None,
        keyword_query: str | None = None,
    ) -> list[HybridSearchResult]:
        effective_vector_query = vector_query or query
        effective_keyword_query = keyword_query or query
        vector_results = await self.vector_searcher.search(effective_vector_query, limit * 3, project_ids)
        keyword_results = await self.keyword_searcher.search(effective_keyword_query, limit * 3, project_ids)
        return await self.result_combiner.combine_results(
            vector_results, keyword_results, query_context, limit, source_types, project_ids
        )


