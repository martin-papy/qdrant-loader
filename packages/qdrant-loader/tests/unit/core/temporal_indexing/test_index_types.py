"""Tests for temporal index types and data structures."""

import uuid
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from qdrant_loader.core.temporal_indexing.index_types import (
    IndexStatus,
    IndexType,
    TemporalIndex,
    TemporalIndexConfig,
    TemporalIndexStatistics,
    TemporalQueryHint,
    TemporalQueryPlan,
)


class TestIndexType:
    """Test IndexType enum."""

    def test_index_type_values(self):
        """Test IndexType enum values."""
        assert IndexType.BTREE.value == "btree"
        assert IndexType.COMPOSITE.value == "composite"
        assert IndexType.HASH.value == "hash"
        assert IndexType.RANGE.value == "range"
        assert IndexType.CLUSTERING.value == "clustering"

    def test_index_type_count(self):
        """Test that all expected index types are present."""
        assert len(IndexType) == 5


class TestIndexStatus:
    """Test IndexStatus enum."""

    def test_index_status_values(self):
        """Test IndexStatus enum values."""
        assert IndexStatus.BUILDING.value == "building"
        assert IndexStatus.ACTIVE.value == "active"
        assert IndexStatus.REBUILDING.value == "rebuilding"
        assert IndexStatus.DISABLED.value == "disabled"
        assert IndexStatus.ERROR.value == "error"

    def test_index_status_count(self):
        """Test that all expected statuses are present."""
        assert len(IndexStatus) == 5


