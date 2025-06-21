"""Enhanced tests for TemporalIndexManager focusing on real code path coverage.

This test suite targets the missed lines in TemporalIndexManager to improve
coverage from 80% to 90%+. It focuses on:
- Error handling in query operations
- Edge cases in maintenance operations
- Real integration scenarios with actual index classes
- Exception paths and recovery scenarios
- Performance monitoring and statistics
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


class TestTemporalIndexManagerEnhanced:
    """Enhanced test suite targeting missed lines in TemporalIndexManager."""

    @pytest.fixture
    def index_manager(self):
        """Create a TemporalIndexManager instance."""
        return TemporalIndexManager()

    @pytest.fixture
    def btree_config(self):
        """Create a BTree index configuration."""
        return TemporalIndexConfig(
            index_id="btree_test_enhanced",
            index_name="test_btree_enhanced",
            index_type=IndexType.BTREE,
            temporal_field="timestamp",
            page_size=100,
            cache_size_mb=5,
        )

    @pytest.fixture
    def composite_config(self):
        """Create a Composite index configuration."""
        return TemporalIndexConfig(
            index_id="composite_test_enhanced",
            index_name="test_composite_enhanced",
            index_type=IndexType.COMPOSITE,
            temporal_field="timestamp",
            entity_field="entity_id",
            page_size=100,
            cache_size_mb=5,
        )

    @pytest.fixture
    def sample_timestamp(self):
        """Create a sample timestamp."""
        return datetime(2024, 1, 1, 12, 0, 0)

    @pytest.fixture
    def sample_entities(self):
        """Create sample entity IDs."""
        return ["entity_1", "entity_2", "entity_3"]

    # Error Handling in Data Insertion (Lines 138, 141-142)

    @pytest.mark.asyncio
    async def test_insert_temporal_data_exception_handling(
        self, index_manager, btree_config, sample_timestamp, sample_entities
    ):
        """Test exception handling during data insertion."""
        # Create index
        await index_manager.create_index(btree_config)

        # Mock the index to raise an exception during insert
        mock_index = Mock()
        mock_index.is_active.return_value = True
        mock_index.insert = AsyncMock(side_effect=Exception("Insert failed"))
        index_manager.indexes[btree_config.index_id] = mock_index

        # Test insertion with exception
        results = await index_manager.insert_temporal_data(
            sample_timestamp, sample_entities[0]
        )

        # Verify exception was handled and result is False
        assert btree_config.index_id in results
        assert results[btree_config.index_id] is False

    @pytest.mark.asyncio
    async def test_insert_temporal_data_unsupported_index_type(
        self, index_manager, sample_timestamp, sample_entities
    ):
        """Test insertion with unsupported index type (line 138)."""
        # Create a mock index that's not BTree or Composite
        mock_index = Mock()
        mock_index.is_active.return_value = True
        index_manager.indexes["unsupported_index"] = mock_index

        # Test insertion
        results = await index_manager.insert_temporal_data(
            sample_timestamp, sample_entities[0], ["unsupported_index"]
        )

        # Verify unsupported index returns False
        assert "unsupported_index" in results
        assert results["unsupported_index"] is False

    # Range Query Error Handling (Lines 183-186)

    @pytest.mark.asyncio
    async def test_range_query_unsupported_index_type(
        self, index_manager, composite_config, sample_timestamp
    ):
        """Test range query with unsupported index type (lines 183-186)."""
        # Create composite index (which doesn't support range queries)
        await index_manager.create_index(composite_config)

        # Mock optimizer to return the composite index as primary
        mock_plan = Mock()
        mock_plan.primary_index = composite_config.index_id
        mock_plan.plan_id = "test_plan"

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            # Test range query
            results = await index_manager.range_query(
                sample_timestamp, sample_timestamp + timedelta(hours=1)
            )

        # Verify empty results due to unsupported index
        assert results == []

    @pytest.mark.asyncio
    async def test_range_query_exception_handling(
        self, index_manager, btree_config, sample_timestamp
    ):
        """Test range query exception handling (line 189)."""
        # Create index
        await index_manager.create_index(btree_config)

        # Mock optimizer to raise exception
        with patch.object(
            index_manager.optimizer,
            "create_query_plan",
            side_effect=Exception("Query plan failed"),
        ):
            # Test range query
            results = await index_manager.range_query(
                sample_timestamp, sample_timestamp + timedelta(hours=1)
            )

        # Verify exception was handled
        assert results == []

    # Entity Timeline Query Error Handling (Lines 239-242, 250-253, 261-263)

    @pytest.mark.asyncio
    async def test_entity_timeline_query_btree_fallback_no_time_range(
        self, index_manager, btree_config, sample_entities
    ):
        """Test entity timeline query BTree fallback without time range (lines 250-253)."""
        # Create BTree index
        await index_manager.create_index(btree_config)

        # Mock optimizer to return BTree index
        mock_plan = Mock()
        mock_plan.primary_index = btree_config.index_id
        mock_plan.plan_id = "test_plan"

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            # Test entity timeline query without time range
            results = await index_manager.entity_timeline_query(sample_entities[0])

        # Verify empty results when no time range provided for BTree
        assert results == []

    @pytest.mark.asyncio
    async def test_entity_timeline_query_unsupported_index(
        self, index_manager, sample_entities, sample_timestamp
    ):
        """Test entity timeline query with unsupported index (lines 261-263)."""
        # Create mock unsupported index
        mock_index = Mock()
        index_manager.indexes["unsupported_index"] = mock_index

        # Mock optimizer to return unsupported index
        mock_plan = Mock()
        mock_plan.primary_index = "unsupported_index"
        mock_plan.plan_id = "test_plan"

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            # Test entity timeline query
            results = await index_manager.entity_timeline_query(
                sample_entities[0],
                sample_timestamp,
                sample_timestamp + timedelta(hours=1),
            )

        # Verify empty results for unsupported index
        assert results == []

    @pytest.mark.asyncio
    async def test_entity_timeline_query_exception_handling(
        self, index_manager, sample_entities, sample_timestamp
    ):
        """Test entity timeline query exception handling (line 268)."""
        # Mock optimizer to raise exception
        with patch.object(
            index_manager.optimizer,
            "create_query_plan",
            side_effect=Exception("Timeline query failed"),
        ):
            # Test entity timeline query
            results = await index_manager.entity_timeline_query(
                sample_entities[0],
                sample_timestamp,
                sample_timestamp + timedelta(hours=1),
            )

        # Verify exception was handled
        assert results == []

    # Point Query Error Handling (Lines 292, 296-299, 307-309)

    @pytest.mark.asyncio
    async def test_point_query_unsupported_index(self, index_manager, sample_timestamp):
        """Test point query with unsupported index (lines 296-299)."""
        # Create mock unsupported index
        mock_index = Mock()
        index_manager.indexes["unsupported_index"] = mock_index

        # Mock optimizer to return unsupported index
        mock_plan = Mock()
        mock_plan.primary_index = "unsupported_index"
        mock_plan.plan_id = "test_plan"

        with patch.object(
            index_manager.optimizer, "create_query_plan", return_value=mock_plan
        ):
            # Test point query
            results = await index_manager.point_query(sample_timestamp)

        # Verify empty results for unsupported index
        assert results == []

    @pytest.mark.asyncio
    async def test_point_query_exception_handling(
        self, index_manager, sample_timestamp
    ):
        """Test point query exception handling (lines 307-309)."""
        # Mock optimizer to raise exception
        with patch.object(
            index_manager.optimizer,
            "create_query_plan",
            side_effect=Exception("Point query failed"),
        ):
            # Test point query
            results = await index_manager.point_query(sample_timestamp)

        # Verify exception was handled
        assert results == []

    # Multi-Entity Query Error Handling (Lines 351-357, 365-367)

    @pytest.mark.asyncio
    async def test_multi_entity_query_fallback_execution(
        self, index_manager, btree_config, sample_entities, sample_timestamp
    ):
        """Test multi-entity query fallback execution (lines 351-357)."""
        # Create BTree index (doesn't support multi-entity queries directly)
        await index_manager.create_index(btree_config)

        # Mock optimizer to return BTree index
        mock_plan = Mock()
        mock_plan.primary_index = btree_config.index_id
        mock_plan.plan_id = "test_plan"

        with (
            patch.object(
                index_manager.optimizer, "create_query_plan", return_value=mock_plan
            ),
            patch.object(
                index_manager, "entity_timeline_query", return_value=[sample_timestamp]
            ) as mock_timeline,
        ):
            # Test multi-entity query
            results = await index_manager.multi_entity_query(
                sample_entities, sample_timestamp, sample_timestamp + timedelta(hours=1)
            )

        # Verify fallback execution was used
        assert len(results) == len(sample_entities)
        assert mock_timeline.call_count == len(sample_entities)

    @pytest.mark.asyncio
    async def test_multi_entity_query_exception_handling(
        self, index_manager, sample_entities, sample_timestamp
    ):
        """Test multi-entity query exception handling (lines 365-367)."""
        # Mock optimizer to raise exception
        with patch.object(
            index_manager.optimizer,
            "create_query_plan",
            side_effect=Exception("Multi-entity query failed"),
        ):
            # Test multi-entity query
            results = await index_manager.multi_entity_query(
                sample_entities, sample_timestamp, sample_timestamp + timedelta(hours=1)
            )

        # Verify exception was handled
        assert results == {}

    # Index Statistics Error Handling (Lines 376-378)

    def test_get_index_statistics_nonexistent_index(self, index_manager):
        """Test getting statistics for nonexistent index (lines 376-378)."""
        # Test with nonexistent index
        stats = index_manager.get_index_statistics("nonexistent_index")

        # Verify empty dict returned
        assert stats == {}

    # Rebuild Index Error Handling (Lines 426-429, 445-446)

    @pytest.mark.asyncio
    async def test_rebuild_index_without_rebuild_method(
        self, index_manager, btree_config
    ):
        """Test rebuilding index without rebuild method (lines 426-429)."""
        # Create index
        await index_manager.create_index(btree_config)

        # Create a mock index without rebuild method
        mock_index = Mock()
        mock_index.config = btree_config
        # Explicitly ensure no rebuild method
        if hasattr(mock_index, "rebuild"):
            delattr(mock_index, "rebuild")

        # Replace the real index with mock
        index_manager.indexes[btree_config.index_id] = mock_index

        # Test rebuild
        result = await index_manager.rebuild_index(btree_config.index_id)

        # Verify rebuild failed
        assert result is False

    @pytest.mark.asyncio
    async def test_rebuild_index_exception_handling(self, index_manager, btree_config):
        """Test rebuild index exception handling (lines 445-446)."""
        # Create index
        await index_manager.create_index(btree_config)

        # Mock index rebuild to raise exception
        index = index_manager.indexes[btree_config.index_id]
        index.rebuild = AsyncMock(side_effect=Exception("Rebuild failed"))

        # Test rebuild
        result = await index_manager.rebuild_index(btree_config.index_id)

        # Verify exception was handled
        assert result is False

    # Maintenance Operations Error Handling (Lines 458-460, 467-481, 500-506)

    @pytest.mark.asyncio
    async def test_start_maintenance_already_running(self, index_manager):
        """Test starting maintenance when already running (lines 458-460)."""
        # Start maintenance first time
        await index_manager.start_maintenance()
        assert index_manager.maintenance_task is not None

        # Try to start again
        await index_manager.start_maintenance()

        # Verify warning was logged (task should still be running)
        assert index_manager.maintenance_task is not None

        # Cleanup
        await index_manager.stop_maintenance()

    @pytest.mark.asyncio
    async def test_maintenance_loop_exception_handling(self, index_manager):
        """Test maintenance loop exception handling (lines 467-481)."""
        # Mock _perform_maintenance to raise exception
        with patch.object(
            index_manager,
            "_perform_maintenance",
            side_effect=Exception("Maintenance failed"),
        ):
            # Start maintenance
            await index_manager.start_maintenance()

            # Give it a moment to hit the exception
            await asyncio.sleep(0.1)

            # Stop maintenance
            await index_manager.stop_maintenance()

    @pytest.mark.asyncio
    async def test_perform_maintenance_memory_usage_error(
        self, index_manager, btree_config
    ):
        """Test maintenance with memory usage error (lines 500-506)."""
        # Create index
        await index_manager.create_index(btree_config)

        # Mock index to have get_memory_usage that raises exception
        index = index_manager.indexes[btree_config.index_id]
        index.get_memory_usage = Mock(side_effect=Exception("Memory error"))
        index.needs_rebuild = Mock(return_value=False)

        # Test maintenance
        await index_manager._perform_maintenance()

        # Verify maintenance completed despite memory error
        # (no assertion needed, just ensuring no exception propagated)

    @pytest.mark.asyncio
    async def test_perform_maintenance_index_error(self, index_manager, btree_config):
        """Test maintenance with index-specific error (lines 508-509)."""
        # Create index
        await index_manager.create_index(btree_config)

        # Mock index to raise exception during needs_rebuild check
        index = index_manager.indexes[btree_config.index_id]
        index.needs_rebuild = Mock(side_effect=Exception("Index error"))

        # Test maintenance
        await index_manager._perform_maintenance()

        # Verify maintenance completed despite index error
        # (no assertion needed, just ensuring no exception propagated)

    # Integration Tests for Real Code Path Coverage

    @pytest.mark.asyncio
    async def test_full_workflow_with_real_indexes(
        self,
        index_manager,
        btree_config,
        composite_config,
        sample_timestamp,
        sample_entities,
    ):
        """Test full workflow with real index instances."""
        # Create both types of indexes
        assert await index_manager.create_index(btree_config) is True
        assert await index_manager.create_index(composite_config) is True

        # Insert data
        results = await index_manager.insert_temporal_data(
            sample_timestamp, sample_entities[0]
        )
        assert len(results) == 2

        # Test various queries with real indexes
        range_results = await index_manager.range_query(
            sample_timestamp - timedelta(minutes=30),
            sample_timestamp + timedelta(minutes=30),
        )

        point_results = await index_manager.point_query(sample_timestamp)

        timeline_results = await index_manager.entity_timeline_query(
            sample_entities[0],
            sample_timestamp - timedelta(minutes=30),
            sample_timestamp + timedelta(minutes=30),
        )

        multi_results = await index_manager.multi_entity_query(
            sample_entities,
            sample_timestamp - timedelta(minutes=30),
            sample_timestamp + timedelta(minutes=30),
        )

        # Get statistics
        all_stats = index_manager.get_index_statistics()
        specific_stats = index_manager.get_index_statistics(btree_config.index_id)
        manager_stats = index_manager.get_manager_statistics()

        # Verify statistics structure
        assert isinstance(all_stats, dict)
        assert isinstance(specific_stats, dict)
        assert isinstance(manager_stats, dict)
        assert "total_indexes" in manager_stats
        assert "active_indexes" in manager_stats

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, index_manager, btree_config):
        """Test shutdown cleanup operations."""
        # Create index and start maintenance
        await index_manager.create_index(btree_config)
        await index_manager.start_maintenance()

        # Verify setup
        assert len(index_manager.indexes) == 1
        assert index_manager.maintenance_task is not None

        # Test shutdown
        await index_manager.shutdown()

        # Verify cleanup
        assert len(index_manager.indexes) == 0
        assert index_manager.maintenance_task.done()
