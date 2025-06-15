"""Conflict Resolution and Versioning System for QDrant and Neo4j.

This module provides conflict detection and resolution mechanisms for handling
concurrent updates across both databases, including versioning, conflict resolution
strategies, and manual intervention workflows.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable

from ..utils.logging import LoggingConfig
from .id_mapping_manager import IDMapping, IDMappingManager
from .neo4j_manager import Neo4jManager
from .qdrant_manager import QdrantManager
from .sync_event_system import ChangeEvent, ChangeType, DatabaseType
from .types import EntityType

logger = LoggingConfig.get_logger(__name__)


class ConflictType(Enum):
    """Types of conflicts that can occur during synchronization."""

    VERSION_CONFLICT = "version_conflict"  # Different versions of same entity
    CONCURRENT_UPDATE = "concurrent_update"  # Simultaneous updates
    DATA_MISMATCH = "data_mismatch"  # Data inconsistency between databases
    MISSING_ENTITY = "missing_entity"  # Entity exists in one DB but not the other
    ORPHANED_MAPPING = "orphaned_mapping"  # Mapping exists but entity is missing
    SCHEMA_CONFLICT = "schema_conflict"  # Schema differences between databases


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""

    LAST_WRITE_WINS = "last_write_wins"  # Use the most recent update
    FIRST_WRITE_WINS = "first_write_wins"  # Use the earliest update
    MANUAL_INTERVENTION = "manual_intervention"  # Queue for manual review
    MERGE_STRATEGY = "merge_strategy"  # Attempt to merge changes
    SOURCE_PRIORITY = "source_priority"  # Prioritize specific database
    CUSTOM_RULES = "custom_rules"  # Use custom resolution rules


class ConflictStatus(Enum):
    """Status of conflict resolution."""

    DETECTED = "detected"  # Conflict has been detected
    PENDING = "pending"  # Awaiting resolution
    RESOLVING = "resolving"  # Currently being resolved
    RESOLVED = "resolved"  # Successfully resolved
    FAILED = "failed"  # Resolution failed
    MANUAL_REVIEW = "manual_review"  # Requires manual intervention


@dataclass
class EntityVersion:
    """Version information for an entity."""

    entity_id: str
    database_type: DatabaseType
    version_number: int = 1
    last_modified: datetime = field(default_factory=lambda: datetime.now(UTC))
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def increment_version(self) -> None:
        """Increment the version number and update timestamp."""
        self.version_number += 1
        self.last_modified = datetime.now(UTC)

    def is_newer_than(self, other: "EntityVersion") -> bool:
        """Check if this version is newer than another version."""
        if self.version_number != other.version_number:
            return self.version_number > other.version_number
        return self.last_modified > other.last_modified

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "entity_id": self.entity_id,
            "database_type": self.database_type.value,
            "version_number": self.version_number,
            "last_modified": self.last_modified.isoformat(),
            "checksum": self.checksum,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityVersion":
        """Create from dictionary."""
        return cls(
            entity_id=data["entity_id"],
            database_type=DatabaseType(data["database_type"]),
            version_number=data["version_number"],
            last_modified=datetime.fromisoformat(data["last_modified"]),
            checksum=data.get("checksum"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConflictRecord:
    """Record of a detected conflict."""

    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType = ConflictType.VERSION_CONFLICT
    entity_mapping: Optional[IDMapping] = None
    source_version: Optional[EntityVersion] = None
    target_version: Optional[EntityVersion] = None
    source_data: Optional[Dict[str, Any]] = None
    target_data: Optional[Dict[str, Any]] = None

    # Conflict metadata
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolution_strategy: Optional[ConflictResolutionStrategy] = None
    status: ConflictStatus = ConflictStatus.DETECTED
    resolution_attempts: int = 0
    max_resolution_attempts: int = 3

    # Resolution tracking
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # System or user ID
    resolution_data: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None
    error_message: Optional[str] = None

    def mark_resolving(self, strategy: ConflictResolutionStrategy) -> None:
        """Mark conflict as being resolved."""
        self.status = ConflictStatus.RESOLVING
        self.resolution_strategy = strategy
        self.resolution_attempts += 1

    def mark_resolved(
        self,
        resolved_by: str,
        resolution_data: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Mark conflict as resolved."""
        self.status = ConflictStatus.RESOLVED
        self.resolved_at = datetime.now(UTC)
        self.resolved_by = resolved_by
        self.resolution_data = resolution_data
        self.resolution_notes = notes

    def mark_failed(self, error: str) -> None:
        """Mark conflict resolution as failed."""
        self.status = ConflictStatus.FAILED
        self.error_message = error

    def requires_manual_review(self) -> bool:
        """Check if conflict requires manual review."""
        return (
            self.status == ConflictStatus.MANUAL_REVIEW
            or self.resolution_attempts >= self.max_resolution_attempts
            or self.resolution_strategy
            == ConflictResolutionStrategy.MANUAL_INTERVENTION
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "entity_mapping": (
                self.entity_mapping.to_dict() if self.entity_mapping else None
            ),
            "source_version": (
                self.source_version.to_dict() if self.source_version else None
            ),
            "target_version": (
                self.target_version.to_dict() if self.target_version else None
            ),
            "source_data": self.source_data,
            "target_data": self.target_data,
            "detected_at": self.detected_at.isoformat(),
            "resolution_strategy": (
                self.resolution_strategy.value if self.resolution_strategy else None
            ),
            "status": self.status.value,
            "resolution_attempts": self.resolution_attempts,
            "max_resolution_attempts": self.max_resolution_attempts,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_data": self.resolution_data,
            "resolution_notes": self.resolution_notes,
            "error_message": self.error_message,
        }


