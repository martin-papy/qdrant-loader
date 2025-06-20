"""Temporal B-tree index implementation.

This module provides a B-tree index optimized for temporal data queries,
supporting efficient range queries and time-based lookups.
"""

import bisect
import time
from datetime import datetime

from ...utils.logging import LoggingConfig
from .index_types import IndexStatus, TemporalIndex, TemporalIndexConfig

logger = LoggingConfig.get_logger(__name__)


class TemporalBTreeNode:
    """Node in the temporal B-tree index."""

    def __init__(self, is_leaf: bool = False, max_keys: int = 255):
        """Initialize a B-tree node.

        Args:
            is_leaf: Whether this is a leaf node
            max_keys: Maximum number of keys per node
        """
        self.is_leaf = is_leaf
        self.max_keys = max_keys
        self.keys: list[datetime] = []  # Temporal keys (timestamps)
        self.values: list[list[str]] = []  # Entity IDs for each timestamp
        self.children: list[TemporalBTreeNode] = []

    def is_full(self) -> bool:
        """Check if node is full."""
        return len(self.keys) >= self.max_keys

    def find_child_index(self, key: datetime) -> int:
        """Find the index of child that should contain the key."""
        return bisect.bisect_left(self.keys, key)

    def insert_key(self, key: datetime, value: str) -> None:
        """Insert a key-value pair into this node."""
        index = bisect.bisect_left(self.keys, key)

        if index < len(self.keys) and self.keys[index] == key:
            # Key already exists, add to values list
            if value not in self.values[index]:
                self.values[index].append(value)
        else:
            # Insert new key
            self.keys.insert(index, key)
            self.values.insert(index, [value])


