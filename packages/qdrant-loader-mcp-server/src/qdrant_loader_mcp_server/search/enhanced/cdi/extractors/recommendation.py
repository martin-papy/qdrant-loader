from __future__ import annotations

from ....components.models import HybridSearchResult
from ..interfaces import Recommender
from ..models import ComplementaryContent


class DefaultRecommender(Recommender):
    """Adapter to legacy ComplementaryContentFinder for behavior parity."""

    def __init__(self, similarity_calculator, knowledge_graph=None):
        from ...cross_document_intelligence import (
            ComplementaryContentFinder as LegacyComplementaryFinder,  # type: ignore
        )

        self._legacy = LegacyComplementaryFinder(similarity_calculator, knowledge_graph)

    def recommend(
        self,
        target: HybridSearchResult,
        pool: list[HybridSearchResult],
    ) -> ComplementaryContent:  # type: ignore[override]
        return self._legacy.find_complementary_content(target, pool)
