import types
import pytest

from qdrant_loader_mcp_server.search.hybrid.components.boosting import ResultBooster


def _mk(score: float):
    o = types.SimpleNamespace()
    o.score = score
    return o


@pytest.mark.unit
def test_booster_multiplies_score():
    items = [_mk(1.0), _mk(2.0), _mk(3.0)]
    booster = ResultBooster(lambda r: 2.0)
    out = booster.apply(items)
    assert [x.score for x in out] == [2.0, 4.0, 6.0]


