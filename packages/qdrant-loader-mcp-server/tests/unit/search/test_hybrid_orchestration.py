import asyncio
from types import SimpleNamespace

import pytest

from qdrant_loader_mcp_server.search.hybrid.orchestration import (
    QueryPlanner,
    HybridOrchestrator,
)


@pytest.mark.unit
def test_query_planner_prefers_pipeline():
    planner = QueryPlanner()
    plan = planner.make_plan(has_pipeline=True, expanded_query="expanded")
    assert plan.use_pipeline is True
    assert plan.expanded_query == "expanded"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_calls_pipeline_run():
    # Prepare a dummy pipeline with an async run method
    called = {}

    async def _run(**kwargs):
        called.update(kwargs)
        return ["ok"]

    pipeline = SimpleNamespace(run=_run)
    orch = HybridOrchestrator()

    out = await orch.run_pipeline(
        pipeline,
        query="q",
        limit=5,
        query_context={"ctx": True},
        source_types=["git"],
        project_ids=["p1"],
        vector_query="vq",
        keyword_query="kq",
    )

    assert out == ["ok"]
    assert called["query"] == "q"
    assert called["limit"] == 5
    assert called["query_context"] == {"ctx": True}
    assert called["source_types"] == ["git"]
    assert called["project_ids"] == ["p1"]
    assert called["vector_query"] == "vq"
    assert called["keyword_query"] == "kq"


