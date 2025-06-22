from unittest.mock import Mock

import pytest
from qdrant_loader_mcp_server.search.enhanced_hybrid.fusion_engine import (
    ResultFusionEngine,
)
from qdrant_loader_mcp_server.search.enhanced_hybrid.models import (
    EnhancedSearchConfig,
    EnhancedSearchResult,
    FusionStrategy,
    QueryWeights,
    SearchMode,
)


class TestResultFusionEngine:
    """Test ResultFusionEngine functionality."""

    @pytest.fixture
    def fusion_config(self):
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
    def fusion_engine(self, fusion_config):
        """Create a ResultFusionEngine instance."""
        return ResultFusionEngine(fusion_config)

    @pytest.fixture
    def sample_results(self):
        """Create sample search results for testing."""
        vector_results = [
            EnhancedSearchResult(
                id="vec-1",
                content="Vector result 1",
                title="Vector Title 1",
                source_type="document",
                combined_score=0.9,
                vector_score=0.9,
            ),
            EnhancedSearchResult(
                id="vec-2",
                content="Vector result 2",
                title="Vector Title 2",
                source_type="document",
                combined_score=0.8,
                vector_score=0.8,
            ),
        ]

        keyword_results = [
            EnhancedSearchResult(
                id="key-1",
                content="Keyword result 1",
                title="Keyword Title 1",
                source_type="document",
                combined_score=0.7,
                keyword_score=0.7,
            ),
            EnhancedSearchResult(
                id="key-2",
                content="Keyword result 2",
                title="Keyword Title 2",
                source_type="document",
                combined_score=0.6,
                keyword_score=0.6,
            ),
        ]

        graph_results = [
            EnhancedSearchResult(
                id="graph-1",
                content="Graph result 1",
                title="Graph Title 1",
                source_type="graph",
                combined_score=0.85,
                graph_score=0.85,
            ),
        ]

        return vector_results, keyword_results, graph_results

    def test_fusion_engine_initialization(self, fusion_engine, fusion_config):
        """Test fusion engine initialization."""
        assert fusion_engine.config == fusion_config

    def test_normalize_scores(self, fusion_engine, sample_results):
        """Test score normalization."""
        vector_results, _, _ = sample_results

        normalized = fusion_engine.normalize_scores(vector_results, "vector_score")

        assert len(normalized) == len(vector_results)
        assert all(0.0 <= r.vector_score <= 1.0 for r in normalized)

    def test_weighted_sum_fusion(self, fusion_engine, sample_results):
        """Test weighted sum fusion strategy."""
        vector_results, keyword_results, graph_results = sample_results

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)
        # Results should be sorted by combined score
        assert all(
            fused[i].combined_score >= fused[i + 1].combined_score
            for i in range(len(fused) - 1)
        )

    def test_reciprocal_rank_fusion(self, fusion_engine, sample_results):
        """Test reciprocal rank fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.RECIPROCAL_RANK_FUSION
        vector_results, keyword_results, graph_results = sample_results

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)

    def test_mmr_fusion(self, fusion_engine, sample_results):
        """Test MMR (Maximal Marginal Relevance) fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.MMR
        vector_results, keyword_results, graph_results = sample_results

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)

    def test_graph_enhanced_weighted_fusion(self, fusion_engine, sample_results):
        """Test graph-enhanced weighted fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.GRAPH_ENHANCED_WEIGHTED
        vector_results, keyword_results, graph_results = sample_results

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)

    def test_confidence_adaptive_fusion(self, fusion_engine, sample_results):
        """Test confidence adaptive fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.CONFIDENCE_ADAPTIVE
        vector_results, keyword_results, graph_results = sample_results

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)

    def test_multi_stage_fusion(self, fusion_engine, sample_results):
        """Test multi-stage fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.MULTI_STAGE
        vector_results, keyword_results, graph_results = sample_results

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)

    def test_context_aware_fusion(self, fusion_engine, sample_results):
        """Test context-aware fusion strategy."""
        fusion_engine.config.fusion_strategy = FusionStrategy.CONTEXT_AWARE
        vector_results, keyword_results, graph_results = sample_results

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)

    def test_fusion_with_query_weights(self, fusion_engine, sample_results):
        """Test fusion with custom query weights."""
        vector_results, keyword_results, graph_results = sample_results
        query_weights = QueryWeights(
            vector_weight=0.7, keyword_weight=0.2, graph_weight=0.1
        )

        fused = fusion_engine.fuse_results(
            vector_results, keyword_results, graph_results, query_weights
        )

        assert len(fused) > 0
        assert all(isinstance(r, EnhancedSearchResult) for r in fused)

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
