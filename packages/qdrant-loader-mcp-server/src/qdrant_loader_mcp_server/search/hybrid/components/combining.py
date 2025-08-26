from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class HybridCombiner:
    """Simple combiner that preserves input order.

    This is intentionally minimal to avoid changing behavior while creating
    seams for future extractions from the engine.
    """

    def combine(
        self, vector_results: Iterable[Any], keyword_results: Iterable[Any]
    ) -> list[Any]:
        combined: list[Any] = []
        combined.extend(list(vector_results))
        combined.extend(list(keyword_results))
        return combined
