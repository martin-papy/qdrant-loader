"""Unit tests for the performance testing module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_loader_mcp_server.search.enhanced_hybrid_search import SearchMode
from qdrant_loader_mcp_server.utils.performance_testing import (
    BenchmarkConfig,
    BenchmarkResult,
    PerformanceMetrics,
    PerformanceTester,
)


class TestPerformanceMetrics:
    """Test the PerformanceMetrics dataclass."""

    def test_default_values(self):
        """Test that PerformanceMetrics has correct default values."""
        metrics = PerformanceMetrics()
        assert metrics.total_time == 0.0
        assert metrics.queries_per_second == 0.0
        assert metrics.result_count == 0
        assert metrics.error_count == 0
        assert metrics.timeout_count == 0


class TestBenchmarkConfig:
    """Test the BenchmarkConfig dataclass."""

    def test_default_values(self):
        """Test that BenchmarkConfig has correct default values."""
        config = BenchmarkConfig()
        assert config.num_queries == 100
        assert config.concurrent_queries == 10
        assert config.timeout_seconds == 30.0
        assert config.warmup_queries == 10
        assert SearchMode.HYBRID in config.search_modes
        assert config.max_latency_ms == 1000.0
        assert config.min_throughput_qps == 10.0
        assert config.min_cache_hit_rate == 0.3

    def test_custom_values(self):
        """Test that BenchmarkConfig accepts custom values."""
        config = BenchmarkConfig(
            num_queries=50,
            concurrent_queries=5,
            search_modes=[SearchMode.VECTOR_ONLY],
            max_latency_ms=500.0,
        )
        assert config.num_queries == 50
        assert config.concurrent_queries == 5
        assert config.search_modes == [SearchMode.VECTOR_ONLY]
        assert config.max_latency_ms == 500.0


class TestBenchmarkResult:
    """Test the BenchmarkResult dataclass."""

    def test_initialization(self):
        """Test that BenchmarkResult initializes correctly."""
        config = BenchmarkConfig()
        result = BenchmarkResult(config=config)
        assert result.config == config
        assert isinstance(result.metrics, dict)
        assert isinstance(result.summary, dict)
        assert isinstance(result.recommendations, list)
        assert isinstance(result.timestamp, float)


class TestPerformanceTester:
    """Test the PerformanceTester class."""

    def create_mock_search_engine(self):
        """Create a mock search engine for testing."""
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock()
        mock_engine.clear_cache = MagicMock()
        mock_engine.get_cache_stats = MagicMock(return_value={"hit_rate": 0.75})
        return mock_engine

    def test_initialization(self):
        """Test that PerformanceTester initializes correctly."""
        mock_engine = self.create_mock_search_engine()
        tester = PerformanceTester(mock_engine)
        assert tester.search_engine == mock_engine
        assert hasattr(tester, "test_queries")
        assert 5 in tester.test_queries
        assert 15 in tester.test_queries
        assert 50 in tester.test_queries

    @pytest.mark.asyncio
    async def test_warmup(self):
        """Test the warmup functionality."""
        mock_engine = self.create_mock_search_engine()
        mock_engine.search.return_value = [{"id": "test", "content": "test"}]

        tester = PerformanceTester(mock_engine)
        config = BenchmarkConfig(warmup_queries=3)

        await tester._warmup(config)

        # Should have called search for warmup queries
        assert mock_engine.search.call_count == 3

    @pytest.mark.asyncio
    async def test_warmup_with_errors(self):
        """Test warmup handles errors gracefully."""
        mock_engine = self.create_mock_search_engine()
        mock_engine.search.side_effect = Exception("Test error")

        tester = PerformanceTester(mock_engine)
        config = BenchmarkConfig(warmup_queries=2)

        # Should not raise exception
        await tester._warmup(config)
        assert mock_engine.search.call_count == 2

    @pytest.mark.asyncio
    async def test_test_search_mode(self):
        """Test the search mode testing functionality."""
        mock_engine = self.create_mock_search_engine()
        mock_engine.search.return_value = [
            {"id": "1", "content": "result 1"},
            {"id": "2", "content": "result 2"},
        ]

        tester = PerformanceTester(mock_engine)
        config = BenchmarkConfig(
            num_queries=4,  # Small number for testing
            query_lengths=[5, 15],
            result_limits=[5],
        )

        metrics = await tester._test_search_mode(SearchMode.HYBRID, config)

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.queries_per_second > 0
        assert metrics.result_count > 0
        assert metrics.error_count == 0
        assert metrics.timeout_count == 0

    @pytest.mark.asyncio
    async def test_test_search_mode_with_timeout(self):
        """Test search mode testing handles timeouts."""
        mock_engine = self.create_mock_search_engine()

        # Mock a slow search that will timeout
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(1.0)  # Longer than timeout
            return []

        mock_engine.search.side_effect = slow_search

        tester = PerformanceTester(mock_engine)
        config = BenchmarkConfig(
            num_queries=2, query_lengths=[5], timeout_seconds=0.1  # Very short timeout
        )

        metrics = await tester._test_search_mode(SearchMode.HYBRID, config)

        assert metrics.timeout_count > 0

    @pytest.mark.asyncio
    async def test_test_cache_performance(self):
        """Test cache performance testing."""
        mock_engine = self.create_mock_search_engine()
        mock_engine.search.return_value = [{"id": "1", "content": "cached result"}]

        tester = PerformanceTester(mock_engine)
        config = BenchmarkConfig()

        metrics = await tester._test_cache_performance(config)

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_time > 0
        assert metrics.cache_hit_rate == 0.75  # From mock

        # Should have called search twice (cache miss + cache hit)
        assert mock_engine.search.call_count == 2
        # Should have cleared cache once
        mock_engine.clear_cache.assert_called_once()

    def test_generate_summary(self):
        """Test summary generation."""
        mock_engine = self.create_mock_search_engine()
        tester = PerformanceTester(mock_engine)

        # Create mock metrics
        metrics = {
            "hybrid": PerformanceMetrics(
                queries_per_second=15.0, total_time=2.0, error_count=1
            ),
            "vector_only": PerformanceMetrics(
                queries_per_second=20.0, total_time=1.5, error_count=0
            ),
            "cache": PerformanceMetrics(cache_hit_rate=0.8),
        }

        summary = tester._generate_summary(metrics)

        assert summary["best_mode"] == "vector_only"
        assert summary["best_qps"] == 20.0
        assert summary["cache_effectiveness"] == 0.8
        assert summary["error_rate"] > 0  # Should detect the error

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        mock_engine = self.create_mock_search_engine()
        tester = PerformanceTester(mock_engine)

        config = BenchmarkConfig(
            max_latency_ms=100.0,  # Very low threshold
            min_throughput_qps=50.0,  # Very high threshold
            min_cache_hit_rate=0.9,  # Very high threshold
        )

        # Create metrics that will trigger recommendations
        metrics = {
            "hybrid": PerformanceMetrics(
                queries_per_second=5.0, error_count=2  # Low QPS
            ),
            "cache": PerformanceMetrics(cache_hit_rate=0.5),  # Low cache hit rate
        }

        recommendations = tester._generate_recommendations(metrics, config)

        assert len(recommendations) > 0
        # Should recommend improvements for low throughput and cache hit rate
        assert any("throughput" in rec.lower() for rec in recommendations)
        assert any("cache" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_run_benchmark_integration(self):
        """Test the full benchmark run integration."""
        mock_engine = self.create_mock_search_engine()
        mock_engine.search.return_value = [{"id": "1", "content": "test result"}]

        tester = PerformanceTester(mock_engine)
        config = BenchmarkConfig(
            num_queries=4,  # Small for testing
            warmup_queries=1,
            search_modes=[SearchMode.HYBRID],  # Test just one mode
            query_lengths=[15],
        )

        result = await tester.run_benchmark(config)

        assert isinstance(result, BenchmarkResult)
        assert result.config == config
        assert "hybrid" in result.metrics
        assert "cache" in result.metrics
        assert isinstance(result.summary, dict)
        assert isinstance(result.recommendations, list)
        assert result.timestamp > 0
