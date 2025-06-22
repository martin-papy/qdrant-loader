"""Comprehensive tests for TemporalCompositeIndex.

This test suite covers:
- Index initialization and configuration
- Entity-timestamp insertion and management
- Timeline queries for specific entities
- Entity queries at specific timestamps
- Multi-entity time range queries
- Temporal neighbor discovery
- Statistics and performance metrics
- Index rebuilding and maintenance
- Error handling and edge cases
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from qdrant_loader.core.temporal_indexing.composite_index import TemporalCompositeIndex
from qdrant_loader.core.temporal_indexing.index_types import (
    IndexStatus,
    IndexType,
    TemporalIndexConfig,
)


class TestTemporalCompositeIndex:
    """Test suite for TemporalCompositeIndex."""

    @pytest.fixture
    def index_config(self):
        """Create a test index configuration."""
        return TemporalIndexConfig(
            index_name="test_composite_index",
            index_type=IndexType.COMPOSITE,
            temporal_field="timestamp",
            entity_field="entity_id",
            page_size=100,
            cache_size_mb=10,
        )

    @pytest.fixture
    def composite_index(self, index_config):
        """Create a TemporalCompositeIndex instance."""
        return TemporalCompositeIndex(index_config)

    @pytest.fixture
    def sample_timestamps(self):
        """Create sample timestamps for testing."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        return [
            base_time,
            base_time + timedelta(hours=1),
            base_time + timedelta(hours=2),
            base_time + timedelta(hours=3),
            base_time + timedelta(days=1),
        ]

    @pytest.fixture
    def sample_entities(self):
        """Create sample entity IDs for testing."""
        return ["entity_1", "entity_2", "entity_3", "entity_4"]

    # Initialization Tests

    def test_composite_index_initialization(self, index_config):
        """Test composite index initialization."""
        index = TemporalCompositeIndex(index_config)

        assert index.config == index_config
        assert index.status == IndexStatus.ACTIVE
        assert isinstance(index.entity_indexes, dict)
        assert isinstance(index.time_index, dict)
        assert isinstance(index.entity_times, dict)
        assert len(index.entity_indexes) == 0

    def test_composite_index_initialization_with_build_failure(self, index_config):
        """Test composite index initialization with build failure."""
        with patch.object(
            TemporalCompositeIndex,
            "_build_index",
            side_effect=Exception("Build failed"),
        ):
            with pytest.raises(Exception, match="Build failed"):
                index = TemporalCompositeIndex(index_config)

    def test_is_active_method(self, composite_index):
        """Test is_active method."""
        assert composite_index.is_active() is True

        composite_index.status = IndexStatus.ERROR
        assert composite_index.is_active() is False

        composite_index.status = IndexStatus.DISABLED
        assert composite_index.is_active() is False

    # Insertion Tests

    @pytest.mark.asyncio
    async def test_insert_single_entity_timestamp(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test inserting a single entity-timestamp mapping."""
        timestamp = sample_timestamps[0]
        entity_id = sample_entities[0]

        result = await composite_index.insert(timestamp, entity_id)

        assert result is True
        assert entity_id in composite_index.entity_indexes
        assert entity_id in composite_index.time_index[timestamp]
        assert timestamp in composite_index.entity_times[entity_id]
        assert composite_index.statistics.total_entries == 1

    @pytest.mark.asyncio
    async def test_insert_multiple_entities_same_timestamp(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test inserting multiple entities at the same timestamp."""
        timestamp = sample_timestamps[0]

        for entity_id in sample_entities[:3]:
            result = await composite_index.insert(timestamp, entity_id)
            assert result is True

        assert len(composite_index.time_index[timestamp]) == 3
        assert all(
            entity_id in composite_index.entity_indexes
            for entity_id in sample_entities[:3]
        )
        assert composite_index.statistics.total_entries == 3

    @pytest.mark.asyncio
    async def test_insert_same_entity_multiple_timestamps(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test inserting the same entity at multiple timestamps."""
        entity_id = sample_entities[0]

        for timestamp in sample_timestamps[:3]:
            result = await composite_index.insert(timestamp, entity_id)
            assert result is True

        assert len(composite_index.entity_times[entity_id]) == 3
        assert all(
            timestamp in composite_index.time_index
            for timestamp in sample_timestamps[:3]
        )
        assert composite_index.statistics.total_entries == 3

    @pytest.mark.asyncio
    async def test_insert_with_metadata(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test inserting with metadata."""
        timestamp = sample_timestamps[0]
        entity_id = sample_entities[0]
        metadata = {"type": "event", "priority": "high"}

        result = await composite_index.insert(timestamp, entity_id, metadata)

        assert result is True
        assert entity_id in composite_index.entity_indexes

    @pytest.mark.asyncio
    async def test_insert_inactive_index(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test insertion when index is inactive."""
        composite_index.status = IndexStatus.DISABLED

        result = await composite_index.insert(sample_timestamps[0], sample_entities[0])

        assert result is False
        assert composite_index.statistics.total_entries == 0

    @pytest.mark.asyncio
    async def test_insert_with_exception(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test insertion with exception handling."""
        with patch.object(
            composite_index, "entity_indexes", side_effect=Exception("Insert failed")
        ):
            result = await composite_index.insert(
                sample_timestamps[0], sample_entities[0]
            )
            assert result is False

    # Entity Timeline Query Tests

    @pytest.mark.asyncio
    async def test_query_entity_timeline_all_timestamps(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test querying all timestamps for an entity."""
        entity_id = sample_entities[0]

        # Insert multiple timestamps for the entity
        for timestamp in sample_timestamps[:3]:
            await composite_index.insert(timestamp, entity_id)

        result = await composite_index.query_entity_timeline(entity_id)

        assert len(result) == 3
        assert all(ts in result for ts in sample_timestamps[:3])
        assert result == sorted(sample_timestamps[:3])

    @pytest.mark.asyncio
    async def test_query_entity_timeline_with_limit(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test querying entity timeline with limit."""
        entity_id = sample_entities[0]

        # Insert multiple timestamps
        for timestamp in sample_timestamps:
            await composite_index.insert(timestamp, entity_id)

        result = await composite_index.query_entity_timeline(entity_id, limit=2)

        assert len(result) == 2
        assert result == sorted(sample_timestamps)[:2]

    @pytest.mark.asyncio
    async def test_query_entity_timeline_with_time_range(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test querying entity timeline with time range."""
        entity_id = sample_entities[0]

        # Insert all timestamps
        for timestamp in sample_timestamps:
            await composite_index.insert(timestamp, entity_id)

        # Query with time range
        start_time = sample_timestamps[1]
        end_time = sample_timestamps[3]

        with patch.object(
            composite_index.entity_indexes[entity_id],
            "range_query",
            return_value=[(ts, entity_id) for ts in sample_timestamps[1:4]],
        ) as mock_range:
            result = await composite_index.query_entity_timeline(
                entity_id, start_time, end_time
            )

            mock_range.assert_called_once_with(start_time, end_time, None)
            assert len(result) == 3
            assert result == sample_timestamps[1:4]

    @pytest.mark.asyncio
    async def test_query_entity_timeline_nonexistent_entity(self, composite_index):
        """Test querying timeline for nonexistent entity."""
        result = await composite_index.query_entity_timeline("nonexistent_entity")
        assert result == []

    @pytest.mark.asyncio
    async def test_query_entity_timeline_inactive_index(
        self, composite_index, sample_entities
    ):
        """Test querying timeline when index is inactive."""
        composite_index.status = IndexStatus.DISABLED

        result = await composite_index.query_entity_timeline(sample_entities[0])
        assert result == []

    @pytest.mark.asyncio
    async def test_query_entity_timeline_with_exception(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test entity timeline query with exception handling."""
        entity_id = sample_entities[0]
        await composite_index.insert(sample_timestamps[0], entity_id)

        with patch.object(
            composite_index, "entity_times", side_effect=Exception("Query failed")
        ):
            result = await composite_index.query_entity_timeline(entity_id)
            assert result == []

    # Entities at Time Query Tests

    @pytest.mark.asyncio
    async def test_query_entities_at_time(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test querying entities at a specific time."""
        timestamp = sample_timestamps[0]

        # Insert multiple entities at the same timestamp
        for entity_id in sample_entities[:3]:
            await composite_index.insert(timestamp, entity_id)

        result = await composite_index.query_entities_at_time(timestamp)

        assert len(result) == 3
        assert all(entity_id in result for entity_id in sample_entities[:3])

    @pytest.mark.asyncio
    async def test_query_entities_at_time_with_filter(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test querying entities at time with entity filter."""
        timestamp = sample_timestamps[0]

        # Insert all entities
        for entity_id in sample_entities:
            await composite_index.insert(timestamp, entity_id)

        # Query with filter
        entity_filter = {sample_entities[0], sample_entities[2]}
        result = await composite_index.query_entities_at_time(timestamp, entity_filter)

        assert len(result) == 2
        assert all(entity_id in entity_filter for entity_id in result)

    @pytest.mark.asyncio
    async def test_query_entities_at_time_no_entities(
        self, composite_index, sample_timestamps
    ):
        """Test querying entities at time with no entities."""
        result = await composite_index.query_entities_at_time(sample_timestamps[0])
        assert result == []

    @pytest.mark.asyncio
    async def test_query_entities_at_time_inactive_index(
        self, composite_index, sample_timestamps
    ):
        """Test querying entities at time when index is inactive."""
        composite_index.status = IndexStatus.DISABLED

        result = await composite_index.query_entities_at_time(sample_timestamps[0])
        assert result == []

    @pytest.mark.asyncio
    async def test_query_entities_at_time_with_exception(
        self, composite_index, sample_timestamps
    ):
        """Test entities at time query with exception handling."""
        with patch.object(
            composite_index, "time_index", side_effect=Exception("Query failed")
        ):
            result = await composite_index.query_entities_at_time(sample_timestamps[0])
            assert result == []

    # Multi-Entity Time Range Query Tests

    @pytest.mark.asyncio
    async def test_query_entity_time_range(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test querying multiple entities within a time range."""
        # Setup data
        for i, entity_id in enumerate(sample_entities[:2]):
            for j, timestamp in enumerate(sample_timestamps[:3]):
                if (i + j) % 2 == 0:  # Sparse pattern
                    await composite_index.insert(timestamp, entity_id)

        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        # Mock the entity timeline queries
        with patch.object(composite_index, "query_entity_timeline") as mock_timeline:
            mock_timeline.side_effect = [
                [sample_timestamps[0], sample_timestamps[2]],  # entity_1
                [sample_timestamps[1]],  # entity_2
            ]

            result = await composite_index.query_entity_time_range(
                sample_entities[:2], start_time, end_time
            )

            assert len(result) == 2
            assert sample_entities[0] in result
            assert sample_entities[1] in result
            assert len(result[sample_entities[0]]) == 2
            assert len(result[sample_entities[1]]) == 1

    @pytest.mark.asyncio
    async def test_query_entity_time_range_with_limit(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test multi-entity time range query with limit."""
        entity_ids = sample_entities[:2]
        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]
        limit = 1

        with patch.object(composite_index, "query_entity_timeline") as mock_timeline:
            mock_timeline.side_effect = [
                [sample_timestamps[0]],  # Limited to 1
                [sample_timestamps[1]],  # Limited to 1
            ]

            result = await composite_index.query_entity_time_range(
                entity_ids, start_time, end_time, limit
            )

            # Verify timeline queries were called with limit
            for call in mock_timeline.call_args_list:
                assert call[1]["limit"] == limit

    @pytest.mark.asyncio
    async def test_query_entity_time_range_empty_entities(
        self, composite_index, sample_timestamps
    ):
        """Test multi-entity time range query with empty entity list."""
        result = await composite_index.query_entity_time_range(
            [], sample_timestamps[0], sample_timestamps[1]
        )
        assert result == {}

    # Temporal Neighbors Tests

    @pytest.mark.asyncio
    async def test_find_temporal_neighbors(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test finding temporal neighbors for an entity."""
        target_entity = sample_entities[0]
        target_timestamp = sample_timestamps[2]

        # Setup entities around the target time
        await composite_index.insert(
            sample_timestamps[1], sample_entities[1]
        )  # 1 hour before
        await composite_index.insert(sample_timestamps[2], target_entity)  # Target time
        await composite_index.insert(
            sample_timestamps[3], sample_entities[2]
        )  # 1 hour after
        await composite_index.insert(
            sample_timestamps[4], sample_entities[3]
        )  # 1 day after (outside window)

        result = await composite_index.find_temporal_neighbors(
            target_entity, target_timestamp, time_window_seconds=7200  # 2 hours
        )

        # Should find neighbors within 2-hour window
        assert len(result) >= 2  # At least the entities 1 hour before and after

        # Verify result structure (entity_id, timestamp, distance_seconds)
        for entity_id, timestamp, distance in result:
            assert isinstance(entity_id, str)
            assert isinstance(timestamp, datetime)
            assert isinstance(distance, float)
            assert distance >= 0.0  # Distance should be non-negative

    @pytest.mark.asyncio
    async def test_find_temporal_neighbors_nonexistent_entity(
        self, composite_index, sample_timestamps
    ):
        """Test finding temporal neighbors for nonexistent entity."""
        result = await composite_index.find_temporal_neighbors(
            "nonexistent", sample_timestamps[0]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_find_temporal_neighbors_no_neighbors(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test finding temporal neighbors when no neighbors exist in window."""
        entity_id = sample_entities[0]
        timestamp = sample_timestamps[0]

        # Insert only the target entity
        await composite_index.insert(timestamp, entity_id)

        result = await composite_index.find_temporal_neighbors(
            entity_id, timestamp, time_window_seconds=3600
        )

        # Should return empty list or only the entity itself
        assert len(result) <= 1

    # Statistics and Performance Tests

    @pytest.mark.asyncio
    async def test_get_entity_count(
        self, composite_index, sample_entities, sample_timestamps
    ):
        """Test getting entity count."""
        # Initially empty
        assert composite_index.get_entity_count() == 0

        # Add some entities using the insert method
        await composite_index.insert(sample_timestamps[0], sample_entities[0])
        await composite_index.insert(sample_timestamps[1], sample_entities[1])

        assert composite_index.get_entity_count() == 2

    def test_get_timestamp_count(self, composite_index, sample_timestamps):
        """Test getting timestamp count."""
        # Initially empty
        assert composite_index.get_timestamp_count() == 0

        # Add some timestamps
        composite_index.time_index[sample_timestamps[0]].add("entity_1")
        composite_index.time_index[sample_timestamps[1]].add("entity_2")

        assert composite_index.get_timestamp_count() == 2

    @pytest.mark.asyncio
    async def test_get_entity_statistics(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test getting statistics for a specific entity."""
        entity_id = sample_entities[0]

        # Insert data for the entity
        for timestamp in sample_timestamps[:3]:
            await composite_index.insert(timestamp, entity_id)

        stats = composite_index.get_entity_statistics(entity_id)

        assert stats is not None
        assert stats["entity_id"] == entity_id
        assert stats["total_timestamps"] == 3
        assert "earliest_timestamp" in stats
        assert "latest_timestamp" in stats
        assert "index_memory_usage" in stats
        assert "index_statistics" in stats

    def test_get_entity_statistics_nonexistent(self, composite_index):
        """Test getting statistics for nonexistent entity."""
        stats = composite_index.get_entity_statistics("nonexistent")
        assert stats is None

    def test_get_memory_usage(self, composite_index):
        """Test getting memory usage estimation."""
        usage = composite_index.get_memory_usage()
        assert isinstance(usage, int)
        assert usage >= 0

    # Index Maintenance Tests

    @pytest.mark.asyncio
    async def test_rebuild_index(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test rebuilding the index."""
        # Add some data first
        for timestamp in sample_timestamps[:2]:
            for entity_id in sample_entities[:2]:
                await composite_index.insert(timestamp, entity_id)

        # Rebuild
        result = await composite_index.rebuild()

        assert result is True
        assert composite_index.status == IndexStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_rebuild_index_with_failure(self, composite_index):
        """Test rebuilding index with failure."""
        with patch.object(
            composite_index, "_build_index", side_effect=Exception("Rebuild failed")
        ):
            result = await composite_index.rebuild()

            assert result is False
            assert composite_index.status == IndexStatus.ERROR

    # Statistics Update Tests

    @pytest.mark.asyncio
    async def test_query_statistics_update(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test that query statistics are properly updated."""
        entity_id = sample_entities[0]
        timestamp = sample_timestamps[0]

        # Insert data
        await composite_index.insert(timestamp, entity_id)

        # Perform queries
        await composite_index.query_entity_timeline(entity_id)
        await composite_index.query_entities_at_time(timestamp)

        # Check that statistics were updated
        assert composite_index.statistics.total_queries >= 2

    def test_update_query_stats(self, composite_index):
        """Test internal query statistics update method."""
        initial_avg = composite_index.statistics.average_query_time_ms

        composite_index._update_query_stats(100.0)

        # Should update average query time
        assert composite_index.statistics.average_query_time_ms != initial_avg

    # Error Handling and Edge Cases

    @pytest.mark.asyncio
    async def test_concurrent_insertions(
        self, composite_index, sample_timestamps, sample_entities
    ):
        """Test concurrent insertions to the same index."""
        # Create multiple insertion tasks
        tasks = []
        for i, timestamp in enumerate(sample_timestamps):
            for j, entity_id in enumerate(sample_entities):
                task = composite_index.insert(timestamp, f"{entity_id}_{i}_{j}")
                tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most insertions should succeed
        success_count = sum(1 for result in results if result is True)
        assert success_count > 0

    @pytest.mark.asyncio
    async def test_large_entity_set(self, composite_index):
        """Test handling large number of entities."""
        timestamp = datetime.now()
        large_entity_set = [f"entity_{i}" for i in range(100)]

        # Insert many entities
        for entity_id in large_entity_set:
            await composite_index.insert(timestamp, entity_id)

        # Query should handle large result set
        result = await composite_index.query_entities_at_time(timestamp)
        assert len(result) == 100

    @pytest.mark.asyncio
    async def test_extreme_time_ranges(self, composite_index, sample_entities):
        """Test handling extreme time ranges."""
        entity_id = sample_entities[0]

        # Very old and very new timestamps
        old_time = datetime(1900, 1, 1)
        new_time = datetime(2100, 12, 31)

        await composite_index.insert(old_time, entity_id)
        await composite_index.insert(new_time, entity_id)

        result = await composite_index.query_entity_timeline(entity_id)
        assert len(result) == 2
        assert old_time in result
        assert new_time in result

    def test_config_property_access(self, composite_index, index_config):
        """Test accessing configuration properties."""
        assert composite_index.config == index_config
        assert composite_index.config.index_name == "test_composite_index"
        assert composite_index.config.index_type == IndexType.COMPOSITE

    @pytest.mark.asyncio
    async def test_entity_index_creation_optimization(
        self, composite_index, sample_entities
    ):
        """Test that entity-specific indexes are created efficiently."""
        timestamp = datetime.now()
        entity_id = sample_entities[0]

        # First insert should create entity index
        assert entity_id not in composite_index.entity_indexes
        await composite_index.insert(timestamp, entity_id)
        assert entity_id in composite_index.entity_indexes

        # Second insert should reuse existing index
        entity_index = composite_index.entity_indexes[entity_id]
        await composite_index.insert(timestamp + timedelta(hours=1), entity_id)
        assert composite_index.entity_indexes[entity_id] is entity_index
