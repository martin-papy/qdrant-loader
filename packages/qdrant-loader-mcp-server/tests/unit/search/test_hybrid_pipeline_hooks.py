from types import SimpleNamespace

import pytest

from qdrant_loader_mcp_server.search.hybrid.pipeline import HybridPipeline


class _Vector:
    async def search(self, query, limit, project_ids):
        return [{"score": 1.0, "text": "a", "metadata": {}, "source_type": "git"}]


class _Keyword:
    async def search(self, query, limit, project_ids):
        return [{"score": 0.5, "text": "b", "metadata": {}, "source_type": "confluence"}]


class _Combiner:
    async def combine_results(self, vector_results, keyword_results, query_context, limit, source_types, project_ids):
        # Return simple objects with a score attribute for hook processing
        return [SimpleNamespace(score=0.5), SimpleNamespace(score=0.25)]


class _Booster:
    def apply(self, results):
        for r in results:
            r.score *= 2
        return results


class _Normalizer:
    def scale(self, values):
        mx = max(values) if values else 1.0
        return [v / mx for v in values]


class _Dedup:
    def __init__(self):
        self._seen = False

    def deduplicate(self, results):
        # Drop the second result to simulate deduplication
        return results[:1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_optional_hooks_applied_in_order():
    pipe = HybridPipeline(
        vector_searcher=_Vector(),
        keyword_searcher=_Keyword(),
        result_combiner=_Combiner(),
        booster=_Booster(),
        normalizer=_Normalizer(),
        deduplicator=_Dedup(),
        reranker=None,
    )

    out = await pipe.run("q", 5, {}, None, None)
    assert len(out) == 1
    assert out[0].score == pytest.approx(1.0)


