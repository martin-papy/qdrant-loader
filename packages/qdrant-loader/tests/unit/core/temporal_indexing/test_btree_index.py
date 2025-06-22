"""Comprehensive tests for temporal B-tree index implementation."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from qdrant_loader.core.temporal_indexing.btree_index import (
    TemporalBTreeIndex,
    TemporalBTreeNode,
)
from qdrant_loader.core.temporal_indexing.index_types import (
    IndexStatus,
    IndexType,
    TemporalIndexConfig,
)


class TestTemporalBTreeNode:
    """Test cases for TemporalBTreeNode."""

    def test_node_initialization(self):
        """Test node initialization with default and custom parameters."""
        # Default initialization
        node = TemporalBTreeNode()
        assert not node.is_leaf
        assert node.max_keys == 255
        assert node.keys == []
        assert node.values == []
        assert node.children == []

        # Custom initialization
        node = TemporalBTreeNode(is_leaf=True, max_keys=100)
        assert node.is_leaf
        assert node.max_keys == 100
        assert node.keys == []
        assert node.values == []
        assert node.children == []

    def test_is_full(self):
        """Test node fullness detection."""
        node = TemporalBTreeNode(max_keys=3)
        assert not node.is_full()

        # Add keys up to max
        base_time = datetime.now()
        for i in range(3):
            node.keys.append(base_time + timedelta(hours=i))
            node.values.append([f"entity_{i}"])

        assert node.is_full()

    def test_find_child_index(self):
        """Test finding correct child index for a key."""
        node = TemporalBTreeNode()
        base_time = datetime.now()

        # Add some keys
        node.keys = [
            base_time + timedelta(hours=1),
            base_time + timedelta(hours=3),
            base_time + timedelta(hours=5),
        ]

        # Test finding child indices
        assert node.find_child_index(base_time) == 0  # Before first key
        assert (
            node.find_child_index(base_time + timedelta(hours=2)) == 1
        )  # Between keys
        assert (
            node.find_child_index(base_time + timedelta(hours=4)) == 2
        )  # Between keys
        assert (
            node.find_child_index(base_time + timedelta(hours=6)) == 3
        )  # After last key

    def test_insert_key_new(self):
        """Test inserting a new key-value pair."""
        node = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Insert first key
        node.insert_key(base_time + timedelta(hours=2), "entity_1")
        assert len(node.keys) == 1
        assert node.keys[0] == base_time + timedelta(hours=2)
        assert node.values[0] == ["entity_1"]

        # Insert key before existing key
        node.insert_key(base_time + timedelta(hours=1), "entity_2")
        assert len(node.keys) == 2
        assert node.keys[0] == base_time + timedelta(hours=1)
        assert node.values[0] == ["entity_2"]
        assert node.keys[1] == base_time + timedelta(hours=2)
        assert node.values[1] == ["entity_1"]

        # Insert key after existing keys
        node.insert_key(base_time + timedelta(hours=3), "entity_3")
        assert len(node.keys) == 3
        assert node.keys[2] == base_time + timedelta(hours=3)
        assert node.values[2] == ["entity_3"]

    def test_insert_key_existing(self):
        """Test inserting value for existing key."""
        node = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()
        timestamp = base_time + timedelta(hours=1)

        # Insert first value
        node.insert_key(timestamp, "entity_1")
        assert len(node.keys) == 1
        assert node.values[0] == ["entity_1"]

        # Insert second value for same key
        node.insert_key(timestamp, "entity_2")
        assert len(node.keys) == 1  # Still one key
        assert len(node.values[0]) == 2
        assert "entity_1" in node.values[0]
        assert "entity_2" in node.values[0]

        # Insert duplicate value (should not be added)
        node.insert_key(timestamp, "entity_1")
        assert len(node.values[0]) == 2  # Still two values


class TestTemporalBTreeIndex:
    """Test cases for TemporalBTreeIndex."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TemporalIndexConfig(
            index_name="test_btree",
            index_type=IndexType.BTREE,
            page_size=1024,
        )

    @pytest.fixture
    def index(self, config):
        """Create test index."""
        return TemporalBTreeIndex(config)

    def test_initialization(self, config):
        """Test index initialization."""
        index = TemporalBTreeIndex(config)

        assert index.config == config
        assert index.status == IndexStatus.ACTIVE
        assert index.root is not None
        assert index.root.is_leaf
        assert index.max_keys == min(config.page_size // 32, 255)
        assert index.statistics.index_name == "test_btree"

    def test_initialization_error(self, config):
        """Test index initialization with error."""
        with patch.object(
            TemporalBTreeIndex, "_build_index", side_effect=Exception("Build error")
        ):
            with pytest.raises(Exception, match="Build error"):
                TemporalBTreeIndex(config)

    @pytest.mark.asyncio
    async def test_insert_single(self, index):
        """Test inserting a single timestamp-entity pair."""
        timestamp = datetime.now()
        entity_id = "entity_1"

        result = await index.insert(timestamp, entity_id)

        assert result is True
        assert index.statistics.total_entries == 1
        assert index.root.keys == [timestamp]
        assert index.root.values == [[entity_id]]

    @pytest.mark.asyncio
    async def test_insert_multiple_same_timestamp(self, index):
        """Test inserting multiple entities for same timestamp."""
        timestamp = datetime.now()

        await index.insert(timestamp, "entity_1")
        await index.insert(timestamp, "entity_2")

        assert index.statistics.total_entries == 2
        assert len(index.root.keys) == 1
        assert len(index.root.values[0]) == 2
        assert "entity_1" in index.root.values[0]
        assert "entity_2" in index.root.values[0]

    @pytest.mark.asyncio
    async def test_insert_multiple_different_timestamps(self, index):
        """Test inserting entities with different timestamps."""
        base_time = datetime.now()

        await index.insert(base_time + timedelta(hours=2), "entity_1")
        await index.insert(base_time + timedelta(hours=1), "entity_2")
        await index.insert(base_time + timedelta(hours=3), "entity_3")

        assert index.statistics.total_entries == 3
        assert len(index.root.keys) == 3
        # Keys should be sorted
        assert index.root.keys[0] == base_time + timedelta(hours=1)
        assert index.root.keys[1] == base_time + timedelta(hours=2)
        assert index.root.keys[2] == base_time + timedelta(hours=3)

    @pytest.mark.asyncio
    async def test_insert_inactive_index(self, index):
        """Test inserting into inactive index."""
        index.status = IndexStatus.DISABLED

        result = await index.insert(datetime.now(), "entity_1")

        assert result is False
        assert index.statistics.total_entries == 0

    @pytest.mark.asyncio
    async def test_insert_no_root(self, index):
        """Test inserting when root is None."""
        index.root = None

        result = await index.insert(datetime.now(), "entity_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_insert_with_error(self, index):
        """Test insert with exception handling."""
        with patch.object(
            index, "_insert_non_full", side_effect=Exception("Insert error")
        ):
            result = await index.insert(datetime.now(), "entity_1")
            assert result is False

    @pytest.mark.asyncio
    async def test_insert_causes_split(self, config):
        """Test insertion that causes node split."""
        # Create index with small max_keys for easier testing
        config.page_size = 64  # This will result in small max_keys
        index = TemporalBTreeIndex(config)

        base_time = datetime.now()

        # Fill the root node to capacity
        for i in range(index.max_keys):
            await index.insert(base_time + timedelta(hours=i), f"entity_{i}")

        # Root should still be a leaf
        assert index.root is not None
        assert index.root.is_leaf

        # Insert one more to trigger split
        await index.insert(
            base_time + timedelta(hours=index.max_keys), f"entity_{index.max_keys}"
        )

        # Root should now be internal node
        assert index.root is not None
        assert not index.root.is_leaf
        assert len(index.root.children) == 2

    @pytest.mark.asyncio
    async def test_point_query_existing(self, index):
        """Test point query for existing timestamp."""
        timestamp = datetime.now()

        await index.insert(timestamp, "entity_1")
        await index.insert(timestamp, "entity_2")

        result = await index.point_query(timestamp)

        assert len(result) == 2
        assert "entity_1" in result
        assert "entity_2" in result
        assert index.statistics.total_queries == 1

    @pytest.mark.asyncio
    async def test_point_query_nonexistent(self, index):
        """Test point query for non-existent timestamp."""
        await index.insert(datetime.now(), "entity_1")

        result = await index.point_query(datetime.now() + timedelta(hours=1))

        assert result == []
        assert index.statistics.total_queries == 1

    @pytest.mark.asyncio
    async def test_point_query_inactive_index(self, index):
        """Test point query on inactive index."""
        index.status = IndexStatus.DISABLED

        result = await index.point_query(datetime.now())

        assert result == []

    @pytest.mark.asyncio
    async def test_point_query_no_root(self, index):
        """Test point query when root is None."""
        index.root = None

        result = await index.point_query(datetime.now())

        assert result == []

    @pytest.mark.asyncio
    async def test_point_query_with_error(self, index):
        """Test point query with exception handling."""
        with patch.object(index, "_point_search", side_effect=Exception("Query error")):
            result = await index.point_query(datetime.now())
            assert result == []

    @pytest.mark.asyncio
    async def test_range_query_basic(self, index):
        """Test basic range query."""
        base_time = datetime.now()

        # Insert test data
        await index.insert(base_time + timedelta(hours=1), "entity_1")
        await index.insert(base_time + timedelta(hours=2), "entity_2")
        await index.insert(base_time + timedelta(hours=3), "entity_3")
        await index.insert(base_time + timedelta(hours=4), "entity_4")

        # Query range
        result = await index.range_query(
            base_time + timedelta(hours=1.5), base_time + timedelta(hours=3.5)
        )

        assert len(result) == 2
        timestamps = [r[0] for r in result]
        assert base_time + timedelta(hours=2) in timestamps
        assert base_time + timedelta(hours=3) in timestamps

    @pytest.mark.asyncio
    async def test_range_query_with_limit(self, index):
        """Test range query with limit."""
        base_time = datetime.now()

        # Insert test data
        for i in range(10):
            await index.insert(base_time + timedelta(hours=i), f"entity_{i}")

        # Query with limit
        result = await index.range_query(
            base_time, base_time + timedelta(hours=10), limit=3
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_range_query_empty_range(self, index):
        """Test range query with no matching results."""
        base_time = datetime.now()

        await index.insert(base_time + timedelta(hours=1), "entity_1")

        result = await index.range_query(
            base_time + timedelta(hours=2), base_time + timedelta(hours=3)
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_range_query_inactive_index(self, index):
        """Test range query on inactive index."""
        index.status = IndexStatus.DISABLED

        result = await index.range_query(
            datetime.now(), datetime.now() + timedelta(hours=1)
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_range_query_no_root(self, index):
        """Test range query when root is None."""
        index.root = None

        result = await index.range_query(
            datetime.now(), datetime.now() + timedelta(hours=1)
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_range_query_with_error(self, index):
        """Test range query with exception handling."""
        with patch.object(index, "_range_search", side_effect=Exception("Query error")):
            result = await index.range_query(
                datetime.now(), datetime.now() + timedelta(hours=1)
            )
            assert result == []

    def test_update_query_stats(self, index):
        """Test query statistics updates."""
        # First query
        index._update_query_stats(10.0)
        assert index.statistics.average_query_time_ms == 10.0

        # Second query
        index.statistics.total_queries = 1
        index._update_query_stats(20.0)
        assert index.statistics.average_query_time_ms == 15.0  # (10 + 20) / 2

    @pytest.mark.asyncio
    async def test_rebuild_success(self, index):
        """Test successful index rebuild."""
        base_time = datetime.now()

        # Insert test data
        await index.insert(base_time + timedelta(hours=1), "entity_1")
        await index.insert(base_time + timedelta(hours=2), "entity_2")

        result = await index.rebuild()

        assert result is True
        assert index.status == IndexStatus.ACTIVE
        assert index.statistics.maintenance_operations == 1
        assert index.statistics.last_rebuild is not None
        assert index.statistics.fragmentation_ratio == 0.0

        # Verify data is preserved
        query_result = await index.point_query(base_time + timedelta(hours=1))
        assert "entity_1" in query_result

    @pytest.mark.asyncio
    async def test_rebuild_with_error(self, index):
        """Test rebuild with error."""
        with patch.object(index, "_build_index", side_effect=Exception("Build error")):
            result = await index.rebuild()
            assert result is False
            assert index.status == IndexStatus.ERROR

    def test_extract_all_data(self, index):
        """Test extracting all data from index."""
        # Empty index
        data = index._extract_all_data()
        assert data == []

        # Index with no root
        index.root = None
        data = index._extract_all_data()
        assert data == []

    def test_extract_all_data_with_content(self, index):
        """Test extracting data from index with content."""
        base_time = datetime.now()

        # Add data directly to root for testing
        index.root.keys = [
            base_time + timedelta(hours=1),
            base_time + timedelta(hours=2),
        ]
        index.root.values = [["entity_1"], ["entity_2"]]

        data = index._extract_all_data()

        assert len(data) == 2
        assert (base_time + timedelta(hours=1), ["entity_1"]) in data
        assert (base_time + timedelta(hours=2), ["entity_2"]) in data

    def test_get_memory_usage(self, index):
        """Test memory usage calculation."""
        # Empty index
        usage = index.get_memory_usage()
        assert usage >= 0

        # Index with no root
        index.root = None
        usage = index.get_memory_usage()
        assert usage == 0

    def test_get_memory_usage_with_content(self, index):
        """Test memory usage calculation with content."""
        base_time = datetime.now()

        # Add data to root
        index.root.keys = [base_time]
        index.root.values = [["entity_1", "entity_2"]]

        usage = index.get_memory_usage()
        assert usage > 0

    def test_calculate_node_memory(self, index):
        """Test node memory calculation."""
        node = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Empty node
        memory = index._calculate_node_memory(node)
        assert memory == 0

        # Node with data
        node.keys = [base_time]
        node.values = [["entity_1"]]
        memory = index._calculate_node_memory(node)
        assert memory > 0

    def test_calculate_node_memory_with_children(self, index):
        """Test node memory calculation with children."""
        parent = TemporalBTreeNode(is_leaf=False)
        child = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Add data to child
        child.keys = [base_time]
        child.values = [["entity_1"]]

        # Add child to parent
        parent.children = [child]

        memory = index._calculate_node_memory(parent)
        assert memory > 0

    def test_split_child_leaf_node(self, index):
        """Test splitting a leaf node."""
        parent = TemporalBTreeNode(is_leaf=False, max_keys=5)
        child = TemporalBTreeNode(is_leaf=True, max_keys=5)
        base_time = datetime.now()

        # Fill child node
        for i in range(5):
            child.keys.append(base_time + timedelta(hours=i))
            child.values.append([f"entity_{i}"])

        parent.children = [child]

        # Split the child
        index._split_child(parent, 0)

        # Parent should now have a key and two children
        assert len(parent.keys) == 1
        assert len(parent.children) == 2

        # Children should have split keys
        left_child = parent.children[0]
        right_child = parent.children[1]

        assert len(left_child.keys) == 2  # First half
        assert len(right_child.keys) == 2  # Second half

    def test_split_child_internal_node(self, index):
        """Test splitting an internal node."""
        parent = TemporalBTreeNode(is_leaf=False, max_keys=3)
        child = TemporalBTreeNode(is_leaf=False, max_keys=3)
        base_time = datetime.now()

        # Fill child node with keys and children
        for i in range(3):
            child.keys.append(base_time + timedelta(hours=i))
            child.values.append([f"entity_{i}"])
            child.children.append(TemporalBTreeNode(is_leaf=True))

        # Add one more child (internal nodes have n+1 children)
        child.children.append(TemporalBTreeNode(is_leaf=True))

        parent.children = [child]

        # Split the child
        index._split_child(parent, 0)

        # Verify split
        assert len(parent.keys) == 1
        assert len(parent.children) == 2

        left_child = parent.children[0]
        right_child = parent.children[1]

        # Children should have proper number of keys and children
        assert len(left_child.keys) == 1
        assert len(left_child.children) == 2
        assert len(right_child.keys) == 1
        assert len(right_child.children) == 2

    def test_insert_non_full_leaf(self, index):
        """Test inserting into non-full leaf node."""
        node = TemporalBTreeNode(is_leaf=True)
        timestamp = datetime.now()

        index._insert_non_full(node, timestamp, "entity_1")

        assert len(node.keys) == 1
        assert node.keys[0] == timestamp
        assert node.values[0] == ["entity_1"]

    def test_insert_non_full_internal_no_split(self, index):
        """Test inserting into internal node without child split."""
        parent = TemporalBTreeNode(is_leaf=False, max_keys=5)
        child = TemporalBTreeNode(is_leaf=True, max_keys=5)
        base_time = datetime.now()

        # Add one key to parent and two children
        parent.keys = [base_time + timedelta(hours=5)]
        parent.values = [["middle_entity"]]
        parent.children = [child, TemporalBTreeNode(is_leaf=True, max_keys=5)]

        # Insert into first child (should not cause split)
        index._insert_non_full(parent, base_time + timedelta(hours=1), "entity_1")

        assert len(child.keys) == 1
        assert child.keys[0] == base_time + timedelta(hours=1)

    def test_insert_non_full_internal_with_split(self, index):
        """Test inserting into internal node with child split."""
        parent = TemporalBTreeNode(is_leaf=False, max_keys=5)
        child = TemporalBTreeNode(is_leaf=True, max_keys=3)
        base_time = datetime.now()

        # Fill child to capacity
        for i in range(3):
            child.keys.append(base_time + timedelta(hours=i))
            child.values.append([f"entity_{i}"])

        parent.keys = [base_time + timedelta(hours=10)]
        parent.values = [["high_entity"]]
        parent.children = [child, TemporalBTreeNode(is_leaf=True, max_keys=3)]

        # Insert should cause child to split
        index._insert_non_full(parent, base_time + timedelta(hours=0.5), "new_entity")

        # Parent should now have more keys and children
        assert len(parent.keys) == 2  # Original key + split key
        assert len(parent.children) == 3  # Original 2 + 1 from split

    def test_point_search_leaf_found(self, index):
        """Test point search in leaf node - key found."""
        node = TemporalBTreeNode(is_leaf=True)
        timestamp = datetime.now()

        node.keys = [timestamp]
        node.values = [["entity_1", "entity_2"]]

        result = index._point_search(node, timestamp)
        assert result == ["entity_1", "entity_2"]

    def test_point_search_leaf_not_found(self, index):
        """Test point search in leaf node - key not found."""
        node = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        node.keys = [base_time + timedelta(hours=1)]
        node.values = [["entity_1"]]

        result = index._point_search(node, base_time + timedelta(hours=2))
        assert result == []

    def test_point_search_internal_node(self, index):
        """Test point search in internal node."""
        parent = TemporalBTreeNode(is_leaf=False)
        child = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Set up child with target key
        target_time = base_time + timedelta(hours=1)
        child.keys = [target_time]
        child.values = [["entity_1"]]

        # Set up parent
        parent.keys = [base_time + timedelta(hours=5)]
        parent.values = [["middle_entity"]]
        parent.children = [child, TemporalBTreeNode(is_leaf=True)]

        result = index._point_search(parent, target_time)
        assert result == ["entity_1"]

    def test_range_search_leaf_node(self, index):
        """Test range search in leaf node."""
        node = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Add keys
        for i in range(5):
            node.keys.append(base_time + timedelta(hours=i))
            node.values.append([f"entity_{i}"])

        results = []
        index._range_search(
            node,
            base_time + timedelta(hours=1),
            base_time + timedelta(hours=3),
            results,
            None,
        )

        assert len(results) == 3  # Hours 1, 2, 3
        timestamps = [r[0] for r in results]
        assert base_time + timedelta(hours=1) in timestamps
        assert base_time + timedelta(hours=2) in timestamps
        assert base_time + timedelta(hours=3) in timestamps

    def test_range_search_with_limit(self, index):
        """Test range search with limit."""
        node = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Add many keys
        for i in range(10):
            node.keys.append(base_time + timedelta(hours=i))
            node.values.append([f"entity_{i}"])

        results = []
        index._range_search(
            node, base_time, base_time + timedelta(hours=10), results, limit=3
        )

        assert len(results) == 3

    def test_range_search_internal_node(self, index):
        """Test range search in internal node."""
        parent = TemporalBTreeNode(is_leaf=False)
        left_child = TemporalBTreeNode(is_leaf=True)
        right_child = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Set up children
        left_child.keys = [base_time + timedelta(hours=1)]
        left_child.values = [["entity_1"]]

        right_child.keys = [base_time + timedelta(hours=3)]
        right_child.values = [["entity_3"]]

        # Set up parent
        parent.keys = [base_time + timedelta(hours=2)]
        parent.values = [["entity_2"]]
        parent.children = [left_child, right_child]

        results = []
        index._range_search(
            parent, base_time, base_time + timedelta(hours=4), results, None
        )

        # Should find all entities
        assert len(results) == 3
        entity_ids = [entity for _, entities in results for entity in entities]
        assert "entity_1" in entity_ids
        assert "entity_2" in entity_ids
        assert "entity_3" in entity_ids

    def test_extract_node_data_leaf(self, index):
        """Test extracting data from leaf node."""
        node = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        node.keys = [base_time + timedelta(hours=1), base_time + timedelta(hours=2)]
        node.values = [["entity_1"], ["entity_2"]]

        data = []
        index._extract_node_data(node, data)

        assert len(data) == 2
        assert (base_time + timedelta(hours=1), ["entity_1"]) in data
        assert (base_time + timedelta(hours=2), ["entity_2"]) in data

    def test_extract_node_data_internal(self, index):
        """Test extracting data from internal node."""
        parent = TemporalBTreeNode(is_leaf=False)
        child = TemporalBTreeNode(is_leaf=True)
        base_time = datetime.now()

        # Set up child
        child.keys = [base_time + timedelta(hours=1)]
        child.values = [["child_entity"]]

        # Set up parent
        parent.keys = [base_time + timedelta(hours=2)]
        parent.values = [["parent_entity"]]
        parent.children = [child]

        data = []
        index._extract_node_data(parent, data)

        assert len(data) == 2
        # Should extract from child first, then parent
        assert (base_time + timedelta(hours=1), ["child_entity"]) in data
        assert (base_time + timedelta(hours=2), ["parent_entity"]) in data

    @pytest.mark.asyncio
    async def test_integration_complex_operations(self, index):
        """Test complex integration scenario."""
        base_time = datetime.now()

        # Insert data across multiple time periods
        for day in range(7):
            for hour in range(24):
                timestamp = base_time + timedelta(days=day, hours=hour)
                await index.insert(timestamp, f"entity_{day}_{hour}")

        # Perform various queries
        # Point query
        specific_time = base_time + timedelta(days=3, hours=12)
        point_result = await index.point_query(specific_time)
        assert "entity_3_12" in point_result

        # Range query
        range_start = base_time + timedelta(days=2)
        range_end = base_time + timedelta(days=2, hours=23)
        range_result = await index.range_query(range_start, range_end)
        assert len(range_result) == 24  # 24 hours

        # Rebuild index
        rebuild_result = await index.rebuild()
        assert rebuild_result is True

        # Verify data integrity after rebuild
        post_rebuild_result = await index.point_query(specific_time)
        assert "entity_3_12" in post_rebuild_result

        # Check statistics
        assert index.statistics.total_entries == 7 * 24 * 2  # 2 for rebuild
        assert index.statistics.total_queries >= 3
        assert index.statistics.maintenance_operations == 1
