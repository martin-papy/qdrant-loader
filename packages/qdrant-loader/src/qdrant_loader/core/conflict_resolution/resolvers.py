"""Conflict resolution strategies and handlers.

This module contains all the different strategies for resolving conflicts
between QDrant and Neo4j databases.
"""

from collections.abc import Callable
from typing import Any

from ...utils.logging import LoggingConfig
from ..managers import IDMapping
from ..sync.event_system import DatabaseType
from .merge_strategies import AdvancedMergeStrategy, MergeStrategy
from .models import (
    ConflictRecord,
    ConflictResolutionStrategy,
    ConflictStatus,
    ConflictType,
)

logger = LoggingConfig.get_logger(__name__)


class ConflictResolver:
    """Handles resolution of conflicts using various strategies."""

    def __init__(self, config, sync_provider=None):
        """Initialize the conflict resolver.

        Args:
            config: Conflict resolution configuration
            sync_provider: Provider for database synchronization operations
        """
        self.config = config
        self.sync_provider = sync_provider
        self._advanced_merge_strategy = AdvancedMergeStrategy()

        # Statistics
        self._conflicts_resolved = 0
        self._conflicts_failed = 0
        self._manual_interventions = 0

        # Initialize resolution handlers
        self._resolution_handlers: dict[ConflictResolutionStrategy, Callable] = {
            ConflictResolutionStrategy.LAST_WRITE_WINS: self._resolve_last_write_wins,
            ConflictResolutionStrategy.FIRST_WRITE_WINS: self._resolve_first_write_wins,
            ConflictResolutionStrategy.SOURCE_PRIORITY: self._resolve_source_priority,
            ConflictResolutionStrategy.MERGE_STRATEGY: self._resolve_merge_strategy,
            ConflictResolutionStrategy.MANUAL_INTERVENTION: self._queue_manual_intervention,
            ConflictResolutionStrategy.CUSTOM_RULES: self._resolve_custom_rules,
        }

    async def resolve_conflict(
        self,
        conflict: ConflictRecord,
        strategy: ConflictResolutionStrategy | None = None,
    ) -> bool:
        """Resolve a specific conflict.

        Args:
            conflict: The conflict to resolve
            strategy: Resolution strategy to use (uses default if None)

        Returns:
            True if resolved successfully, False otherwise
        """
        try:
            # Use provided strategy or default
            resolution_strategy = strategy or self.config.default_strategy
            conflict.mark_resolving(resolution_strategy)

            # Get resolution handler
            handler = self._resolution_handlers.get(resolution_strategy)
            if not handler:
                raise ValueError(f"No handler for strategy: {resolution_strategy}")

            # Execute resolution
            success = await handler(conflict)

            if success:
                conflict.mark_resolved(
                    "system", notes=f"Resolved using {resolution_strategy.value}"
                )
                self._conflicts_resolved += 1
                logger.info(f"Conflict {conflict.conflict_id} resolved successfully")
            else:
                conflict.mark_failed("Resolution handler returned False")
                self._conflicts_failed += 1

            return success

        except Exception as e:
            conflict.mark_failed(str(e))
            self._conflicts_failed += 1
            logger.error(f"Error resolving conflict {conflict.conflict_id}: {e}")
            return False

    async def _resolve_last_write_wins(self, conflict: ConflictRecord) -> bool:
        """Resolve conflict using last-write-wins strategy."""
        if not conflict.source_version or not conflict.target_version:
            return False

        # Use the version with the latest timestamp
        if conflict.source_version.is_newer_than(conflict.target_version):
            # Source is newer, update target
            return await self._apply_source_to_target(conflict)
        else:
            # Target is newer, update source
            return await self._apply_target_to_source(conflict)

    async def _resolve_first_write_wins(self, conflict: ConflictRecord) -> bool:
        """Resolve conflict using first-write-wins strategy."""
        if not conflict.source_version or not conflict.target_version:
            return False

        # Use the version with the earliest timestamp
        if (
            conflict.source_version.last_modified
            < conflict.target_version.last_modified
        ):
            # Source is older, update target with source
            return await self._apply_source_to_target(conflict)
        else:
            # Target is older, update source with target
            return await self._apply_target_to_source(conflict)

    async def _resolve_source_priority(self, conflict: ConflictRecord) -> bool:
        """Resolve conflict by prioritizing the source database."""
        if not self.config.source_priority_database:
            logger.warning("Source priority database not configured")
            return False

        # Always apply changes from the priority database
        if (
            conflict.source_version
            and conflict.source_version.database_type
            == self.config.source_priority_database
        ):
            return await self._apply_source_to_target(conflict)
        else:
            return await self._apply_target_to_source(conflict)

    async def _resolve_merge_strategy(self, conflict: ConflictRecord) -> bool:
        """Resolve conflict by attempting to merge changes."""
        if not self.config.enable_merge_strategy:
            logger.warning("Merge strategy not enabled")
            return False

        # Implement merge logic based on conflict type
        if conflict.conflict_type == ConflictType.DATA_MISMATCH:
            return await self._merge_data_changes(conflict)
        elif conflict.conflict_type == ConflictType.CONCURRENT_UPDATE:
            return await self._merge_concurrent_updates(conflict)
        else:
            # Fall back to last-write-wins for other conflict types
            return await self._resolve_last_write_wins(conflict)

    async def _queue_manual_intervention(self, conflict: ConflictRecord) -> bool:
        """Queue conflict for manual intervention."""
        conflict.status = ConflictStatus.MANUAL_REVIEW
        self._manual_interventions += 1

        logger.info(
            f"Conflict {conflict.conflict_id} queued for manual review",
            extra={"conflict_type": conflict.conflict_type.value},
        )

        return True

    async def _resolve_custom_rules(self, conflict: ConflictRecord) -> bool:
        """Resolve conflict using custom rules."""
        # Implement custom resolution logic based on configuration
        custom_rules = self.config.custom_rules

        # Example custom rule implementation
        if "entity_type_priority" in custom_rules:
            entity_type_priority = custom_rules["entity_type_priority"]
            if (
                conflict.entity_mapping
                and conflict.entity_mapping.entity_type.value in entity_type_priority
            ):
                # Apply priority-based resolution
                return await self._apply_priority_resolution(
                    conflict, entity_type_priority
                )

        # Fall back to default strategy
        return await self._resolve_last_write_wins(conflict)

    async def _apply_source_to_target(self, conflict: ConflictRecord) -> bool:
        """Apply source data to target database."""
        try:
            if (
                not conflict.entity_mapping
                or not conflict.source_data
                or not conflict.source_version
            ):
                return False

            if not self.sync_provider:
                logger.error("Sync provider not available")
                return False

            mapping = conflict.entity_mapping
            source_data = conflict.source_data

            # Determine target database and apply changes
            if conflict.source_version.database_type == DatabaseType.QDRANT:
                # Apply QDrant data to Neo4j
                return await self.sync_provider.sync_qdrant_to_neo4j(
                    mapping, source_data
                )
            else:
                # Apply Neo4j data to QDrant
                return await self.sync_provider.sync_neo4j_to_qdrant(
                    mapping, source_data
                )

        except Exception as e:
            logger.error(f"Error applying source to target: {e}")
            return False

    async def _apply_target_to_source(self, conflict: ConflictRecord) -> bool:
        """Apply target data to source database."""
        try:
            if (
                not conflict.entity_mapping
                or not conflict.target_data
                or not conflict.target_version
            ):
                return False

            if not self.sync_provider:
                logger.error("Sync provider not available")
                return False

            mapping = conflict.entity_mapping
            target_data = conflict.target_data

            # Determine source database and apply changes
            if conflict.target_version.database_type == DatabaseType.QDRANT:
                # Apply QDrant data to Neo4j
                return await self.sync_provider.sync_qdrant_to_neo4j(
                    mapping, target_data
                )
            else:
                # Apply Neo4j data to QDrant
                return await self.sync_provider.sync_neo4j_to_qdrant(
                    mapping, target_data
                )

        except Exception as e:
            logger.error(f"Error applying target to source: {e}")
            return False

    async def _merge_data_changes(self, conflict: ConflictRecord) -> bool:
        """Merge data changes from both sources using advanced merge strategies."""
        try:
            if (
                not conflict.source_data
                or not conflict.target_data
                or not conflict.entity_mapping
                or not conflict.source_version
                or not conflict.target_version
            ):
                return False

            # Prepare field metadata for advanced merging
            field_metadata = {
                "source_timestamp": {
                    "timestamp": conflict.source_version.last_modified,
                    "database": conflict.source_version.database_type.value,
                },
                "target_timestamp": {
                    "timestamp": conflict.target_version.last_modified,
                    "database": conflict.target_version.database_type.value,
                },
            }

            # Use advanced merge strategy with field-level merging
            merge_result = await self._advanced_merge_strategy.merge_data(
                source_data=conflict.source_data,
                target_data=conflict.target_data,
                strategy=MergeStrategy.FIELD_LEVEL,
                field_metadata=field_metadata,
            )

            if not merge_result.success or not merge_result.merged_data:
                logger.warning(
                    f"Advanced merge failed for conflict {conflict.conflict_id}: "
                    f"{len(merge_result.conflicts)} conflicts detected"
                )
                return False

            # Log merge statistics
            logger.info(
                f"Advanced merge completed for conflict {conflict.conflict_id}: "
                f"{merge_result.fields_merged} fields merged, "
                f"{merge_result.conflicts_resolved} conflicts auto-resolved, "
                f"{merge_result.conflicts_requiring_manual_review} require manual review"
            )

            # Store merge conflicts in conflict record for audit
            if merge_result.conflicts:
                conflict.resolution_data = {
                    "merge_result": merge_result.to_dict(),
                    "merge_conflicts": [c.to_dict() for c in merge_result.conflicts],
                }

            # If there are conflicts requiring manual review, flag the conflict
            if merge_result.conflicts_requiring_manual_review > 0:
                conflict.status = ConflictStatus.MANUAL_REVIEW
                conflict.resolution_notes = (
                    f"Merge completed but {merge_result.conflicts_requiring_manual_review} "
                    f"conflicts require manual review"
                )
                return True  # Partial success - merge done but needs manual review

            # Apply merged data to both databases
            success_source = await self._apply_merged_data(
                conflict.entity_mapping,
                merge_result.merged_data,
                conflict.source_version.database_type,
            )
            success_target = await self._apply_merged_data(
                conflict.entity_mapping,
                merge_result.merged_data,
                conflict.target_version.database_type,
            )

            return success_source and success_target

        except Exception as e:
            logger.error(
                f"Error in advanced merge for conflict {conflict.conflict_id}: {e}"
            )
            return False

    async def _merge_concurrent_updates(self, conflict: ConflictRecord) -> bool:
        """Merge concurrent updates using advanced merge strategies."""
        try:
            if (
                not conflict.source_data
                or not conflict.target_data
                or not conflict.entity_mapping
                or not conflict.source_version
                or not conflict.target_version
            ):
                return False

            # For concurrent updates, try to get common ancestor data for three-way merge
            ancestor_data = await self._get_common_ancestor_data(conflict)

            # Prepare field metadata with timestamps for conflict resolution
            field_metadata = {
                "source_timestamp": {
                    "timestamp": conflict.source_version.last_modified,
                    "database": conflict.source_version.database_type.value,
                    "version": conflict.source_version.version_number,
                },
                "target_timestamp": {
                    "timestamp": conflict.target_version.last_modified,
                    "database": conflict.target_version.database_type.value,
                    "version": conflict.target_version.version_number,
                },
            }

            # Use three-way merge if ancestor data is available, otherwise field-level merge
            merge_strategy = (
                MergeStrategy.THREE_WAY if ancestor_data else MergeStrategy.FIELD_LEVEL
            )

            merge_result = await self._advanced_merge_strategy.merge_data(
                source_data=conflict.source_data,
                target_data=conflict.target_data,
                strategy=merge_strategy,
                ancestor_data=ancestor_data,
                field_metadata=field_metadata,
            )

            if not merge_result.success or not merge_result.merged_data:
                logger.warning(
                    f"Concurrent update merge failed for conflict {conflict.conflict_id}, "
                    f"falling back to last-write-wins"
                )
                return await self._resolve_last_write_wins(conflict)

            # Log merge statistics
            logger.info(
                f"Concurrent update merge completed for conflict {conflict.conflict_id}: "
                f"strategy={merge_strategy.value}, "
                f"{merge_result.fields_merged} fields merged, "
                f"{merge_result.conflicts_resolved} conflicts auto-resolved"
            )

            # Store merge result for audit
            conflict.resolution_data = {
                "merge_strategy": merge_strategy.value,
                "merge_result": merge_result.to_dict(),
                "ancestor_available": ancestor_data is not None,
            }

            # If there are unresolved conflicts, flag for manual review
            if merge_result.conflicts_requiring_manual_review > 0:
                conflict.status = ConflictStatus.MANUAL_REVIEW
                conflict.resolution_notes = (
                    f"Concurrent update merge completed but "
                    f"{merge_result.conflicts_requiring_manual_review} conflicts require manual review"
                )
                return True

            # Apply merged data to both databases
            success_source = await self._apply_merged_data(
                conflict.entity_mapping,
                merge_result.merged_data,
                conflict.source_version.database_type,
            )
            success_target = await self._apply_merged_data(
                conflict.entity_mapping,
                merge_result.merged_data,
                conflict.target_version.database_type,
            )

            return success_source and success_target

        except Exception as e:
            logger.error(
                f"Error in concurrent update merge for conflict {conflict.conflict_id}: {e}"
            )
            # Fall back to last-write-wins on error
            return await self._resolve_last_write_wins(conflict)

    async def _apply_priority_resolution(
        self, conflict: ConflictRecord, priority_rules: dict[str, Any]
    ) -> bool:
        """Apply resolution based on entity type priority."""
        # Implement priority-based resolution logic
        return await self._resolve_last_write_wins(conflict)

    async def _get_common_ancestor_data(
        self, conflict: ConflictRecord
    ) -> dict[str, Any] | None:
        """Get common ancestor data for three-way merge.

        Args:
            conflict: Conflict record containing version information

        Returns:
            Common ancestor data if available, None otherwise
        """
        try:
            if (
                not conflict.entity_mapping
                or not conflict.source_version
                or not conflict.target_version
            ):
                return None

            # Try to find a common ancestor version
            # This is a simplified implementation - in practice, this would query
            # version history to find the last common version

            # For now, we'll try to get the earlier version as a proxy for ancestor
            if (
                conflict.source_version.version_number
                == conflict.target_version.version_number
            ):
                # Same version number but different timestamps - no clear ancestor
                return None

            # Use the version with the lower version number as ancestor approximation
            if (
                conflict.source_version.version_number
                < conflict.target_version.version_number
            ):
                # Source is older, try to get its data as ancestor
                return conflict.source_data
            else:
                # Target is older, try to get its data as ancestor
                return conflict.target_data

        except Exception as e:
            logger.error(f"Error getting common ancestor data: {e}")
            return None

    async def _apply_merged_data(
        self, mapping: IDMapping, data: dict[str, Any], database_type: DatabaseType
    ) -> bool:
        """Apply merged data to a specific database."""
        try:
            if not self.sync_provider:
                logger.error("Sync provider not available")
                return False

            if database_type == DatabaseType.QDRANT:
                return await self.sync_provider.sync_neo4j_to_qdrant(mapping, data)
            else:
                return await self.sync_provider.sync_qdrant_to_neo4j(mapping, data)
        except Exception as e:
            logger.error(f"Error applying merged data to {database_type.value}: {e}")
            return False

    async def resolve_manual_conflict(
        self,
        conflict: ConflictRecord,
        resolution_data: dict[str, Any],
        resolved_by: str,
        notes: str | None = None,
    ) -> bool:
        """Manually resolve a conflict.

        Args:
            conflict: The conflict to resolve
            resolution_data: Data to use for resolution
            resolved_by: User or system that resolved the conflict
            notes: Optional resolution notes

        Returns:
            True if resolved successfully, False otherwise
        """
        try:
            # Apply the manual resolution
            success = await self._apply_manual_resolution(conflict, resolution_data)

            if success:
                conflict.mark_resolved(resolved_by, resolution_data, notes)
                self._conflicts_resolved += 1
                logger.info(
                    f"Conflict {conflict.conflict_id} manually resolved by {resolved_by}"
                )
            else:
                conflict.mark_failed("Manual resolution failed")
                self._conflicts_failed += 1

            return success

        except Exception as e:
            conflict.mark_failed(str(e))
            logger.error(f"Error in manual conflict resolution: {e}")
            return False

    async def _apply_manual_resolution(
        self, conflict: ConflictRecord, resolution_data: dict[str, Any]
    ) -> bool:
        """Apply manual resolution data."""
        # Implement manual resolution logic
        # This would apply the user-provided resolution data
        logger.info(f"Applying manual resolution for conflict {conflict.conflict_id}")
        return True

    @property
    def statistics(self) -> dict[str, int]:
        """Get resolver statistics."""
        return {
            "conflicts_resolved": self._conflicts_resolved,
            "conflicts_failed": self._conflicts_failed,
            "manual_interventions": self._manual_interventions,
        }
