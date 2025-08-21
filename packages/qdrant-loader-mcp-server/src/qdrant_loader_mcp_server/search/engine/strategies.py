"""
Search Strategy Selection.

This module implements intelligent strategy selection for document clustering
and analysis based on document characteristics and content patterns.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import SearchEngine

from ...utils.logging import LoggingConfig
from ..enhanced.cross_document_intelligence import ClusteringStrategy

logger = LoggingConfig.get_logger(__name__)


class StrategySelector:
    """Handles intelligent strategy selection for search operations."""

    def __init__(self, engine: "SearchEngine"):
        """Initialize with search engine reference."""
        self.engine = engine
        self.logger = LoggingConfig.get_logger(__name__)

    def select_optimal_strategy(self, documents: list) -> str:
        """Analyze document characteristics and select optimal clustering strategy."""
        if not documents:
            return "mixed_features"

        # Analyze document characteristics
        analysis = self.analyze_document_characteristics(documents)

        # Strategy scoring system
        strategy_scores = {
            "entity_based": 0,
            "topic_based": 0,
            "project_based": 0,
            "hierarchical": 0,
            "mixed_features": 0,
        }

        # Score based on entity richness
        if analysis["entity_richness"] > 0.7:
            strategy_scores["entity_based"] += 3
            strategy_scores["mixed_features"] += 1
        elif analysis["entity_richness"] > 0.4:
            strategy_scores["entity_based"] += 1
            strategy_scores["mixed_features"] += 2

        # Score based on topic clarity
        if analysis["topic_clarity"] > 0.7:
            strategy_scores["topic_based"] += 3
            strategy_scores["mixed_features"] += 1
        elif analysis["topic_clarity"] > 0.4:
            strategy_scores["topic_based"] += 1
            strategy_scores["mixed_features"] += 2

        # Score based on project distribution
        if analysis["project_distribution"] > 0.6:
            strategy_scores["project_based"] += 3
        elif analysis["project_distribution"] > 0.3:
            strategy_scores["project_based"] += 1
            strategy_scores["mixed_features"] += 1

        # Score based on hierarchical structure
        if analysis["hierarchical_structure"] > 0.6:
            strategy_scores["hierarchical"] += 3
        elif analysis["hierarchical_structure"] > 0.3:
            strategy_scores["hierarchical"] += 1
            strategy_scores["mixed_features"] += 1

        # Score based on source diversity
        if analysis["source_diversity"] > 0.7:
            strategy_scores["mixed_features"] += 2

        # Bonus for mixed_features as a safe default
        strategy_scores["mixed_features"] += 1

        # Select strategy with highest score
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]

        self.logger.info(f"Strategy analysis: {analysis}")
        self.logger.info(f"Strategy scores: {strategy_scores}")
        self.logger.info(f"Selected strategy: {best_strategy}")

        # Validate against ClusteringStrategy enum; fallback to safe default
        try:
            _ = ClusteringStrategy(best_strategy)
        except ValueError as e:
            self.logger.warning(
                f"Unsupported clustering strategy '{best_strategy}', falling back to 'mixed_features'",
                error=str(e),
            )
            best_strategy = "mixed_features"

        return best_strategy

    def analyze_document_characteristics(self, documents: list) -> dict[str, float]:
        """Analyze characteristics of documents to inform strategy selection."""
        if not documents:
            return {
                "entity_richness": 0,
                "topic_clarity": 0,
                "project_distribution": 0,
                "hierarchical_structure": 0,
                "source_diversity": 0,
            }

        # Entity analysis
        entity_counts = []
        for doc in documents:
            entities = getattr(doc, "entities", []) or []
            entity_count = len(entities)
            entity_counts.append(entity_count)

        avg_entities = sum(entity_counts) / len(entity_counts) if entity_counts else 0
        entity_richness = min(
            1.0, avg_entities / 5.0
        )  # Normalize to 0-1, assuming 5+ entities is rich

        # Topic analysis
        topic_counts = []
        for doc in documents:
            topics = getattr(doc, "topics", []) or []
            topic_count = len(topics)
            topic_counts.append(topic_count)

        avg_topics = sum(topic_counts) / len(topic_counts) if topic_counts else 0
        topic_clarity = min(
            1.0, avg_topics / 3.0
        )  # Normalize to 0-1, assuming 3+ topics is clear

        # Project distribution analysis
        project_ids = [getattr(doc, "project_id", None) for doc in documents]
        unique_projects = len({p for p in project_ids if p})
        total_docs = len(documents)

        # High project distribution means documents are well-distributed across projects
        if unique_projects > 1:
            project_distribution = min(1.0, unique_projects / (total_docs * 0.5))
        else:
            project_distribution = 0

        # Hierarchical structure analysis
        breadcrumb_counts = []
        for doc in documents:
            breadcrumb = getattr(doc, "breadcrumb_text", "")
            if breadcrumb:
                depth = len(breadcrumb.split(" > "))
                breadcrumb_counts.append(depth)

        if breadcrumb_counts:
            avg_depth = sum(breadcrumb_counts) / len(breadcrumb_counts)
            hierarchical_structure = min(
                1.0, (avg_depth - 1) / 3.0
            )  # Normalize: depth 1 = 0, depth 4+ = 1
        else:
            hierarchical_structure = 0

        # Source diversity analysis
        source_types = [getattr(doc, "source_type", "") for doc in documents]
        unique_sources = len(set(source_types))
        source_diversity = min(
            1.0, unique_sources / 4.0
        )  # Normalize: 4+ source types = max diversity

        return {
            "entity_richness": entity_richness,
            "topic_clarity": topic_clarity,
            "project_distribution": project_distribution,
            "hierarchical_structure": hierarchical_structure,
            "source_diversity": source_diversity,
        }
