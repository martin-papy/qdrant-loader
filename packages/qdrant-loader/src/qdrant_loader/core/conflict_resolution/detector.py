"""Conflict detection logic for the conflict resolution system.

This module handles the detection of various types of conflicts between
QDrant and Neo4j databases during synchronization.
"""

from typing import Any, Dict, Optional

from ...utils.logging import LoggingConfig
from ..sync import ChangeEvent, DatabaseType
from ..managers import IDMapping
from .models import ConflictType, ConflictRecord, EntityVersion

logger = LoggingConfig.get_logger(__name__)


class ConflictDetector:
    """Handles detection of conflicts between databases."""

    def __init__(self):
        """Initialize the conflict detector."""
        self._version_cache: Dict[str, EntityVersion] = {}

    async def detect_conflict(
        self,
        mapping: IDMapping,
        source_event: ChangeEvent,
        target_data: Optional[Dict[str, Any]] = None,
        version_provider=None,  # Will be injected by the system
    ) -> Optional[ConflictRecord]:
        """Detect if a conflict exists for the given entity.

        Args:
            mapping: ID mapping for the entity
            source_event: Change event that triggered the check
            target_data: Current data in target database
            version_provider: Provider for entity version information

        Returns:
            ConflictRecord if conflict detected, None otherwise
        """
        try:
            if not version_provider:
                logger.error("Version provider not available for conflict detection")
                return None

            # Get version information for both databases
            source_version = await version_provider.get_entity_version(
                mapping, source_event.database_type
            )
            target_version = await version_provider.get_entity_version(
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

                logger.warning(
                    f"Conflict detected: {conflict_type.value}",
                    extra={
                        "conflict_id": conflict.conflict_id,
                        "entity_id": mapping.entity_name,
                        "source_db": source_event.database_type.value,
                    },
                )

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
        """Determine the type of conflict based on version information.

        Args:
            source_version: Version information from source database
            target_version: Version information from target database
            source_event: The change event that triggered detection
            target_data: Current data in target database

        Returns:
            ConflictType if conflict detected, None otherwise
        """
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

    def _get_opposite_database(self, database_type: DatabaseType) -> DatabaseType:
        """Get the opposite database type.

        Args:
            database_type: The current database type

        Returns:
            The opposite database type
        """
        return (
            DatabaseType.NEO4J
            if database_type == DatabaseType.QDRANT
            else DatabaseType.QDRANT
        )
