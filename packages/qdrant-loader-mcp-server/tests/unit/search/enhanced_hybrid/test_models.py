import pytest

from qdrant_loader_mcp_server.search.enhanced_hybrid.models import (
    EnhancedSearchConfig,
    EnhancedSearchResult,
    FusionStrategy,
    QueryWeights,
    RerankingStrategy,
    SearchMode,
    validate_query_weights,
)
from qdrant_loader_mcp_server.search.models import SearchResult


class TestQueryWeights:
    """Test QueryWeights class functionality."""

    def test_query_weights_initialization(self):
        """Test QueryWeights initialization."""
        weights = QueryWeights()
        assert weights.vector_weight is None
        assert weights.keyword_weight is None
        assert weights.graph_weight is None
        assert not weights.has_weights()

    def test_query_weights_with_values(self):
        """Test QueryWeights with specific values."""
        weights = QueryWeights(vector_weight=0.5, keyword_weight=0.3, graph_weight=0.2)
        assert weights.vector_weight == 0.5
        assert weights.keyword_weight == 0.3
        assert weights.graph_weight == 0.2
        assert weights.has_weights()

    def test_query_weights_validation_success(self):
        """Test successful weight validation."""
        # Valid weights that sum to 1.0
        weights = QueryWeights(vector_weight=0.5, keyword_weight=0.3, graph_weight=0.2)
        assert weights.has_weights()

        # Partial weights should also be valid
        weights = QueryWeights(vector_weight=0.8)
        assert weights.has_weights()

    def test_query_weights_validation_invalid_range(self):
        """Test weight validation with invalid ranges."""
        with pytest.raises(
            ValueError, match="vector_weight must be between 0.0 and 1.0"
        ):
            QueryWeights(vector_weight=1.5)

        with pytest.raises(
            ValueError, match="keyword_weight must be between 0.0 and 1.0"
        ):
            QueryWeights(keyword_weight=-0.1)

        with pytest.raises(
            ValueError, match="graph_weight must be between 0.0 and 1.0"
        ):
            QueryWeights(graph_weight=2.0)

    def test_query_weights_validation_sum_error(self):
        """Test weight validation when sum is not 1.0."""
        with pytest.raises(ValueError, match="All three weights must sum to 1.0"):
            QueryWeights(vector_weight=0.5, keyword_weight=0.5, graph_weight=0.5)

    def test_query_weights_get_effective_weights(self):
        """Test getting effective weights with config fallback."""
        config = EnhancedSearchConfig(
            vector_weight=0.6, keyword_weight=0.3, graph_weight=0.1
        )

        # With no query weights, should use config defaults
        weights = QueryWeights()
        effective = weights.get_effective_weights(config)
        assert effective == (0.6, 0.3, 0.1)

        # With partial query weights, should override only specified
        weights = QueryWeights(vector_weight=0.8)
        effective = weights.get_effective_weights(config)
        assert effective == (0.8, 0.3, 0.1)

        # With all query weights, should use all overrides
        weights = QueryWeights(vector_weight=0.5, keyword_weight=0.4, graph_weight=0.1)
        effective = weights.get_effective_weights(config)
        assert effective == (0.5, 0.4, 0.1)

    def test_query_weights_to_dict(self):
        """Test converting QueryWeights to dictionary."""
        weights = QueryWeights(vector_weight=0.5, keyword_weight=0.3, graph_weight=0.2)
        result = weights.to_dict()
        expected = {
            "vector_weight": 0.5,
            "keyword_weight": 0.3,
            "graph_weight": 0.2,
        }
        assert result == expected


class TestValidateQueryWeights:
    """Test the validate_query_weights function."""

    def test_validate_query_weights_success(self):
        """Test successful query weight validation."""
        weights = validate_query_weights(
            vector_weight=0.5, keyword_weight=0.3, graph_weight=0.2
        )
        assert isinstance(weights, QueryWeights)
        assert weights.vector_weight == 0.5
        assert weights.keyword_weight == 0.3
        assert weights.graph_weight == 0.2

    def test_validate_query_weights_partial(self):
        """Test validation with partial weights."""
        weights = validate_query_weights(vector_weight=0.8)
        assert isinstance(weights, QueryWeights)
        assert weights.vector_weight == 0.8
        assert weights.keyword_weight is None
        assert weights.graph_weight is None

    def test_validate_query_weights_invalid(self):
        """Test validation with invalid weights."""
        with pytest.raises(ValueError):
            validate_query_weights(
                vector_weight=0.5, keyword_weight=0.5, graph_weight=0.5
            )


