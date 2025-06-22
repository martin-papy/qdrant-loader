"""Tests for temporal query optimizer."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from qdrant_loader.core.temporal_indexing.index_types import (
    IndexType,
    TemporalIndex,
    TemporalIndexConfig,
    TemporalIndexStatistics,
    TemporalQueryHint,
    TemporalQueryPlan,
)
from qdrant_loader.core.temporal_indexing.query_optimizer import TemporalQueryOptimizer


class TestTemporalQueryOptimizer:
    """Test cases for TemporalQueryOptimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create a temporal query optimizer."""
        return TemporalQueryOptimizer()

    @pytest.fixture
    def mock_index(self):
        """Create a mock temporal index."""
        config = TemporalIndexConfig(
            index_id="test_index_1",
            index_name="Test Index 1",
            index_type=IndexType.BTREE,
        )
        stats = TemporalIndexStatistics(
            index_id="test_index_1", index_name="Test Index 1"
        )
        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = True
        return index

    @pytest.fixture
    def mock_composite_index(self):
        """Create a mock composite temporal index."""
        config = TemporalIndexConfig(
            index_id="test_index_2",
            index_name="Test Index 2",
            index_type=IndexType.COMPOSITE,
        )
        stats = TemporalIndexStatistics(
            index_id="test_index_2", index_name="Test Index 2"
        )
        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = True
        return index

    @pytest.fixture
    def mock_inactive_index(self):
        """Create a mock inactive temporal index."""
        config = TemporalIndexConfig(
            index_id="test_index_3",
            index_name="Test Index 3",
            index_type=IndexType.BTREE,
        )
        stats = TemporalIndexStatistics(
            index_id="test_index_3", index_name="Test Index 3"
        )
        index = Mock(spec=TemporalIndex)
        index.config = config
        index.statistics = stats
        index.is_active.return_value = False
        return index

    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer.available_indexes == {}
        assert optimizer.query_cache == {}
        assert optimizer.performance_history == {}

    def test_register_index(self, optimizer, mock_index):
        """Test registering an index."""
        optimizer.register_index(mock_index)

        assert "test_index_1" in optimizer.available_indexes
        assert optimizer.available_indexes["test_index_1"] == mock_index

    def test_register_multiple_indexes(
        self, optimizer, mock_index, mock_composite_index
    ):
        """Test registering multiple indexes."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_composite_index)

        assert len(optimizer.available_indexes) == 2
        assert "test_index_1" in optimizer.available_indexes
        assert "test_index_2" in optimizer.available_indexes

    def test_unregister_index(self, optimizer, mock_index):
        """Test unregistering an index."""
        optimizer.register_index(mock_index)
        optimizer.unregister_index("test_index_1")

        assert "test_index_1" not in optimizer.available_indexes

    def test_unregister_nonexistent_index(self, optimizer):
        """Test unregistering a non-existent index."""
        # Should not raise an exception
        optimizer.unregister_index("nonexistent")
        assert len(optimizer.available_indexes) == 0

    def test_create_query_plan_basic(self, optimizer, mock_index):
        """Test creating a basic query plan."""
        optimizer.register_index(mock_index)

        plan = optimizer.create_query_plan("range")

        assert isinstance(plan, TemporalQueryPlan)
        assert plan.query_hash is not None
        assert plan.primary_index == "test_index_1"
        assert plan.execution_strategy is not None
        assert plan.estimated_cost >= 0
        assert plan.estimated_rows >= 0

    def test_create_query_plan_with_time_range(self, optimizer, mock_index):
        """Test creating a query plan with time range."""
        optimizer.register_index(mock_index)

        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()

        plan = optimizer.create_query_plan(
            "range", start_time=start_time, end_time=end_time
        )

        assert plan.primary_index == "test_index_1"
        assert plan.estimated_cost > 0

    def test_create_query_plan_with_entity_ids(self, optimizer, mock_index):
        """Test creating a query plan with entity IDs."""
        optimizer.register_index(mock_index)

        entity_ids = ["entity1", "entity2", "entity3"]

        plan = optimizer.create_query_plan("entity_timeline", entity_ids=entity_ids)

        assert plan.primary_index == "test_index_1"
        assert plan.estimated_cost > 0

    def test_create_query_plan_with_hints(
        self, optimizer, mock_index, mock_composite_index
    ):
        """Test creating a query plan with hints."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_composite_index)

        hints = TemporalQueryHint(preferred_indexes=["test_index_2"])

        plan = optimizer.create_query_plan("range", hints=hints)

        assert plan.primary_index == "test_index_2"

    def test_create_query_plan_with_avoid_hints(
        self, optimizer, mock_index, mock_composite_index
    ):
        """Test creating a query plan with avoid hints."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_composite_index)

        hints = TemporalQueryHint(avoid_indexes=["test_index_1"])

        plan = optimizer.create_query_plan("range", hints=hints)

        assert plan.primary_index == "test_index_2"

    def test_create_query_plan_no_active_indexes(self, optimizer, mock_inactive_index):
        """Test creating a query plan with no active indexes."""
        optimizer.register_index(mock_inactive_index)

        plan = optimizer.create_query_plan("range")

        assert plan.primary_index is None
        assert plan.secondary_indexes == []

    def test_query_plan_caching(self, optimizer, mock_index):
        """Test query plan caching."""
        optimizer.register_index(mock_index)

        # First call should create and cache the plan
        plan1 = optimizer.create_query_plan("range")

        # Second call should return cached plan
        plan2 = optimizer.create_query_plan("range")

        assert plan1.query_hash == plan2.query_hash
        assert plan1.plan_id == plan2.plan_id

    def test_query_signature_creation(self, optimizer):
        """Test query signature creation."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 2, 12, 0, 0)
        entity_ids = ["entity1", "entity2"]
        hints = TemporalQueryHint(preferred_indexes=["index1"])

        signature1 = optimizer._create_query_signature(
            "range", start_time, end_time, entity_ids, hints
        )

        # Same parameters should produce same signature
        signature2 = optimizer._create_query_signature(
            "range", start_time, end_time, entity_ids, hints
        )

        assert signature1 == signature2
        assert len(signature1) == 32  # MD5 hash length

    def test_query_signature_different_parameters(self, optimizer):
        """Test query signature with different parameters."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 2, 12, 0, 0)

        signature1 = optimizer._create_query_signature(
            "range", start_time, end_time, None, None
        )
        signature2 = optimizer._create_query_signature(
            "point", start_time, end_time, None, None
        )

        assert signature1 != signature2

    def test_select_indexes_no_indexes(self, optimizer):
        """Test index selection with no available indexes."""
        selected = optimizer._select_indexes("range", None, None, None, None)

        assert selected == []

    def test_select_indexes_with_preferred_hints(
        self, optimizer, mock_index, mock_composite_index
    ):
        """Test index selection with preferred hints."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_composite_index)

        hints = TemporalQueryHint(preferred_indexes=["test_index_2"])

        selected = optimizer._select_indexes("range", None, None, None, hints)

        assert selected == ["test_index_2"]

    def test_select_indexes_with_avoid_hints(
        self, optimizer, mock_index, mock_composite_index
    ):
        """Test index selection with avoid hints."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_composite_index)

        hints = TemporalQueryHint(avoid_indexes=["test_index_1"])

        selected = optimizer._select_indexes("range", None, None, None, hints)

        assert "test_index_1" not in selected
        assert "test_index_2" in selected

    def test_select_indexes_inactive_filtered(
        self, optimizer, mock_index, mock_inactive_index
    ):
        """Test that inactive indexes are filtered out."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_inactive_index)

        selected = optimizer._select_indexes("range", None, None, None, None)

        assert "test_index_1" in selected
        assert "test_index_3" not in selected

    def test_score_index_for_query_btree(self, optimizer, mock_index):
        """Test scoring a BTree index for different query types."""
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()

        # BTree should score well for range queries
        score_range = optimizer._score_index_for_query(
            mock_index, "range", start_time, end_time, None
        )

        # BTree should score well for point queries
        score_point = optimizer._score_index_for_query(
            mock_index, "point", start_time, None, None
        )

        assert score_range > 0
        assert score_point > 0

    def test_score_index_for_query_composite(self, optimizer, mock_composite_index):
        """Test scoring a composite index for different query types."""
        entity_ids = ["entity1", "entity2"]

        # Composite should score well for entity queries
        score_entity = optimizer._score_index_for_query(
            mock_composite_index, "entity_timeline", None, None, entity_ids
        )

        assert score_entity > 0

    def test_determine_execution_strategy_range(self, optimizer):
        """Test execution strategy determination for range queries."""
        strategy = optimizer._determine_execution_strategy(
            "range", ["test_index_1"], None
        )

        assert strategy in ["sequential", "parallel", "streaming"]

    def test_determine_execution_strategy_point(self, optimizer):
        """Test execution strategy determination for point queries."""
        strategy = optimizer._determine_execution_strategy(
            "point", ["test_index_1"], None
        )

        assert strategy in ["sequential", "parallel", "streaming"]

    def test_determine_execution_strategy_with_hints(self, optimizer):
        """Test execution strategy determination with hints."""
        hints = TemporalQueryHint(parallel_execution=True)

        strategy = optimizer._determine_execution_strategy(
            "range", ["test_index_1", "test_index_2"], hints
        )

        assert strategy == "parallel"

    def test_estimate_query_cost_basic(self, optimizer):
        """Test basic query cost estimation."""
        cost = optimizer._estimate_query_cost(
            "range", ["test_index_1"], None, None, None
        )

        assert cost > 0
        assert isinstance(cost, float)

    def test_estimate_query_cost_with_time_range(self, optimizer):
        """Test query cost estimation with time range."""
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()

        cost = optimizer._estimate_query_cost(
            "range", ["test_index_1"], start_time, end_time, None
        )

        assert cost > 0

    def test_estimate_query_cost_with_entities(self, optimizer):
        """Test query cost estimation with entity IDs."""
        entity_ids = ["entity1", "entity2", "entity3"]

        cost = optimizer._estimate_query_cost(
            "entity_timeline", ["test_index_1"], None, None, entity_ids
        )

        assert cost > 0

    def test_estimate_result_size_basic(self, optimizer):
        """Test basic result size estimation."""
        size = optimizer._estimate_result_size(
            "range", ["test_index_1"], None, None, None
        )

        assert size >= 0
        assert isinstance(size, int)

    def test_estimate_result_size_with_time_range(self, optimizer):
        """Test result size estimation with time range."""
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()

        size = optimizer._estimate_result_size(
            "range", ["test_index_1"], start_time, end_time, None
        )

        assert size >= 0

    def test_estimate_execution_time(self, optimizer):
        """Test execution time estimation."""
        time_ms = optimizer._estimate_execution_time(100.0, "index_scan")

        assert time_ms > 0
        assert isinstance(time_ms, float)

    def test_estimate_memory_usage(self, optimizer):
        """Test memory usage estimation."""
        memory_mb = optimizer._estimate_memory_usage(1000, "index_scan")

        assert memory_mb > 0
        assert isinstance(memory_mb, float)

    def test_should_use_index_intersection_multiple_indexes(self, optimizer):
        """Test index intersection decision with multiple indexes."""
        should_use = optimizer._should_use_index_intersection(
            ["index1", "index2"], "range"
        )

        assert isinstance(should_use, bool)

    def test_should_use_index_intersection_single_index(self, optimizer):
        """Test index intersection decision with single index."""
        should_use = optimizer._should_use_index_intersection(["index1"], "range")

        assert should_use is False

    def test_should_use_temporal_clustering(self, optimizer):
        """Test temporal clustering decision."""
        should_use = optimizer._should_use_temporal_clustering("range", None)

        assert isinstance(should_use, bool)

    def test_should_use_temporal_clustering_with_hints(self, optimizer):
        """Test temporal clustering decision with hints."""
        hints = TemporalQueryHint(use_clustering=False)

        should_use = optimizer._should_use_temporal_clustering("range", hints)

        assert should_use is False

    def test_should_cache_intermediate_results_fast_query(self, optimizer):
        """Test caching decision for fast queries."""
        should_cache = optimizer._should_cache_intermediate_results(100.0, 10.0)

        assert should_cache is False

    def test_should_cache_intermediate_results_slow_query(self, optimizer):
        """Test caching decision for slow queries."""
        should_cache = optimizer._should_cache_intermediate_results(150.0, 30.0)

        assert should_cache is True

    def test_record_query_performance(self, optimizer):
        """Test recording query performance."""
        plan_id = "test_plan_123"
        execution_time = 250.5

        optimizer.record_query_performance(plan_id, execution_time)

        assert plan_id in optimizer.performance_history
        assert optimizer.performance_history[plan_id] == [execution_time]

    def test_record_query_performance_multiple(self, optimizer):
        """Test recording multiple query performances."""
        plan_id = "test_plan_123"

        optimizer.record_query_performance(plan_id, 100.0)
        optimizer.record_query_performance(plan_id, 200.0)
        optimizer.record_query_performance(plan_id, 150.0)

        assert len(optimizer.performance_history[plan_id]) == 3
        assert optimizer.performance_history[plan_id] == [100.0, 200.0, 150.0]

    def test_record_query_performance_limit(self, optimizer):
        """Test query performance recording with limit."""
        plan_id = "test_plan_123"

        # Record more than 100 performances
        for i in range(105):
            optimizer.record_query_performance(plan_id, float(i))

        # Should keep only the last 100
        assert len(optimizer.performance_history[plan_id]) == 100
        assert optimizer.performance_history[plan_id][0] == 5.0  # First kept value
        assert optimizer.performance_history[plan_id][-1] == 104.0  # Last value

    def test_get_optimizer_statistics_empty(self, optimizer):
        """Test getting optimizer statistics when empty."""
        stats = optimizer.get_optimizer_statistics()

        assert stats["registered_indexes"] == 0
        assert stats["active_indexes"] == 0
        assert stats["cached_plans"] == 0
        assert stats["performance_history_entries"] == 0

    def test_get_optimizer_statistics_with_data(
        self, optimizer, mock_index, mock_inactive_index
    ):
        """Test getting optimizer statistics with data."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_inactive_index)

        # Create a cached plan
        optimizer.create_query_plan("range")

        # Record some performance
        optimizer.record_query_performance("plan1", 100.0)
        optimizer.record_query_performance("plan2", 200.0)

        stats = optimizer.get_optimizer_statistics()

        assert stats["registered_indexes"] == 2
        assert stats["active_indexes"] == 1
        assert stats["cached_plans"] == 1
        assert stats["performance_history_entries"] == 2

    def test_clear_cache(self, optimizer, mock_index):
        """Test clearing the query cache."""
        optimizer.register_index(mock_index)

        # Create some cached plans
        optimizer.create_query_plan("range")
        optimizer.create_query_plan("point")

        assert len(optimizer.query_cache) == 2

        optimizer.clear_cache()

        assert len(optimizer.query_cache) == 0

    def test_integration_complex_query_planning(
        self, optimizer, mock_index, mock_composite_index
    ):
        """Test complex query planning integration."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_composite_index)

        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()
        entity_ids = ["entity1", "entity2", "entity3"]
        hints = TemporalQueryHint(use_clustering=True)

        plan = optimizer.create_query_plan(
            "entity_timeline",
            start_time=start_time,
            end_time=end_time,
            entity_ids=entity_ids,
            hints=hints,
        )

        assert plan.primary_index is not None
        assert plan.estimated_cost > 0
        assert plan.estimated_rows >= 0
        assert plan.estimated_execution_time_ms > 0
        assert plan.estimated_memory_usage_mb > 0
        assert isinstance(plan.use_temporal_clustering, bool)

    def test_optimization_flags_setting(
        self, optimizer, mock_index, mock_composite_index
    ):
        """Test that optimization flags are properly set."""
        optimizer.register_index(mock_index)
        optimizer.register_index(mock_composite_index)

        plan = optimizer.create_query_plan("range")

        assert isinstance(plan.use_index_intersection, bool)
        assert isinstance(plan.use_temporal_clustering, bool)
        assert isinstance(plan.cache_intermediate_results, bool)

    def test_query_plan_properties(self, optimizer, mock_index):
        """Test that query plan has all required properties."""
        optimizer.register_index(mock_index)

        plan = optimizer.create_query_plan("range")

        # Check all required properties exist
        assert hasattr(plan, "query_hash")
        assert hasattr(plan, "plan_id")
        assert hasattr(plan, "primary_index")
        assert hasattr(plan, "secondary_indexes")
        assert hasattr(plan, "execution_strategy")
        assert hasattr(plan, "estimated_cost")
        assert hasattr(plan, "estimated_rows")
        assert hasattr(plan, "estimated_execution_time_ms")
        assert hasattr(plan, "estimated_memory_usage_mb")
        assert hasattr(plan, "use_index_intersection")
        assert hasattr(plan, "use_temporal_clustering")
        assert hasattr(plan, "cache_intermediate_results")
