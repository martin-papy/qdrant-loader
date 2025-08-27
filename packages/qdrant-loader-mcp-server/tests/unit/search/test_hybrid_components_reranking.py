import pytest
from qdrant_loader_mcp_server.search.hybrid.components.reranking import HybridReranker


@pytest.mark.unit
def test_reranker_identity():
    r = HybridReranker()
    data = [3, 1, 2]
    # Snapshot input to ensure no hidden mutation
    original = list(data)
    out = r.rerank(data)
    assert out == original
    # Optional: the identity implementation should return same reference
    assert out is data
