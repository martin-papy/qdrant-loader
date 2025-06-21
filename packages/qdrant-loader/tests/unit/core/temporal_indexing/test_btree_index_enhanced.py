"""Enhanced tests for temporal B-tree index implementation focusing on error handling and edge cases."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from qdrant_loader.core.temporal_indexing.btree_index import (
    TemporalBTreeIndex,
    TemporalBTreeNode,
)
from qdrant_loader.core.temporal_indexing.index_types import (
    IndexStatus,
    IndexType,
    TemporalIndexConfig,
)


class TestTemporalBTreeIndexErrorHandling:
    """Test error handling and edge cases in TemporalBTreeIndex."""

    @pytest.fixture
    def index_config(self):
        """Create a test index configuration."""
        return TemporalIndexConfig(
            index_name="test_btree_error_index",
            index_type=IndexType.BTREE,
            temporal_field="timestamp",
            page_size=50,
            cache_size_mb=5,
        )

    @pytest.fixture
    def btree_index(self, index_config):
        """Create a TemporalBTreeIndex instance."""
        return TemporalBTreeIndex(index_config)

    def test_build_index_exception_handling(self, index_config):
        """Test exception handling during index building."""
        with patch.object(
            TemporalBTreeNode, "__init__", side_effect=Exception("Build failed")
        ):
            index = TemporalBTreeIndex(index_config)

            # Should have set status to ERROR due to build failure
            assert index.status == IndexStatus.ERROR

    @pytest.mark.asyncio
    async def test_range_query_with_internal_exception(self, btree_index):
        """Test range query with internal processing exception."""
        # First insert some data
        timestamp = datetime.now()
        await btree_index.insert(timestamp, "entity_1")

        # Mock _range_search to raise an exception
        with patch.object(
            btree_index, "_range_search", side_effect=Exception("Internal error")
        ):
            start_time = timestamp - timedelta(hours=1)
            end_time = timestamp + timedelta(hours=1)

            result = await btree_index.range_query(start_time, end_time)

            # Should return empty list on exception
            assert result == []

    @pytest.mark.asyncio
    async def test_point_query_with_internal_exception(self, btree_index):
        """Test point query with internal processing exception."""
        # First insert some data
        timestamp = datetime.now()
        await btree_index.insert(timestamp, "entity_1")

        # Mock _point_search to raise an exception
        with patch.object(
            btree_index, "_point_search", side_effect=Exception("Search error")
        ):
            result = await btree_index.point_query(timestamp)

            # Should return empty list on exception
            assert result == []

    @pytest.mark.asyncio
    async def test_insert_with_statistics_update_edge_cases(self, btree_index):
        """Test insert with edge cases in statistics updates."""
        timestamp = datetime.now()

        # Test first insert (total_queries == 0 case)
        result = await btree_index.insert(timestamp, "entity_1")
        assert result is True
        assert btree_index.statistics.total_entries == 1

        # Test subsequent insert (running average case)
        result = await btree_index.insert(timestamp + timedelta(seconds=1), "entity_2")
        assert result is True
        assert btree_index.statistics.total_entries == 2

    @pytest.mark.asyncio
    async def test_rebuild_with_existing_data(self, btree_index):
        """Test rebuild functionality with existing data."""
        # Insert some test data
        base_time = datetime.now()
        for i in range(5):
            timestamp = base_time + timedelta(hours=i)
            await btree_index.insert(timestamp, f"entity_{i}")

        # Verify data exists
        assert btree_index.statistics.total_entries == 5

        # Rebuild the index
        result = await btree_index.rebuild()
        assert result is True
        assert btree_index.statistics.maintenance_operations == 1
        assert btree_index.statistics.last_rebuild is not None
        assert btree_index.statistics.fragmentation_ratio == 0.0

    @pytest.mark.asyncio
    async def test_rebuild_with_exception_during_rebuild(self, btree_index):
        """Test rebuild with exception during the rebuild process."""
        # Insert some test data
        timestamp = datetime.now()
        await btree_index.insert(timestamp, "entity_1")

        # Mock _build_index to raise an exception during rebuild
        with patch.object(
            btree_index, "_build_index", side_effect=Exception("Rebuild failed")
        ):
            result = await btree_index.rebuild()

            assert result is False
            assert btree_index.status == IndexStatus.ERROR

    def test_extract_all_data_empty_index(self, btree_index):
        """Test extracting data from empty index."""
        # Clear the root to simulate empty index
        btree_index.root = None

        data = btree_index._extract_all_data()
        assert data == []

    def test_get_memory_usage_empty_index(self, btree_index):
        """Test memory usage calculation for empty index."""
        # Clear the root to simulate empty index
        btree_index.root = None

        memory_usage = btree_index.get_memory_usage()
        assert memory_usage == 0

    def test_memory_calculation_with_complex_tree(self, btree_index):
        """Test memory calculation with a tree that has children."""
        # Create a more complex tree structure manually
        root = TemporalBTreeNode(is_leaf=False, max_keys=3)
        child1 = TemporalBTreeNode(is_leaf=True, max_keys=3)
        child2 = TemporalBTreeNode(is_leaf=True, max_keys=3)

        # Add data to children
        base_time = datetime.now()
        child1.keys = [base_time]
        child1.values = [["entity_1", "entity_2"]]

        child2.keys = [base_time + timedelta(hours=1)]
        child2.values = [["entity_3"]]

        # Set up parent-child relationships
        root.keys = [base_time + timedelta(minutes=30)]
        root.values = [["middle_entity"]]
        root.children = [child1, child2]

        btree_index.root = root

        # Calculate memory usage
        memory_usage = btree_index.get_memory_usage()
        assert memory_usage > 0

        # Should account for all nodes, keys, values, and children
        expected_minimum = (
            len(root.keys) * 24  # Root keys
            + len(child1.keys) * 24  # Child1 keys
            + len(child2.keys) * 24  # Child2 keys
            + 2 * 50  # Child1 values (2 entities)
            + 1 * 50  # Child2 values (1 entity)
            + 1 * 50  # Root values (1 entity)
            + 2 * 8  # Child pointers
        )
        assert memory_usage >= expected_minimum

    @pytest.mark.asyncio
    async def test_range_search_early_termination_with_limit(self, btree_index):
        """Test range search with early termination due to limit."""
        # Insert multiple entries
        base_time = datetime.now()
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            await btree_index.insert(timestamp, f"entity_{i}")

        # Query with a small limit
        start_time = base_time
        end_time = base_time + timedelta(hours=20)
        results = await btree_index.range_query(start_time, end_time, limit=3)

        # Should stop at limit
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_complex_tree_operations_with_splits(self, btree_index):
        """Test operations that cause tree splits and complex tree structures."""
        # Use a small max_keys to force splits
        btree_index.max_keys = 3
        btree_index._build_index()  # Rebuild with new max_keys

        # Insert enough data to cause multiple splits
        base_time = datetime.now()
        for i in range(15):  # This should cause splits
            timestamp = base_time + timedelta(minutes=i)
            result = await btree_index.insert(timestamp, f"entity_{i}")
            assert result is True

        # Verify the tree structure can handle queries
        results = await btree_index.range_query(
            base_time, base_time + timedelta(hours=1)
        )
        assert len(results) == 15

        # Test point queries on the complex tree
        for i in range(15):
            timestamp = base_time + timedelta(minutes=i)
            entities = await btree_index.point_query(timestamp)
            assert f"entity_{i}" in entities

    def test_node_insert_key_with_existing_key(self):
        """Test inserting a key that already exists in a node."""
        node = TemporalBTreeNode(is_leaf=True, max_keys=5)
        timestamp = datetime.now()

        # Insert initial key
        node.insert_key(timestamp, "entity_1")
        assert len(node.keys) == 1
        assert len(node.values) == 1
        assert "entity_1" in node.values[0]

        # Insert same timestamp with different entity
        node.insert_key(timestamp, "entity_2")
        assert len(node.keys) == 1  # Still one key
        assert len(node.values) == 1  # Still one value list
        assert "entity_1" in node.values[0]
        assert "entity_2" in node.values[0]
        assert len(node.values[0]) == 2

    def test_find_child_index_edge_cases(self):
        """Test find_child_index with various edge cases."""
        node = TemporalBTreeNode(is_leaf=False, max_keys=5)
        base_time = datetime.now()

        # Set up keys
        node.keys = [
            base_time + timedelta(hours=2),
            base_time + timedelta(hours=4),
            base_time + timedelta(hours=6),
        ]

        # Test key before all existing keys
        index = node.find_child_index(base_time)
        assert index == 0

        # Test key between existing keys
        index = node.find_child_index(base_time + timedelta(hours=3))
        assert index == 1

        # Test key after all existing keys
        index = node.find_child_index(base_time + timedelta(hours=8))
        assert index == 3

        # Test key equal to existing key
        index = node.find_child_index(base_time + timedelta(hours=4))
        assert index == 1  # bisect_left returns the index of the existing key

    @pytest.mark.asyncio
    async def test_statistics_query_counting(self, btree_index):
        """Test that query statistics are properly maintained."""
        timestamp = datetime.now()
        await btree_index.insert(timestamp, "entity_1")

        initial_queries = btree_index.statistics.total_queries

        # Perform a range query
        await btree_index.range_query(
            timestamp - timedelta(hours=1), timestamp + timedelta(hours=1)
        )
        assert btree_index.statistics.total_queries == initial_queries + 1

        # Perform a point query
        await btree_index.point_query(timestamp)
        assert btree_index.statistics.total_queries == initial_queries + 2

        # Verify average query time is being calculated
        assert btree_index.statistics.average_query_time_ms >= 0
