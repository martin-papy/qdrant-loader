"""Main conflict resolution system orchestration.

This module contains the main ConflictResolutionSystem class that orchestrates
all conflict resolution components including detection, resolution, persistence,
and statistics.
"""

from typing import Any

from ...utils.logging import LoggingConfig
from ..managers import IDMapping, IDMappingManager, Neo4jManager, QdrantManager
from ..sync.event_system import ChangeEvent
from .detector import ConflictDetector
from .models import ConflictRecord, ConflictResolutionConfig, ConflictResolutionStrategy
from .persistence import ConflictPersistence, SyncProvider, VersionProvider
from .resolvers import ConflictResolver
from .statistics import ConflictStatistics

logger = LoggingConfig.get_logger(__name__)


class ConflictResolutionSystem:
    """Main system for detecting and resolving conflicts between QDrant and Neo4j."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        config: ConflictResolutionConfig | None = None,
    ):
        """Initialize the conflict resolution system.

        Args:
            qdrant_manager: QDrant manager instance
            neo4j_manager: Neo4j manager instance
            id_mapping_manager: ID mapping manager instance
            config: Conflict resolution configuration
        """
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.config = config or ConflictResolutionConfig()

        # In-memory storage for active conflicts
        self._active_conflicts: dict[str, ConflictRecord] = {}

        # Initialize components
        self._detector = ConflictDetector()
        self._persistence = ConflictPersistence(neo4j_manager)
        self._version_provider = VersionProvider(qdrant_manager, neo4j_manager)
        self._sync_provider = SyncProvider(qdrant_manager, neo4j_manager)
        self._resolver = ConflictResolver(self.config, self._sync_provider)
        self._statistics = ConflictStatistics()

    async def detect_conflict(
        self,
        mapping: IDMapping,
        source_event: ChangeEvent,
        target_data: dict[str, Any] | None = None,
    ) -> ConflictRecord | None:
        """Detect if a conflict exists for the given entity.

        Args:
            mapping: ID mapping for the entity
            source_event: Change event that triggered the check
            target_data: Current data in target database

        Returns:
            ConflictRecord if conflict detected, None otherwise
        """
        try:
            conflict = await self._detector.detect_conflict(
                mapping, source_event, target_data, self._version_provider
            )

            if conflict:
                self._active_conflicts[conflict.conflict_id] = conflict
                self._statistics.increment_detected()

                # Persist conflict to database
                await self._persistence.persist_conflict(conflict)

                return conflict

            return None

        except Exception as e:
            logger.error(f"Error detecting conflict: {e}")
            return None

    async def resolve_conflict(
        self, conflict_id: str, strategy: ConflictResolutionStrategy | None = None
    ) -> bool:
        """Resolve a specific conflict.

        Args:
            conflict_id: ID of the conflict to resolve
            strategy: Resolution strategy to use (uses default if None)

        Returns:
            True if resolved successfully, False otherwise
        """
        conflict = self._active_conflicts.get(conflict_id)
        if not conflict:
            logger.error(f"Conflict {conflict_id} not found")
            return False

        try:
            success = await self._resolver.resolve_conflict(conflict, strategy)

            if success:
                self._statistics.increment_resolved()
            else:
                self._statistics.increment_failed()

            # Update conflict in database
            await self._persistence.persist_conflict(conflict)

            return success

        except Exception as e:
            logger.error(f"Error resolving conflict {conflict_id}: {e}")
            self._statistics.increment_failed()
            return False

    async def get_conflicts_for_manual_review(self) -> list[ConflictRecord]:
        """Get all conflicts that require manual review."""
        return await self._persistence.get_conflicts_for_manual_review(
            self._active_conflicts
        )

    async def resolve_manual_conflict(
        self,
        conflict_id: str,
        resolution_data: dict[str, Any],
        resolved_by: str,
        notes: str | None = None,
    ) -> bool:
        """Manually resolve a conflict.

        Args:
            conflict_id: ID of the conflict to resolve
            resolution_data: Data to use for resolution
            resolved_by: User or system that resolved the conflict
            notes: Optional resolution notes

        Returns:
            True if resolved successfully, False otherwise
        """
        conflict = self._active_conflicts.get(conflict_id)
        if not conflict:
            return False

        try:
            success = await self._resolver.resolve_manual_conflict(
                conflict, resolution_data, resolved_by, notes
            )

            if success:
                self._statistics.increment_resolved()
            else:
                self._statistics.increment_failed()

            await self._persistence.persist_conflict(conflict)
            return success

        except Exception as e:
            logger.error(f"Error in manual conflict resolution: {e}")
            self._statistics.increment_failed()
            return False

    async def get_conflict_statistics(self) -> dict[str, Any]:
        """Get comprehensive conflict resolution statistics."""
        manual_review_conflicts = await self.get_conflicts_for_manual_review()
        cache_size = self._version_provider.get_cache_size()

        return await self._statistics.get_comprehensive_statistics(
            self._active_conflicts,
            manual_review_conflicts,
            cache_size,
            self.config.enable_merge_strategy,
        )

    async def cleanup_resolved_conflicts(self, older_than_days: int = 30) -> int:
        """Clean up resolved conflicts older than specified days.

        Args:
            older_than_days: Remove conflicts resolved more than this many days ago

        Returns:
            Number of conflicts cleaned up
        """
        return await self._persistence.cleanup_resolved_conflicts(
            self._active_conflicts, older_than_days
        )

    async def health_check(self) -> dict[str, Any]:
        """Perform health check of the conflict resolution system."""
        manual_review_conflicts = await self.get_conflicts_for_manual_review()
        cache_size = self._version_provider.get_cache_size()

        return await self._statistics.health_check(
            self._active_conflicts,
            manual_review_conflicts,
            cache_size,
            self.config,
            self.config.enable_merge_strategy,
        )

    def clear_version_cache(self) -> None:
        """Clear the version cache."""
        self._version_provider.clear_version_cache()

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self._statistics.reset_statistics()

    @property
    def active_conflicts_count(self) -> int:
        """Get the number of active conflicts."""
        return len(self._active_conflicts)

    @property
    def basic_statistics(self) -> dict[str, int]:
        """Get basic statistics."""
        return self._statistics.basic_statistics

    def get_conflict(self, conflict_id: str) -> ConflictRecord | None:
        """Get a specific conflict by ID.

        Args:
            conflict_id: ID of the conflict to retrieve

        Returns:
            ConflictRecord if found, None otherwise
        """
        return self._active_conflicts.get(conflict_id)

    def get_all_conflicts(self) -> dict[str, ConflictRecord]:
        """Get all active conflicts.

        Returns:
            Dictionary of all active conflicts
        """
        return self._active_conflicts.copy()
