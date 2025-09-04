from types import SimpleNamespace

import pytest
from qdrant_loader_mcp_server.search.hybrid.orchestration import (
    HybridOrchestrator,
    QueryPlanner,
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_preserves_empty_queries():
    # Prepare a dummy pipeline that records inputs
    called = {}

    async def _run(**kwargs):
        called.update(kwargs)
        return ["ok"]

    pipeline = SimpleNamespace(run=_run)
    orch = HybridOrchestrator()

    out = await orch.run_pipeline(
        pipeline,
        query="Q",
        limit=3,
        query_context={"ctx": True},
        vector_query="",
        keyword_query="",
    )

    assert out == ["ok"]
    # Empty strings must be preserved and NOT defaulted to query
    assert called["vector_query"] == ""
    assert called["keyword_query"] == ""
    # Other params still passed through
    assert called["query"] == "Q"
    assert called["limit"] == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_defaults_none_queries():
    # Prepare a dummy pipeline that records inputs
    called = {}

    async def _run(**kwargs):
        called.update(kwargs)
        return ["ok"]

    pipeline = SimpleNamespace(run=_run)
    orch = HybridOrchestrator()

    out = await orch.run_pipeline(
        pipeline,
        query="Q",
        limit=2,
        query_context={},
        vector_query=None,
        keyword_query=None,
    )

    assert out == ["ok"]
    # None should default to the main query value
    assert called["vector_query"] == "Q"
    assert called["keyword_query"] == "Q"
