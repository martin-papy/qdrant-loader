"""Cross-Database ID Mapping System for QDrant and Neo4j synchronization.

This module provides a comprehensive mapping service that maintains relationships
between QDrant point IDs and Neo4j node IDs, ensuring referential integrity
across both databases with temporal tracking and validation capabilities.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from neo4j import Session
from qdrant_client.http.models import PointStruct

from ...utils.logging import LoggingConfig
from .neo4j_manager import Neo4jManager
from .qdrant_manager import QdrantManager
from ..types import EntityType, TemporalInfo

logger = LoggingConfig.get_logger(__name__)


class MappingStatus(Enum):
    """Status of ID mappings."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_SYNC = "pending_sync"
    SYNC_FAILED = "sync_failed"
    ORPHANED = "orphaned"


class MappingType(Enum):
    """Type of entity being mapped."""

    DOCUMENT = "document"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    EPISODE = "episode"


@dataclass
class IDMapping:
    """Container for cross-database ID mapping information."""

    # Core mapping information
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    qdrant_point_id: Optional[str] = None
    neo4j_node_id: Optional[str] = None
    neo4j_node_uuid: Optional[str] = None  # For Graphiti nodes

    # Entity information
    entity_type: EntityType = EntityType.CONCEPT
    mapping_type: MappingType = MappingType.DOCUMENT
    entity_name: Optional[str] = None

    # Status and metadata
    status: MappingStatus = MappingStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Temporal tracking
    temporal_info: TemporalInfo = field(default_factory=TemporalInfo)

    # Sync tracking
    last_sync_time: Optional[datetime] = None
    sync_version: int = 1
    sync_errors: List[str] = field(default_factory=list)

    # Document versioning and update tracking
    document_version: int = 1  # Version of the actual document content
    last_update_time: Optional[datetime] = None  # When document was last updated
    created_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    update_source: Optional[str] = (
        None  # Source of the last update (e.g., "qdrant", "neo4j", "manual")
    )
    content_hash: Optional[str] = None  # Hash of document content for change detection

    # Historical tracking
    version_history: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Track version changes
    update_frequency: int = 0  # Number of updates performed

    # Validation fields
    qdrant_exists: bool = False
    neo4j_exists: bool = False
    last_validation_time: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Check if the mapping is valid and both entities exist."""
        return (
            self.status == MappingStatus.ACTIVE
            and self.qdrant_exists
            and self.neo4j_exists
            and self.temporal_info.is_currently_valid()
        )

    def is_orphaned(self) -> bool:
        """Check if the mapping is orphaned (one or both entities don't exist)."""
        return not self.qdrant_exists or not self.neo4j_exists

    def mark_sync_failed(self, error: str) -> None:
        """Mark the mapping as sync failed with error details."""
        self.status = MappingStatus.SYNC_FAILED
        self.sync_errors.append(f"{datetime.now(UTC).isoformat()}: {error}")

    def mark_sync_success(self) -> None:
        """Mark the mapping as successfully synced."""
        self.status = MappingStatus.ACTIVE
        self.last_sync_time = datetime.now(UTC)
        self.sync_version += 1
        self.sync_errors.clear()

    def increment_document_version(
        self,
        update_source: str = "unknown",
        content_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Increment document version and record update details.

        Args:
            update_source: Source of the update (e.g., "qdrant", "neo4j", "manual")
            content_hash: Hash of the updated content for change detection
            metadata: Additional metadata about the update
        """
        # Store previous version in history
        previous_version = {
            "version": self.document_version,
            "timestamp": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "source": self.update_source,
            "content_hash": self.content_hash,
            "metadata": metadata or {},
        }
        self.version_history.append(previous_version)

        # Update to new version
        self.document_version += 1
        self.last_update_time = datetime.now(UTC)
        self.update_source = update_source
        self.content_hash = content_hash
        self.update_frequency += 1

        # Update temporal info version as well
        self.temporal_info.version = self.document_version
        self.temporal_info.transaction_time = self.last_update_time

    def get_version_at_time(self, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Get the document version that was active at a specific time.

        Args:
            timestamp: The timestamp to check

        Returns:
            Version information if found, None otherwise
        """
        # Check if current version was active at that time
        if self.last_update_time and timestamp >= self.last_update_time:
            return {
                "version": self.document_version,
                "timestamp": self.last_update_time.isoformat(),
                "source": self.update_source,
                "content_hash": self.content_hash,
                "is_current": True,
            }

        # Search through version history
        for version_info in reversed(self.version_history):
            if version_info["timestamp"]:
                version_time = datetime.fromisoformat(version_info["timestamp"])
                if timestamp >= version_time:
                    version_info["is_current"] = False
                    return version_info

        # If no version found, return creation info
        if timestamp >= self.created_time:
            return {
                "version": 1,
                "timestamp": self.created_time.isoformat(),
                "source": "creation",
                "content_hash": None,
                "is_current": False,
            }

        return None

    def get_update_statistics(self) -> Dict[str, Any]:
        """Get statistics about document updates.

        Returns:
            Dictionary containing update statistics
        """
        now = datetime.now(UTC)
        time_since_creation = (now - self.created_time).total_seconds()
        time_since_last_update = (
            (now - self.last_update_time).total_seconds()
            if self.last_update_time
            else time_since_creation
        )

        return {
            "current_version": self.document_version,
            "total_updates": self.update_frequency,
            "created_time": self.created_time.isoformat(),
            "last_update_time": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "time_since_creation_hours": time_since_creation / 3600,
            "time_since_last_update_hours": time_since_last_update / 3600,
            "update_rate_per_day": (
                self.update_frequency / max(time_since_creation / 86400, 1)
            ),
            "version_history_count": len(self.version_history),
            "last_update_source": self.update_source,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping to dictionary format."""
        return {
            "mapping_id": self.mapping_id,
            "qdrant_point_id": self.qdrant_point_id,
            "neo4j_node_id": self.neo4j_node_id,
            "neo4j_node_uuid": self.neo4j_node_uuid,
            "entity_type": self.entity_type.value,
            "mapping_type": self.mapping_type.value,
            "entity_name": self.entity_name,
            "status": self.status.value,
            "metadata": self.metadata,
            "temporal_info": self.temporal_info.to_dict(),
            "last_sync_time": (
                self.last_sync_time.isoformat() if self.last_sync_time else None
            ),
            "sync_version": self.sync_version,
            "sync_errors": self.sync_errors,
            # Document versioning fields
            "document_version": self.document_version,
            "last_update_time": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "created_time": self.created_time.isoformat(),
            "update_source": self.update_source,
            "content_hash": self.content_hash,
            "version_history": self.version_history,
            "update_frequency": self.update_frequency,
            # Validation fields
            "qdrant_exists": self.qdrant_exists,
            "neo4j_exists": self.neo4j_exists,
            "last_validation_time": (
                self.last_validation_time.isoformat()
                if self.last_validation_time
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IDMapping":
        """Create IDMapping from dictionary."""
        mapping = cls(
            mapping_id=data["mapping_id"],
            qdrant_point_id=data.get("qdrant_point_id"),
            neo4j_node_id=data.get("neo4j_node_id"),
            neo4j_node_uuid=data.get("neo4j_node_uuid"),
            entity_type=EntityType(data["entity_type"]),
            mapping_type=MappingType(data["mapping_type"]),
            entity_name=data.get("entity_name"),
            status=MappingStatus(data["status"]),
            metadata=data.get("metadata", {}),
            sync_version=data.get("sync_version", 1),
            sync_errors=data.get("sync_errors", []),
            # Document versioning fields
            document_version=data.get("document_version", 1),
            update_source=data.get("update_source"),
            content_hash=data.get("content_hash"),
            version_history=data.get("version_history", []),
            update_frequency=data.get("update_frequency", 0),
            # Validation fields
            qdrant_exists=data.get("qdrant_exists", False),
            neo4j_exists=data.get("neo4j_exists", False),
        )

        # Parse temporal info
        if "temporal_info" in data:
            mapping.temporal_info = TemporalInfo.from_dict(data["temporal_info"])

        # Parse timestamps
        if data.get("last_sync_time"):
            mapping.last_sync_time = datetime.fromisoformat(data["last_sync_time"])
        if data.get("last_validation_time"):
            mapping.last_validation_time = datetime.fromisoformat(
                data["last_validation_time"]
            )
        if data.get("last_update_time"):
            mapping.last_update_time = datetime.fromisoformat(data["last_update_time"])
        if data.get("created_time"):
            mapping.created_time = datetime.fromisoformat(data["created_time"])

        return mapping


class IDMappingManager:
    """Manager for cross-database ID mappings between QDrant and Neo4j."""

    def __init__(
        self,
        neo4j_manager: Neo4jManager,
        qdrant_manager: QdrantManager,
        enable_validation: bool = True,
        validation_interval_hours: int = 24,
    ):
        """Initialize the ID mapping manager.

        Args:
            neo4j_manager: Neo4j manager instance
            qdrant_manager: QDrant manager instance
            enable_validation: Whether to enable automatic validation
            validation_interval_hours: Hours between validation runs
        """
        self.neo4j_manager = neo4j_manager
        self.qdrant_manager = qdrant_manager
        self.enable_validation = enable_validation
        self.validation_interval_hours = validation_interval_hours

        # In-memory cache for frequently accessed mappings
        self._mapping_cache: Dict[str, IDMapping] = {}
        self._cache_max_size = 10000

        # Ensure mapping table exists
        self._ensure_mapping_table()

    def _ensure_mapping_table(self) -> None:
        """Ensure the ID mapping table exists in Neo4j."""
        try:
            create_mapping_query = """
            CREATE CONSTRAINT id_mapping_unique IF NOT EXISTS
            FOR (m:IDMapping) REQUIRE m.mapping_id IS UNIQUE
            """
            self.neo4j_manager.execute_write_query(create_mapping_query)

            # Create indexes for performance
            indexes = [
                "CREATE INDEX idx_id_mapping_qdrant IF NOT EXISTS FOR (m:IDMapping) ON (m.qdrant_point_id)",
                "CREATE INDEX idx_id_mapping_neo4j_id IF NOT EXISTS FOR (m:IDMapping) ON (m.neo4j_node_id)",
                "CREATE INDEX idx_id_mapping_neo4j_uuid IF NOT EXISTS FOR (m:IDMapping) ON (m.neo4j_node_uuid)",
                "CREATE INDEX idx_id_mapping_entity_type IF NOT EXISTS FOR (m:IDMapping) ON (m.entity_type)",
                "CREATE INDEX idx_id_mapping_status IF NOT EXISTS FOR (m:IDMapping) ON (m.status)",
                "CREATE INDEX idx_id_mapping_type IF NOT EXISTS FOR (m:IDMapping) ON (m.mapping_type)",
            ]

            for index_query in indexes:
                self.neo4j_manager.execute_write_query(index_query)

            logger.info("ID mapping table and indexes ensured in Neo4j")

        except Exception as e:
            logger.error(f"Failed to ensure ID mapping table: {e}")
            raise

    async def create_mapping(
        self,
        qdrant_point_id: Optional[str] = None,
        neo4j_node_id: Optional[str] = None,
        neo4j_node_uuid: Optional[str] = None,
        entity_type: EntityType = EntityType.CONCEPT,
        mapping_type: MappingType = MappingType.DOCUMENT,
        entity_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        validate_existence: bool = True,
    ) -> IDMapping:
        """Create a new ID mapping.

        Args:
            qdrant_point_id: QDrant point ID
            neo4j_node_id: Neo4j node ID
            neo4j_node_uuid: Neo4j node UUID (for Graphiti nodes)
            entity_type: Type of entity being mapped
            mapping_type: Type of mapping
            entity_name: Name of the entity
            metadata: Additional metadata
            validate_existence: Whether to validate that entities exist

        Returns:
            Created IDMapping instance

        Raises:
            ValueError: If mapping validation fails
        """
        if not qdrant_point_id and not neo4j_node_id and not neo4j_node_uuid:
            raise ValueError("At least one ID must be provided")

        # Create mapping instance
        mapping = IDMapping(
            qdrant_point_id=qdrant_point_id,
            neo4j_node_id=neo4j_node_id,
            neo4j_node_uuid=neo4j_node_uuid,
            entity_type=entity_type,
            mapping_type=mapping_type,
            entity_name=entity_name,
            metadata=metadata or {},
        )

        # Validate existence if requested
        if validate_existence:
            await self._validate_mapping_existence(mapping)

        # Store in Neo4j
        await self._store_mapping(mapping)

        # Cache the mapping
        self._cache_mapping(mapping)

        logger.debug(f"Created ID mapping: {mapping.mapping_id}")
        return mapping

    async def get_mapping_by_qdrant_id(
        self, qdrant_point_id: str
    ) -> Optional[IDMapping]:
        """Get mapping by QDrant point ID."""
        # Check cache first
        for mapping in self._mapping_cache.values():
            if mapping.qdrant_point_id == qdrant_point_id:
                return mapping

        # Query Neo4j
        query = """
        MATCH (m:IDMapping {qdrant_point_id: $qdrant_point_id})
        RETURN m
        """

        results = self.neo4j_manager.execute_read_query(
            query, {"qdrant_point_id": qdrant_point_id}
        )

        if results:
            mapping = self._neo4j_result_to_mapping(results[0]["m"])
            self._cache_mapping(mapping)
            return mapping

        return None

    async def get_mapping_by_neo4j_id(self, neo4j_node_id: str) -> Optional[IDMapping]:
        """Get mapping by Neo4j node ID."""
        # Check cache first
        for mapping in self._mapping_cache.values():
            if mapping.neo4j_node_id == neo4j_node_id:
                return mapping

        # Query Neo4j
        query = """
        MATCH (m:IDMapping {neo4j_node_id: $neo4j_node_id})
        RETURN m
        """

        results = self.neo4j_manager.execute_read_query(
            query, {"neo4j_node_id": neo4j_node_id}
        )

        if results:
            mapping = self._neo4j_result_to_mapping(results[0]["m"])
            self._cache_mapping(mapping)
            return mapping

        return None

    async def get_mapping_by_neo4j_uuid(
        self, neo4j_node_uuid: str
    ) -> Optional[IDMapping]:
        """Get mapping by Neo4j node UUID."""
        # Check cache first
        for mapping in self._mapping_cache.values():
            if mapping.neo4j_node_uuid == neo4j_node_uuid:
                return mapping

        # Query Neo4j
        query = """
        MATCH (m:IDMapping {neo4j_node_uuid: $neo4j_node_uuid})
        RETURN m
        """

        results = self.neo4j_manager.execute_read_query(
            query, {"neo4j_node_uuid": neo4j_node_uuid}
        )

        if results:
            mapping = self._neo4j_result_to_mapping(results[0]["m"])
            self._cache_mapping(mapping)
            return mapping

        return None

    async def get_mapping_by_id(self, mapping_id: str) -> Optional[IDMapping]:
        """Get mapping by mapping ID."""
        # Check cache first
        if mapping_id in self._mapping_cache:
            return self._mapping_cache[mapping_id]

        # Query Neo4j
        query = """
        MATCH (m:IDMapping {mapping_id: $mapping_id})
        RETURN m
        """

        results = self.neo4j_manager.execute_read_query(
            query, {"mapping_id": mapping_id}
        )

        if results:
            mapping = self._neo4j_result_to_mapping(results[0]["m"])
            self._cache_mapping(mapping)
            return mapping

        return None

    async def update_mapping(
        self,
        mapping_id: str,
        updates: Dict[str, Any],
        validate_existence: bool = True,
    ) -> Optional[IDMapping]:
        """Update an existing mapping.

        Args:
            mapping_id: ID of mapping to update
            updates: Dictionary of fields to update
            validate_existence: Whether to validate entity existence

        Returns:
            Updated mapping or None if not found
        """
        mapping = await self.get_mapping_by_id(mapping_id)
        if not mapping:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(mapping, key):
                setattr(mapping, key, value)

        # Update temporal info
        mapping.temporal_info.transaction_time = datetime.now(UTC)
        mapping.temporal_info.version += 1

        # Validate if requested
        if validate_existence:
            await self._validate_mapping_existence(mapping)

        # Store updated mapping
        await self._store_mapping(mapping)

        # Update cache
        self._cache_mapping(mapping)

        logger.debug(f"Updated ID mapping: {mapping_id}")
        return mapping

    async def update_document_version(
        self,
        mapping_id: str,
        update_source: str,
        content_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        validate_existence: bool = True,
    ) -> Optional[IDMapping]:
        """Update document version and timestamp for a mapping.

        Args:
            mapping_id: ID of the mapping to update
            update_source: Source of the update (e.g., "qdrant", "neo4j", "manual")
            content_hash: Hash of the updated content for change detection
            metadata: Additional metadata about the update
            validate_existence: Whether to validate entity existence

        Returns:
            Updated IDMapping if successful, None otherwise
        """
        try:
            # Get existing mapping
            mapping = await self.get_mapping_by_id(mapping_id)
            if not mapping:
                logger.warning(f"Mapping {mapping_id} not found for version update")
                return None

            # Increment document version
            mapping.increment_document_version(
                update_source=update_source,
                content_hash=content_hash,
                metadata=metadata,
            )

            # Validate existence if requested
            if validate_existence:
                await self._validate_mapping_existence(mapping)

            # Store updated mapping
            await self._store_mapping(mapping)
            self._cache_mapping(mapping)

            logger.debug(
                f"Updated document version for mapping {mapping_id} to v{mapping.document_version}"
            )
            return mapping

        except Exception as e:
            logger.error(
                f"Failed to update document version for mapping {mapping_id}: {e}"
            )
            return None

    async def get_mappings_by_version_range(
        self,
        min_version: int = 1,
        max_version: Optional[int] = None,
        entity_type: Optional[EntityType] = None,
        limit: int = 1000,
    ) -> List[IDMapping]:
        """Get mappings within a specific version range.

        Args:
            min_version: Minimum document version (inclusive)
            max_version: Maximum document version (inclusive), None for no upper limit
            entity_type: Optional entity type filter
            limit: Maximum number of mappings to return

        Returns:
            List of IDMapping objects matching the criteria
        """
        try:
            # Build query conditions
            conditions = [f"m.document_version >= {min_version}"]

            if max_version is not None:
                conditions.append(f"m.document_version <= {max_version}")

            if entity_type:
                conditions.append(f"m.entity_type = '{entity_type.value}'")

            where_clause = " AND ".join(conditions)

            query = f"""
            MATCH (m:IDMapping)
            WHERE {where_clause}
            RETURN m
            ORDER BY m.document_version DESC
            LIMIT {limit}
            """

            results = self.neo4j_manager.execute_read_query(query)
            mappings = []

            for result in results:
                node_data = result["m"]
                mapping = self._neo4j_result_to_mapping(node_data)
                mappings.append(mapping)

            logger.debug(
                f"Found {len(mappings)} mappings in version range {min_version}-{max_version}"
            )
            return mappings

        except Exception as e:
            logger.error(f"Failed to get mappings by version range: {e}")
            return []

    async def get_recently_updated_mappings(
        self,
        hours: int = 24,
        update_source: Optional[str] = None,
        limit: int = 1000,
    ) -> List[IDMapping]:
        """Get mappings that were updated within the specified time period.

        Args:
            hours: Number of hours to look back
            update_source: Optional filter by update source
            limit: Maximum number of mappings to return

        Returns:
            List of recently updated IDMapping objects
        """
        try:
            from datetime import timedelta

            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
            cutoff_iso = cutoff_time.isoformat()

            # Build query conditions
            conditions = [f"m.last_update_time >= '{cutoff_iso}'"]

            if update_source:
                conditions.append(f"m.update_source = '{update_source}'")

            where_clause = " AND ".join(conditions)

            query = f"""
            MATCH (m:IDMapping)
            WHERE {where_clause}
            RETURN m
            ORDER BY m.last_update_time DESC
            LIMIT {limit}
            """

            results = self.neo4j_manager.execute_read_query(query)
            mappings = []

            for result in results:
                node_data = result["m"]
                mapping = self._neo4j_result_to_mapping(node_data)
                mappings.append(mapping)

            logger.debug(
                f"Found {len(mappings)} mappings updated in last {hours} hours"
            )
            return mappings

        except Exception as e:
            logger.error(f"Failed to get recently updated mappings: {e}")
            return []

    async def delete_mapping(self, mapping_id: str) -> bool:
        """Delete a mapping.

        Args:
            mapping_id: ID of mapping to delete

        Returns:
            True if deleted, False if not found
        """
        query = """
        MATCH (m:IDMapping {mapping_id: $mapping_id})
        DELETE m
        RETURN count(m) as deleted_count
        """

        results = self.neo4j_manager.execute_write_query(
            query, {"mapping_id": mapping_id}
        )

        deleted = results[0]["deleted_count"] > 0 if results else False

        if deleted:
            # Remove from cache
            self._mapping_cache.pop(mapping_id, None)
            logger.debug(f"Deleted ID mapping: {mapping_id}")

        return deleted

    async def get_mappings_by_entity_type(
        self,
        entity_type: EntityType,
        status: Optional[MappingStatus] = None,
        limit: int = 1000,
    ) -> List[IDMapping]:
        """Get mappings by entity type and optionally status."""
        query_parts = ["MATCH (m:IDMapping {entity_type: $entity_type})"]
        params = {"entity_type": entity_type.value}

        if status:
            query_parts.append("WHERE m.status = $status")
            params["status"] = status.value

        query_parts.extend(["RETURN m", f"LIMIT {limit}"])

        query = " ".join(query_parts)
        results = self.neo4j_manager.execute_read_query(query, params)

        mappings = []
        for result in results:
            mapping = self._neo4j_result_to_mapping(result["m"])
            mappings.append(mapping)
            self._cache_mapping(mapping)

        return mappings

    async def get_orphaned_mappings(self, limit: int = 1000) -> List[IDMapping]:
        """Get mappings where one or both entities don't exist."""
        query = """
        MATCH (m:IDMapping)
        WHERE m.status = $orphaned_status
           OR (m.qdrant_exists = false OR m.neo4j_exists = false)
        RETURN m
        LIMIT $limit
        """

        results = self.neo4j_manager.execute_read_query(
            query, {"orphaned_status": MappingStatus.ORPHANED.value, "limit": limit}
        )

        mappings = []
        for result in results:
            mapping = self._neo4j_result_to_mapping(result["m"])
            mappings.append(mapping)
            self._cache_mapping(mapping)

        return mappings

    async def validate_all_mappings(
        self,
        batch_size: int = 100,
        max_mappings: Optional[int] = None,
    ) -> Dict[str, int]:
        """Validate all mappings and update their existence status.

        Args:
            batch_size: Number of mappings to process in each batch
            max_mappings: Maximum number of mappings to validate (None for all)

        Returns:
            Dictionary with validation statistics
        """
        stats = {
            "total_validated": 0,
            "valid_mappings": 0,
            "orphaned_mappings": 0,
            "qdrant_missing": 0,
            "neo4j_missing": 0,
            "validation_errors": 0,
        }

        # Get all mappings in batches
        offset = 0
        while True:
            query = """
            MATCH (m:IDMapping)
            RETURN m
            SKIP $offset
            LIMIT $batch_size
            """

            results = self.neo4j_manager.execute_read_query(
                query, {"offset": offset, "batch_size": batch_size}
            )

            if not results:
                break

            # Process batch
            for result in results:
                if max_mappings and stats["total_validated"] >= max_mappings:
                    break

                try:
                    mapping = self._neo4j_result_to_mapping(result["m"])
                    await self._validate_mapping_existence(mapping)

                    # Update statistics
                    stats["total_validated"] += 1

                    if mapping.is_valid():
                        stats["valid_mappings"] += 1
                    elif mapping.is_orphaned():
                        stats["orphaned_mappings"] += 1
                        if not mapping.qdrant_exists:
                            stats["qdrant_missing"] += 1
                        if not mapping.neo4j_exists:
                            stats["neo4j_missing"] += 1

                    # Store updated mapping
                    await self._store_mapping(mapping)

                except Exception as e:
                    logger.error(
                        f"Error validating mapping {result['m'].get('mapping_id')}: {e}"
                    )
                    stats["validation_errors"] += 1

            if max_mappings and stats["total_validated"] >= max_mappings:
                break

            offset += batch_size

        logger.info(f"Validation completed: {stats}")
        return stats

    async def cleanup_orphaned_mappings(
        self,
        dry_run: bool = True,
        max_age_days: int = 7,
    ) -> Dict[str, int]:
        """Clean up orphaned mappings older than specified age.

        Args:
            dry_run: If True, only report what would be deleted
            max_age_days: Maximum age in days for orphaned mappings

        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = datetime.now(UTC).replace(
            day=datetime.now(UTC).day - max_age_days
        )

        query = """
        MATCH (m:IDMapping)
        WHERE m.status = $orphaned_status
          AND datetime(m.last_validation_time) < datetime($cutoff_date)
        RETURN m
        """

        results = self.neo4j_manager.execute_read_query(
            query,
            {
                "orphaned_status": MappingStatus.ORPHANED.value,
                "cutoff_date": cutoff_date.isoformat(),
            },
        )

        stats = {
            "found_orphaned": len(results),
            "deleted": 0,
            "errors": 0,
        }

        if not dry_run:
            for result in results:
                try:
                    mapping_id = result["m"]["mapping_id"]
                    if await self.delete_mapping(mapping_id):
                        stats["deleted"] += 1
                except Exception as e:
                    logger.error(f"Error deleting orphaned mapping: {e}")
                    stats["errors"] += 1

        logger.info(f"Orphaned mapping cleanup (dry_run={dry_run}): {stats}")
        return stats

    async def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get comprehensive mapping statistics."""
        query = """
        MATCH (m:IDMapping)
        RETURN 
            count(m) as total_mappings,
            count(CASE WHEN m.status = 'active' THEN 1 END) as active_mappings,
            count(CASE WHEN m.status = 'orphaned' THEN 1 END) as orphaned_mappings,
            count(CASE WHEN m.status = 'sync_failed' THEN 1 END) as sync_failed_mappings,
            count(CASE WHEN m.qdrant_exists = false THEN 1 END) as qdrant_missing,
            count(CASE WHEN m.neo4j_exists = false THEN 1 END) as neo4j_missing,
            collect(DISTINCT m.entity_type) as entity_types,
            collect(DISTINCT m.mapping_type) as mapping_types
        """

        results = self.neo4j_manager.execute_read_query(query)

        if results:
            stats = results[0]
            stats["cache_size"] = len(self._mapping_cache)
            stats["cache_max_size"] = self._cache_max_size
            return stats

        return {
            "total_mappings": 0,
            "active_mappings": 0,
            "orphaned_mappings": 0,
            "sync_failed_mappings": 0,
            "qdrant_missing": 0,
            "neo4j_missing": 0,
            "entity_types": [],
            "mapping_types": [],
            "cache_size": len(self._mapping_cache),
            "cache_max_size": self._cache_max_size,
        }

    async def _validate_mapping_existence(self, mapping: IDMapping) -> None:
        """Validate that entities referenced in mapping actually exist."""
        mapping.last_validation_time = datetime.now(UTC)

        # Validate QDrant existence
        if mapping.qdrant_point_id:
            try:
                # Check if point exists in QDrant
                client = self.qdrant_manager._ensure_client_connected()
                points = client.retrieve(
                    collection_name=self.qdrant_manager.collection_name,
                    ids=[mapping.qdrant_point_id],
                )
                mapping.qdrant_exists = len(points) > 0
            except Exception as e:
                logger.warning(
                    f"Error validating QDrant point {mapping.qdrant_point_id}: {e}"
                )
                mapping.qdrant_exists = False
        else:
            mapping.qdrant_exists = True  # No QDrant ID to validate

        # Validate Neo4j existence
        neo4j_exists = False
        if mapping.neo4j_node_id:
            try:
                query = "MATCH (n) WHERE id(n) = $node_id RETURN count(n) as count"
                results = self.neo4j_manager.execute_read_query(
                    query, {"node_id": int(mapping.neo4j_node_id)}
                )
                neo4j_exists = results[0]["count"] > 0 if results else False
            except Exception as e:
                logger.warning(
                    f"Error validating Neo4j node ID {mapping.neo4j_node_id}: {e}"
                )

        if mapping.neo4j_node_uuid and not neo4j_exists:
            try:
                query = "MATCH (n {uuid: $node_uuid}) RETURN count(n) as count"
                results = self.neo4j_manager.execute_read_query(
                    query, {"node_uuid": mapping.neo4j_node_uuid}
                )
                neo4j_exists = results[0]["count"] > 0 if results else False
            except Exception as e:
                logger.warning(
                    f"Error validating Neo4j node UUID {mapping.neo4j_node_uuid}: {e}"
                )

        mapping.neo4j_exists = neo4j_exists or (
            not mapping.neo4j_node_id and not mapping.neo4j_node_uuid
        )

        # Update status based on existence
        if mapping.is_orphaned():
            mapping.status = MappingStatus.ORPHANED
        elif mapping.status == MappingStatus.ORPHANED and not mapping.is_orphaned():
            mapping.status = MappingStatus.ACTIVE

    async def _store_mapping(self, mapping: IDMapping) -> None:
        """Store mapping in Neo4j."""
        query = """
        MERGE (m:IDMapping {mapping_id: $mapping_id})
        SET m += $properties
        """

        properties = mapping.to_dict()
        # Remove mapping_id from properties since it's used in MERGE
        properties.pop("mapping_id", None)

        self.neo4j_manager.execute_write_query(
            query, {"mapping_id": mapping.mapping_id, "properties": properties}
        )

    def _cache_mapping(self, mapping: IDMapping) -> None:
        """Cache mapping in memory with size limit."""
        if len(self._mapping_cache) >= self._cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._mapping_cache))
            del self._mapping_cache[oldest_key]

        self._mapping_cache[mapping.mapping_id] = mapping

    def _neo4j_result_to_mapping(self, node_data: Dict[str, Any]) -> IDMapping:
        """Convert Neo4j node data to IDMapping instance."""
        return IDMapping.from_dict(node_data)

    async def clear_cache(self) -> None:
        """Clear the in-memory mapping cache."""
        self._mapping_cache.clear()
        logger.debug("ID mapping cache cleared")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the ID mapping system."""
        try:
            # Test Neo4j connection
            neo4j_healthy = self.neo4j_manager.test_connection()

            # Test QDrant connection
            qdrant_healthy = True
            try:
                self.qdrant_manager._ensure_client_connected()
            except Exception:
                qdrant_healthy = False

            # Get basic statistics
            stats = await self.get_mapping_statistics()

            return {
                "healthy": neo4j_healthy and qdrant_healthy,
                "neo4j_healthy": neo4j_healthy,
                "qdrant_healthy": qdrant_healthy,
                "cache_size": len(self._mapping_cache),
                "total_mappings": stats.get("total_mappings", 0),
                "active_mappings": stats.get("active_mappings", 0),
                "orphaned_mappings": stats.get("orphaned_mappings", 0),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "cache_size": len(self._mapping_cache),
            }
