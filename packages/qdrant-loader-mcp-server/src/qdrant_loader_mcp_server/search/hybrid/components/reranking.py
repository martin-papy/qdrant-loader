from __future__ import annotations

from typing import Any, List


class HybridReranker:
    """Placeholder reranker for hybrid results.

    Current implementation is identity to keep behavior unchanged.
    """

    def rerank(self, results: List[Any]) -> List[Any]:
        return results


