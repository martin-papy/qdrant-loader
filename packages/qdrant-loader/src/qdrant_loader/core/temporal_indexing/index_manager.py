"""Temporal index manager.

This module provides the main coordination layer for temporal indexes,
managing index lifecycle, query routing, and maintenance operations.
"""

import asyncio
from datetime import datetime
from typing import Any

from ...utils.logging import LoggingConfig
from .btree_index import TemporalBTreeIndex
from .composite_index import TemporalCompositeIndex
from .index_types import (
    IndexType,
    TemporalIndex,
    TemporalIndexConfig,
    TemporalQueryHint,
)
from .query_optimizer import TemporalQueryOptimizer

logger = LoggingConfig.get_logger(__name__)


class TemporalIndexManager:
    """Manager for temporal indexes and query optimization."""

    def __init__(self):
        """Initialize the temporal index manager."""
        self.indexes: dict[str, TemporalIndex] = {}
        self.optimizer = TemporalQueryOptimizer()
        self.maintenance_task: asyncio.Task | None = None
        self.maintenance_interval_hours = 24
        self._shutdown_event = asyncio.Event()

    async def create_index(self, config: TemporalIndexConfig) -> bool:
        """Create a new temporal index.

        Args:
            config: Index configuration

        Returns:
            True if index was created successfully
        """
        try:
            # Check if index already exists
            if config.index_id in self.indexes:
                logger.warning(f"Index {config.index_id} already exists")
                return False

            # Create index based on type
            if config.index_type == IndexType.BTREE:
                index = TemporalBTreeIndex(config)
            elif config.index_type == IndexType.COMPOSITE:
                index = TemporalCompositeIndex(config)
            else:
                logger.error(f"Unsupported index type: {config.index_type}")
                return False

            # Register with manager and optimizer
            self.indexes[config.index_id] = index
            self.optimizer.register_index(index)

            logger.info(
                f"Created temporal index {config.index_name} ({config.index_type.value})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create index {config.index_name}: {e}")
            return False

    async def drop_index(self, index_id: str) -> bool:
        """Drop an existing temporal index.

        Args:
            index_id: ID of index to drop

        Returns:
            True if index was dropped successfully
        """
        try:
            if index_id not in self.indexes:
                logger.warning(f"Index {index_id} does not exist")
                return False

            # Unregister from optimizer
            self.optimizer.unregister_index(index_id)

            # Remove from manager
            index = self.indexes.pop(index_id)

            logger.info(f"Dropped temporal index {index.config.index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to drop index {index_id}: {e}")
            return False

    async def insert_temporal_data(
        self,
        timestamp: datetime,
        entity_id: str,
        target_indexes: list[str] | None = None,
    ) -> dict[str, bool]:
        """Insert temporal data into indexes.

        Args:
            timestamp: Temporal key
            entity_id: Entity identifier
            target_indexes: Optional list of specific indexes to update

        Returns:
            Dictionary mapping index_id to success status
        """
        results = {}

        # Determine which indexes to update
        if target_indexes:
            indexes_to_update = {
                idx_id: idx
                for idx_id, idx in self.indexes.items()
                if idx_id in target_indexes and idx.is_active()
            }
        else:
            indexes_to_update = {
                idx_id: idx for idx_id, idx in self.indexes.items() if idx.is_active()
            }

        # Insert into each index
        for idx_id, index in indexes_to_update.items():
            try:
                if isinstance(index, TemporalBTreeIndex):
                    success = await index.insert(timestamp, entity_id)
                elif isinstance(index, TemporalCompositeIndex):
                    success = await index.insert(timestamp, entity_id)
                else:
                    success = False

                results[idx_id] = success

            except Exception as e:
                logger.error(f"Failed to insert into index {idx_id}: {e}")
                results[idx_id] = False

        return results

    async def range_query(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int | None = None,
        hints: TemporalQueryHint | None = None,
    ) -> list[tuple[datetime, list[str]]]:
        """Perform a temporal range query.

        Args:
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of results
            hints: Optional query optimization hints

        Returns:
            List of (timestamp, entity_ids) tuples
        """
        try:
            # Create query plan
            plan = self.optimizer.create_query_plan(
                "range_query", start_time, end_time, None, hints
            )

            if not plan.primary_index:
                logger.warning("No suitable index found for range query")
                return []

            # Execute query
            start_execution = datetime.now()
            primary_index = self.indexes.get(plan.primary_index)

            if isinstance(primary_index, TemporalBTreeIndex):
                results = await primary_index.range_query(start_time, end_time, limit)
            else:
                logger.error(
                    f"Index {plan.primary_index} does not support range queries"
                )
                return []

            # Record performance
            execution_time = (datetime.now() - start_execution).total_seconds() * 1000
            self.optimizer.record_query_performance(plan.plan_id, execution_time)

            return results

        except Exception as e:
            logger.error(f"Range query failed: {e}")
            return []

    async def entity_timeline_query(
        self,
        entity_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        hints: TemporalQueryHint | None = None,
    ) -> list[datetime]:
        """Query the timeline for a specific entity.

        Args:
            entity_id: Entity to query
            start_time: Optional start of time range
            end_time: Optional end of time range
            limit: Maximum number of results
            hints: Optional query optimization hints

        Returns:
            List of timestamps for the entity
        """
        try:
            # Create query plan
            plan = self.optimizer.create_query_plan(
                "entity_timeline", start_time, end_time, [entity_id], hints
            )

            if not plan.primary_index:
                logger.warning("No suitable index found for entity timeline query")
                return []

            # Execute query
            start_execution = datetime.now()
            primary_index = self.indexes.get(plan.primary_index)

            if isinstance(primary_index, TemporalCompositeIndex):
                results = await primary_index.query_entity_timeline(
                    entity_id, start_time, end_time, limit
                )
            elif isinstance(primary_index, TemporalBTreeIndex):
                # Fallback to range query and filter
                if start_time and end_time:
                    range_results = await primary_index.range_query(
                        start_time, end_time, limit
                    )
                    results = [
                        timestamp
                        for timestamp, entities in range_results
                        if entity_id in entities
                    ]
                else:
                    results = []
            else:
                logger.error(
                    f"Index {plan.primary_index} does not support entity timeline queries"
                )
                return []

            # Record performance
            execution_time = (datetime.now() - start_execution).total_seconds() * 1000
            self.optimizer.record_query_performance(plan.plan_id, execution_time)

            return results

        except Exception as e:
            logger.error(f"Entity timeline query failed: {e}")
            return []

    async def point_query(
        self, timestamp: datetime, hints: TemporalQueryHint | None = None
    ) -> list[str]:
        """Find all entities at a specific timestamp.

        Args:
            timestamp: Exact timestamp to query
            hints: Optional query optimization hints

        Returns:
            List of entity IDs
        """
        try:
            # Create query plan
            plan = self.optimizer.create_query_plan(
                "point_query", timestamp, timestamp, None, hints
            )

            if not plan.primary_index:
                logger.warning("No suitable index found for point query")
                return []

            # Execute query
            start_execution = datetime.now()
            primary_index = self.indexes.get(plan.primary_index)

            if isinstance(primary_index, TemporalBTreeIndex):
                results = await primary_index.point_query(timestamp)
            elif isinstance(primary_index, TemporalCompositeIndex):
                results = await primary_index.query_entities_at_time(timestamp)
            else:
                logger.error(
                    f"Index {plan.primary_index} does not support point queries"
                )
                return []

            # Record performance
            execution_time = (datetime.now() - start_execution).total_seconds() * 1000
            self.optimizer.record_query_performance(plan.plan_id, execution_time)

            return results

        except Exception as e:
            logger.error(f"Point query failed: {e}")
            return []

    async def multi_entity_query(
        self,
        entity_ids: list[str],
        start_time: datetime,
        end_time: datetime,
        limit: int | None = None,
        hints: TemporalQueryHint | None = None,
    ) -> dict[str, list[datetime]]:
        """Query multiple entities within a time range.

        Args:
            entity_ids: List of entities to query
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum results per entity
            hints: Optional query optimization hints

        Returns:
            Dictionary mapping entity_id to list of timestamps
        """
        try:
            # Create query plan
            plan = self.optimizer.create_query_plan(
                "multi_entity_query", start_time, end_time, entity_ids, hints
            )

            if not plan.primary_index:
                logger.warning("No suitable index found for multi-entity query")
                return {}

            # Execute query
            start_execution = datetime.now()
            primary_index = self.indexes.get(plan.primary_index)

            if isinstance(primary_index, TemporalCompositeIndex):
                results = await primary_index.query_entity_time_range(
                    entity_ids, start_time, end_time, limit
                )
            else:
                # Fallback: execute individual queries
                results = {}
                for entity_id in entity_ids:
                    timeline = await self.entity_timeline_query(
                        entity_id, start_time, end_time, limit, hints
                    )
                    if timeline:
                        results[entity_id] = timeline

            # Record performance
            execution_time = (datetime.now() - start_execution).total_seconds() * 1000
            self.optimizer.record_query_performance(plan.plan_id, execution_time)

            return results

        except Exception as e:
            logger.error(f"Multi-entity query failed: {e}")
            return {}

    def get_index_statistics(self, index_id: str | None = None) -> dict[str, Any]:
        """Get statistics for indexes.

        Args:
            index_id: Optional specific index ID, or None for all indexes

        Returns:
            Dictionary with index statistics
        """
        if index_id:
            if index_id in self.indexes:
                return self.indexes[index_id].statistics.to_dict()
            else:
                return {}
        else:
            return {
                idx_id: idx.statistics.to_dict() for idx_id, idx in self.indexes.items()
            }

    def get_manager_statistics(self) -> dict[str, Any]:
        """Get overall manager statistics."""
        active_indexes = sum(1 for idx in self.indexes.values() if idx.is_active())
        total_entries = sum(
            idx.statistics.total_entries for idx in self.indexes.values()
        )
        total_queries = sum(
            idx.statistics.total_queries for idx in self.indexes.values()
        )

        return {
            "total_indexes": len(self.indexes),
            "active_indexes": active_indexes,
            "total_entries": total_entries,
            "total_queries": total_queries,
            "optimizer_stats": self.optimizer.get_optimizer_statistics(),
        }

    async def rebuild_index(self, index_id: str) -> bool:
        """Rebuild a specific index.

        Args:
            index_id: ID of index to rebuild

        Returns:
            True if rebuild was successful
        """
        if index_id not in self.indexes:
            logger.warning(f"Index {index_id} does not exist")
            return False

        try:
            index = self.indexes[index_id]

            # Check if index supports rebuilding
            if hasattr(index, "rebuild") and callable(index.rebuild):
                success = await index.rebuild()
            else:
                logger.warning(
                    f"Index {index.config.index_name} does not support rebuilding"
                )
                return False

            if success:
                logger.info(f"Successfully rebuilt index {index.config.index_name}")
            else:
                logger.error(f"Failed to rebuild index {index.config.index_name}")

            return success

        except Exception as e:
            logger.error(f"Error rebuilding index {index_id}: {e}")
            return False

    async def start_maintenance(self) -> None:
        """Start the background maintenance task."""
        if self.maintenance_task and not self.maintenance_task.done():
            logger.warning("Maintenance task is already running")
            return

        self.maintenance_task = asyncio.create_task(self._maintenance_loop())
        logger.info("Started temporal index maintenance task")

    async def stop_maintenance(self) -> None:
        """Stop the background maintenance task."""
        self._shutdown_event.set()

        if self.maintenance_task and not self.maintenance_task.done():
            try:
                await asyncio.wait_for(self.maintenance_task, timeout=30.0)
            except TimeoutError:
                self.maintenance_task.cancel()
                logger.warning("Maintenance task did not stop gracefully, cancelled")

        logger.info("Stopped temporal index maintenance task")

    async def _maintenance_loop(self) -> None:
        """Background maintenance loop."""
        while not self._shutdown_event.is_set():
            try:
                await self._perform_maintenance()

                # Wait for next maintenance cycle
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.maintenance_interval_hours * 3600,
                )

            except TimeoutError:
                # Normal timeout, continue maintenance
                continue
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def _perform_maintenance(self) -> None:
        """Perform maintenance operations on indexes."""
        logger.debug("Starting temporal index maintenance")

        for index_id, index in self.indexes.items():
            try:
                # Check if index needs rebuilding
                if index.needs_rebuild() and index.config.auto_rebuild:
                    logger.info(f"Auto-rebuilding index {index.config.index_name}")
                    await self.rebuild_index(index_id)

                # Update memory usage statistics
                if hasattr(index, "get_memory_usage") and callable(
                    index.get_memory_usage
                ):
                    try:
                        index.statistics.memory_usage_bytes = index.get_memory_usage()
                    except Exception as mem_error:
                        logger.warning(
                            f"Failed to update memory usage for index {index_id}: {mem_error}"
                        )

            except Exception as e:
                logger.error(f"Error maintaining index {index_id}: {e}")

        # Clear old query plans from optimizer
        self.optimizer.clear_cache()

        logger.debug("Completed temporal index maintenance")

    async def shutdown(self) -> None:
        """Shutdown the index manager."""
        await self.stop_maintenance()

        # Clear all indexes
        self.indexes.clear()

        logger.info("Temporal index manager shutdown complete")
