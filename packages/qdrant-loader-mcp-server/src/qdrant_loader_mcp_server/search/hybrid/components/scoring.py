from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class ScoreComponents:
    vector_score: float
    keyword_score: float
    metadata_score: float


class HybridScorer:
    """Compute hybrid scores from component scores using simple weighted sum.

    This is an initial scaffold to enable modularization. The engine continues
    to own the weights; this class only applies them deterministically.
    """

    def __init__(
        self, vector_weight: float, keyword_weight: float, metadata_weight: float
    ):
        self.vector_weight = float(vector_weight)
        self.keyword_weight = float(keyword_weight)
        self.metadata_weight = float(metadata_weight)

    def compute(self, components: ScoreComponents) -> float:
        return (
            components.vector_score * self.vector_weight
            + components.keyword_score * self.keyword_weight
            + components.metadata_score * self.metadata_weight
        )

    def normalize_many(self, scores: Iterable[float]) -> list[float]:
        values = list(scores)
        if not values:
            return []
        max_value = max(values)
        if max_value <= 0:
            return [0.0 for _ in values]
        return [v / max_value for v in values]
