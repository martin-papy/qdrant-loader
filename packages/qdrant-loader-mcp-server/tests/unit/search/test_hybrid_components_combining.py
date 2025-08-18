import pytest

from qdrant_loader_mcp_server.search.hybrid.components.combining import HybridCombiner


@pytest.mark.unit
def test_combiner_preserves_order():
    combiner = HybridCombiner()
    combined = combiner.combine([1, 2], [3, 4])
    assert combined == [1, 2, 3, 4]


