from __future__ import annotations

from typing import Any, Iterable, List


class ResultBooster:
    """Apply simple multiplicative boosts using a provided function.

    The booster accepts a callable that returns a multiplier for a given result.
    Default behavior is neutral (multiplier=1.0).
    """

    def __init__(self, boost_fn: callable | None = None):
        self.boost_fn = boost_fn or (lambda _r: 1.0)

    def apply(self, results: Iterable[Any]) -> List[Any]:
        # This scaffold assumes results have a 'score' attribute. If not present,
        # items are returned unchanged.
        boosted: List[Any] = []
        for r in results:
            multiplier = float(self.boost_fn(r))
            if hasattr(r, "score") and isinstance(getattr(r, "score"), (int, float)):
                try:
                    r.score = float(r.score) * multiplier
                except Exception:
                    pass
            boosted.append(r)
        return boosted


