from types import SimpleNamespace

import pytest

from qdrant_loader_mcp_server.search.hybrid.components.reranking import HybridReranker


@pytest.mark.unit
def test_hybrid_reranker_identity_behavior():
    reranker = HybridReranker()
    items = [SimpleNamespace(score=0.2), SimpleNamespace(score=0.8)]
    out = reranker.rerank(items)
    # Current implementation is identity
    assert out == items


