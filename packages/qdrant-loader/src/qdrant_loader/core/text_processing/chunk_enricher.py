"""Shared chunk NLP enrichment.

The single definition of what semantic metadata a chunk gets, so the markdown and
docling chunking strategies produce identical fields. Owns one ``SemanticAnalyzer``
and turns ``(content, doc_id)`` into the enrichment metadata dict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qdrant_loader.core.text_processing.semantic_analyzer import SemanticAnalyzer
from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = LoggingConfig.get_logger(__name__)


def _empty() -> dict[str, Any]:
    """The always-present enrichment keys with no data — fresh lists each call."""
    return {"entities": [], "topics": [], "key_phrases": []}


class ChunkEnricher:
    """Owns a ``SemanticAnalyzer`` and maps ``(content, doc_id)`` to chunk metadata."""

    def __init__(self, settings: "Settings") -> None:
        chunking = settings.global_config.chunking
        self._enhanced = bool(chunking.enable_enhanced_semantic_analysis)
        self._analyzer: SemanticAnalyzer | None = None
        if chunking.enable_semantic_analysis:
            sa = settings.global_config.semantic_analysis
            self._analyzer = SemanticAnalyzer(
                spacy_model=sa.spacy_model,
                num_topics=sa.num_topics,
                passes=sa.lda_passes,
            )

    @property
    def enabled(self) -> bool:
        return self._analyzer is not None

    def fit_topics(self, contents: list[str]) -> None:
        """Front-load the document-level topic model on a document's chunk contents.

        Training one model over all chunks lets each subsequent :meth:`enrich` call
        infer the chunk's topics against it, instead of training a degenerate
        single-chunk model each time. No-op when semantic analysis is disabled; a
        fit failure is swallowed so chunks simply fall back to per-chunk topics.
        """
        if self._analyzer is None:
            return
        try:
            self._analyzer.fit_topic_model(contents)
        except Exception:
            logger.warning(
                "Topic model fit failed; chunks will fall back to per-chunk topics",
                exc_info=True,
            )

    def enrich(self, content: str, doc_id: str) -> dict[str, Any]:
        if self._analyzer is None:
            return _empty()
        try:
            result = self._analyzer.analyze_text(
                content, doc_id=doc_id, include_enhanced=self._enhanced
            )
        except Exception:
            logger.warning(
                "Chunk semantic enrichment failed; emitting empty enrichment",
                doc_id=doc_id,
                exc_info=True,
            )
            return _empty()
        enriched: dict[str, Any] = {
            "entities": result.entities,
            "topics": result.topics,
            "key_phrases": result.key_phrases,
        }
        if self._enhanced:
            enriched["pos_tags"] = result.pos_tags
            enriched["dependencies"] = result.dependencies
            enriched["document_similarity"] = result.document_similarity
        return enriched

    def shutdown(self) -> None:
        if self._analyzer is not None:
            self._analyzer.shutdown()
            self._analyzer = None
