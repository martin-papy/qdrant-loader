import pytest
from qdrant_loader_mcp_server.search.hybrid.pipeline import HybridPipeline


class _DummyVector:
    async def search(self, query, limit, project_ids):
        return []


class _DummyKeyword:
    async def search(self, query, limit, project_ids):
        return []


class _DummyCombiner:
    async def combine_results(
        self,
        vector_results,
        keyword_results,
        query_context,
        limit,
        source_types,
        project_ids,
    ):
        return []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_pipeline_runs_empty():
    pipe = HybridPipeline(
        vector_searcher=_DummyVector(),
        keyword_searcher=_DummyKeyword(),
        result_combiner=_DummyCombiner(),
    )
    results = await pipe.run("q", 5, {}, None, None)
    assert results == []
