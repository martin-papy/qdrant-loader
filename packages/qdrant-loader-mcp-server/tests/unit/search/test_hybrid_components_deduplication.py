import types
import pytest

from qdrant_loader_mcp_server.search.hybrid.components.deduplication import ResultDeduplicator


def _mk(id_: str):
    o = types.SimpleNamespace()
    o.id = id_
    return o


@pytest.mark.unit
def test_deduplicator_by_id():
    items = [_mk("a"), _mk("b"), _mk("a"), _mk("c"), _mk("b")]
    d = ResultDeduplicator()
    out = d.deduplicate(items)
    assert [x.id for x in out] == ["a", "b", "c"]


