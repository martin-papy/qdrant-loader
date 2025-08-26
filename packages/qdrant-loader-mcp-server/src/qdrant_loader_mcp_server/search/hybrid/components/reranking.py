from __future__ import annotations

from typing import Any


class HybridReranker:
    """Placeholder reranker for hybrid results.

    Current implementation is identity to keep behavior unchanged.
    """

    def rerank(self, results: list[Any]) -> list[Any]:
        return results
