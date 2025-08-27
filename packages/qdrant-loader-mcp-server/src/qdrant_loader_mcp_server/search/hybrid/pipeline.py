from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..components.search_result_models import HybridSearchResult
from .components.boosting import ResultBooster
from .components.deduplication import ResultDeduplicator
from .components.normalization import ScoreNormalizer
from .interfaces import KeywordSearcher, Reranker, ResultCombinerLike, VectorSearcher


@dataclass
class HybridPipeline:
    vector_searcher: VectorSearcher
    keyword_searcher: KeywordSearcher
    result_combiner: ResultCombinerLike
    reranker: Reranker | None = None
    booster: ResultBooster | None = None
    normalizer: ScoreNormalizer | None = None
    deduplicator: ResultDeduplicator | None = None

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
        effective_vector_query = vector_query if vector_query is not None else query
        effective_keyword_query = keyword_query if keyword_query is not None else query
        vector_results, keyword_results = await asyncio.gather(
            self.vector_searcher.search(effective_vector_query, limit * 3, project_ids),
            self.keyword_searcher.search(
                effective_keyword_query, limit * 3, project_ids
            ),
        )
        results = await self.result_combiner.combine_results(
            vector_results,
            keyword_results,
            query_context,
            limit,
            source_types,
            project_ids,
        )
        # Optional post-processing hooks (disabled by default; no behavior change)
        if self.booster is not None:
            results = self.booster.apply(results)
        if self.normalizer is not None:
            # Normalize score values in-place using current scores
            normalized = self.normalizer.scale([r.score for r in results])
            if len(normalized) != len(results):
                raise ValueError(
                    f"Normalizer returned {len(normalized)} values for {len(results)} results"
                )
            for r, v in zip(results, normalized, strict=False):
                r.score = v
        if self.deduplicator is not None:
            results = self.deduplicator.deduplicate(results)
        if self.reranker is not None:
            return self.reranker.rerank(results)
        return results
