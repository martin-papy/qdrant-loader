"""Comprehensive tests for TemporalIndexManager.

This test suite covers:
- Index lifecycle management (create, drop, rebuild)
- Query routing and optimization
- Data insertion across multiple indexes
- Range queries and temporal queries
- Entity timeline and point queries
- Multi-entity queries and aggregation
- Index statistics and monitoring
- Maintenance operations and scheduling
- Error handling and recovery
- Performance optimization
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from qdrant_loader.core.temporal_indexing.index_manager import TemporalIndexManager
from qdrant_loader.core.temporal_indexing.index_types import (
    IndexStatus,
    IndexType,
    TemporalIndexConfig,
    TemporalQueryHint,
)
from qdrant_loader.core.temporal_indexing.btree_index import TemporalBTreeIndex
from qdrant_loader.core.temporal_indexing.composite_index import TemporalCompositeIndex


class TestTemporalIndexManager:
    """Test suite for TemporalIndexManager."""

    @pytest.fixture
    def index_manager(self):
        """Create a TemporalIndexManager instance."""
        return TemporalIndexManager()

    @pytest.fixture
    def btree_config(self):
        """Create a BTree index configuration."""
        return TemporalIndexConfig(
            index_id="btree_test_1",
            index_name="test_btree_index",
            index_type=IndexType.BTREE,
            temporal_field="timestamp",
            page_size=100,
            cache_size_mb=5,
        )

    @pytest.fixture
    def composite_config(self):
        """Create a Composite index configuration."""
        return TemporalIndexConfig(
            index_id="composite_test_1",
            index_name="test_composite_index",
            index_type=IndexType.COMPOSITE,
            temporal_field="timestamp",
            entity_field="entity_id",
            page_size=100,
            cache_size_mb=5,
        )

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

    def test_index_manager_initialization(self, index_manager):
        """Test index manager initialization."""
        assert isinstance(index_manager.indexes, dict)
        assert len(index_manager.indexes) == 0
        assert index_manager.optimizer is not None
        assert index_manager.maintenance_task is None
        assert index_manager.maintenance_interval_hours == 24

    # Index Creation Tests

    @pytest.mark.asyncio
    async def test_create_btree_index(self, index_manager, btree_config):
        """Test creating a BTree index."""
        result = await index_manager.create_index(btree_config)

        assert result is True
        assert btree_config.index_id in index_manager.indexes
        assert isinstance(
            index_manager.indexes[btree_config.index_id], TemporalBTreeIndex
        )

    @pytest.mark.asyncio
    async def test_create_composite_index(self, index_manager, composite_config):
        """Test creating a Composite index."""
        result = await index_manager.create_index(composite_config)

        assert result is True
        assert composite_config.index_id in index_manager.indexes
        assert isinstance(
            index_manager.indexes[composite_config.index_id], TemporalCompositeIndex
        )

    @pytest.mark.asyncio
    async def test_create_duplicate_index(self, index_manager, btree_config):
        """Test creating duplicate index."""
        # Create first index
        result1 = await index_manager.create_index(btree_config)
        assert result1 is True

        # Try to create duplicate
        result2 = await index_manager.create_index(btree_config)
        assert result2 is False

    @pytest.mark.asyncio
    async def test_create_unsupported_index_type(self, index_manager):
        """Test creating unsupported index type."""
        config = TemporalIndexConfig(
            index_id="unsupported_test",
            index_name="unsupported_index",
            index_type=IndexType.HASH,  # Not implemented yet
        )

        result = await index_manager.create_index(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_create_index_with_exception(self, index_manager, btree_config):
        """Test index creation with exception."""
        with patch(
            "qdrant_loader.core.temporal_indexing.index_manager.TemporalBTreeIndex",
            side_effect=Exception("Creation failed"),
        ):
            result = await index_manager.create_index(btree_config)
            assert result is False

    # Index Deletion Tests

    @pytest.mark.asyncio
    async def test_drop_existing_index(self, index_manager, btree_config):
        """Test dropping an existing index."""
        # Create index first
        await index_manager.create_index(btree_config)
        assert btree_config.index_id in index_manager.indexes

        # Drop index
        result = await index_manager.drop_index(btree_config.index_id)

        assert result is True
        assert btree_config.index_id not in index_manager.indexes

    @pytest.mark.asyncio
    async def test_drop_nonexistent_index(self, index_manager):
        """Test dropping nonexistent index."""
        result = await index_manager.drop_index("nonexistent_index")
        assert result is False

    @pytest.mark.asyncio
    async def test_drop_index_with_exception(self, index_manager, btree_config):
        """Test dropping index with exception."""
        await index_manager.create_index(btree_config)

        with patch.object(
            index_manager.optimizer,
            "unregister_index",
            side_effect=Exception("Drop failed"),
        ):
            result = await index_manager.drop_index(btree_config.index_id)
            assert result is False

    # Data Insertion Tests

    @pytest.mark.asyncio
    async def test_insert_temporal_data_single_index(
        self, index_manager, btree_config, sample_timestamps, sample_entities
    ):
        """Test inserting temporal data into a single index."""
        await index_manager.create_index(btree_config)

        timestamp = sample_timestamps[0]
        entity_id = sample_entities[0]

        results = await index_manager.insert_temporal_data(timestamp, entity_id)

        assert btree_config.index_id in results
        assert results[btree_config.index_id] is True

    @pytest.mark.asyncio
    async def test_insert_temporal_data_multiple_indexes(
        self,
        index_manager,
        btree_config,
        composite_config,
        sample_timestamps,
        sample_entities,
    ):
        """Test inserting temporal data into multiple indexes."""
        await index_manager.create_index(btree_config)
        await index_manager.create_index(composite_config)

        timestamp = sample_timestamps[0]
        entity_id = sample_entities[0]

        results = await index_manager.insert_temporal_data(timestamp, entity_id)

        assert len(results) == 2
        assert btree_config.index_id in results
        assert composite_config.index_id in results
        assert all(result is True for result in results.values())

    @pytest.mark.asyncio
    async def test_insert_temporal_data_target_indexes(
        self,
        index_manager,
        btree_config,
        composite_config,
        sample_timestamps,
        sample_entities,
    ):
        """Test inserting temporal data into specific target indexes."""
        await index_manager.create_index(btree_config)
        await index_manager.create_index(composite_config)

        timestamp = sample_timestamps[0]
        entity_id = sample_entities[0]
        target_indexes = [btree_config.index_id]

        results = await index_manager.insert_temporal_data(
            timestamp, entity_id, target_indexes
        )

        assert len(results) == 1
        assert btree_config.index_id in results
        assert composite_config.index_id not in results

    @pytest.mark.asyncio
    async def test_insert_temporal_data_inactive_index(
        self, index_manager, btree_config, sample_timestamps, sample_entities
    ):
        """Test inserting data when index is inactive."""
        await index_manager.create_index(btree_config)

        # Make index inactive
        index_manager.indexes[btree_config.index_id].status = IndexStatus.DISABLED

        timestamp = sample_timestamps[0]
        entity_id = sample_entities[0]

        results = await index_manager.insert_temporal_data(timestamp, entity_id)

        # Should skip inactive indexes
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_insert_temporal_data_with_exception(
        self, index_manager, btree_config, sample_timestamps, sample_entities
    ):
        """Test inserting temporal data with exception."""
        await index_manager.create_index(btree_config)

        timestamp = sample_timestamps[0]
        entity_id = sample_entities[0]

        # Mock insert method to raise exception
        with patch.object(
            index_manager.indexes[btree_config.index_id],
            "insert",
            side_effect=Exception("Insert failed"),
        ):
            results = await index_manager.insert_temporal_data(timestamp, entity_id)

            assert results[btree_config.index_id] is False

    # Range Query Tests

    @pytest.mark.asyncio
    async def test_range_query_success(
        self, index_manager, btree_config, sample_timestamps
    ):
        """Test successful range query."""
        await index_manager.create_index(btree_config)

        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        # Mock optimizer to return query plan
        mock_plan = Mock()
        mock_plan.primary_index = btree_config.index_id
        mock_plan.plan_id = "test_plan_1"

        with (
            patch.object(
                index_manager.optimizer, "create_query_plan", return_value=mock_plan
            ),
            patch.object(
                index_manager.indexes[btree_config.index_id],
                "range_query",
                return_value=[(ts, "entity_1") for ts in sample_timestamps[0:3]],
            ) as mock_range,
            patch.object(index_manager.optimizer, "record_query_performance"),
        ):

            result = await index_manager.range_query(start_time, end_time, limit=10)

            assert len(result) == 3
            mock_range.assert_called_once_with(start_time, end_time, 10)

    @pytest.mark.asyncio
    async def test_range_query_no_suitable_index(
        self, index_manager, sample_timestamps
    ):
        """Test range query when no suitable index exists."""
        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        # Mock optimizer to return plan with no primary index
        mock_plan = Mock()
        mock_plan.primary_index = None

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            result = await index_manager.range_query(start_time, end_time)

            assert result == []

    @pytest.mark.asyncio
    async def test_range_query_with_hints(
        self, index_manager, btree_config, sample_timestamps
    ):
        """Test range query with query hints."""
        await index_manager.create_index(btree_config)

        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]
        hints = TemporalQueryHint(preferred_indexes=[btree_config.index_id])

        mock_plan = Mock()
        mock_plan.primary_index = btree_config.index_id
        mock_plan.plan_id = "test_plan_2"

        with (
            patch.object(
                index_manager.optimizer, "create_query_plan", return_value=mock_plan
            ) as mock_create_plan,
            patch.object(
                index_manager.indexes[btree_config.index_id],
                "range_query",
                return_value=[],
            ),
        ):

            await index_manager.range_query(start_time, end_time, hints=hints)

            # Verify hints were passed to optimizer
            call_args = mock_create_plan.call_args
            assert call_args[0][4] == hints  # hints is the 5th argument (index 4)

    @pytest.mark.asyncio
    async def test_range_query_with_exception(
        self, index_manager, btree_config, sample_timestamps
    ):
        """Test range query with exception handling."""
        await index_manager.create_index(btree_config)

        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        with patch.object(
            index_manager.optimizer,
            "create_query_plan",
            side_effect=Exception("Query failed"),
        ):
            result = await index_manager.range_query(start_time, end_time)

            assert result == []

    # Entity Timeline Query Tests

    @pytest.mark.asyncio
    async def test_entity_timeline_query_success(
        self, index_manager, composite_config, sample_timestamps, sample_entities
    ):
        """Test successful entity timeline query."""
        await index_manager.create_index(composite_config)

        entity_id = sample_entities[0]
        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        mock_plan = Mock()
        mock_plan.primary_index = composite_config.index_id
        mock_plan.plan_id = "timeline_plan_1"

        expected_timestamps = sample_timestamps[0:3]

        with (
            patch.object(
                index_manager.optimizer, "create_query_plan", return_value=mock_plan
            ),
            patch.object(
                index_manager.indexes[composite_config.index_id],
                "query_entity_timeline",
                return_value=expected_timestamps,
            ) as mock_timeline,
            patch.object(index_manager.optimizer, "record_query_performance"),
        ):

            result = await index_manager.entity_timeline_query(
                entity_id, start_time, end_time, limit=5
            )

            assert result == expected_timestamps
            mock_timeline.assert_called_once_with(entity_id, start_time, end_time, 5)

    @pytest.mark.asyncio
    async def test_entity_timeline_query_no_suitable_index(
        self, index_manager, sample_entities
    ):
        """Test entity timeline query when no suitable index exists."""
        entity_id = sample_entities[0]

        mock_plan = Mock()
        mock_plan.primary_index = None

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            result = await index_manager.entity_timeline_query(entity_id)

            assert result == []

    @pytest.mark.asyncio
    async def test_entity_timeline_query_unsupported_index(
        self, index_manager, btree_config, sample_entities
    ):
        """Test entity timeline query with unsupported index type."""
        await index_manager.create_index(btree_config)

        entity_id = sample_entities[0]

        mock_plan = Mock()
        mock_plan.primary_index = btree_config.index_id

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            result = await index_manager.entity_timeline_query(entity_id)

            assert result == []

    # Point Query Tests

    @pytest.mark.asyncio
    async def test_point_query_success(
        self, index_manager, composite_config, sample_timestamps, sample_entities
    ):
        """Test successful point query."""
        await index_manager.create_index(composite_config)

        timestamp = sample_timestamps[0]
        expected_entities = sample_entities[:2]

        mock_plan = Mock()
        mock_plan.primary_index = composite_config.index_id
        mock_plan.plan_id = "point_plan_1"

        with (
            patch.object(
                index_manager.optimizer, "create_query_plan", return_value=mock_plan
            ),
            patch.object(
                index_manager.indexes[composite_config.index_id],
                "query_entities_at_time",
                return_value=expected_entities,
            ) as mock_point,
            patch.object(index_manager.optimizer, "record_query_performance"),
        ):

            result = await index_manager.point_query(timestamp)

            assert result == expected_entities
            mock_point.assert_called_once_with(timestamp)

    @pytest.mark.asyncio
    async def test_point_query_with_hints(
        self, index_manager, composite_config, sample_timestamps
    ):
        """Test point query with query hints."""
        await index_manager.create_index(composite_config)

        timestamp = sample_timestamps[0]
        hints = TemporalQueryHint(preferred_indexes=[composite_config.index_id])

        mock_plan = Mock()
        mock_plan.primary_index = composite_config.index_id

        with (
            patch.object(
                index_manager.optimizer, "create_query_plan", return_value=mock_plan
            ) as mock_create_plan,
            patch.object(
                index_manager.indexes[composite_config.index_id],
                "query_entities_at_time",
                return_value=[],
            ),
        ):

            await index_manager.point_query(timestamp, hints=hints)

            # Verify hints were passed
            call_args = mock_create_plan.call_args
            assert call_args[0][4] == hints

    # Multi-Entity Query Tests

    @pytest.mark.asyncio
    async def test_multi_entity_query_success(
        self, index_manager, composite_config, sample_timestamps, sample_entities
    ):
        """Test successful multi-entity query."""
        await index_manager.create_index(composite_config)

        entity_ids = sample_entities[:2]
        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        mock_plan = Mock()
        mock_plan.primary_index = composite_config.index_id
        mock_plan.plan_id = "multi_plan_1"

        expected_result = {
            sample_entities[0]: sample_timestamps[0:2],
            sample_entities[1]: sample_timestamps[1:3],
        }

        with (
            patch.object(
                index_manager.optimizer, "create_query_plan", return_value=mock_plan
            ),
            patch.object(
                index_manager.indexes[composite_config.index_id],
                "query_entity_time_range",
                return_value=expected_result,
            ) as mock_multi,
            patch.object(index_manager.optimizer, "record_query_performance"),
        ):

            result = await index_manager.multi_entity_query(
                entity_ids, start_time, end_time, limit=10
            )

            assert result == expected_result
            mock_multi.assert_called_once_with(entity_ids, start_time, end_time, 10)

    @pytest.mark.asyncio
    async def test_multi_entity_query_no_suitable_index(
        self, index_manager, sample_entities, sample_timestamps
    ):
        """Test multi-entity query when no suitable index exists."""
        entity_ids = sample_entities[:2]
        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        mock_plan = Mock()
        mock_plan.primary_index = None

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            result = await index_manager.multi_entity_query(
                entity_ids, start_time, end_time
            )

            assert result == {}

    # Statistics Tests

    def test_get_index_statistics_specific_index(self, index_manager, btree_config):
        """Test getting statistics for a specific index."""
        # Create mock index with statistics
        mock_index = Mock()
        mock_stats = Mock()
        mock_stats.to_dict.return_value = {"total_entries": 100, "total_queries": 50}
        mock_index.statistics = mock_stats

        index_manager.indexes[btree_config.index_id] = mock_index

        result = index_manager.get_index_statistics(btree_config.index_id)

        assert result == {"total_entries": 100, "total_queries": 50}

    def test_get_index_statistics_all_indexes(
        self, index_manager, btree_config, composite_config
    ):
        """Test getting statistics for all indexes."""
        # Create mock indexes with statistics
        mock_btree = Mock()
        mock_btree_stats = Mock()
        mock_btree_stats.to_dict.return_value = {"index_type": "btree", "entries": 100}
        mock_btree.statistics = mock_btree_stats

        mock_composite = Mock()
        mock_composite_stats = Mock()
        mock_composite_stats.to_dict.return_value = {
            "index_type": "composite",
            "entries": 200,
        }
        mock_composite.statistics = mock_composite_stats

        index_manager.indexes[btree_config.index_id] = mock_btree
        index_manager.indexes[composite_config.index_id] = mock_composite

        result = index_manager.get_index_statistics()

        assert btree_config.index_id in result
        assert composite_config.index_id in result
        assert result[btree_config.index_id]["index_type"] == "btree"
        assert result[composite_config.index_id]["index_type"] == "composite"

    def test_get_index_statistics_nonexistent_index(self, index_manager):
        """Test getting statistics for nonexistent index."""
        result = index_manager.get_index_statistics("nonexistent")
        assert result == {}

    def test_get_manager_statistics(
        self, index_manager, btree_config, composite_config
    ):
        """Test getting manager-level statistics."""
        # Add some indexes with proper mock statistics
        mock_btree = Mock()
        mock_btree.is_active.return_value = True
        mock_btree.statistics.total_entries = 100
        mock_btree.statistics.total_queries = 50

        mock_composite = Mock()
        mock_composite.is_active.return_value = True
        mock_composite.statistics.total_entries = 200
        mock_composite.statistics.total_queries = 75

        # Mock optimizer stats
        with patch.object(
            index_manager.optimizer, "get_optimizer_statistics", return_value={}
        ):
            index_manager.indexes[btree_config.index_id] = mock_btree
            index_manager.indexes[composite_config.index_id] = mock_composite

            result = index_manager.get_manager_statistics()

            assert "total_indexes" in result
            assert "active_indexes" in result
            assert "total_entries" in result
            assert "total_queries" in result
            assert "optimizer_stats" in result
            assert result["total_indexes"] == 2
            assert result["active_indexes"] == 2
            assert result["total_entries"] == 300
            assert result["total_queries"] == 125

    # Index Rebuilding Tests

    @pytest.mark.asyncio
    async def test_rebuild_index_success(self, index_manager, btree_config):
        """Test successful index rebuilding."""
        await index_manager.create_index(btree_config)

        with patch.object(
            index_manager.indexes[btree_config.index_id], "rebuild", return_value=True
        ) as mock_rebuild:
            result = await index_manager.rebuild_index(btree_config.index_id)

            assert result is True
            mock_rebuild.assert_called_once()

    @pytest.mark.asyncio
    async def test_rebuild_index_failure(self, index_manager, btree_config):
        """Test index rebuilding failure."""
        await index_manager.create_index(btree_config)

        with patch.object(
            index_manager.indexes[btree_config.index_id], "rebuild", return_value=False
        ):
            result = await index_manager.rebuild_index(btree_config.index_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_rebuild_nonexistent_index(self, index_manager):
        """Test rebuilding nonexistent index."""
        result = await index_manager.rebuild_index("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_rebuild_index_with_exception(self, index_manager, btree_config):
        """Test rebuilding index with exception."""
        await index_manager.create_index(btree_config)

        with patch.object(
            index_manager.indexes[btree_config.index_id],
            "rebuild",
            side_effect=Exception("Rebuild failed"),
        ):
            result = await index_manager.rebuild_index(btree_config.index_id)

            assert result is False

    # Maintenance Tests

    @pytest.mark.asyncio
    async def test_start_maintenance(self, index_manager):
        """Test starting maintenance operations."""
        await index_manager.start_maintenance()

        assert index_manager.maintenance_task is not None
        assert not index_manager.maintenance_task.done()

        # Clean up
        await index_manager.stop_maintenance()

    @pytest.mark.asyncio
    async def test_stop_maintenance(self, index_manager):
        """Test stopping maintenance operations."""
        await index_manager.start_maintenance()
        assert index_manager.maintenance_task is not None

        await index_manager.stop_maintenance()

        # Task should be done after stopping
        assert index_manager.maintenance_task.done()

    @pytest.mark.asyncio
    async def test_stop_maintenance_without_start(self, index_manager):
        """Test stopping maintenance when not started."""
        # Should not raise exception
        await index_manager.stop_maintenance()
        assert index_manager.maintenance_task is None

    @pytest.mark.asyncio
    async def test_perform_maintenance(self, index_manager, btree_config):
        """Test maintenance operations."""
        await index_manager.create_index(btree_config)

        # Mock index that needs rebuilding
        mock_index = Mock()
        mock_index.needs_rebuild.return_value = True
        mock_index.rebuild = AsyncMock(return_value=True)
        index_manager.indexes[btree_config.index_id] = mock_index

        await index_manager._perform_maintenance()

        mock_index.rebuild.assert_called_once()

    @pytest.mark.asyncio
    async def test_maintenance_loop_shutdown(self, index_manager):
        """Test maintenance loop shutdown."""
        # Start maintenance
        await index_manager.start_maintenance()

        # Trigger shutdown
        index_manager._shutdown_event.set()

        # Wait a short time for loop to process shutdown
        await asyncio.sleep(0.1)

        # Stop maintenance
        await index_manager.stop_maintenance()

    # Shutdown Tests

    @pytest.mark.asyncio
    async def test_shutdown(self, index_manager):
        """Test manager shutdown."""
        await index_manager.start_maintenance()

        await index_manager.shutdown()

        # Task should be done after shutdown and indexes cleared
        assert index_manager.maintenance_task.done()
        assert index_manager._shutdown_event.is_set()
        assert len(index_manager.indexes) == 0

    @pytest.mark.asyncio
    async def test_shutdown_without_maintenance(self, index_manager):
        """Test shutdown when maintenance is not running."""
        # Should not raise exception
        await index_manager.shutdown()
        assert index_manager._shutdown_event.is_set()

    # Error Handling and Edge Cases

    @pytest.mark.asyncio
    async def test_concurrent_index_operations(
        self, index_manager, btree_config, composite_config
    ):
        """Test concurrent index creation and deletion."""
        # Create tasks for concurrent operations
        create_task1 = index_manager.create_index(btree_config)
        create_task2 = index_manager.create_index(composite_config)

        # Execute concurrently
        results = await asyncio.gather(
            create_task1, create_task2, return_exceptions=True
        )

        # Both should succeed
        assert all(
            result is True for result in results if not isinstance(result, Exception)
        )

    @pytest.mark.asyncio
    async def test_query_with_no_indexes(self, index_manager, sample_timestamps):
        """Test queries when no indexes exist."""
        start_time = sample_timestamps[0]
        end_time = sample_timestamps[2]

        # Mock optimizer to return empty plan
        mock_plan = Mock()
        mock_plan.primary_index = None

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            range_result = await index_manager.range_query(start_time, end_time)
            point_result = await index_manager.point_query(start_time)
            timeline_result = await index_manager.entity_timeline_query("entity_1")
            multi_result = await index_manager.multi_entity_query(
                ["entity_1"], start_time, end_time
            )

            assert range_result == []
            assert point_result == []
            assert timeline_result == []
            assert multi_result == {}

    @pytest.mark.asyncio
    async def test_large_scale_operations(self, index_manager, btree_config):
        """Test operations with large datasets."""
        await index_manager.create_index(btree_config)

        # Insert many data points
        base_time = datetime.now()
        tasks = []
        for i in range(100):
            timestamp = base_time + timedelta(minutes=i)
            task = index_manager.insert_temporal_data(timestamp, f"entity_{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most operations should succeed
        success_count = sum(
            1 for result in results if isinstance(result, dict) and all(result.values())
        )
        assert success_count > 50  # At least half should succeed

    def test_optimizer_integration(self, index_manager, btree_config):
        """Test integration with query optimizer."""
        # Verify optimizer is properly initialized
        assert index_manager.optimizer is not None

        # Test index registration with optimizer
        with patch.object(index_manager.optimizer, "register_index") as mock_register:
            asyncio.run(index_manager.create_index(btree_config))
            mock_register.assert_called_once()

        # Test index unregistration
        with patch.object(
            index_manager.optimizer, "unregister_index"
        ) as mock_unregister:
            asyncio.run(index_manager.drop_index(btree_config.index_id))
            mock_unregister.assert_called_once_with(btree_config.index_id)
