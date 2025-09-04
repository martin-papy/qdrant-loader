from __future__ import annotations

from ....components.search_result_models import HybridSearchResult
from ..interfaces import Ranker


class DefaultRanker(Ranker):
    def rank(self, results: list[HybridSearchResult]) -> list[HybridSearchResult]:  # type: ignore[override]
        # Keep default behavior as identity to preserve legacy ordering for now
        return results
