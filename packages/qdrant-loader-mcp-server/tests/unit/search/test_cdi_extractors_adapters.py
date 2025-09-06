from types import SimpleNamespace

import pytest


def test_default_recommender_adapter_invokes_legacy(monkeypatch):
    from qdrant_loader_mcp_server.search.enhanced.cdi.extractors.recommendation import (
        DefaultRecommender,
    )

    called = {"args": None}

    class FakeLegacy:
        def __init__(self, *a, **kw):
            pass

        def find_complementary_content(self, target, pool):
            called["args"] = (target, pool)
            return SimpleNamespace(items=["ok"])  # minimal shape

    # Patch the legacy class used by the adapter
    monkeypatch.setattr(
        "qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence.ComplementaryContentFinder",
        FakeLegacy,
        raising=True,
    )

    adapter = DefaultRecommender(similarity_calculator=None, knowledge_graph=None)
    target = SimpleNamespace()
    pool = [SimpleNamespace()]
    result = adapter.recommend(target, pool)

    assert called["args"] == (target, pool)
    assert hasattr(result, "items")


@pytest.mark.asyncio
async def test_default_conflict_detector_adapter_invokes_legacy(monkeypatch):
    from qdrant_loader_mcp_server.search.enhanced.cdi.extractors.conflicts import (
        DefaultConflictDetector,
    )

    called = {"args": None}

    class FakeLegacy:
        def __init__(self, *a, **kw):
            pass

        async def detect_conflicts(self, results):
            called["args"] = (results,)
            return SimpleNamespace(conflicts=["c1"])  # minimal shape

    monkeypatch.setattr(
        "qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence.ConflictDetector",
        FakeLegacy,
        raising=True,
    )

    adapter = DefaultConflictDetector(spacy_analyzer=None)

    results = [SimpleNamespace()]
    out = await adapter.detect(results)

    assert called["args"] == (results,)
    assert hasattr(out, "conflicts")


def test_default_graph_builder_builds_network():
    """GraphBuilder should build a citation network using the primary analyzer path."""
    from qdrant_loader_mcp_server.search.enhanced.cdi.extractors.graph import (
        DefaultGraphBuilder,
    )

    builder = DefaultGraphBuilder()
    network = builder.build([])
    # The network object provides nodes and edges collections
    assert hasattr(network, "nodes")
    assert hasattr(network, "edges")