class TemporalBTreeIndex(TemporalIndex):
    """B-tree index optimized for temporal data."""

    def __init__(self, config: TemporalIndexConfig):
        """Initialize the temporal B-tree index.

        Args:
            config: Index configuration
        """
        super().__init__(config)
        self.root: TemporalBTreeNode | None = None
        self.max_keys = min(config.page_size // 32, 255)  # Estimate based on page size
        self._build_index()

    def _build_index(self) -> None:
        """Build the initial index structure."""
        try:
            self.root = TemporalBTreeNode(is_leaf=True, max_keys=self.max_keys)
            self.status = IndexStatus.ACTIVE
            logger.debug(f"Built B-tree index {self.config.index_name}")
        except Exception as e:
            logger.error(f"Failed to build B-tree index {self.config.index_name}: {e}")
            self.status = IndexStatus.ERROR

    async def insert(self, timestamp: datetime, entity_id: str) -> bool:
        """Insert a timestamp-entity mapping into the index.

        Args:
            timestamp: Temporal key
            entity_id: Entity identifier

        Returns:
            True if insertion was successful
        """
        if not self.is_active() or not self.root:
            return False

        try:
            start_time = time.time()

            # If root is full, create new root
            if self.root.is_full():
                new_root = TemporalBTreeNode(is_leaf=False, max_keys=self.max_keys)
                new_root.children.append(self.root)
                self._split_child(new_root, 0)
                self.root = new_root

            self._insert_non_full(self.root, timestamp, entity_id)

            # Update statistics
            self.statistics.total_entries += 1
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)

            return True

        except Exception as e:
            logger.error(f"Failed to insert into B-tree index: {e}")
            return False

    def _insert_non_full(
        self, node: TemporalBTreeNode, key: datetime, value: str
    ) -> None:
        """Insert into a non-full node."""
        if node.is_leaf:
            node.insert_key(key, value)
        else:
            # Find child to insert into
            child_index = node.find_child_index(key)
            child = node.children[child_index]

            if child.is_full():
                self._split_child(node, child_index)
                # After split, determine which child to use
                if key > node.keys[child_index]:
                    child_index += 1
                child = node.children[child_index]

            self._insert_non_full(child, key, value)

    def _split_child(self, parent: TemporalBTreeNode, child_index: int) -> None:
        """Split a full child node."""
        full_child = parent.children[child_index]
        new_child = TemporalBTreeNode(
            is_leaf=full_child.is_leaf, max_keys=self.max_keys
        )

        mid_index = len(full_child.keys) // 2

        # Save middle key and value before modifying the child
        middle_key = full_child.keys[mid_index]
        middle_value = full_child.values[mid_index]

        # Move half the keys to new child
        new_child.keys = full_child.keys[mid_index + 1 :]
        new_child.values = full_child.values[mid_index + 1 :]
        full_child.keys = full_child.keys[:mid_index]
        full_child.values = full_child.values[:mid_index]

        # Move children if not leaf
        if not full_child.is_leaf:
            new_child.children = full_child.children[mid_index + 1 :]
            full_child.children = full_child.children[: mid_index + 1]

        # Insert middle key into parent
        parent.keys.insert(child_index, middle_key)
        parent.values.insert(child_index, middle_value)
        parent.children.insert(child_index + 1, new_child)

    async def range_query(
        self, start_time: datetime, end_time: datetime, limit: int | None = None
    ) -> list[tuple[datetime, list[str]]]:
        """Perform a range query on the temporal index.

        Args:
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of results

        Returns:
            List of (timestamp, entity_ids) tuples
        """
        if not self.is_active() or not self.root:
            return []

        try:
            start_query_time = time.time()
            results = []

            self._range_search(self.root, start_time, end_time, results, limit)

            # Update statistics
            query_time = (time.time() - start_query_time) * 1000
            self._update_query_stats(query_time)
            self.statistics.total_queries += 1

            return results

        except Exception as e:
            logger.error(f"Range query failed: {e}")
            return []

    def _range_search(
        self,
        node: TemporalBTreeNode,
        start_time: datetime,
        end_time: datetime,
        results: list[tuple[datetime, list[str]]],
        limit: int | None,
    ) -> None:
        """Recursively search for values in range."""
        if limit and len(results) >= limit:
            return

        for i, key in enumerate(node.keys):
            # Check children before this key
            if not node.is_leaf and i < len(node.children):
                self._range_search(
                    node.children[i], start_time, end_time, results, limit
                )
                if limit and len(results) >= limit:
                    return

            # Check if key is in range
            if start_time <= key <= end_time:
                results.append((key, node.values[i].copy()))
                if limit and len(results) >= limit:
                    return
            elif key > end_time:
                break

        # Check last child
        if not node.is_leaf and len(node.children) > len(node.keys):
            self._range_search(node.children[-1], start_time, end_time, results, limit)

    async def point_query(self, timestamp: datetime) -> list[str]:
        """Find all entities at a specific timestamp.

        Args:
            timestamp: Exact timestamp to query

        Returns:
            List of entity IDs
        """
        if not self.is_active() or not self.root:
            return []

        try:
            start_time = time.time()
            result = self._point_search(self.root, timestamp)

            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            self.statistics.total_queries += 1

            return result

        except Exception as e:
            logger.error(f"Point query failed: {e}")
            return []

    def _point_search(self, node: TemporalBTreeNode, key: datetime) -> list[str]:
        """Search for exact key in the tree."""
        index = bisect.bisect_left(node.keys, key)

        if index < len(node.keys) and node.keys[index] == key:
            return node.values[index].copy()
        elif node.is_leaf:
            return []
        else:
            # Search in appropriate child
            child_index = min(index, len(node.children) - 1)
            return self._point_search(node.children[child_index], key)

    def _update_query_stats(self, query_time_ms: float) -> None:
        """Update query performance statistics."""
        total_queries = self.statistics.total_queries
        if total_queries == 0:
            self.statistics.average_query_time_ms = query_time_ms
        else:
            # Running average
            current_avg = self.statistics.average_query_time_ms
            self.statistics.average_query_time_ms = (
                current_avg * total_queries + query_time_ms
            ) / (total_queries + 1)

    async def rebuild(self) -> bool:
        """Rebuild the index from scratch.

        Returns:
            True if rebuild was successful
        """
        try:
            self.status = IndexStatus.REBUILDING

            # Store current data
            old_data = self._extract_all_data()

            # Rebuild index structure
            self._build_index()

            # Reinsert data
            for timestamp, entity_ids in old_data:
                for entity_id in entity_ids:
                    await self.insert(timestamp, entity_id)

            self.statistics.maintenance_operations += 1
            self.statistics.last_rebuild = datetime.now()
            self.statistics.fragmentation_ratio = 0.0

            logger.info(f"Successfully rebuilt B-tree index {self.config.index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild B-tree index: {e}")
            self.status = IndexStatus.ERROR
            return False

    def _extract_all_data(self) -> list[tuple[datetime, list[str]]]:
        """Extract all data from the current index."""
        if not self.root:
            return []

        data = []
        self._extract_node_data(self.root, data)
        return data

    def _extract_node_data(
        self, node: TemporalBTreeNode, data: list[tuple[datetime, list[str]]]
    ) -> None:
        """Recursively extract data from nodes."""
        for i, key in enumerate(node.keys):
            if not node.is_leaf and i < len(node.children):
                self._extract_node_data(node.children[i], data)

            data.append((key, node.values[i].copy()))

        if not node.is_leaf and len(node.children) > len(node.keys):
            self._extract_node_data(node.children[-1], data)

    def get_memory_usage(self) -> int:
        """Calculate approximate memory usage in bytes."""
        if not self.root:
            return 0

        return self._calculate_node_memory(self.root)

    def _calculate_node_memory(self, node: TemporalBTreeNode) -> int:
        """Calculate memory usage of a node and its children."""
        # Approximate memory calculation
        node_size = (
            len(node.keys) * 24  # datetime objects
            + sum(len(values) * 50 for values in node.values)  # string lists
            + len(node.children) * 8  # pointers
        )

        for child in node.children:
            node_size += self._calculate_node_memory(child)

        return node_size
