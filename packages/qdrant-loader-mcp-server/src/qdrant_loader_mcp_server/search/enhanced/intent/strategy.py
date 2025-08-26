"""
Adaptive Search Strategy for Intent-Based Configuration.

This module implements the AdaptiveSearchStrategy that configures search
parameters based on classified intents to optimize search results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....utils.logging import LoggingConfig
from .models import AdaptiveSearchConfig, IntentType, SearchIntent

if TYPE_CHECKING:
    from ...models import SearchResult
    from ..knowledge_graph import DocumentKnowledgeGraph, TraversalStrategy
else:
    # Runtime imports to avoid circular dependencies
    try:
        from ...models import SearchResult
        from ..knowledge_graph import DocumentKnowledgeGraph, TraversalStrategy
    except ImportError:
        DocumentKnowledgeGraph = None
        TraversalStrategy = None
        SearchResult = None

logger = LoggingConfig.get_logger(__name__)


class AdaptiveSearchStrategy:
    """Adaptive search strategy that configures search based on classified intent."""

    def __init__(self, knowledge_graph=None):
        """Initialize the adaptive search strategy."""
        self.knowledge_graph = knowledge_graph
        self.logger = LoggingConfig.get_logger(__name__)

        # Define intent-specific search configurations
        self.intent_configs = {
            IntentType.TECHNICAL_LOOKUP: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.8,  # Higher vector weight for semantic similarity
                keyword_weight=0.2,
                use_knowledge_graph=True,
                kg_traversal_strategy=None,  # Will be set in __post_init__ if available
                max_graph_hops=2,
                kg_expansion_weight=0.3,
                result_filters={"content_type": ["code", "documentation", "technical"]},
                ranking_boosts={"source_type": {"git": 1.4, "confluence": 1.2}},
                source_type_preferences={"git": 1.5, "documentation": 1.3},
                expand_query=True,
                expansion_aggressiveness=0.4,
                semantic_expansion=True,
                entity_expansion=True,
                max_results=25,
                min_score_threshold=0.15,
                authority_bias=0.3,
            ),
            IntentType.BUSINESS_CONTEXT: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.6,  # Balanced approach
                keyword_weight=0.4,
                use_knowledge_graph=True,
                kg_traversal_strategy=None,  # Will be set in __post_init__ if available
                max_graph_hops=3,
                kg_expansion_weight=0.2,
                result_filters={
                    "content_type": ["requirements", "business", "strategy"]
                },
                ranking_boosts={
                    "section_type": {"requirements": 1.5, "objectives": 1.4}
                },
                source_type_preferences={"confluence": 1.4, "documentation": 1.2},
                expand_query=True,
                expansion_aggressiveness=0.3,
                semantic_expansion=True,
                entity_expansion=False,
                max_results=20,
                min_score_threshold=0.1,
                authority_bias=0.4,
            ),
            IntentType.VENDOR_EVALUATION: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.5,  # Equal weight for structured comparison
                keyword_weight=0.5,
                use_knowledge_graph=True,
                kg_traversal_strategy=None,  # Will be set in __post_init__ if available
                max_graph_hops=2,
                kg_expansion_weight=0.25,
                result_filters={
                    "content_type": ["proposal", "evaluation", "comparison"]
                },
                ranking_boosts={"has_money_entities": 1.3, "has_org_entities": 1.2},
                source_type_preferences={"confluence": 1.3, "documentation": 1.1},
                expand_query=True,
                expansion_aggressiveness=0.35,
                semantic_expansion=True,
                entity_expansion=True,
                max_results=15,
                min_score_threshold=0.12,
                diversity_factor=0.3,  # Encourage diverse vendor options
                authority_bias=0.2,
            ),
            IntentType.PROCEDURAL: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.7,  # Higher semantic matching for procedures
                keyword_weight=0.3,
                use_knowledge_graph=True,
                kg_traversal_strategy=None,  # Will be set in __post_init__ if available
                max_graph_hops=2,
                kg_expansion_weight=0.2,
                result_filters={"content_type": ["guide", "tutorial", "procedure"]},
                ranking_boosts={
                    "section_type": {"steps": 1.5, "procedure": 1.4, "guide": 1.3}
                },
                source_type_preferences={"documentation": 1.4, "git": 1.2},
                expand_query=True,
                expansion_aggressiveness=0.25,
                semantic_expansion=True,
                entity_expansion=False,
                max_results=15,
                min_score_threshold=0.15,
                temporal_bias=0.2,  # Prefer recent procedures
            ),
            IntentType.INFORMATIONAL: AdaptiveSearchConfig(
                search_strategy="vector",  # Vector-first for conceptual understanding
                vector_weight=0.9,
                keyword_weight=0.1,
                use_knowledge_graph=True,
                kg_traversal_strategy=None,  # Will be set in __post_init__ if available
                max_graph_hops=3,
                kg_expansion_weight=0.4,  # More expansion for discovery
                result_filters={},
                ranking_boosts={"section_type": {"overview": 1.4, "introduction": 1.3}},
                source_type_preferences={"documentation": 1.3, "confluence": 1.1},
                expand_query=True,
                expansion_aggressiveness=0.5,  # Aggressive expansion for discovery
                semantic_expansion=True,
                entity_expansion=True,
                max_results=30,
                min_score_threshold=0.05,
                diversity_factor=0.4,  # Encourage diverse perspectives
                authority_bias=0.3,
            ),
            IntentType.TROUBLESHOOTING: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.6,
                keyword_weight=0.4,  # Higher keyword weight for specific errors
                use_knowledge_graph=True,
                kg_traversal_strategy=None,  # Will be set in __post_init__ if available
                max_graph_hops=2,
                kg_expansion_weight=0.15,
                result_filters={"content_type": ["troubleshooting", "fix", "solution"]},
                ranking_boosts={
                    "has_problem_indicators": 1.4,
                    "section_type": {"solution": 1.5},
                },
                source_type_preferences={"git": 1.3, "documentation": 1.2},
                expand_query=False,  # Don't expand error-specific queries
                expansion_aggressiveness=0.1,
                semantic_expansion=False,
                entity_expansion=False,
                max_results=10,
                min_score_threshold=0.2,
                temporal_bias=0.3,  # Prefer recent solutions
            ),
            IntentType.EXPLORATORY: AdaptiveSearchConfig(
                search_strategy="vector",  # Vector-first for exploration
                vector_weight=0.85,
                keyword_weight=0.15,
                use_knowledge_graph=True,
                kg_traversal_strategy=None,  # Will be set in __post_init__ if available
                max_graph_hops=4,  # Deeper exploration
                kg_expansion_weight=0.5,  # Maximum expansion
                result_filters={},
                ranking_boosts={},
                source_type_preferences={},
                expand_query=True,
                expansion_aggressiveness=0.6,  # Very aggressive expansion
                semantic_expansion=True,
                entity_expansion=True,
                max_results=40,  # More results for exploration
                min_score_threshold=0.03,  # Lower threshold
                diversity_factor=0.6,  # Maximum diversity
                authority_bias=0.1,
            ),
            # Fallback configuration
            IntentType.GENERAL: AdaptiveSearchConfig(
                search_strategy="hybrid",
                vector_weight=0.7,
                keyword_weight=0.3,
                use_knowledge_graph=False,
                expand_query=True,
                expansion_aggressiveness=0.3,
                semantic_expansion=True,
                entity_expansion=True,
                max_results=20,
                min_score_threshold=0.1,
            ),
        }

        # Set TraversalStrategy defaults if available
        self._set_traversal_strategies()

        logger.info(
            "Initialized adaptive search strategy with intent-specific configurations"
        )

    def _set_traversal_strategies(self):
        """Set default TraversalStrategy values if available."""
        if TraversalStrategy is not None:
            # Set specific traversal strategies for each intent type
            traversal_map = {
                IntentType.TECHNICAL_LOOKUP: TraversalStrategy.SEMANTIC,
                IntentType.BUSINESS_CONTEXT: TraversalStrategy.WEIGHTED,
                IntentType.VENDOR_EVALUATION: TraversalStrategy.CENTRALITY,
                IntentType.PROCEDURAL: TraversalStrategy.BREADTH_FIRST,
                IntentType.INFORMATIONAL: TraversalStrategy.SEMANTIC,
                IntentType.TROUBLESHOOTING: TraversalStrategy.WEIGHTED,
                IntentType.EXPLORATORY: TraversalStrategy.BREADTH_FIRST,
            }

            for intent_type, traversal_strategy in traversal_map.items():
                if intent_type in self.intent_configs:
                    self.intent_configs[intent_type].kg_traversal_strategy = (
                        traversal_strategy
                    )

    def adapt_search(
        self,
        search_intent: SearchIntent,
        query: str,
        _base_results=None,
    ) -> AdaptiveSearchConfig:
        """Adapt search configuration based on classified intent."""

        try:
            # Get base configuration for the primary intent
            config = self._get_base_config(search_intent.intent_type)

            # Apply confidence-based adjustments
            config = self._apply_confidence_adjustments(config, search_intent)

            # Apply secondary intent blending
            if search_intent.secondary_intents:
                config = self._blend_secondary_intents(
                    config, search_intent.secondary_intents
                )

            # Apply query-specific adaptations
            config = self._apply_query_adaptations(config, search_intent, query)

            # Apply session context adaptations
            if search_intent.session_context:
                config = self._apply_session_adaptations(
                    config, search_intent.session_context
                )

            logger.debug(
                f"Adapted search configuration for {search_intent.intent_type.value}",
                confidence=search_intent.confidence,
                vector_weight=config.vector_weight,
                use_kg=config.use_knowledge_graph,
                max_results=config.max_results,
            )

            return config

        except Exception as e:
            logger.error(f"Failed to adapt search configuration: {e}")
            return self.intent_configs[IntentType.GENERAL]

    def _get_base_config(self, intent_type: IntentType) -> AdaptiveSearchConfig:
        """Get base configuration for intent type."""
        return self.intent_configs.get(
            intent_type, self.intent_configs[IntentType.GENERAL]
        )

    def _apply_confidence_adjustments(
        self, config: AdaptiveSearchConfig, search_intent: SearchIntent
    ) -> AdaptiveSearchConfig:
        """Apply confidence-based adjustments to the configuration."""

        # Low confidence: reduce aggressiveness, increase diversity
        if search_intent.confidence < 0.5:
            config.expansion_aggressiveness *= 0.7
            config.diversity_factor = min(1.0, config.diversity_factor + 0.2)
            config.min_score_threshold *= 0.8

        # High confidence: increase precision, reduce diversity
        elif search_intent.confidence > 0.8:
            config.expansion_aggressiveness *= 1.3
            config.diversity_factor *= 0.7
            config.min_score_threshold *= 1.2

        return config

    def _blend_secondary_intents(
        self,
        config: AdaptiveSearchConfig,
        secondary_intents: list[tuple[IntentType, float]],
    ) -> AdaptiveSearchConfig:
        """Blend secondary intent configurations with primary."""

        for intent_type, confidence in secondary_intents:
            if confidence > 0.3:  # Only blend significant secondary intents
                secondary_config = self.intent_configs.get(intent_type)
                if secondary_config:
                    blend_factor = confidence * 0.3  # Max 30% blending

                    # Blend key parameters
                    config.vector_weight = (
                        config.vector_weight * (1 - blend_factor)
                        + secondary_config.vector_weight * blend_factor
                    )
                    config.expansion_aggressiveness = (
                        config.expansion_aggressiveness * (1 - blend_factor)
                        + secondary_config.expansion_aggressiveness * blend_factor
                    )
                    # Safely handle potential None values for diversity_factor
                    left = (
                        config.diversity_factor
                        if config.diversity_factor is not None
                        else 0
                    )
                    right_base = (
                        secondary_config.diversity_factor
                        if secondary_config.diversity_factor is not None
                        else 0
                    )
                    right = right_base * blend_factor
                    config.diversity_factor = max(left, right)

        return config

    def _apply_query_adaptations(
        self, config: AdaptiveSearchConfig, search_intent: SearchIntent, query: str
    ) -> AdaptiveSearchConfig:
        """Apply query-specific adaptations."""

        # Short queries: increase expansion
        if len(query.split()) <= 3:
            config.expansion_aggressiveness *= 1.4
            config.semantic_expansion = True

        # Long queries: reduce expansion, increase precision
        elif len(query.split()) >= 8:
            config.expansion_aggressiveness *= 0.7
            config.min_score_threshold *= 1.2

        # Very complex queries: use knowledge graph more aggressively
        if search_intent.query_complexity > 0.7:
            config.use_knowledge_graph = True
            config.kg_expansion_weight *= 1.3
            config.max_graph_hops = min(4, config.max_graph_hops + 1)

        # Question queries: increase semantic weight
        if search_intent.is_question:
            config.vector_weight = min(0.9, config.vector_weight + 0.1)
            config.semantic_expansion = True

        # Technical queries: boost technical sources
        if search_intent.is_technical:
            config.source_type_preferences["git"] = (
                config.source_type_preferences.get("git", 1.0) * 1.2
            )
            config.authority_bias *= 1.2

        return config

    def _apply_session_adaptations(
        self, config: AdaptiveSearchConfig, session_context: dict[str, Any]
    ) -> AdaptiveSearchConfig:
        """Apply session context adaptations."""

        # Time-sensitive sessions: increase temporal bias
        if session_context.get("urgency") == "high":
            config.temporal_bias = min(1.0, config.temporal_bias + 0.3)
            config.max_results = min(15, config.max_results)

        # Learning sessions: increase diversity and expansion
        session_type = session_context.get("session_type", "")
        if session_type == "learning":
            config.diversity_factor = min(1.0, config.diversity_factor + 0.2)
            config.expansion_aggressiveness *= 1.2
            config.max_results = min(30, config.max_results + 5)

        # Focused sessions: increase precision
        elif session_type == "focused":
            config.min_score_threshold *= 1.3
            config.expansion_aggressiveness *= 0.8
            config.max_results = max(10, config.max_results - 5)

        # User experience level
        experience_level = session_context.get("experience_level", "intermediate")
        if experience_level == "beginner":
            config.source_type_preferences["documentation"] = 1.4
            config.ranking_boosts["section_type"] = {
                "introduction": 1.5,
                "overview": 1.4,
            }
        elif experience_level == "expert":
            config.source_type_preferences["git"] = 1.3
            config.ranking_boosts["section_type"] = {
                "implementation": 1.4,
                "advanced": 1.3,
            }

        return config

    def get_strategy_stats(self) -> dict[str, Any]:
        """Get adaptive search strategy statistics."""
        stats = {
            "intent_types_supported": len(self.intent_configs),
            "has_knowledge_graph": self.knowledge_graph is not None,
            "strategy_types": list(
                {config.search_strategy for config in self.intent_configs.values()}
            ),
        }

        # Add traversal strategies if TraversalStrategy is available
        if TraversalStrategy is not None:
            stats["traversal_strategies"] = list(
                {
                    config.kg_traversal_strategy.value
                    for config in self.intent_configs.values()
                    if config.use_knowledge_graph and config.kg_traversal_strategy
                }
            )

        return stats
