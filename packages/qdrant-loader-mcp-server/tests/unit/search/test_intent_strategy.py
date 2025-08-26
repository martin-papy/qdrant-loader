"""Unit tests for AdaptiveSearchStrategy."""

from unittest.mock import Mock

from qdrant_loader_mcp_server.search.enhanced.intent.models import (
    AdaptiveSearchConfig,
    IntentType,
    SearchIntent,
)
from qdrant_loader_mcp_server.search.enhanced.intent.strategy import (
    AdaptiveSearchStrategy,
)


class TestAdaptiveSearchStrategy:
    """Test the extracted AdaptiveSearchStrategy class."""

    def test_strategy_imports_correctly(self):
        """Test that AdaptiveSearchStrategy can be imported from the strategy module."""
        assert AdaptiveSearchStrategy is not None
        assert AdaptiveSearchStrategy.__name__ == "AdaptiveSearchStrategy"

    def test_strategy_initialization(self):
        """Test that AdaptiveSearchStrategy initializes correctly."""
        strategy = AdaptiveSearchStrategy()

        assert strategy is not None
        assert hasattr(strategy, "intent_configs")
        assert hasattr(strategy, "knowledge_graph")
        assert strategy.knowledge_graph is None

    def test_strategy_with_knowledge_graph(self):
        """Test strategy initialization with knowledge graph."""
        mock_kg = Mock()
        strategy = AdaptiveSearchStrategy(knowledge_graph=mock_kg)

        assert strategy.knowledge_graph == mock_kg

    def test_intent_configs_exist(self):
        """Test that strategy has configurations for all intent types."""
        strategy = AdaptiveSearchStrategy()

        expected_intents = [
            IntentType.TECHNICAL_LOOKUP,
            IntentType.BUSINESS_CONTEXT,
            IntentType.VENDOR_EVALUATION,
            IntentType.PROCEDURAL,
            IntentType.INFORMATIONAL,
            IntentType.TROUBLESHOOTING,
            IntentType.EXPLORATORY,
            IntentType.GENERAL,
        ]

        for intent_type in expected_intents:
            assert intent_type in strategy.intent_configs
            config = strategy.intent_configs[intent_type]
            assert isinstance(config, AdaptiveSearchConfig)

    def test_adapt_search_method(self):
        """Test the adapt_search method."""
        strategy = AdaptiveSearchStrategy()

        # Create a mock SearchIntent
        search_intent = SearchIntent(
            intent_type=IntentType.TECHNICAL_LOOKUP,
            confidence=0.85,
            query_complexity=0.6,
            is_question=True,
            is_technical=True,
        )

        query = "How to use the API?"
        config = strategy.adapt_search(search_intent, query)

        assert isinstance(config, AdaptiveSearchConfig)
        assert config.search_strategy in ["hybrid", "vector", "keyword"]
        assert 0.0 <= config.vector_weight <= 1.0
        assert 0.0 <= config.keyword_weight <= 1.0

    def test_technical_lookup_config(self):
        """Test configuration for technical lookup intent."""
        strategy = AdaptiveSearchStrategy()

        search_intent = SearchIntent(
            intent_type=IntentType.TECHNICAL_LOOKUP, confidence=0.8
        )

        config = strategy.adapt_search(search_intent, "API documentation")

        # Technical lookup should favor vector search
        assert config.vector_weight > config.keyword_weight
        assert config.use_knowledge_graph is True
        assert config.semantic_expansion is True
        assert config.authority_bias > 0

    def test_business_context_config(self):
        """Test configuration for business context intent."""
        strategy = AdaptiveSearchStrategy()

        search_intent = SearchIntent(
            intent_type=IntentType.BUSINESS_CONTEXT, confidence=0.7
        )

        config = strategy.adapt_search(search_intent, "business requirements")

        # Business context should be balanced
        assert config.search_strategy == "hybrid"
        assert config.use_knowledge_graph is True
        assert config.authority_bias > 0

    def test_troubleshooting_config(self):
        """Test configuration for troubleshooting intent."""
        strategy = AdaptiveSearchStrategy()

        search_intent = SearchIntent(
            intent_type=IntentType.TROUBLESHOOTING, confidence=0.9
        )

        config = strategy.adapt_search(search_intent, "error fixing")

        # Troubleshooting should not expand queries
        assert config.expand_query is False
        # Note: semantic_expansion may be True for short queries due to query adaptation
        assert config.entity_expansion is False
        assert config.temporal_bias > 0  # Prefer recent solutions

    def test_exploratory_config(self):
        """Test configuration for exploratory intent."""
        strategy = AdaptiveSearchStrategy()

        search_intent = SearchIntent(intent_type=IntentType.EXPLORATORY, confidence=0.6)

        config = strategy.adapt_search(search_intent, "explore options")

        # Exploratory should favor diversity
        assert config.search_strategy == "vector"
        assert config.diversity_factor > 0.5
        assert config.expansion_aggressiveness > 0.5
        assert config.max_results >= 30

    def test_confidence_adjustments(self):
        """Test that confidence affects configuration adjustments."""
        strategy = AdaptiveSearchStrategy()

        # Low confidence search intent
        low_confidence_intent = SearchIntent(
            intent_type=IntentType.INFORMATIONAL, confidence=0.3
        )

        low_config = strategy.adapt_search(low_confidence_intent, "test query")

        # High confidence search intent
        high_confidence_intent = SearchIntent(
            intent_type=IntentType.INFORMATIONAL, confidence=0.9
        )

        high_config = strategy.adapt_search(high_confidence_intent, "test query")

        # Low confidence should have higher diversity, lower precision
        assert low_config.diversity_factor >= high_config.diversity_factor
        assert low_config.min_score_threshold <= high_config.min_score_threshold

    def test_secondary_intent_blending(self):
        """Test blending of secondary intents."""
        strategy = AdaptiveSearchStrategy()

        search_intent = SearchIntent(
            intent_type=IntentType.TECHNICAL_LOOKUP,
            confidence=0.8,
            secondary_intents=[(IntentType.PROCEDURAL, 0.4)],
        )

        config = strategy.adapt_search(search_intent, "test query")

        # Configuration should be influenced by secondary intent
        assert isinstance(config, AdaptiveSearchConfig)
        # The exact blending is complex, but config should be valid
        assert 0.0 <= config.vector_weight <= 1.0

    def test_query_length_adaptations(self):
        """Test adaptations based on query length."""
        strategy = AdaptiveSearchStrategy()

        search_intent = SearchIntent(
            intent_type=IntentType.INFORMATIONAL, confidence=0.7
        )

        # Short query
        short_config = strategy.adapt_search(search_intent, "API")

        # Long query
        long_query = (
            "How do I configure the API endpoints for authentication with OAuth2"
        )
        long_config = strategy.adapt_search(search_intent, long_query)

        # Short queries should have more expansion
        assert (
            short_config.expansion_aggressiveness
            >= long_config.expansion_aggressiveness
        )

    def test_strategy_stats(self):
        """Test getting strategy statistics."""
        strategy = AdaptiveSearchStrategy()

        stats = strategy.get_strategy_stats()

        assert isinstance(stats, dict)
        assert "intent_types_supported" in stats
        assert "has_knowledge_graph" in stats
        assert "strategy_types" in stats
        assert stats["intent_types_supported"] == len(strategy.intent_configs)
        assert stats["has_knowledge_graph"] is False

    def test_error_handling(self):
        """Test that strategy handles errors gracefully."""
        strategy = AdaptiveSearchStrategy()

        # Create an intent that might cause issues
        search_intent = Mock()
        search_intent.intent_type = None  # Invalid intent type
        search_intent.confidence = 0.5
        search_intent.secondary_intents = []
        search_intent.session_context = {}

        # Should return fallback configuration
        config = strategy.adapt_search(search_intent, "test query")

        assert isinstance(config, AdaptiveSearchConfig)
        # Should get the GENERAL intent configuration
        assert config.search_strategy == "hybrid"