@dataclass
class ConflictResolutionConfig:
    """Configuration for conflict resolution."""

    default_strategy: ConflictResolutionStrategy = (
        ConflictResolutionStrategy.LAST_WRITE_WINS
    )
    enable_auto_resolution: bool = True
    max_resolution_attempts: int = 3
    manual_review_threshold: int = 2
    source_priority_database: Optional[DatabaseType] = None
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    enable_merge_strategy: bool = False
    conflict_retention_days: int = 30
    enable_conflict_logging: bool = True


class ConflictResolutionSystem:
    """System for detecting and resolving conflicts between QDrant and Neo4j."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        config: Optional[ConflictResolutionConfig] = None,
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
        self._active_conflicts: Dict[str, ConflictRecord] = {}
        self._version_cache: Dict[str, EntityVersion] = {}
        self._resolution_handlers: Dict[ConflictResolutionStrategy, Callable] = {}

        # Statistics
        self._conflicts_detected = 0
        self._conflicts_resolved = 0
        self._conflicts_failed = 0
        self._manual_interventions = 0

        # Initialize resolution handlers
        self._register_resolution_handlers()

    def _register_resolution_handlers(self) -> None:
        """Register conflict resolution handlers."""
        self._resolution_handlers = {
            ConflictResolutionStrategy.LAST_WRITE_WINS: self._resolve_last_write_wins,
            ConflictResolutionStrategy.FIRST_WRITE_WINS: self._resolve_first_write_wins,
            ConflictResolutionStrategy.SOURCE_PRIORITY: self._resolve_source_priority,
            ConflictResolutionStrategy.MERGE_STRATEGY: self._resolve_merge_strategy,
            ConflictResolutionStrategy.MANUAL_INTERVENTION: self._queue_manual_intervention,
            ConflictResolutionStrategy.CUSTOM_RULES: self._resolve_custom_rules,
        }

    async def detect_conflict(
        self,
        mapping: IDMapping,
        source_event: ChangeEvent,
        target_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConflictRecord]:
        """Detect if a conflict exists for the given entity.

        Args:
            mapping: ID mapping for the entity
            source_event: Change event that triggered the check
            target_data: Current data in target database

        Returns:
            ConflictRecord if conflict detected, None otherwise
        """
        try:
            # Get version information for both databases
            source_version = await self._get_entity_version(
                mapping, source_event.database_type
            )
            target_version = await self._get_entity_version(
                mapping, self._get_opposite_database(source_event.database_type)
            )

            # Check for various conflict types
            conflict_type = self._determine_conflict_type(
                source_version, target_version, source_event, target_data
            )

            if conflict_type:
                conflict = ConflictRecord(
                    conflict_type=conflict_type,
                    entity_mapping=mapping,
                    source_version=source_version,
                    target_version=target_version,
                    source_data=source_event.new_data,
                    target_data=target_data,
                )

                self._active_conflicts[conflict.conflict_id] = conflict
                self._conflicts_detected += 1

                logger.warning(
                    f"Conflict detected: {conflict_type.value}",
                    extra={
                        "conflict_id": conflict.conflict_id,
                        "entity_id": mapping.entity_name,
                        "source_db": source_event.database_type.value,
                    },
                )

                # Persist conflict to database
                await self._persist_conflict(conflict)

                return conflict

            return None

        except Exception as e:
            logger.error(f"Error detecting conflict: {e}")
            return None

    def _determine_conflict_type(
        self,
        source_version: Optional[EntityVersion],
        target_version: Optional[EntityVersion],
        source_event: ChangeEvent,
        target_data: Optional[Dict[str, Any]],
    ) -> Optional[ConflictType]:
        """Determine the type of conflict based on version information."""
        # Missing entity conflicts
        if source_version and not target_version:
            return ConflictType.MISSING_ENTITY
        if target_version and not source_version:
            return ConflictType.MISSING_ENTITY

        # No conflict if no target version exists
        if not target_version:
            return None

        # Version conflicts
        if source_version and target_version:
            # Check for concurrent updates (same version but different timestamps)
            if (
                source_version.version_number == target_version.version_number
                and abs(
                    (
                        source_version.last_modified - target_version.last_modified
                    ).total_seconds()
                )
                < 60  # Within 1 minute
            ):
                return ConflictType.CONCURRENT_UPDATE

            # Check for version conflicts
            if source_version.version_number != target_version.version_number:
                return ConflictType.VERSION_CONFLICT

            # Check for data mismatches
            if source_version.checksum and target_version.checksum:
                if source_version.checksum != target_version.checksum:
                    return ConflictType.DATA_MISMATCH

        return None

    async def resolve_conflict(
        self, conflict_id: str, strategy: Optional[ConflictResolutionStrategy] = None
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
                logger.info(f"Conflict {conflict_id} resolved successfully")
            else:
                conflict.mark_failed("Resolution handler returned False")
                self._conflicts_failed += 1

            # Update conflict in database
            await self._persist_conflict(conflict)

            return success

        except Exception as e:
            conflict.mark_failed(str(e))
            self._conflicts_failed += 1
            logger.error(f"Error resolving conflict {conflict_id}: {e}")
            await self._persist_conflict(conflict)
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

        # Persist the conflict with manual review status
        await self._persist_conflict(conflict)
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

            mapping = conflict.entity_mapping
            source_data = conflict.source_data

            # Determine target database and apply changes
            if conflict.source_version.database_type == DatabaseType.QDRANT:
                # Apply QDrant data to Neo4j
                return await self._sync_qdrant_to_neo4j(mapping, source_data)
            else:
                # Apply Neo4j data to QDrant
                return await self._sync_neo4j_to_qdrant(mapping, source_data)

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

            mapping = conflict.entity_mapping
            target_data = conflict.target_data

            # Determine source database and apply changes
            if conflict.target_version.database_type == DatabaseType.QDRANT:
                # Apply QDrant data to Neo4j
                return await self._sync_qdrant_to_neo4j(mapping, target_data)
            else:
                # Apply Neo4j data to QDrant
                return await self._sync_neo4j_to_qdrant(mapping, target_data)

        except Exception as e:
            logger.error(f"Error applying target to source: {e}")
            return False

    async def _merge_data_changes(self, conflict: ConflictRecord) -> bool:
        """Merge data changes from both sources."""
        # Implement data merging logic
        # This is a simplified implementation - real merging would be more sophisticated
        try:
            if (
                not conflict.source_data
                or not conflict.target_data
                or not conflict.entity_mapping
                or not conflict.source_version
                or not conflict.target_version
            ):
                return False

            # Merge dictionaries, preferring source for conflicts
            merged_data = {**conflict.target_data, **conflict.source_data}

            # Apply merged data to both databases
            success_source = await self._apply_merged_data(
                conflict.entity_mapping,
                merged_data,
                conflict.source_version.database_type,
            )
            success_target = await self._apply_merged_data(
                conflict.entity_mapping,
                merged_data,
                conflict.target_version.database_type,
            )

            return success_source and success_target

        except Exception as e:
            logger.error(f"Error merging data changes: {e}")
            return False

    async def _merge_concurrent_updates(self, conflict: ConflictRecord) -> bool:
        """Merge concurrent updates."""
        # For concurrent updates, use last-write-wins as fallback
        return await self._resolve_last_write_wins(conflict)

    async def _apply_priority_resolution(
        self, conflict: ConflictRecord, priority_rules: Dict[str, Any]
    ) -> bool:
        """Apply resolution based on entity type priority."""
        # Implement priority-based resolution logic
        return await self._resolve_last_write_wins(conflict)

    async def _apply_merged_data(
        self, mapping: IDMapping, data: Dict[str, Any], database_type: DatabaseType
    ) -> bool:
        """Apply merged data to a specific database."""
        try:
            if database_type == DatabaseType.QDRANT:
                return await self._sync_neo4j_to_qdrant(mapping, data)
            else:
                return await self._sync_qdrant_to_neo4j(mapping, data)
        except Exception as e:
            logger.error(f"Error applying merged data to {database_type.value}: {e}")
            return False

    async def _sync_qdrant_to_neo4j(
        self, mapping: IDMapping, data: Dict[str, Any]
    ) -> bool:
        """Sync data from QDrant to Neo4j."""
        # Implement QDrant to Neo4j synchronization
        # This would use the bidirectional sync engine
        logger.info(f"Syncing QDrant data to Neo4j for mapping {mapping.mapping_id}")
        return True

    async def _sync_neo4j_to_qdrant(
        self, mapping: IDMapping, data: Dict[str, Any]
    ) -> bool:
        """Sync data from Neo4j to QDrant."""
        # Implement Neo4j to QDrant synchronization
        # This would use the bidirectional sync engine
        logger.info(f"Syncing Neo4j data to QDrant for mapping {mapping.mapping_id}")
        return True

    async def _get_entity_version(
        self, mapping: IDMapping, database_type: DatabaseType
    ) -> Optional[EntityVersion]:
        """Get version information for an entity in a specific database."""
        try:
            # Check cache first
            cache_key = f"{mapping.mapping_id}:{database_type.value}"
            if cache_key in self._version_cache:
                return self._version_cache[cache_key]

            # Retrieve version from database
            if database_type == DatabaseType.QDRANT:
                version = await self._get_qdrant_version(mapping)
            else:
                version = await self._get_neo4j_version(mapping)

            # Cache the version
            if version:
                self._version_cache[cache_key] = version

            return version

        except Exception as e:
            logger.error(f"Error getting entity version: {e}")
            return None

    async def _get_qdrant_version(self, mapping: IDMapping) -> Optional[EntityVersion]:
        """Get version information from QDrant."""
        # Implement QDrant version retrieval
        # This would query QDrant for version metadata
        return EntityVersion(
            entity_id=mapping.qdrant_point_id or "",
            database_type=DatabaseType.QDRANT,
            version_number=1,
            last_modified=datetime.now(UTC),
        )

    async def _get_neo4j_version(self, mapping: IDMapping) -> Optional[EntityVersion]:
        """Get version information from Neo4j."""
        # Implement Neo4j version retrieval
        # This would query Neo4j for version metadata
        return EntityVersion(
            entity_id=mapping.neo4j_node_id or "",
            database_type=DatabaseType.NEO4J,
            version_number=1,
            last_modified=datetime.now(UTC),
        )

    def _get_opposite_database(self, database_type: DatabaseType) -> DatabaseType:
        """Get the opposite database type."""
        return (
            DatabaseType.NEO4J
            if database_type == DatabaseType.QDRANT
            else DatabaseType.QDRANT
        )

    async def _persist_conflict(self, conflict: ConflictRecord) -> None:
        """Persist conflict record to database."""
        try:
            # Store conflict in Neo4j for audit trail
            query = """
            MERGE (c:ConflictRecord {conflict_id: $conflict_id})
            SET c += $properties
            RETURN c
            """

            properties = conflict.to_dict()
            self.neo4j_manager.execute_write_query(
                query,
                parameters={
                    "conflict_id": conflict.conflict_id,
                    "properties": properties,
                },
            )

            logger.debug(f"Persisted conflict {conflict.conflict_id}")

        except Exception as e:
            logger.error(f"Error persisting conflict: {e}")

    async def get_conflicts_for_manual_review(self) -> List[ConflictRecord]:
        """Get all conflicts that require manual review."""
        return [
            conflict
            for conflict in self._active_conflicts.values()
            if conflict.requires_manual_review()
        ]

    async def resolve_manual_conflict(
        self,
        conflict_id: str,
        resolution_data: Dict[str, Any],
        resolved_by: str,
        notes: Optional[str] = None,
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
            # Apply the manual resolution
            success = await self._apply_manual_resolution(conflict, resolution_data)

            if success:
                conflict.mark_resolved(resolved_by, resolution_data, notes)
                self._conflicts_resolved += 1
                logger.info(
                    f"Conflict {conflict_id} manually resolved by {resolved_by}"
                )
            else:
                conflict.mark_failed("Manual resolution failed")
                self._conflicts_failed += 1

            await self._persist_conflict(conflict)
            return success

        except Exception as e:
            conflict.mark_failed(str(e))
            await self._persist_conflict(conflict)
            logger.error(f"Error in manual conflict resolution: {e}")
            return False

    async def _apply_manual_resolution(
        self, conflict: ConflictRecord, resolution_data: Dict[str, Any]
    ) -> bool:
        """Apply manual resolution data."""
        # Implement manual resolution logic
        # This would apply the user-provided resolution data
        logger.info(f"Applying manual resolution for conflict {conflict.conflict_id}")
        return True

    async def get_conflict_statistics(self) -> Dict[str, Any]:
        """Get conflict resolution statistics."""
        active_conflicts = len(self._active_conflicts)
        manual_review_count = len(await self.get_conflicts_for_manual_review())

        return {
            "conflicts_detected": self._conflicts_detected,
            "conflicts_resolved": self._conflicts_resolved,
            "conflicts_failed": self._conflicts_failed,
            "manual_interventions": self._manual_interventions,
            "active_conflicts": active_conflicts,
            "manual_review_queue": manual_review_count,
            "resolution_rate": (
                self._conflicts_resolved / max(self._conflicts_detected, 1)
            ),
            "cache_size": len(self._version_cache),
        }

    async def cleanup_resolved_conflicts(self, older_than_days: int = 30) -> int:
        """Clean up resolved conflicts older than specified days.

        Args:
            older_than_days: Remove conflicts resolved more than this many days ago

        Returns:
            Number of conflicts cleaned up
        """
        cutoff_date = datetime.now(UTC).replace(
            day=datetime.now(UTC).day - older_than_days
        )

        cleaned_count = 0
        conflicts_to_remove = []

        for conflict_id, conflict in self._active_conflicts.items():
            if (
                conflict.status == ConflictStatus.RESOLVED
                and conflict.resolved_at
                and conflict.resolved_at < cutoff_date
            ):
                conflicts_to_remove.append(conflict_id)

        for conflict_id in conflicts_to_remove:
            del self._active_conflicts[conflict_id]
            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} resolved conflicts")
        return cleaned_count

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the conflict resolution system."""
        try:
            stats = await self.get_conflict_statistics()

            return {
                "status": "healthy",
                "statistics": stats,
                "config": {
                    "default_strategy": self.config.default_strategy.value,
                    "auto_resolution_enabled": self.config.enable_auto_resolution,
                    "max_attempts": self.config.max_resolution_attempts,
                },
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
