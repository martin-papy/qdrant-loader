from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any


class ResultBooster:
    """Apply simple multiplicative boosts using a provided function.

    The booster accepts a callable that returns a multiplier for a given result.
    Default behavior is neutral (multiplier=1.0).
    """

    def __init__(self, boost_fn: callable | None = None):
        self.boost_fn = boost_fn or (lambda _r: 1.0)

    def apply(self, results: Iterable[Any]) -> list[Any]:
        """Apply boost multipliers to result scores in-place.

        - Mutates: updates each item's `score` attribute in-place when present and numeric.
        - Errors: invalid multipliers or score operations are logged and skipped.
        """
        logger = logging.getLogger(__name__)
        boosted: list[Any] = []
        for r in results:
            try:
                multiplier = float(self.boost_fn(r))
            except (TypeError, ValueError) as exc:
                logger.warning("ResultBooster: invalid multiplier for %r: %s", r, exc)
                multiplier = 1.0

            if hasattr(r, "score") and isinstance(r.score, int | float):
                try:
                    r.score = float(r.score) * multiplier
                except (TypeError, ValueError) as exc:
                    logger.warning(
                        "ResultBooster: failed to apply boost for %r: %s", r, exc
                    )
            boosted.append(r)
        return boosted
