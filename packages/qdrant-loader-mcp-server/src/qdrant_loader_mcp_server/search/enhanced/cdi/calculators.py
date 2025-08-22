"""
Document Similarity Calculation for Cross-Document Intelligence.

This module implements comprehensive document similarity calculation using multiple
metrics including entity overlap, topic overlap, metadata similarity, content features,
hierarchical distance, and semantic similarity with spaCy integration.
"""

from __future__ import annotations

import time
import warnings

from ....utils.logging import LoggingConfig
from ...models import SearchResult
from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer
from .models import DocumentSimilarity, RelationshipType, SimilarityMetric
from .extractors.similarity_helpers import (
    get_shared_entities as cdi_get_shared_entities,
    get_shared_topics as cdi_get_shared_topics,
    combine_metric_scores as cdi_combine_metric_scores,
    calculate_semantic_similarity_spacy as cdi_calc_semantic_spacy,
    calculate_metadata_similarity as cdi_calc_metadata_similarity,
    calculate_content_features_similarity as cdi_calc_content_features_similarity,
)
from .utils import hierarchical_distance_from_breadcrumbs

logger = LoggingConfig.get_logger(__name__)


class DocumentSimilarityCalculator:
    """Calculates similarity between documents using multiple metrics."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the similarity calculator."""
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)

    def calculate_similarity(
        self,
        doc1: SearchResult,
        doc2: SearchResult,
        metrics: list[SimilarityMetric] = None,
    ) -> DocumentSimilarity:
        """Calculate comprehensive similarity between two documents."""
        if metrics is None:
            metrics = [
                SimilarityMetric.ENTITY_OVERLAP,
                SimilarityMetric.TOPIC_OVERLAP,
                SimilarityMetric.METADATA_SIMILARITY,
                SimilarityMetric.CONTENT_FEATURES,
            ]

        start_time = time.time()
        metric_scores = {}

        # Calculate individual metric scores
        for metric in metrics:
            if metric == SimilarityMetric.ENTITY_OVERLAP:
                metric_scores[metric] = self._calculate_entity_overlap(doc1, doc2)
            elif metric == SimilarityMetric.TOPIC_OVERLAP:
                metric_scores[metric] = self._calculate_topic_overlap(doc1, doc2)
            elif metric == SimilarityMetric.METADATA_SIMILARITY:
                metric_scores[metric] = self._calculate_metadata_similarity(doc1, doc2)
            elif metric == SimilarityMetric.CONTENT_FEATURES:
                metric_scores[metric] = self._calculate_content_features_similarity(
                    doc1, doc2
                )
            elif metric == SimilarityMetric.HIERARCHICAL_DISTANCE:
                metric_scores[metric] = self._calculate_hierarchical_similarity(
                    doc1, doc2
                )
            elif metric == SimilarityMetric.SEMANTIC_SIMILARITY:
                metric_scores[metric] = self._calculate_semantic_similarity(doc1, doc2)

        # Calculate combined similarity score
        combined_score = self._combine_metric_scores(metric_scores)

        # Extract shared entities and topics
        shared_entities = self._get_shared_entities(doc1, doc2)
        shared_topics = self._get_shared_topics(doc1, doc2)

        # Determine relationship type
        relationship_type = self._determine_relationship_type(doc1, doc2, metric_scores)

        processing_time = (time.time() - start_time) * 1000
        self.logger.debug(
            f"Calculated similarity between documents in {processing_time:.2f}ms"
        )

        return DocumentSimilarity(
            doc1_id=f"{doc1.source_type}:{doc1.source_title}",
            doc2_id=f"{doc2.source_type}:{doc2.source_title}",
            similarity_score=combined_score,
            metric_scores=metric_scores,
            shared_entities=shared_entities,
            shared_topics=shared_topics,
            relationship_type=relationship_type,
        )

    def _calculate_entity_overlap(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> float:
        """Calculate entity overlap between documents."""
        entities1 = self._extract_entity_texts(doc1.entities)
        entities2 = self._extract_entity_texts(doc2.entities)

        if not entities1 and not entities2:
            return 0.0
        if not entities1 or not entities2:
            return 0.0

        # Jaccard similarity
        intersection = len(set(entities1) & set(entities2))
        union = len(set(entities1) | set(entities2))

        return intersection / union if union > 0 else 0.0

    def _calculate_topic_overlap(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate topic overlap between documents."""
        topics1 = self._extract_topic_texts(doc1.topics)
        topics2 = self._extract_topic_texts(doc2.topics)

        if not topics1 and not topics2:
            return 0.0
        if not topics1 or not topics2:
            return 0.0

        # Jaccard similarity with topic weighting
        intersection = len(set(topics1) & set(topics2))
        union = len(set(topics1) | set(topics2))

        return intersection / union if union > 0 else 0.0

    def _calculate_metadata_similarity(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> float:
        """Calculate metadata similarity (delegates to CDI helper)."""
        return cdi_calc_metadata_similarity(doc1, doc2)

    def _calculate_content_features_similarity(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> float:
        """Calculate content features similarity (delegates to CDI helper)."""
        return cdi_calc_content_features_similarity(doc1, doc2)

    def _calculate_hierarchical_similarity(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> float:
        """Calculate hierarchical relationship similarity."""
        # Check for direct parent-child relationship
        if (
            doc1.parent_id
            and doc1.parent_id == f"{doc2.source_type}:{doc2.source_title}"
        ):
            return 1.0
        if (
            doc2.parent_id
            and doc2.parent_id == f"{doc1.source_type}:{doc1.source_title}"
        ):
            return 1.0

        # Check for sibling relationship (same parent)
        if doc1.parent_id and doc2.parent_id and doc1.parent_id == doc2.parent_id:
            return 0.8

        # Breadcrumb-based similarity
        if doc1.breadcrumb_text and doc2.breadcrumb_text:
            return hierarchical_distance_from_breadcrumbs(
                doc1.breadcrumb_text, doc2.breadcrumb_text
            )

        return 0.0

    def _calculate_semantic_similarity(
        self, doc1: SearchResult, doc2: SearchResult
    ) -> float:
        """Calculate semantic similarity using spaCy."""
        try:
            return cdi_calc_semantic_spacy(self.spacy_analyzer, doc1.text, doc2.text)
        except Exception as e:
            self.logger.warning(f"Failed to calculate semantic similarity: {e}")
            return 0.0

    def _combine_metric_scores(
        self, metric_scores: dict[SimilarityMetric, float]
    ) -> float:
        """Combine multiple metric scores into final similarity score (delegates to CDI helper)."""
        return cdi_combine_metric_scores(metric_scores)

    def _get_shared_entities(self, doc1: SearchResult, doc2: SearchResult) -> list[str]:
        """Get shared entities between documents (delegates to CDI helper)."""
        return cdi_get_shared_entities(doc1, doc2)

    def _get_shared_topics(self, doc1: SearchResult, doc2: SearchResult) -> list[str]:
        """Get shared topics between documents (delegates to CDI helper)."""
        return cdi_get_shared_topics(doc1, doc2)

    def _extract_entity_texts(self, entities: list[dict | str]) -> list[str]:
        """Deprecated. Use CDI utils instead: `utils.extract_texts_from_mixed`.

        Replacement: use CDI utils `extract_texts_from_mixed`.
        """
        warnings.warn(
            "DocumentSimilarityCalculator._extract_entity_texts is deprecated; "
            "use CDI utils.extract_texts_from_mixed instead",
            category=DeprecationWarning,
            stacklevel=2,
        )
        from .utils import extract_texts_from_mixed
        return extract_texts_from_mixed(entities)

    def _extract_topic_texts(self, topics: list[dict | str]) -> list[str]:
        """Deprecated. Use CDI utils instead: `utils.extract_texts_from_mixed`.

        Replacement: use CDI utils `extract_texts_from_mixed`.
        """
        warnings.warn(
            "DocumentSimilarityCalculator._extract_topic_texts is deprecated; "
            "use CDI utils.extract_texts_from_mixed instead",
            category=DeprecationWarning,
            stacklevel=2,
        )
        from .utils import extract_texts_from_mixed
        return extract_texts_from_mixed(topics)

    def _determine_relationship_type(
        self,
        doc1: SearchResult,
        doc2: SearchResult,
        metric_scores: dict[SimilarityMetric, float],
    ) -> RelationshipType:
        """Determine the type of relationship between documents."""
        # Check for hierarchical relationship
        if (
            SimilarityMetric.HIERARCHICAL_DISTANCE in metric_scores
            and metric_scores[SimilarityMetric.HIERARCHICAL_DISTANCE] > 0.7
        ):
            return RelationshipType.HIERARCHICAL

        # Check for cross-references
        if doc1.cross_references or doc2.cross_references:
            return RelationshipType.CROSS_REFERENCE

        # Check for project grouping
        if doc1.project_id and doc2.project_id and doc1.project_id == doc2.project_id:
            return RelationshipType.PROJECT_GROUPING

        # Default to semantic similarity
        return RelationshipType.SEMANTIC_SIMILARITY
