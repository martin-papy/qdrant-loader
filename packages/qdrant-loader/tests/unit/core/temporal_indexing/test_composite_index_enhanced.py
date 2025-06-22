"""Enhanced tests for TemporalCompositeIndex targeting missed coverage lines.

This test suite targets the missed lines in TemporalCompositeIndex to improve
coverage from 88% to 95%+. It focuses on:
- Error handling in build and query operations
- Edge cases in multi-entity scenarios
- Real integration with actual BTree indexes
- Memory management and statistics
- Rebuild and maintenance operations
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from qdrant_loader.core.temporal_indexing.composite_index import TemporalCompositeIndex
from qdrant_loader.core.temporal_indexing.index_types import (
    IndexStatus,
    IndexType,
    TemporalIndexConfig,
)


class TestTemporalCompositeIndexEnhanced:
    """Enhanced tests for TemporalCompositeIndex targeting missed coverage."""

    @pytest.fixture
    def composite_config(self):
        """Create a composite index configuration."""
        return TemporalIndexConfig(
            index_id="composite_test_enhanced",
            index_name="test_composite_enhanced",
            index_type=IndexType.COMPOSITE,
            temporal_field="timestamp",
            entity_field="entity_id",
            page_size=100,
            cache_size_mb=10,
        )

    @pytest.fixture
    def composite_index(self, composite_config):
        """Create a composite index instance."""
        return TemporalCompositeIndex(composite_config)

    @pytest.mark.asyncio
    async def test_build_index_exception_handling(self, composite_index):
        """Test exception handling in _build_index method (lines 46-50)."""
        # Mock the logger to capture error messages
        with patch(
            "qdrant_loader.core.temporal_indexing.composite_index.logger"
        ) as mock_logger:
            # Force an exception during build by patching the logger call itself
            with patch.object(composite_index, "status", IndexStatus.BUILDING):
                # Mock logger.debug to raise an exception
                mock_logger.debug.side_effect = Exception("Test error")

                # This should trigger an exception in _build_index
                composite_index._build_index()

                # Verify error was logged and status set
                mock_logger.error.assert_called()
                assert composite_index.status == IndexStatus.ERROR

    @pytest.mark.asyncio
    async def test_query_entity_timeline_exception_handling(self, composite_index):
        """Test exception handling in query_entity_timeline (line 156)."""
        # Add some data first
        timestamp = datetime.now()
        entity_id = "test_entity"
        await composite_index.insert(timestamp, entity_id)

        # Mock the entity index to raise an exception
        with patch.object(
            composite_index.entity_indexes[entity_id],
            "range_query",
            side_effect=Exception("Test error"),
        ):
            with patch(
                "qdrant_loader.core.temporal_indexing.composite_index.logger"
            ) as mock_logger:
                # This should trigger exception handling
                result = await composite_index.query_entity_timeline(
                    entity_id,
                    datetime.now() - timedelta(hours=1),
                    datetime.now() + timedelta(hours=1),
                )

                # Verify error was logged and empty result returned
                mock_logger.error.assert_called()
                assert result == []

    @pytest.mark.asyncio
    async def test_query_entities_at_time_exception_handling(self, composite_index):
        """Test exception handling in query_entities_at_time (line 190)."""
        # Add some data first
        timestamp = datetime.now()
        await composite_index.insert(timestamp, "entity1")

        # Mock the time_index entirely to raise an exception
        with patch.object(composite_index, "time_index") as mock_time_index:
            mock_time_index.get.side_effect = Exception("Test error")

            with patch(
                "qdrant_loader.core.temporal_indexing.composite_index.logger"
            ) as mock_logger:
                # This should trigger exception handling
                result = await composite_index.query_entities_at_time(timestamp)

                # Verify error was logged and empty result returned
                mock_logger.error.assert_called()
                assert result == []

    @pytest.mark.asyncio
    async def test_query_entity_time_range_exception_handling(self, composite_index):
        """Test exception handling in query_entity_time_range (line 234)."""
        # Add some data first
        timestamp = datetime.now()
        entity_id = "test_entity"
        await composite_index.insert(timestamp, entity_id)

        # Mock query_entity_timeline to raise an exception
        with patch.object(
            composite_index,
            "query_entity_timeline",
            side_effect=Exception("Test error"),
        ):
            with patch(
                "qdrant_loader.core.temporal_indexing.composite_index.logger"
            ) as mock_logger:
                # This should trigger exception handling
                result = await composite_index.query_entity_time_range(
                    [entity_id],
                    datetime.now() - timedelta(hours=1),
                    datetime.now() + timedelta(hours=1),
                )

                # Verify error was logged and empty result returned
                mock_logger.error.assert_called()
                assert result == {}

    @pytest.mark.asyncio
    async def test_find_temporal_neighbors_exception_handling(self, composite_index):
        """Test exception handling in find_temporal_neighbors (line 281)."""
        # Add some data first
        timestamp = datetime.now()
        await composite_index.insert(timestamp, "entity1")
        await composite_index.insert(timestamp + timedelta(minutes=5), "entity2")

        # Mock the time_index entirely to raise an exception
        with patch.object(composite_index, "time_index") as mock_time_index:
            mock_time_index.__iter__.side_effect = Exception("Test error")

            with patch(
                "qdrant_loader.core.temporal_indexing.composite_index.logger"
            ) as mock_logger:
                # This should trigger exception handling
                result = await composite_index.find_temporal_neighbors(
                    "entity1", timestamp
                )

                # Verify error was logged and empty result returned
                mock_logger.error.assert_called()
                assert result == []

    @pytest.mark.asyncio
    async def test_insert_exception_handling(self, composite_index):
        """Test exception handling in insert method (line 98)."""
        # Mock the entity index creation to raise an exception
        with patch(
            "qdrant_loader.core.temporal_indexing.composite_index.TemporalBTreeIndex",
            side_effect=Exception("Test error"),
        ):
            with patch(
                "qdrant_loader.core.temporal_indexing.composite_index.logger"
            ) as mock_logger:
                # This should trigger exception handling
                result = await composite_index.insert(datetime.now(), "test_entity")

                # Verify error was logged and False returned
                mock_logger.error.assert_called()
                assert result is False

    @pytest.mark.asyncio
    async def test_query_entity_timeline_with_no_range_constraints(
        self, composite_index
    ):
        """Test query_entity_timeline with no start/end time (line 140, 142)."""
        # Add multiple timestamps for an entity
        entity_id = "test_entity"
        timestamps = [
            datetime.now() - timedelta(hours=2),
            datetime.now() - timedelta(hours=1),
            datetime.now(),
            datetime.now() + timedelta(hours=1),
        ]

        for ts in timestamps:
            await composite_index.insert(ts, entity_id)

        # Query without start/end time (should return all timestamps)
        result = await composite_index.query_entity_timeline(entity_id)

        # Verify all timestamps returned in sorted order
        assert len(result) == 4
        assert result == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_query_entity_timeline_with_limit_no_range(self, composite_index):
        """Test query_entity_timeline with limit but no range (line 142)."""
        # Add multiple timestamps for an entity
        entity_id = "test_entity"
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(5)]

        for ts in timestamps:
            await composite_index.insert(ts, entity_id)

        # Query with limit but no start/end time
        result = await composite_index.query_entity_timeline(entity_id, limit=3)

        # Verify only 3 results returned
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_query_entities_at_time_with_filter(self, composite_index):
        """Test query_entities_at_time with entity filter (line 181)."""
        # Add entities at the same timestamp
        timestamp = datetime.now()
        entities = ["entity1", "entity2", "entity3", "entity4"]

        for entity in entities:
            await composite_index.insert(timestamp, entity)

        # Query with entity filter
        entity_filter = {"entity1", "entity3"}
        result = await composite_index.query_entities_at_time(timestamp, entity_filter)

        # Verify only filtered entities returned
        assert set(result) == entity_filter

    @pytest.mark.asyncio
    async def test_query_entity_time_range_with_results(self, composite_index):
        """Test query_entity_time_range with entities that have results (line 213)."""
        # Add data for multiple entities
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)
        entities = ["entity1", "entity2", "entity3"]

        # Add timestamps for each entity
        for i, entity in enumerate(entities):
            timestamp = start_time + timedelta(minutes=30 * i)
            await composite_index.insert(timestamp, entity)

        # Query entity time range
        result = await composite_index.query_entity_time_range(
            entities,
            start_time - timedelta(minutes=10),
            end_time + timedelta(minutes=10),
        )

        # Verify results for entities with data
        assert len(result) == 3
        for entity in entities:
            assert entity in result
            assert len(result[entity]) > 0

    @pytest.mark.asyncio
    async def test_get_entity_statistics_nonexistent_entity(self, composite_index):
        """Test get_entity_statistics for nonexistent entity (line 293)."""
        # Query statistics for nonexistent entity
        result = composite_index.get_entity_statistics("nonexistent_entity")

        # Verify None returned
        assert result is None

    @pytest.mark.asyncio
    async def test_rebuild_with_existing_data(self, composite_index):
        """Test rebuild functionality with existing data (line 376)."""
        # Add some data first
        entities = ["entity1", "entity2"]
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(3)]

        for entity in entities:
            for timestamp in timestamps:
                await composite_index.insert(timestamp, entity)

        # Store original data count
        original_count = composite_index.statistics.total_entries

        # Rebuild the index
        success = await composite_index.rebuild()

        # Verify rebuild succeeded
        assert success is True
        # Note: Rebuild clears data, so entries will be 0 after rebuild
        # This tests the rebuild functionality itself

    @pytest.mark.asyncio
    async def test_rebuild_exception_handling(self, composite_index):
        """Test rebuild exception handling."""
        # Mock _build_index to raise an exception
        with patch.object(
            composite_index, "_build_index", side_effect=Exception("Test error")
        ):
            with patch(
                "qdrant_loader.core.temporal_indexing.composite_index.logger"
            ) as mock_logger:
                # This should trigger exception handling
                success = await composite_index.rebuild()

                # Verify error was logged and False returned
                mock_logger.error.assert_called()
                assert success is False
                assert composite_index.status == IndexStatus.ERROR

    @pytest.mark.asyncio
    async def test_inactive_index_operations(self, composite_index):
        """Test operations on inactive index return appropriate defaults."""
        # Set index to inactive
        composite_index.status = IndexStatus.ERROR

        # Test various operations
        assert await composite_index.insert(datetime.now(), "entity") is False
        assert await composite_index.query_entity_timeline("entity") == []
        assert await composite_index.query_entities_at_time(datetime.now()) == []
        assert (
            await composite_index.query_entity_time_range(
                ["entity"], datetime.now(), datetime.now()
            )
            == {}
        )
        assert (
            await composite_index.find_temporal_neighbors("entity", datetime.now())
            == []
        )

    @pytest.mark.asyncio
    async def test_memory_usage_calculation(self, composite_index):
        """Test memory usage calculation with multiple entities."""
        # Add data for multiple entities
        entities = ["entity1", "entity2", "entity3"]
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(3)]

        for entity in entities:
            for timestamp in timestamps:
                await composite_index.insert(timestamp, entity)

        # Calculate memory usage
        memory_usage = composite_index.get_memory_usage()

        # Verify memory usage is calculated
        assert memory_usage > 0
        assert isinstance(memory_usage, int)

    @pytest.mark.asyncio
    async def test_statistics_update_during_operations(self, composite_index):
        """Test that statistics are properly updated during operations."""
        # Perform various operations
        timestamp = datetime.now()
        entity = "test_entity"

        # Insert operation
        await composite_index.insert(timestamp, entity)
        assert composite_index.statistics.total_entries == 1

        # Query operations
        await composite_index.query_entity_timeline(entity)
        await composite_index.query_entities_at_time(timestamp)
        await composite_index.query_entity_time_range([entity], timestamp, timestamp)

        # Verify query statistics updated
        assert composite_index.statistics.total_queries > 0
        assert composite_index.statistics.average_query_time_ms >= 0

    @pytest.mark.asyncio
    async def test_complex_temporal_neighbor_search(self, composite_index):
        """Test complex temporal neighbor search scenarios."""
        # Create a complex scenario with multiple entities at different times
        base_time = datetime.now()
        entities_data = [
            ("entity1", base_time),
            ("entity2", base_time + timedelta(minutes=10)),
            ("entity3", base_time + timedelta(minutes=20)),
            ("entity4", base_time + timedelta(minutes=30)),
            ("entity5", base_time + timedelta(hours=2)),  # Outside window
        ]

        for entity, timestamp in entities_data:
            await composite_index.insert(timestamp, entity)

        # Find neighbors within 1 hour window
        neighbors = await composite_index.find_temporal_neighbors(
            "entity1", base_time, 3600
        )

        # Verify neighbors found and sorted by distance
        assert len(neighbors) == 3  # entity2, entity3, entity4 (entity5 outside window)

        # Verify sorting by distance
        distances = [neighbor[2] for neighbor in neighbors]
        assert distances == sorted(distances)

        # Verify entity1 is not in its own neighbors
        neighbor_entities = [neighbor[0] for neighbor in neighbors]
        assert "entity1" not in neighbor_entities