class TestTemporalIndexConfig:
    """Test TemporalIndexConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TemporalIndexConfig()

        # UUID should be generated
        assert config.index_id is not None
        assert len(config.index_id) == 36  # UUID length

        # Default values
        assert config.index_name == ""
        assert config.index_type == IndexType.BTREE
        assert config.temporal_field == "valid_from"
        assert config.entity_field is None
        assert config.additional_fields == []
        assert config.page_size == 4096
        assert config.cache_size_mb == 64
        assert config.max_depth == 10
        assert config.auto_rebuild is True
        assert config.rebuild_threshold == 0.3
        assert config.maintenance_interval_hours == 24
        assert config.cluster_by_entity is True
        assert config.cluster_time_window_hours == 24

    def test_custom_values(self):
        """Test configuration with custom values."""
        config = TemporalIndexConfig(
            index_name="test_index",
            index_type=IndexType.HASH,
            temporal_field="timestamp",
            entity_field="entity_id",
            additional_fields=["field1", "field2"],
            page_size=8192,
            cache_size_mb=128,
            max_depth=15,
            auto_rebuild=False,
            rebuild_threshold=0.5,
            maintenance_interval_hours=12,
            cluster_by_entity=False,
            cluster_time_window_hours=48,
        )

        assert config.index_name == "test_index"
        assert config.index_type == IndexType.HASH
        assert config.temporal_field == "timestamp"
        assert config.entity_field == "entity_id"
        assert config.additional_fields == ["field1", "field2"]
        assert config.page_size == 8192
        assert config.cache_size_mb == 128
        assert config.max_depth == 15
        assert config.auto_rebuild is False
        assert config.rebuild_threshold == 0.5
        assert config.maintenance_interval_hours == 12
        assert config.cluster_by_entity is False
        assert config.cluster_time_window_hours == 48

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = TemporalIndexConfig(
            index_name="test_index",
            index_type=IndexType.COMPOSITE,
            temporal_field="created_at",
            entity_field="user_id",
            additional_fields=["status", "category"],
        )

        result = config.to_dict()

        expected_keys = {
            "index_id",
            "index_name",
            "index_type",
            "temporal_field",
            "entity_field",
            "additional_fields",
            "page_size",
            "cache_size_mb",
            "max_depth",
            "auto_rebuild",
            "rebuild_threshold",
            "maintenance_interval_hours",
            "cluster_by_entity",
            "cluster_time_window_hours",
        }

        assert set(result.keys()) == expected_keys
        assert result["index_name"] == "test_index"
        assert result["index_type"] == "composite"
        assert result["temporal_field"] == "created_at"
        assert result["entity_field"] == "user_id"
        assert result["additional_fields"] == ["status", "category"]


class TestTemporalIndexStatistics:
    """Test TemporalIndexStatistics dataclass."""

    def test_default_values(self):
        """Test default statistics values."""
        stats = TemporalIndexStatistics(index_id="test-id", index_name="test-index")

        assert stats.index_id == "test-id"
        assert stats.index_name == "test-index"
        assert stats.total_entries == 0
        assert stats.index_size_bytes == 0
        assert stats.memory_usage_bytes == 0
        assert stats.total_queries == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.average_query_time_ms == 0.0
        assert stats.last_rebuild is None
        assert stats.fragmentation_ratio == 0.0
        assert stats.maintenance_operations == 0
        assert stats.earliest_timestamp is None
        assert stats.latest_timestamp is None

    def test_cache_hit_ratio_zero_queries(self):
        """Test cache hit ratio with no queries."""
        stats = TemporalIndexStatistics(index_id="test-id", index_name="test-index")
        assert stats.cache_hit_ratio() == 0.0

    def test_cache_hit_ratio_with_queries(self):
        """Test cache hit ratio calculation."""
        stats = TemporalIndexStatistics(
            index_id="test-id", index_name="test-index", cache_hits=75, cache_misses=25
        )
        assert stats.cache_hit_ratio() == 0.75

    def test_cache_hit_ratio_all_hits(self):
        """Test cache hit ratio with all hits."""
        stats = TemporalIndexStatistics(
            index_id="test-id", index_name="test-index", cache_hits=100, cache_misses=0
        )
        assert stats.cache_hit_ratio() == 1.0

    def test_to_dict_with_timestamps(self):
        """Test conversion to dictionary with timestamps."""
        now = datetime.now(UTC)
        earlier = datetime(2024, 1, 1, tzinfo=UTC)

        stats = TemporalIndexStatistics(
            index_id="test-id",
            index_name="test-index",
            total_entries=1000,
            cache_hits=800,
            cache_misses=200,
            last_rebuild=now,
            earliest_timestamp=earlier,
            latest_timestamp=now,
        )

        result = stats.to_dict()

        assert result["index_id"] == "test-id"
        assert result["index_name"] == "test-index"
        assert result["total_entries"] == 1000
        assert result["cache_hit_ratio"] == 0.8
        assert result["last_rebuild"] == now.isoformat()
        assert result["earliest_timestamp"] == earlier.isoformat()
        assert result["latest_timestamp"] == now.isoformat()

    def test_to_dict_without_timestamps(self):
        """Test conversion to dictionary without timestamps."""
        stats = TemporalIndexStatistics(index_id="test-id", index_name="test-index")

        result = stats.to_dict()

        assert result["last_rebuild"] is None
        assert result["earliest_timestamp"] is None
        assert result["latest_timestamp"] is None


class TestTemporalIndex:
    """Test TemporalIndex dataclass."""

    def test_default_initialization(self):
        """Test default temporal index initialization."""
        config = TemporalIndexConfig(index_name="test_index")
        index = TemporalIndex(config=config)

        assert index.config == config
        assert index.status == IndexStatus.BUILDING
        assert isinstance(index.created_at, datetime)
        assert isinstance(index.last_updated, datetime)
        assert index._index_data == {}
        assert index._cache == {}
        assert isinstance(index.statistics, TemporalIndexStatistics)
        assert index.statistics.index_id == config.index_id
        assert index.statistics.index_name == "test_index"

    def test_custom_initialization(self):
        """Test temporal index with custom values."""
        config = TemporalIndexConfig(index_name="custom_index")
        created_time = datetime(2024, 1, 1, tzinfo=UTC)

        index = TemporalIndex(
            config=config,
            status=IndexStatus.ACTIVE,
            created_at=created_time,
            last_updated=created_time,
        )

        assert index.status == IndexStatus.ACTIVE
        assert index.created_at == created_time
        assert index.last_updated == created_time

    def test_is_active_true(self):
        """Test is_active returns True for active status."""
        config = TemporalIndexConfig()
        index = TemporalIndex(config=config, status=IndexStatus.ACTIVE)
        assert index.is_active() is True

    def test_is_active_false(self):
        """Test is_active returns False for non-active statuses."""
        config = TemporalIndexConfig()

        for status in [
            IndexStatus.BUILDING,
            IndexStatus.REBUILDING,
            IndexStatus.DISABLED,
            IndexStatus.ERROR,
        ]:
            index = TemporalIndex(config=config, status=status)
            assert index.is_active() is False

    def test_needs_rebuild_high_fragmentation(self):
        """Test needs_rebuild with high fragmentation."""
        config = TemporalIndexConfig(rebuild_threshold=0.3)
        index = TemporalIndex(config=config, status=IndexStatus.ACTIVE)
        index.statistics.fragmentation_ratio = 0.5

        assert index.needs_rebuild() is True

    def test_needs_rebuild_error_status(self):
        """Test needs_rebuild with error status."""
        config = TemporalIndexConfig()
        index = TemporalIndex(config=config, status=IndexStatus.ERROR)
        index.statistics.fragmentation_ratio = 0.1

        assert index.needs_rebuild() is True

    def test_needs_rebuild_false(self):
        """Test needs_rebuild returns False for healthy index."""
        config = TemporalIndexConfig(rebuild_threshold=0.3)
        index = TemporalIndex(config=config, status=IndexStatus.ACTIVE)
        index.statistics.fragmentation_ratio = 0.1

        assert index.needs_rebuild() is False

    @pytest.mark.asyncio
    async def test_rebuild_base_implementation(self):
        """Test base rebuild implementation logs warning."""
        config = TemporalIndexConfig()
        index = TemporalIndex(config=config)

        with patch(
            "qdrant_loader.core.temporal_indexing.index_types.logger"
        ) as mock_logger:
            result = await index.rebuild()

            assert result is False
            mock_logger.warning.assert_called_once()

    def test_get_memory_usage_base_implementation(self):
        """Test base get_memory_usage implementation."""
        config = TemporalIndexConfig()
        index = TemporalIndex(config=config)

        assert index.get_memory_usage() == 0


class TestTemporalQueryHint:
    """Test TemporalQueryHint dataclass."""

    def test_default_values(self):
        """Test default query hint values."""
        hint = TemporalQueryHint()

        assert hint.preferred_indexes == []
        assert hint.avoid_indexes == []
        assert hint.use_clustering is True
        assert hint.use_caching is True
        assert hint.parallel_execution is False
        assert hint.expected_result_size is None
        assert hint.time_range_selectivity is None
        assert hint.max_memory_mb is None
        assert hint.streaming_results is False

    def test_custom_values(self):
        """Test query hint with custom values."""
        hint = TemporalQueryHint(
            preferred_indexes=["idx1", "idx2"],
            avoid_indexes=["idx3"],
            use_clustering=False,
            use_caching=False,
            parallel_execution=True,
            expected_result_size=1000,
            time_range_selectivity=0.5,
            max_memory_mb=512,
            streaming_results=True,
        )

        assert hint.preferred_indexes == ["idx1", "idx2"]
        assert hint.avoid_indexes == ["idx3"]
        assert hint.use_clustering is False
        assert hint.use_caching is False
        assert hint.parallel_execution is True
        assert hint.expected_result_size == 1000
        assert hint.time_range_selectivity == 0.5
        assert hint.max_memory_mb == 512
        assert hint.streaming_results is True


class TestTemporalQueryPlan:
    """Test TemporalQueryPlan dataclass."""

    def test_default_values(self):
        """Test default query plan values."""
        plan = TemporalQueryPlan()

        # UUID should be generated
        assert plan.plan_id is not None
        assert len(plan.plan_id) == 36  # UUID length

        assert plan.query_hash == ""
        assert plan.primary_index is None
        assert plan.secondary_indexes == []
        assert plan.execution_strategy == "sequential"
        assert plan.estimated_cost == 0.0
        assert plan.estimated_rows == 0
        assert plan.use_index_intersection is False
        assert plan.use_temporal_clustering is False
        assert plan.cache_intermediate_results is False
        assert plan.estimated_execution_time_ms == 0.0
        assert plan.estimated_memory_usage_mb == 0.0

    def test_custom_values(self):
        """Test query plan with custom values."""
        plan = TemporalQueryPlan(
            query_hash="abc123",
            primary_index="main_idx",
            secondary_indexes=["sec_idx1", "sec_idx2"],
            execution_strategy="parallel",
            estimated_cost=100.5,
            estimated_rows=5000,
            use_index_intersection=True,
            use_temporal_clustering=True,
            cache_intermediate_results=True,
            estimated_execution_time_ms=250.0,
            estimated_memory_usage_mb=64.0,
        )

        assert plan.query_hash == "abc123"
        assert plan.primary_index == "main_idx"
        assert plan.secondary_indexes == ["sec_idx1", "sec_idx2"]
        assert plan.execution_strategy == "parallel"
        assert plan.estimated_cost == 100.5
        assert plan.estimated_rows == 5000
        assert plan.use_index_intersection is True
        assert plan.use_temporal_clustering is True
        assert plan.cache_intermediate_results is True
        assert plan.estimated_execution_time_ms == 250.0
        assert plan.estimated_memory_usage_mb == 64.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        plan = TemporalQueryPlan(
            query_hash="test_hash",
            primary_index="primary_idx",
            secondary_indexes=["sec1", "sec2"],
            execution_strategy="streaming",
            estimated_cost=75.25,
            estimated_rows=2500,
        )

        result = plan.to_dict()

        expected_keys = {
            "plan_id",
            "query_hash",
            "primary_index",
            "secondary_indexes",
            "execution_strategy",
            "estimated_cost",
            "estimated_rows",
            "use_index_intersection",
            "use_temporal_clustering",
            "cache_intermediate_results",
            "estimated_execution_time_ms",
            "estimated_memory_usage_mb",
        }

        assert set(result.keys()) == expected_keys
        assert result["query_hash"] == "test_hash"
        assert result["primary_index"] == "primary_idx"
        assert result["secondary_indexes"] == ["sec1", "sec2"]
        assert result["execution_strategy"] == "streaming"
        assert result["estimated_cost"] == 75.25
        assert result["estimated_rows"] == 2500
