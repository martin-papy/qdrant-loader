from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from openai import AsyncOpenAI
from qdrant_loader_mcp_server.search.enhanced_hybrid.models import (
    EnhancedSearchConfig,
    EnhancedSearchResult,
    RerankingStrategy,
)
from qdrant_loader_mcp_server.search.enhanced_hybrid.reranking_engine import (
    RerankingEngine,
)


class TestRerankingEngine:
    """Test RerankingEngine functionality."""

    @pytest.fixture
    def reranking_config(self):
        """Create a test configuration for reranking engine."""
        return EnhancedSearchConfig(
            enable_reranking=True,
            reranking_strategy=RerankingStrategy.COMBINED,
            cross_encoder_model="openai",
        )

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client for reranking."""
        client = Mock(spec=AsyncOpenAI)
        # Mock for the completions API used in cross-encoder reranking
        client.completions.create = AsyncMock()
        client.completions.create.return_value.choices = [Mock(text="Yes 0.8")]
        # Also keep the chat completions mock for other potential uses
        client.chat.completions.create = AsyncMock()
        client.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content="0.8"))
        ]
        return client

    @pytest.fixture
    def reranking_engine(self, reranking_config, mock_openai_client):
        """Create a RerankingEngine instance."""
        return RerankingEngine(reranking_config, mock_openai_client)

    @pytest.fixture
    def sample_rerank_results(self):
        """Create sample results for reranking tests."""
        return [
            EnhancedSearchResult(
                id="rerank-1",
                content="First result content",
                title="First Result",
                source_type="document",
                combined_score=0.8,
                metadata={"timestamp": "2024-01-01T00:00:00Z"},
            ),
            EnhancedSearchResult(
                id="rerank-2",
                content="Second result content",
                title="Second Result",
                source_type="document",
                combined_score=0.7,
                metadata={"timestamp": "2024-01-02T00:00:00Z"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_rerank_results_combined(
        self, reranking_engine, sample_rerank_results
    ):
        """Test combined reranking strategy."""
        reranked = await reranking_engine.rerank_results(
            "test query", sample_rerank_results
        )

        assert len(reranked) == len(sample_rerank_results)
        assert all(isinstance(r, EnhancedSearchResult) for r in reranked)

    @pytest.mark.asyncio
    async def test_cross_encoder_rerank(
        self, reranking_engine, sample_rerank_results, mock_openai_client
    ):
        """Test cross-encoder reranking."""
        reranking_engine.config.reranking_strategy = RerankingStrategy.CROSS_ENCODER

        reranked = await reranking_engine.rerank_results(
            "test query", sample_rerank_results
        )

        assert len(reranked) == len(sample_rerank_results)
        # Verify OpenAI was called for reranking
        mock_openai_client.completions.create.assert_called()

    def test_diversity_rerank(self, reranking_engine, sample_rerank_results):
        """Test diversity-based reranking."""
        reranking_engine.config.reranking_strategy = RerankingStrategy.DIVERSITY_MMR

        # Create results with similar content for diversity testing
        similar_results = [
            EnhancedSearchResult(
                id=f"sim-{i}",
                content=f"Similar content {i}",
                title=f"Similar Title {i}",
                source_type="document",
                combined_score=0.8 - i * 0.1,
            )
            for i in range(3)
        ]

        reranked = reranking_engine._diversity_rerank("test query", similar_results)

        assert len(reranked) <= len(similar_results)
        assert all(isinstance(r, EnhancedSearchResult) for r in reranked)

    def test_temporal_rerank(self, reranking_engine, sample_rerank_results):
        """Test temporal-based reranking."""
        reranked = reranking_engine._temporal_rerank(sample_rerank_results)

        assert len(reranked) == len(sample_rerank_results)
        assert all(isinstance(r, EnhancedSearchResult) for r in reranked)

    def test_contextual_rerank(self, reranking_engine, sample_rerank_results):
        """Test contextual reranking."""
        user_context = {"user_id": "test_user", "preferences": ["technical"]}

        reranked = reranking_engine._contextual_rerank(
            "test query", sample_rerank_results, user_context
        )

        assert len(reranked) == len(sample_rerank_results)
        assert all(isinstance(r, EnhancedSearchResult) for r in reranked)

    def test_content_similarity_calculation(self, reranking_engine):
        """Test content similarity calculation in reranking engine."""
        result1 = EnhancedSearchResult(
            id="test1",
            content="artificial intelligence machine learning",
            title="AI ML",
            source_type="document",
            combined_score=0.5,
        )

        result2 = EnhancedSearchResult(
            id="test2",
            content="machine learning deep learning",
            title="ML DL",
            source_type="document",
            combined_score=0.5,
        )

        similarity = reranking_engine._calculate_content_similarity(result1, result2)
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0  # Should have some similarity due to "machine learning"

    def test_parse_timestamp(self, reranking_engine):
        """Test timestamp parsing for temporal reranking."""
        # Test valid ISO timestamp
        timestamp = reranking_engine._parse_timestamp("2024-01-01T12:00:00Z")
        assert isinstance(timestamp, datetime)

        # Test invalid timestamp
        timestamp = reranking_engine._parse_timestamp("invalid")
        assert timestamp is None

        # Test None input
        timestamp = reranking_engine._parse_timestamp(None)
        assert timestamp is None


class TestRerankingEngineAdvanced:
    """Advanced tests for RerankingEngine functionality."""

    @pytest.fixture
    def bge_reranking_config(self):
        """Create configuration for BGE reranking."""
        return EnhancedSearchConfig(
            enable_reranking=True,
            reranking_strategy=RerankingStrategy.CROSS_ENCODER,
            cross_encoder_model="bge",
            cross_encoder_threshold=0.6,
            diversity_lambda=0.8,
            temporal_decay_factor=0.2,
        )

    @pytest.fixture
    def openai_reranking_config(self):
        """Create configuration for OpenAI reranking."""
        return EnhancedSearchConfig(
            enable_reranking=True,
            reranking_strategy=RerankingStrategy.CROSS_ENCODER,
            cross_encoder_model="openai",
            cross_encoder_threshold=0.5,
            diversity_lambda=0.7,
            temporal_decay_factor=0.1,
        )

    @pytest.fixture
    def mock_bge_reranker(self):
        """Mock BGE CrossEncoder."""
        # Create a mock instance directly instead of patching the import
        mock_instance = Mock()
        mock_instance.predict.return_value = [0.85, 0.45, 0.25]
        return mock_instance

    @pytest.fixture
    def bge_reranking_engine(self, bge_reranking_config, mock_bge_reranker):
        """Create BGE reranking engine with mocked dependencies."""
        # Mock the BGE import to prevent actual initialization
        with patch(
            "qdrant_loader_mcp_server.search.enhanced_hybrid.reranking_engine.RerankingEngine._initialize_bge_reranker"
        ) as mock_init_bge:
            # Create engine with patched initialization
            engine = RerankingEngine(bge_reranking_config)
            # Manually set the mock reranker
            engine.bge_reranker = mock_bge_reranker
            return engine

    @pytest.fixture
    def openai_reranking_engine(self, openai_reranking_config, mock_openai_client):
        """Create OpenAI reranking engine."""
        return RerankingEngine(openai_reranking_config, mock_openai_client)

    @pytest.fixture
    def rerank_test_results(self):
        """Create test results for reranking."""
        return [
            EnhancedSearchResult(
                id="r1",
                content="Machine learning algorithms for data analysis",
                title="ML Algorithms",
                source_type="document",
                combined_score=0.8,
                metadata={"timestamp": "2024-01-15T10:00:00Z", "category": "technical"},
            ),
            EnhancedSearchResult(
                id="r2",
                content="Introduction to artificial intelligence",
                title="AI Intro",
                source_type="document",
                combined_score=0.7,
                metadata={"timestamp": "2024-01-10T10:00:00Z", "category": "general"},
            ),
            EnhancedSearchResult(
                id="r3",
                content="Deep learning neural networks",
                title="Deep Learning",
                source_type="document",
                combined_score=0.6,
                metadata={"timestamp": "2023-12-01T10:00:00Z", "category": "technical"},
            ),
        ]

    def test_bge_cross_encoder_rerank(
        self, bge_reranking_engine, rerank_test_results, mock_bge_reranker
    ):
        """Test BGE cross-encoder reranking."""
        # Mock BGE predictions
        bge_reranking_engine.bge_reranker.compute_score.return_value = [
            0.85,
            0.45,
            0.25,
        ]

        reranked = bge_reranking_engine._bge_cross_encoder_rerank(
            "machine learning", rerank_test_results
        )

        assert len(reranked) == 1  # Only one above threshold of 0.6
        # Results should be reordered by BGE scores
        assert reranked[0].rerank_score == 0.85

        # Verify BGE predict was called with correct format
        bge_reranking_engine.bge_reranker.compute_score.assert_called_once()
        call_args = bge_reranking_engine.bge_reranker.compute_score.call_args[0][0]
        assert len(call_args) == 3  # Should have 3 query-document pairs

    @pytest.mark.asyncio
    async def test_combined_rerank_with_bge(
        self, bge_reranking_engine, rerank_test_results, mock_bge_reranker
    ):
        """Test combined reranking strategy with BGE."""
        bge_reranking_engine.config.reranking_strategy = RerankingStrategy.COMBINED

        # Mock BGE predictions - all above threshold (0.6) to ensure they pass filtering
        bge_reranking_engine.bge_reranker.compute_score.return_value = [0.9, 0.8, 0.7]

        user_context = {"preferences": ["technical"]}

        reranked = await bge_reranking_engine._combined_rerank(
            "machine learning", rerank_test_results, user_context
        )

        assert len(reranked) == len(rerank_test_results)
        # Should apply multiple reranking strategies including BGE
        assert all(hasattr(r, "rerank_score") for r in reranked)

    def test_bge_predict_input_format(self, bge_reranking_engine, mock_bge_reranker):
        """Test BGE predict input format."""
        results = [
            EnhancedSearchResult(
                id="test1",
                content="Test content 1",
                title="Test 1",
                source_type="document",
                combined_score=0.8,
            ),
            EnhancedSearchResult(
                id="test2",
                content="Test content 2",
                title="Test 2",
                source_type="document",
                combined_score=0.7,
            ),
        ]

        bge_reranking_engine.bge_reranker.compute_score.return_value = [0.9, 0.5]

        bge_reranking_engine._bge_cross_encoder_rerank("test query", results)

        # Verify the input format to BGE predict
        bge_reranking_engine.bge_reranker.compute_score.assert_called_once()
        call_args = bge_reranking_engine.bge_reranker.compute_score.call_args[0][0]

        # Should be list of [query, document] pairs (could be tuples or lists)
        assert len(call_args) == 2
        assert call_args[0][0] == "test query"
        assert call_args[0][1] == "Test content 1"
        assert call_args[1][0] == "test query"
        assert call_args[1][1] == "Test content 2"
