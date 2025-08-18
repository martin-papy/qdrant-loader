import pytest

from qdrant_loader_mcp_server.search.hybrid.components.normalization import ScoreNormalizer


@pytest.mark.unit
def test_normalizer_basic_scale():
    n = ScoreNormalizer()
    assert n.scale([]) == []
    assert n.scale([1.0, 1.0]) == [0.0, 0.0]
    out = n.scale([0.0, 5.0, 10.0])
    assert out == [0.0, 0.5, 1.0]