class TestEnhancedSearchConfig:
    """Test EnhancedSearchConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnhancedSearchConfig()
        assert config.mode == SearchMode.HYBRID
        assert config.fusion_strategy == FusionStrategy.RECIPROCAL_RANK_FUSION
        assert config.vector_weight == 0.5
        assert config.keyword_weight == 0.2
        assert config.graph_weight == 0.3
        assert config.enable_caching is True
        assert config.enable_reranking is True

    def test_custom_config(self):
        """Test configuration with custom values."""
        config = EnhancedSearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            fusion_strategy=FusionStrategy.WEIGHTED_SUM,
            vector_weight=0.8,
            keyword_weight=0.1,
            graph_weight=0.1,
            enable_caching=False,
        )
        assert config.mode == SearchMode.VECTOR_ONLY
        assert config.fusion_strategy == FusionStrategy.WEIGHTED_SUM
        assert config.vector_weight == 0.8
        assert config.keyword_weight == 0.1
        assert config.graph_weight == 0.1
        assert config.enable_caching is False

    def test_config_validation(self):
        """Test configuration validation."""
        config = EnhancedSearchConfig()

        # Test that config can be created successfully
        assert config.vector_weight >= 0.0
        assert config.keyword_weight >= 0.0
        assert config.graph_weight >= 0.0

    def test_config_properties(self):
        """Test configuration properties."""
        config = EnhancedSearchConfig()

        # Test that all required properties exist
        assert hasattr(config, "mode")
        assert hasattr(config, "fusion_strategy")
        assert hasattr(config, "vector_weight")
        assert hasattr(config, "keyword_weight")
        assert hasattr(config, "graph_weight")


class TestEnhancedSearchResult:
    """Test EnhancedSearchResult class."""

    def test_enhanced_search_result_creation(self):
        """Test creating an enhanced search result."""
        result = EnhancedSearchResult(
            id="test-1",
            content="Test content",
            title="Test Title",
            source_type="document",
            combined_score=0.85,
            vector_score=0.8,
            keyword_score=0.7,
            graph_score=0.9,
        )

        assert result.id == "test-1"
        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.source_type == "document"
        assert result.combined_score == 0.85
        assert result.vector_score == 0.8
        assert result.keyword_score == 0.7
        assert result.graph_score == 0.9

    def test_enhanced_search_result_defaults(self):
        """Test enhanced search result with default values."""
        result = EnhancedSearchResult(
            id="test-1",
            content="Test content",
            title="Test Title",
            source_type="document",
            combined_score=0.85,
        )

        assert result.vector_score == 0.0
        assert result.keyword_score == 0.0
        assert result.graph_score == 0.0
        assert result.rerank_score == 0.0
        assert result.metadata == {}
        assert result.entity_ids == []
        assert result.relationship_types == []

    def test_enhanced_search_result_to_search_result(self):
        """Test converting enhanced result to basic search result."""
        enhanced_result = EnhancedSearchResult(
            id="test-1",
            content="Test content",
            title="Test Title",
            source_type="document",
            combined_score=0.85,
            metadata={"project_id": "proj-1"},
        )

        # Test conversion logic using correct SearchResult field names
        search_result = SearchResult(
            text=enhanced_result.content,  # content -> text
            source_title=enhanced_result.title,  # title -> source_title
            source_type=enhanced_result.source_type,
            score=enhanced_result.combined_score,
            project_id=enhanced_result.metadata.get("project_id"),
        )

        assert search_result.text == enhanced_result.content
        assert search_result.score == enhanced_result.combined_score
        assert search_result.project_id == "proj-1"
