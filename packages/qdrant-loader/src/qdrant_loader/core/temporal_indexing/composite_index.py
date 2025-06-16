"""Temporal composite index implementation.

This module provides composite indexes that combine entity identifiers
with temporal data for efficient entity-time queries.
"""

import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from ...utils.logging import LoggingConfig
from .btree_index import TemporalBTreeIndex
from .index_types import IndexStatus, TemporalIndex, TemporalIndexConfig

logger = LoggingConfig.get_logger(__name__)


class TemporalCompositeIndex(TemporalIndex):
    """Composite index combining entity and temporal dimensions."""

    def __init__(self, config: TemporalIndexConfig):
        """Initialize the temporal composite index.

        Args:
            config: Index configuration
        """
        super().__init__(config)

        # Primary index: entity_id -> temporal B-tree
        self.entity_indexes: dict[str, TemporalBTreeIndex] = {}

        # Secondary index: timestamp -> set of entity_ids
        self.time_index: dict[datetime, set[str]] = defaultdict(set)

        # Reverse lookup: entity_id -> set of timestamps
        self.entity_times: dict[str, set[datetime]] = defaultdict(set)

        self._build_index()

    def _build_index(self) -> None:
        """Build the initial composite index structure."""
        try:
            self.status = IndexStatus.ACTIVE
            logger.debug(f"Built composite index {self.config.index_name}")
        except Exception as e:
            logger.error(
                f"Failed to build composite index {self.config.index_name}: {e}"
            )
            self.status = IndexStatus.ERROR

    async def insert(
        self,
        timestamp: datetime,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Insert an entity-timestamp mapping into the composite index.

        Args:
            timestamp: Temporal key
            entity_id: Entity identifier
            metadata: Optional metadata for the entry

        Returns:
            True if insertion was successful
        """
        if not self.is_active():
            return False

        try:
            start_time = time.time()

            # Create entity-specific B-tree if it doesn't exist
            if entity_id not in self.entity_indexes:
                entity_config = TemporalIndexConfig(
                    index_name=f"{self.config.index_name}_entity_{entity_id}",
                    index_type=self.config.index_type,
                    temporal_field=self.config.temporal_field,
                    entity_field=entity_id,
                    page_size=self.config.page_size,
                    cache_size_mb=self.config.cache_size_mb
                    // 10,  # Smaller cache per entity
                )
                self.entity_indexes[entity_id] = TemporalBTreeIndex(entity_config)

            # Insert into entity-specific index
            success = await self.entity_indexes[entity_id].insert(timestamp, entity_id)

            if success:
                # Update secondary indexes
                self.time_index[timestamp].add(entity_id)
                self.entity_times[entity_id].add(timestamp)

                # Update statistics
                self.statistics.total_entries += 1
                query_time = (time.time() - start_time) * 1000
                self._update_query_stats(query_time)

            return success

        except Exception as e:
            logger.error(f"Failed to insert into composite index: {e}")
            return False

    async def query_entity_timeline(
        self,
        entity_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[datetime]:
        """Query the timeline for a specific entity.

        Args:
            entity_id: Entity to query
            start_time: Optional start of time range
            end_time: Optional end of time range
            limit: Maximum number of results

        Returns:
            List of timestamps for the entity
        """
        if not self.is_active() or entity_id not in self.entity_indexes:
            return []

        try:
            start_query_time = time.time()

            if start_time is None and end_time is None:
                # Return all timestamps for entity
                timestamps = sorted(self.entity_times[entity_id])
                if limit:
                    timestamps = timestamps[:limit]
                result = timestamps
            else:
                # Use entity-specific B-tree for range query
                entity_index = self.entity_indexes[entity_id]
                if start_time is None:
                    start_time = datetime.min
                if end_time is None:
                    end_time = datetime.max

                range_results = await entity_index.range_query(
                    start_time, end_time, limit
                )
                result = [timestamp for timestamp, _ in range_results]

            # Update statistics
            query_time = (time.time() - start_query_time) * 1000
            self._update_query_stats(query_time)
            self.statistics.total_queries += 1

            return result

        except Exception as e:
            logger.error(f"Entity timeline query failed: {e}")
            return []

    async def query_entities_at_time(
        self, timestamp: datetime, entity_filter: set[str] | None = None
    ) -> list[str]:
        """Query all entities active at a specific time.

        Args:
            timestamp: Timestamp to query
            entity_filter: Optional set of entities to filter by

        Returns:
            List of entity IDs active at the timestamp
        """
        if not self.is_active():
            return []

        try:
            start_time = time.time()

            entities = list(self.time_index.get(timestamp, set()))

            if entity_filter:
                entities = [e for e in entities if e in entity_filter]

            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            self.statistics.total_queries += 1

            return entities

        except Exception as e:
            logger.error(f"Entities at time query failed: {e}")
            return []

    async def query_entity_time_range(
        self,
        entity_ids: list[str],
        start_time: datetime,
        end_time: datetime,
        limit: int | None = None,
    ) -> dict[str, list[datetime]]:
        """Query multiple entities within a time range.

        Args:
            entity_ids: List of entities to query
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum results per entity

        Returns:
            Dictionary mapping entity_id to list of timestamps
        """
        if not self.is_active():
            return {}

        try:
            start_query_time = time.time()
            results = {}

            for entity_id in entity_ids:
                if entity_id in self.entity_indexes:
                    timeline = await self.query_entity_timeline(
                        entity_id, start_time, end_time, limit
                    )
                    if timeline:
                        results[entity_id] = timeline

            # Update statistics
            query_time = (time.time() - start_query_time) * 1000
            self._update_query_stats(query_time)
            self.statistics.total_queries += 1

            return results

        except Exception as e:
            logger.error(f"Entity time range query failed: {e}")
            return {}

    async def find_temporal_neighbors(
        self, entity_id: str, timestamp: datetime, time_window_seconds: int = 3600
    ) -> list[tuple[str, datetime, float]]:
        """Find entities that were active near the same time.

        Args:
            entity_id: Reference entity
            timestamp: Reference timestamp
            time_window_seconds: Time window for neighbors

        Returns:
            List of (entity_id, timestamp, distance_seconds) tuples
        """
        if not self.is_active():
            return []

        try:
            start_time = time.time()
            neighbors = []

            # Find all timestamps within the time window
            from datetime import timedelta

            window_start = timestamp - timedelta(seconds=time_window_seconds)
            window_end = timestamp + timedelta(seconds=time_window_seconds)

            for ts in self.time_index:
                if window_start <= ts <= window_end:
                    for other_entity in self.time_index[ts]:
                        if other_entity != entity_id:
                            distance = abs((ts - timestamp).total_seconds())
                            neighbors.append((other_entity, ts, distance))

            # Sort by distance
            neighbors.sort(key=lambda x: x[2])

            # Update statistics
            query_time = (time.time() - start_time) * 1000
            self._update_query_stats(query_time)
            self.statistics.total_queries += 1

            return neighbors

        except Exception as e:
            logger.error(f"Temporal neighbors query failed: {e}")
            return []

    def get_entity_count(self) -> int:
        """Get the number of unique entities in the index."""
        return len(self.entity_indexes)

    def get_timestamp_count(self) -> int:
        """Get the number of unique timestamps in the index."""
        return len(self.time_index)

    def get_entity_statistics(self, entity_id: str) -> dict[str, Any] | None:
        """Get statistics for a specific entity.

        Args:
            entity_id: Entity to get statistics for

        Returns:
            Dictionary with entity statistics or None if not found
        """
        if entity_id not in self.entity_indexes:
            return None

        entity_index = self.entity_indexes[entity_id]
        timestamps = self.entity_times[entity_id]

        return {
            "entity_id": entity_id,
            "total_timestamps": len(timestamps),
            "earliest_timestamp": min(timestamps) if timestamps else None,
            "latest_timestamp": max(timestamps) if timestamps else None,
            "index_memory_usage": entity_index.get_memory_usage(),
            "index_statistics": entity_index.statistics.to_dict(),
        }

    async def rebuild(self) -> bool:
        """Rebuild the composite index from scratch.

        Returns:
            True if rebuild was successful
        """
        try:
            self.status = IndexStatus.REBUILDING

            # Store current data
            old_data = []
            for entity_id, timestamps in self.entity_times.items():
                for timestamp in timestamps:
                    old_data.append((timestamp, entity_id))

            # Clear all indexes
            self.entity_indexes.clear()
            self.time_index.clear()
            self.entity_times.clear()

            # Rebuild
            self._build_index()

            # Reinsert data
            for timestamp, entity_id in old_data:
                await self.insert(timestamp, entity_id)

            self.statistics.maintenance_operations += 1
            self.statistics.last_rebuild = datetime.now()
            self.statistics.fragmentation_ratio = 0.0

            logger.info(
                f"Successfully rebuilt composite index {self.config.index_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild composite index: {e}")
            self.status = IndexStatus.ERROR
            return False

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

    def get_memory_usage(self) -> int:
        """Calculate total memory usage of the composite index."""
        total_memory = 0

        # Memory from entity indexes
        for entity_index in self.entity_indexes.values():
            total_memory += entity_index.get_memory_usage()

        # Memory from secondary indexes (approximate)
        total_memory += len(self.time_index) * 100  # timestamp + set overhead
        total_memory += len(self.entity_times) * 100  # entity + set overhead

        return total_memory
