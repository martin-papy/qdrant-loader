"""Enhanced tests for temporal query optimizer focusing on edge cases and missed coverage."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from qdrant_loader.core.temporal_indexing.index_types import (
    IndexType,
    TemporalIndex,
    TemporalIndexConfig,
    TemporalIndexStatistics,
    TemporalQueryHint,
)
from qdrant_loader.core.temporal_indexing.query_optimizer import TemporalQueryOptimizer


class TestTemporalQueryOptimizerEnhanced:
    """Enhanced test cases for TemporalQueryOptimizer focusing on missed coverage."""

    @pytest.fixture
    def optimizer(self):
        """Create a temporal query optimizer."""
        return TemporalQueryOptimizer()

    @pytest.fixture
    def mock_index_with_stats(self):
        """Create a mock temporal index with detailed statistics."""
        config = TemporalIndexConfig(
            index_id="stats_index",
            index_name="Stats Index",
            index_type=IndexType.BTREE,
        )
        stats = TemporalIndexStatistics(
            index_id="stats_index", index_name="Stats Index"
        )
        # Set up realistic statistics
        stats.total_entries = 50000
        stats.total_queries = 100
        stats.cache_hits = 75
        stats.cache_misses = 25
        stats.average_query_time_ms = 25.5
        stats.fragmentation_ratio = 0.15

        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = True
        return index

    @pytest.fixture
    def mock_hash_index(self):
        """Create a mock hash index for point queries."""
        config = TemporalIndexConfig(
            index_id="hash_index",
            index_name="Hash Index",
            index_type=IndexType.HASH,
        )
        stats = TemporalIndexStatistics(index_id="hash_index", index_name="Hash Index")
        stats.total_entries = 10000
        stats.total_queries = 50
        stats.cache_hits = 45
        stats.cache_misses = 5
        stats.average_query_time_ms = 5.0
        stats.fragmentation_ratio = 0.05

        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = True
        return index

    @pytest.fixture
    def mock_large_index(self):
        """Create a mock index with large dataset."""
        config = TemporalIndexConfig(
            index_id="large_index",
            index_name="Large Index",
            index_type=IndexType.COMPOSITE,
        )
        stats = TemporalIndexStatistics(
            index_id="large_index", index_name="Large Index"
        )
        stats.total_entries = 500000  # Large dataset
        stats.total_queries = 1000
        stats.cache_hits = 600
        stats.cache_misses = 400
        stats.average_query_time_ms = 150.0  # Slow performance
        stats.fragmentation_ratio = 0.4  # High fragmentation

        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = True
        return index

    def test_score_index_for_query_range_query_btree(
        self, optimizer, mock_index_with_stats
    ):
        """Test scoring for range_query with BTREE index."""
        optimizer.register_index(mock_index_with_stats)

        score = optimizer._score_index_for_query(
            mock_index_with_stats, "range_query", None, None, None
        )

        # Should get base score (10.0) + performance bonuses
        assert score > 10.0
        assert score < 20.0  # Reasonable upper bound

    def test_score_index_for_query_point_query_hash(self, optimizer, mock_hash_index):
        """Test scoring for point_query with HASH index."""
        optimizer.register_index(mock_hash_index)

        score = optimizer._score_index_for_query(
            mock_hash_index, "point_query", None, None, None
        )

        # Should get high base score (10.0) + performance bonuses
        assert score > 15.0  # Hash index should score well for point queries

    def test_score_index_for_query_large_dataset_penalty(
        self, optimizer, mock_large_index
    ):
        """Test scoring penalty for large dataset with poor performance."""
        optimizer.register_index(mock_large_index)

        score = optimizer._score_index_for_query(
            mock_large_index, "entity_timeline", None, None, None
        )

        # Should have reduced score due to poor performance and fragmentation
        assert score >= 0.0  # Score should not go negative
        assert score < 10.0  # Should be penalized

    def test_score_index_for_query_zero_queries(self, optimizer):
        """Test scoring for index with no query history."""
        config = TemporalIndexConfig(
            index_id="new_index",
            index_name="New Index",
            index_type=IndexType.BTREE,
        )
        stats = TemporalIndexStatistics(index_id="new_index", index_name="New Index")
        stats.total_entries = 1000
        stats.total_queries = 0  # No query history
        stats.fragmentation_ratio = 0.0

        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = True

        optimizer.register_index(index)

        score = optimizer._score_index_for_query(index, "range_query", None, None, None)

        # Should get base score + size bonus but no performance bonuses
        assert score > 0.0
        assert score < 15.0

    def test_estimate_query_cost_no_primary_index(self, optimizer):
        """Test cost estimation when primary index is not found."""
        # Create plan with non-existent index
        cost = optimizer._estimate_query_cost(
            "range_query", ["nonexistent_index"], None, None, None
        )

        assert cost == 1000.0  # High cost penalty

    def test_estimate_query_cost_zero_entries(self, optimizer):
        """Test cost estimation for index with zero entries."""
        config = TemporalIndexConfig(
            index_id="empty_index",
            index_name="Empty Index",
            index_type=IndexType.BTREE,
        )
        stats = TemporalIndexStatistics(
            index_id="empty_index", index_name="Empty Index"
        )
        stats.total_entries = 0  # Empty index
        stats.cache_hits = 0
        stats.cache_misses = 0

        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = True

        optimizer.register_index(index)

        cost = optimizer._estimate_query_cost(
            "range_query", ["empty_index"], None, None, None
        )

        assert cost > 0.0
        assert cost < 10.0  # Should be low cost for empty index

    def test_estimate_result_size_point_query_large_index(
        self, optimizer, mock_large_index
    ):
        """Test result size estimation for point query on large index."""
        optimizer.register_index(mock_large_index)

        result_size = optimizer._estimate_result_size(
            "point_query", ["large_index"], None, None, None
        )

        # Point queries should return limited results even for large indexes
        assert result_size <= 10
        assert result_size > 0

    def test_estimate_result_size_entity_timeline_multiple_entities(
        self, optimizer, mock_index_with_stats
    ):
        """Test result size estimation for entity timeline with multiple entities."""
        optimizer.register_index(mock_index_with_stats)

        entity_ids = ["entity1", "entity2", "entity3", "entity4", "entity5"]

        result_size = optimizer._estimate_result_size(
            "entity_timeline", ["stats_index"], None, None, entity_ids
        )

        # Should estimate based on entities and total entries
        assert result_size > 0
        assert result_size <= mock_index_with_stats.statistics.total_entries

    def test_estimate_result_size_default_case(self, optimizer, mock_index_with_stats):
        """Test result size estimation for unknown query type."""
        optimizer.register_index(mock_index_with_stats)

        result_size = optimizer._estimate_result_size(
            "unknown_query_type", ["stats_index"], None, None, None
        )

        # Should return default estimate
        assert result_size == 100  # Default estimate for unknown query type

    def test_estimate_memory_usage_streaming_strategy(self, optimizer):
        """Test memory usage estimation for streaming strategy."""
        memory_usage = optimizer._estimate_memory_usage(1000, "streaming")

        # Streaming should use less memory
        assert memory_usage < 1.0  # Should be less than 1MB for 1000 results
        assert memory_usage > 0.0

    def test_query_plan_with_parallel_execution_hint(
        self, optimizer, mock_index_with_stats, mock_hash_index
    ):
        """Test query plan creation with parallel execution hint."""
        optimizer.register_index(mock_index_with_stats)
        optimizer.register_index(mock_hash_index)

        hints = TemporalQueryHint(parallel_execution=True)

        plan = optimizer.create_query_plan("range_query", hints=hints)

        # Should use parallel strategy if multiple indexes available
        if len(plan.secondary_indexes) > 0:
            assert plan.execution_strategy == "parallel"

    def test_query_plan_with_streaming_hint(self, optimizer, mock_index_with_stats):
        """Test query plan creation with streaming results hint."""
        optimizer.register_index(mock_index_with_stats)

        hints = TemporalQueryHint(streaming_results=True)

        plan = optimizer.create_query_plan("range_query", hints=hints)

        assert plan.execution_strategy == "streaming"

    def test_record_query_performance_history_limit(self, optimizer):
        """Test performance recording with history limit."""
        plan_id = "test_plan"

        # Record more than 100 performance entries
        for i in range(105):
            optimizer.record_query_performance(plan_id, float(i))

        # Should limit to 100 entries
        assert len(optimizer.performance_history[plan_id]) == 100
        # Should keep most recent entries
        assert optimizer.performance_history[plan_id][-1] == 104.0

    def test_get_optimizer_statistics_with_performance_history(
        self, optimizer, mock_index_with_stats
    ):
        """Test optimizer statistics with performance history."""
        optimizer.register_index(mock_index_with_stats)

        # Add some performance history
        optimizer.record_query_performance("plan1", 10.0)
        optimizer.record_query_performance("plan1", 20.0)
        optimizer.record_query_performance("plan2", 30.0)

        stats = optimizer.get_optimizer_statistics()

        assert stats["registered_indexes"] == 1
        assert stats["active_indexes"] == 1
        assert stats["cached_plans"] == 0  # No cached plans yet
        assert stats["performance_history_entries"] == 3  # Three total entries

    def test_query_signature_with_all_parameters(self, optimizer):
        """Test query signature creation with all parameters."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        entity_ids = ["entity1", "entity2"]
        hints = TemporalQueryHint(preferred_indexes=["index1"])

        signature = optimizer._create_query_signature(
            "range_query", start_time, end_time, entity_ids, hints
        )

        assert isinstance(signature, str)
        assert len(signature) == 32  # MD5 hash length

    def test_should_use_index_intersection_entity_timeline(self, optimizer):
        """Test index intersection decision for entity timeline queries."""
        selected_indexes = ["index1", "index2", "index3"]

        should_use = optimizer._should_use_index_intersection(
            selected_indexes, "entity_timeline"
        )

        # Entity timeline queries benefit from index intersection
        assert should_use is True

    def test_should_cache_intermediate_results_boundary_conditions(self, optimizer):
        """Test caching decision at boundary conditions."""
        # Test exactly at threshold (execution_time > 100 AND memory < 50)
        should_cache_valid = optimizer._should_cache_intermediate_results(101.0, 49.0)
        should_not_cache_time = optimizer._should_cache_intermediate_results(
            100.0, 49.0
        )  # time <= 100
        should_not_cache_memory = optimizer._should_cache_intermediate_results(
            101.0, 50.0
        )  # memory >= 50

        # Should cache only if execution_time > 100 AND memory_usage < 50
        assert should_cache_valid is True
        assert should_not_cache_time is False
        assert should_not_cache_memory is False

        # Test below thresholds
        should_not_cache = optimizer._should_cache_intermediate_results(50.0, 50.0)
        assert should_not_cache is False

    def test_create_query_plan_with_complex_hints(
        self, optimizer, mock_index_with_stats, mock_hash_index, mock_large_index
    ):
        """Test query plan creation with complex hint combinations."""
        optimizer.register_index(mock_index_with_stats)
        optimizer.register_index(mock_hash_index)
        optimizer.register_index(mock_large_index)

        # Create hints that avoid one index and prefer another
        hints = TemporalQueryHint(
            preferred_indexes=["hash_index"],
            avoid_indexes=["large_index"],
            parallel_execution=True,
            streaming_results=False,
        )

        plan = optimizer.create_query_plan(
            "point_query",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            entity_ids=["entity1", "entity2"],
            hints=hints,
        )

        # Should prefer hash_index and avoid large_index
        assert plan.primary_index == "hash_index"
        assert "large_index" not in [plan.primary_index] + plan.secondary_indexes

        # Should have realistic estimates
        assert plan.estimated_cost > 0
        assert plan.estimated_rows > 0
        assert plan.estimated_execution_time_ms > 0
        assert plan.estimated_memory_usage_mb >= 0
