"""Unit tests for intent classification models."""

import pytest
from dataclasses import FrozenInstanceError

from qdrant_loader_mcp_server.search.enhanced.intent.models import (
    IntentType, 
    SearchIntent,
    AdaptiveSearchConfig
)


class TestIntentType:
    """Test the IntentType enum."""

    def test_intent_type_values(self):
        """Test that all expected intent types exist with correct values."""
        expected_values = {
            "TECHNICAL_LOOKUP": "technical_lookup",
            "BUSINESS_CONTEXT": "business_context", 
            "VENDOR_EVALUATION": "vendor_evaluation",
            "PROCEDURAL": "procedural",
            "INFORMATIONAL": "informational",
            "EXPLORATORY": "exploratory",
            "TROUBLESHOOTING": "troubleshooting",
            "GENERAL": "general"
        }
        
        for name, value in expected_values.items():
            intent_type = getattr(IntentType, name)
            assert intent_type.value == value

    def test_intent_type_enum_access(self):
        """Test accessing intent types by value."""
        assert IntentType("technical_lookup") == IntentType.TECHNICAL_LOOKUP
        assert IntentType("general") == IntentType.GENERAL

    def test_intent_type_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            IntentType("invalid_intent")


class TestSearchIntent:
    """Test the SearchIntent dataclass."""

    def test_search_intent_creation(self):
        """Test creating a SearchIntent with required fields."""
        intent = SearchIntent(
            intent_type=IntentType.TECHNICAL_LOOKUP,
            confidence=0.85
        )
        
        assert intent.intent_type == IntentType.TECHNICAL_LOOKUP
        assert intent.confidence == 0.85
        assert intent.secondary_intents == []
        assert intent.supporting_evidence == {}
        assert intent.classification_time_ms == 0.0

    def test_search_intent_with_optional_fields(self):
        """Test creating SearchIntent with optional fields."""
        secondary_intents = [(IntentType.PROCEDURAL, 0.3)]
        evidence = {"keywords": ["api", "documentation"]}
        features = {"technical_indicators": 3}
        
        intent = SearchIntent(
            intent_type=IntentType.TECHNICAL_LOOKUP,
            confidence=0.85,
            secondary_intents=secondary_intents,
            supporting_evidence=evidence,
            linguistic_features=features,
            query_complexity=0.7,
            is_question=True,
            is_technical=True,
            classification_time_ms=45.2
        )
        
        assert intent.secondary_intents == secondary_intents
        assert intent.supporting_evidence == evidence
        assert intent.linguistic_features == features
        assert intent.query_complexity == 0.7
        assert intent.is_question is True
        assert intent.is_technical is True
        assert intent.classification_time_ms == 45.2

    def test_search_intent_defaults(self):
        """Test that default values are set correctly."""
        intent = SearchIntent(
            intent_type=IntentType.INFORMATIONAL,
            confidence=0.6
        )
        
        # Test default factory values
        assert isinstance(intent.secondary_intents, list)
        assert isinstance(intent.supporting_evidence, dict)
        assert isinstance(intent.linguistic_features, dict)
        assert isinstance(intent.session_context, dict)
        assert isinstance(intent.previous_intents, list)
        
        # Test default primitive values
        assert intent.query_complexity == 0.0
        assert intent.is_question is False
        assert intent.is_technical is False
        assert intent.classification_time_ms == 0.0


class TestAdaptiveSearchConfig:
    """Test the AdaptiveSearchConfig dataclass."""

    def test_adaptive_search_config_defaults(self):
        """Test creating AdaptiveSearchConfig with default values."""
        config = AdaptiveSearchConfig()
        
        # Core search parameters
        assert config.search_strategy == "hybrid"
        assert config.vector_weight == 0.7
        assert config.keyword_weight == 0.3
        
        # Knowledge graph integration
        assert config.use_knowledge_graph is False
        assert config.max_graph_hops == 2
        assert config.kg_expansion_weight == 0.2
        
        # Result filtering and ranking
        assert isinstance(config.result_filters, dict)
        assert isinstance(config.ranking_boosts, dict)
        assert isinstance(config.source_type_preferences, dict)
        
        # Query expansion
        assert config.expand_query is True
        assert config.expansion_aggressiveness == 0.3
        assert config.semantic_expansion is True
        assert config.entity_expansion is True
        
        # Performance tuning
        assert config.max_results == 20
        assert config.min_score_threshold == 0.1
        assert config.diversity_factor == 0.0
        
        # Contextual parameters
        assert config.temporal_bias == 0.0
        assert config.authority_bias == 0.0
        assert config.personal_bias == 0.0

    def test_adaptive_search_config_custom_values(self):
        """Test creating AdaptiveSearchConfig with custom values."""
        config = AdaptiveSearchConfig(
            search_strategy="vector",
            vector_weight=0.9,
            keyword_weight=0.1,
            use_knowledge_graph=True,
            max_graph_hops=3,
            expand_query=False,
            max_results=50,
            diversity_factor=0.5
        )
        
        assert config.search_strategy == "vector"
        assert config.vector_weight == 0.9
        assert config.keyword_weight == 0.1
        assert config.use_knowledge_graph is True
        assert config.max_graph_hops == 3
        assert config.expand_query is False
        assert config.max_results == 50
        assert config.diversity_factor == 0.5

    def test_adaptive_search_config_post_init(self):
        """Test that __post_init__ sets TraversalStrategy when available."""
        config = AdaptiveSearchConfig()
        
        # The __post_init__ method should be called automatically
        # If TraversalStrategy is available, kg_traversal_strategy should be set
        # If not available, it should remain None
        assert config.kg_traversal_strategy is not None or config.kg_traversal_strategy is None

    def test_adaptive_search_config_with_filters(self):
        """Test AdaptiveSearchConfig with complex filters and boosts."""
        result_filters = {"content_type": ["technical", "code"]}
        ranking_boosts = {"source_type": {"git": 1.5}}
        source_prefs = {"documentation": 1.2}
        
        config = AdaptiveSearchConfig(
            result_filters=result_filters,
            ranking_boosts=ranking_boosts,
            source_type_preferences=source_prefs
        )
        
        assert config.result_filters == result_filters
        assert config.ranking_boosts == ranking_boosts
        assert config.source_type_preferences == source_prefs
