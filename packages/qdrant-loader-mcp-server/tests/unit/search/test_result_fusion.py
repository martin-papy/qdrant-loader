"""Tests for the result fusion mechanism in enhanced hybrid search."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader_mcp_server.search.enhanced_hybrid.fusion_engine import (
    ResultFusionEngine,
)
from qdrant_loader_mcp_server.search.enhanced_hybrid.models import (
    EnhancedSearchConfig,
    EnhancedSearchResult,
    FusionStrategy,
    SearchMode,
)


@pytest.fixture
def fusion_config():
    """Create a test configuration for fusion engine."""
    return EnhancedSearchConfig(
        mode=SearchMode.HYBRID,
        fusion_strategy=FusionStrategy.WEIGHTED_SUM,
        vector_weight=0.5,
        keyword_weight=0.2,
        graph_weight=0.3,
        final_limit=10,
        min_combined_score=0.001,  # Lower threshold to accommodate RRF scores
    )


@pytest.fixture
def fusion_engine(fusion_config):
    """Create a fusion engine instance."""
    return ResultFusionEngine(fusion_config)


@pytest.fixture
def sample_vector_results():
    """Create sample vector search results."""
    return [
        EnhancedSearchResult(
            id="v1",
            content="Vector result 1 content",
            title="Vector Result 1",
            source_type="document",
            combined_score=0.0,
            vector_score=0.9,
        ),
        EnhancedSearchResult(
            id="v2",
            content="Vector result 2 content",
            title="Vector Result 2",
            source_type="document",
            combined_score=0.0,
            vector_score=0.8,
        ),
    ]


@pytest.fixture
def sample_keyword_results():
    """Create sample keyword search results."""
    return [
        EnhancedSearchResult(
            id="k1",
            content="Keyword result 1 content",
            title="Keyword Result 1",
            source_type="document",
            combined_score=0.0,
            keyword_score=0.7,
        ),
        EnhancedSearchResult(
            id="k2",
            content="Keyword result 2 content",
            title="Keyword Result 2",
            source_type="document",
            combined_score=0.0,
            keyword_score=0.6,
        ),
    ]


@pytest.fixture
def sample_graph_results():
    """Create sample graph search results."""
    return [
        EnhancedSearchResult(
            id="g1",
            content="Graph result 1 content",
            title="Graph Result 1",
            source_type="document",
            combined_score=0.0,
            graph_score=0.8,
            entity_ids=["entity1", "entity2"],
            relationship_types=["RELATED_TO"],
            centrality_score=0.5,
        ),
        EnhancedSearchResult(
            id="g2",
            content="Graph result 2 content",
            title="Graph Result 2",
            source_type="document",
            combined_score=0.0,
            graph_score=0.7,
            entity_ids=["entity3"],
            relationship_types=["CONTAINS"],
            centrality_score=0.3,
        ),
    ]


class TestResultFusionEngine:
    """Test cases for the ResultFusionEngine class."""

    def test_initialization(self, fusion_config):
        """Test fusion engine initialization."""
        engine = ResultFusionEngine(fusion_config)
        assert engine.config == fusion_config
        assert engine.logger is not None

    def test_normalize_scores_empty_list(self, fusion_engine):
        """Test score normalization with empty list."""
        results = fusion_engine.normalize_scores([])
        assert results == []

    def test_normalize_scores_single_result(self, fusion_engine):
        """Test score normalization with single result."""
        result = EnhancedSearchResult(
            id="test",
            content="test content",
            title="Test",
            source_type="document",
            combined_score=0.5,
        )
        results = fusion_engine.normalize_scores([result])
        assert len(results) == 1
        assert results[0].combined_score == 1.0  # Single result gets max score

    def test_normalize_scores_multiple_results(self, fusion_engine):
        """Test score normalization with multiple results."""
        results = [
            EnhancedSearchResult(
                id="test1",
                content="test content 1",
                title="Test 1",
                source_type="document",
                combined_score=0.2,
            ),
            EnhancedSearchResult(
                id="test2",
                content="test content 2",
                title="Test 2",
                source_type="document",
                combined_score=0.8,
            ),
        ]

        normalized = fusion_engine.normalize_scores(results)
        assert len(normalized) == 2
        assert normalized[0].combined_score == 0.0  # Min score becomes 0
        assert normalized[1].combined_score == 1.0  # Max score becomes 1

    def test_apply_score_boosting(self, fusion_engine):
        """Test score boosting based on result characteristics."""
        result = EnhancedSearchResult(
            id="test",
            content="test content",
            title="Test",
            source_type="document",
            combined_score=0.5,
            centrality_score=0.8,
            temporal_relevance=0.6,
            entity_ids=["e1", "e2", "e3"],
            relationship_types=["REL1", "REL2"],
        )

        original_score = result.combined_score
        boosted = fusion_engine.apply_score_boosting([result])

        assert len(boosted) == 1
        assert boosted[0].combined_score > original_score
        assert "boost_factor" in boosted[0].debug_info

    def test_weighted_sum_fusion(
        self,
        fusion_engine,
        sample_vector_results,
        sample_keyword_results,
        sample_graph_results,
    ):
        """Test weighted sum fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.WEIGHTED_SUM

        results = fusion_engine.fuse_results(
            sample_vector_results, sample_keyword_results, sample_graph_results
        )

        assert len(results) > 0
        assert all(result.combined_score > 0 for result in results)
        assert (
            results[0].combined_score >= results[-1].combined_score
        )  # Sorted by score

    def test_reciprocal_rank_fusion(
        self,
        fusion_engine,
        sample_vector_results,
        sample_keyword_results,
        sample_graph_results,
    ):
        """Test reciprocal rank fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.RECIPROCAL_RANK_FUSION

        results = fusion_engine.fuse_results(
            sample_vector_results, sample_keyword_results, sample_graph_results
        )

        assert len(results) > 0
        assert all(result.combined_score > 0 for result in results)
        assert (
            results[0].combined_score >= results[-1].combined_score
        )  # Sorted by score

    def test_mmr_fusion(
        self,
        fusion_engine,
        sample_vector_results,
        sample_keyword_results,
        sample_graph_results,
    ):
        """Test MMR fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.MMR

        results = fusion_engine.fuse_results(
            sample_vector_results, sample_keyword_results, sample_graph_results
        )

        assert len(results) > 0
        assert all(result.combined_score is not None for result in results)

    def test_content_similarity_calculation(self, fusion_engine):
        """Test content similarity calculation between results."""
        result1 = EnhancedSearchResult(
            id="test1",
            content="machine learning algorithms",
            title="ML Algorithms",
            source_type="document",
            combined_score=0.5,
            entity_ids=["ml", "algorithms"],
        )

        result2 = EnhancedSearchResult(
            id="test2",
            content="machine learning models",
            title="ML Models",
            source_type="document",
            combined_score=0.5,
            entity_ids=["ml", "models"],
        )

        similarity = fusion_engine._calculate_content_similarity(result1, result2)
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0  # Should have some similarity due to "machine learning"

    def test_select_optimal_fusion_strategy(self, fusion_engine):
        """Test adaptive fusion strategy selection."""
        query = "test query"
        vector_results = [Mock() for _ in range(10)]
        keyword_results = [Mock() for _ in range(8)]
        graph_results = [Mock() for _ in range(12)]

        # Mock the content for diversity calculation
        for i, result in enumerate(vector_results + keyword_results + graph_results):
            result.content = f"content {i}"

        strategy = fusion_engine.select_optimal_fusion_strategy(
            query, vector_results, keyword_results, graph_results
        )

        assert isinstance(strategy, FusionStrategy)
        assert strategy in [
            FusionStrategy.WEIGHTED_SUM,
            FusionStrategy.RECIPROCAL_RANK_FUSION,
            FusionStrategy.MMR,
            FusionStrategy.GRAPH_ENHANCED_WEIGHTED,
            FusionStrategy.CONFIDENCE_ADAPTIVE,
            FusionStrategy.MULTI_STAGE,
            FusionStrategy.CONTEXT_AWARE,
        ]

    def test_fusion_with_empty_results(self, fusion_engine):
        """Test fusion behavior with empty result lists."""
        results = fusion_engine.fuse_results([], [], [])
        assert results == []

    def test_fusion_with_mixed_empty_results(
        self, fusion_engine, sample_vector_results
    ):
        """Test fusion with some empty result lists."""
        results = fusion_engine.fuse_results(sample_vector_results, [], [])
        assert len(results) > 0
        assert all(result.vector_score > 0 for result in results)

    def test_fusion_debug_info(
        self,
        fusion_engine,
        sample_vector_results,
        sample_keyword_results,
        sample_graph_results,
    ):
        """Test that fusion adds debug information to results."""
        results = fusion_engine.fuse_results(
            sample_vector_results, sample_keyword_results, sample_graph_results
        )

        assert len(results) > 0
        for result in results:
            assert "fusion_strategy" in result.debug_info
            assert "weights" in result.debug_info
            assert "boost_factor" in result.debug_info

    def test_fusion_score_thresholding(self, fusion_engine):
        """Test that fusion respects minimum score thresholds."""
        # Create results with very low scores
        low_score_results = [
            EnhancedSearchResult(
                id="low1",
                content="low score content",
                title="Low Score",
                source_type="document",
                combined_score=0.0,
                vector_score=0.01,  # Very low score
            )
        ]

        fusion_engine.config.min_combined_score = 0.5  # High threshold

        results = fusion_engine.fuse_results(low_score_results, [], [])

        # Results below threshold should be filtered out
        assert len(results) == 0 or all(r.combined_score >= 0.5 for r in results)

    @patch(
        "qdrant_loader_mcp_server.search.enhanced_hybrid.fusion_engine.LoggingConfig"
    )
    def test_fusion_error_handling(self, mock_logging, fusion_config):
        """Test error handling in fusion operations."""
        # Create engine with mocked logger
        mock_logger = Mock()
        mock_logging.get_logger.return_value = mock_logger

        engine = ResultFusionEngine(fusion_config)

        # Test with invalid results (should handle gracefully)
        results = engine.fuse_results([], [], [])
        assert results == []

    def test_advanced_fusion_features_integration(self, fusion_engine):
        """Test comprehensive integration of advanced fusion features."""
        # Create diverse results with different characteristics
        vector_results = [
            EnhancedSearchResult(
                id="v1",
                content="Machine learning algorithms for data analysis",
                title="ML Algorithms",
                source_type="document",
                combined_score=0.0,
                vector_score=0.95,
            ),
            EnhancedSearchResult(
                id="v2",
                content="Deep learning neural networks implementation",
                title="Deep Learning",
                source_type="document",
                combined_score=0.0,
                vector_score=0.88,
            ),
        ]

        keyword_results = [
            EnhancedSearchResult(
                id="k1",
                content="Python programming tutorial for beginners",
                title="Python Tutorial",
                source_type="document",
                combined_score=0.0,
                keyword_score=0.82,
            ),
            EnhancedSearchResult(
                id="k2",
                content="Data science best practices and methodologies",
                title="Data Science Guide",
                source_type="document",
                combined_score=0.0,
                keyword_score=0.75,
            ),
        ]

        graph_results = [
            EnhancedSearchResult(
                id="g1",
                content="Statistical analysis methods and applications",
                title="Statistics Methods",
                source_type="document",
                combined_score=0.0,
                graph_score=0.91,
                entity_ids=["statistics", "analysis", "methods"],
                relationship_types=["RELATED_TO", "USES"],
                centrality_score=0.85,
                temporal_relevance=0.7,
            ),
            EnhancedSearchResult(
                id="g2",
                content="Artificial intelligence research trends",
                title="AI Research",
                source_type="document",
                combined_score=0.0,
                graph_score=0.87,
                entity_ids=["ai", "research", "trends", "technology"],
                relationship_types=["CONTAINS", "DESCRIBES"],
                centrality_score=0.92,
                temporal_relevance=0.8,
            ),
        ]

        # Test adaptive strategy selection
        optimal_strategy = fusion_engine.select_optimal_fusion_strategy(
            "complex machine learning data analysis query",
            vector_results,
            keyword_results,
            graph_results,
        )
        assert optimal_strategy in [
            FusionStrategy.WEIGHTED_SUM,
            FusionStrategy.RECIPROCAL_RANK_FUSION,
            FusionStrategy.MMR,
            FusionStrategy.GRAPH_ENHANCED_WEIGHTED,
            FusionStrategy.CONFIDENCE_ADAPTIVE,
            FusionStrategy.MULTI_STAGE,
            FusionStrategy.CONTEXT_AWARE,
        ]

        # Test MMR fusion for diversity
        fusion_engine.config.fusion_strategy = FusionStrategy.MMR
        mmr_results = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(mmr_results) > 0
        assert all(result.combined_score > 0 for result in mmr_results)

        # Verify MMR promotes diversity (different content)
        for i in range(len(mmr_results) - 1):
            similarity = fusion_engine._calculate_content_similarity(
                mmr_results[i], mmr_results[i + 1]
            )
            # MMR should promote diversity (low similarity between consecutive results)
            assert similarity <= 0.8  # High similarity threshold

        # Test score boosting effects
        boosted_results = fusion_engine.apply_score_boosting(graph_results.copy())
        for i, result in enumerate(boosted_results):
            assert "boost_factor" in result.debug_info
            # Results with higher centrality should get more boost
            if result.centrality_score > 0.8:
                assert result.debug_info["boost_factor"] > 1.0

        # Test comprehensive fusion with all strategies
        strategies_to_test = [
            FusionStrategy.WEIGHTED_SUM,
            FusionStrategy.RECIPROCAL_RANK_FUSION,
            FusionStrategy.MMR,
        ]

        for strategy in strategies_to_test:
            fusion_engine.config.fusion_strategy = strategy
            results = fusion_engine.fuse_results(
                vector_results, keyword_results, graph_results
            )

            assert len(results) > 0
            assert all(result.combined_score > 0 for result in results)
            assert results[0].combined_score >= results[-1].combined_score

            # Verify debug info is populated
            for result in results:
                assert "fusion_strategy" in result.debug_info
                assert result.debug_info["fusion_strategy"] == strategy.value
                assert "weights" in result.debug_info
