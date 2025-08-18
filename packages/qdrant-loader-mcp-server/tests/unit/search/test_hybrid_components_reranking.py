import pytest

from qdrant_loader_mcp_server.search.hybrid.components.reranking import HybridReranker


@pytest.mark.unit
def test_reranker_identity():
    r = HybridReranker()
    data = [3, 1, 2]
    assert r.rerank(data) == data


