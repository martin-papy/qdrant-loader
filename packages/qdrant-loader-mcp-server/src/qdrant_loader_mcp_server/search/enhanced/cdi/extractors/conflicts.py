from __future__ import annotations

from ....models import SearchResult
from ..interfaces import ConflictDetector
from ..models import ConflictAnalysis


class DefaultConflictDetector(ConflictDetector):
    """Adapter to legacy ConflictDetector for behavior parity."""

    def __init__(
        self,
        spacy_analyzer,
        qdrant_client=None,
        openai_client=None,
        collection_name: str = "documents",
    ):
        from ...cross_document_intelligence import (
            ConflictDetector as LegacyConflictDetector,  # type: ignore
        )

        self._legacy = LegacyConflictDetector(
            spacy_analyzer=spacy_analyzer,
            qdrant_client=qdrant_client,
            openai_client=openai_client,
            collection_name=collection_name,
        )

    async def detect(self, results: list[SearchResult]) -> ConflictAnalysis:  # type: ignore[override]
        return await self._legacy.detect_conflicts(results)
