from __future__ import annotations

from collections.abc import Iterable


class ScoreNormalizer:
    """Basic min-max style normalization with guard rails."""

    def scale(self, values: Iterable[float]) -> list[float]:
        data = list(values)
        if not data:
            return []
        min_v = min(data)
        max_v = max(data)
        if max_v - min_v <= 0:
            return [0.0 for _ in data]
        return [(v - min_v) / (max_v - min_v) for v in data]
