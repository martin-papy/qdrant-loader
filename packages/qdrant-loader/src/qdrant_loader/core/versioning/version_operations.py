"""Core version operations for the versioning system.

This module implements the core version operations including creation,
retrieval, comparison, and rollback functionality.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from ...utils.logging import LoggingConfig
from ..managers import IDMapping, IDMappingManager, Neo4jManager, QdrantManager
from .version_storage import VersionStorage
from .version_types import (
    VersionConfig,
    VersionDiff,
    VersionMetadata,
    VersionOperation,
    VersionSnapshot,
    VersionStatus,
    VersionType,
)


class VersionOperations:
    """Handles core version operations."""

    def __init__(
        self,
        storage: VersionStorage,
        id_mapping_manager: IDMappingManager,
        neo4j_manager: Neo4jManager,
        qdrant_manager: QdrantManager,
        config: VersionConfig,
    ):
        """Initialize version operations.

        Args:
            storage: Version storage handler
            id_mapping_manager: ID mapping manager
            neo4j_manager: Neo4j manager
            qdrant_manager: Qdrant manager
            config: Version configuration
        """
        self.storage = storage
        self.id_mapping_manager = id_mapping_manager
        self.neo4j_manager = neo4j_manager
        self.qdrant_manager = qdrant_manager
        self.config = config
        self.logger = LoggingConfig.get_logger(__name__)

    async def create_version(
        self,
        entity_id: str,
        version_type: VersionType,
        content: dict[str, Any],
        operation: VersionOperation = VersionOperation.CREATE,
        parent_version_id: str | None = None,
        supersedes: str | None = None,
        created_by: str | None = None,
        tags: list[str] | None = None,
        is_milestone: bool = False,
    ) -> VersionMetadata | None:
        """Create a new version.

        Args:
            entity_id: Entity ID
            version_type: Type of version
            content: Version content
            operation: Version operation
            parent_version_id: Optional parent version ID
            supersedes: Optional version ID this supersedes
            created_by: Optional creator identifier
            tags: Optional tags
            is_milestone: Whether this is a milestone version

        Returns:
            Version metadata if successful, None otherwise
        """
        try:
            # Get existing versions to determine version number
            existing_versions = await self.storage.get_entity_versions(
                entity_id, version_type
            )
            version_number = len(existing_versions) + 1

            # Calculate content hash
            content_hash = self._calculate_content_hash(content)
            content_size = len(json.dumps(content, default=str))

            # Create version metadata
            metadata = VersionMetadata(
                entity_id=entity_id,
                version_type=version_type,
                version_number=version_number,
                parent_version_id=parent_version_id,
                supersedes=supersedes,
                operation=operation,
                content_hash=content_hash,
                content_size=content_size,
                status=VersionStatus.ACTIVE,
                is_milestone=is_milestone,
                created_by=created_by,
                tags=set(tags or []),
            )

            # Store version metadata
            if await self.storage.store_version_metadata(metadata):
                self.logger.info(
                    f"Created version {metadata.version_id} for entity {entity_id}"
                )
                return metadata

        except Exception as e:
            self.logger.error(f"Failed to create version: {e}")

        return None

    async def get_version(self, version_id: str) -> VersionMetadata | None:
        """Get version by ID.

        Args:
            version_id: Version ID

        Returns:
            Version metadata if found, None otherwise
        """
        return await self.storage.get_version_metadata(version_id)

    async def get_latest_version(
        self, entity_id: str, version_type: VersionType
    ) -> VersionMetadata | None:
        """Get the latest version for an entity.

        Args:
            entity_id: Entity ID
            version_type: Version type

        Returns:
            Latest version metadata if found, None otherwise
        """
        versions = await self.storage.get_entity_versions(
            entity_id, version_type, limit=1
        )
        return versions[0] if versions else None

    async def compare_versions(
        self, from_version_id: str, to_version_id: str
    ) -> VersionDiff | None:
        """Compare two versions and generate a diff.

        Args:
            from_version_id: Source version ID
            to_version_id: Target version ID

        Returns:
            Version diff if successful, None otherwise
        """
        try:
            from_version = await self.storage.get_version_metadata(from_version_id)
            to_version = await self.storage.get_version_metadata(to_version_id)

            if not from_version or not to_version:
                self.logger.error("One or both versions not found for comparison")
                return None

            # Get version content based on type
            from_content = await self._get_version_content(from_version)
            to_content = await self._get_version_content(to_version)

            if from_content is None or to_content is None:
                self.logger.error("Failed to retrieve version content for comparison")
                return None

            # Calculate differences
            diff = self._calculate_diff(from_content, to_content)

            version_diff = VersionDiff(
                from_version_id=from_version_id,
                to_version_id=to_version_id,
                diff_type="content",
                added_fields=diff["added"],
                removed_fields=diff["removed"],
                modified_fields=diff["modified"],
                total_changes=diff["total_changes"],
                similarity_score=diff["similarity_score"],
            )

            return version_diff

        except Exception as e:
            self.logger.error(f"Failed to compare versions: {e}")

        return None

    async def rollback_to_version(
        self, entity_id: str, version_id: str, created_by: str | None = None
    ) -> bool:
        """Rollback an entity to a specific version.

        Args:
            entity_id: Entity ID
            version_id: Version ID to rollback to
            created_by: Optional creator identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the target version
            target_version = await self.storage.get_version_metadata(version_id)
            if not target_version:
                self.logger.error(f"Target version {version_id} not found")
                return False

            # Get version content
            content = await self._get_version_content(target_version)
            if content is None:
                self.logger.error("Failed to retrieve version content for rollback")
                return False

            # Restore content based on version type
            success = await self._restore_version_content(target_version, content)

            if success:
                # Create a new version to track the rollback
                await self.create_version(
                    entity_id=entity_id,
                    version_type=target_version.version_type,
                    content=content,
                    operation=VersionOperation.ROLLBACK,
                    created_by=created_by,
                    tags=["rollback", f"restored_from_{version_id}"],
                )

                self.logger.info(
                    f"Successfully rolled back entity {entity_id} to version {version_id}"
                )
                return True

        except Exception as e:
            self.logger.error(f"Failed to rollback to version: {e}")

        return False

    async def create_snapshot(
        self,
        description: str = "",
        entity_ids: list[str] | None = None,
        created_by: str | None = None,
        tags: list[str] | None = None,
    ) -> VersionSnapshot | None:
        """Create a point-in-time snapshot.

        Args:
            description: Snapshot description
            entity_ids: Optional list of specific entity IDs to include
            created_by: Optional creator identifier
            tags: Optional tags

        Returns:
            Version snapshot if successful, None otherwise
        """
        try:
            snapshot = VersionSnapshot(
                description=description,
                created_by=created_by,
                tags=set(tags or []),
            )

            # Collect entities
            if entity_ids:
                # Specific entities
                for entity_id in entity_ids:
                    entity_data = await self._get_entity_snapshot_data(entity_id)
                    if entity_data:
                        snapshot.entities[entity_id] = entity_data
            else:
                # All entities - this would be a large operation
                # For now, we'll limit to recent entities
                pass

            # Update counts
            snapshot.entity_count = len(snapshot.entities)
            snapshot.relationship_count = len(snapshot.relationships)
            snapshot.mapping_count = len(snapshot.mappings)

            # Store snapshot
            if await self.storage.store_version_snapshot(snapshot):
                self.logger.info(f"Created snapshot {snapshot.snapshot_id}")
                return snapshot

        except Exception as e:
            self.logger.error(f"Failed to create snapshot: {e}")

        return None

    def _calculate_content_hash(self, content: dict[str, Any]) -> str:
        """Calculate hash of content for change detection.

        Args:
            content: Content to hash

        Returns:
            Content hash
        """
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()

    async def _get_version_content(
        self, version: VersionMetadata
    ) -> dict[str, Any] | None:
        """Get content for a version based on its type.

        Args:
            version: Version metadata

        Returns:
            Version content if found, None otherwise
        """
        try:
            if version.version_type == VersionType.DOCUMENT:
                # Get document mapping
                mapping = await self.id_mapping_manager.get_mapping_by_id(
                    version.entity_id
                )
                return mapping.to_dict() if mapping else None

            elif version.version_type == VersionType.ENTITY:
                # Get entity from Neo4j using generic query
                query = "MATCH (n) WHERE id(n) = $node_id OR n.uuid = $node_id RETURN n"
                results = self.neo4j_manager.execute_read_query(
                    query, {"node_id": version.entity_id}
                )
                if results:
                    node_data = results[0]["n"]
                    # Convert Neo4j node to dictionary format
                    return {
                        "id": (
                            node_data.element_id
                            if hasattr(node_data, "element_id")
                            else str(node_data.id)
                        ),
                        "labels": (
                            list(node_data.labels)
                            if hasattr(node_data, "labels")
                            else []
                        ),
                        "properties": (
                            dict(node_data) if hasattr(node_data, "__iter__") else {}
                        ),
                    }
                return None

            elif version.version_type == VersionType.RELATIONSHIP:
                # Get relationship from Neo4j using generic query
                query = "MATCH ()-[r]-() WHERE id(r) = $rel_id RETURN r"
                results = self.neo4j_manager.execute_read_query(
                    query, {"rel_id": version.entity_id}
                )
                if results:
                    rel_data = results[0]["r"]
                    # Convert Neo4j relationship to dictionary format
                    return {
                        "id": (
                            rel_data.element_id
                            if hasattr(rel_data, "element_id")
                            else str(rel_data.id)
                        ),
                        "type": (
                            rel_data.type if hasattr(rel_data, "type") else "UNKNOWN"
                        ),
                        "properties": (
                            dict(rel_data) if hasattr(rel_data, "__iter__") else {}
                        ),
                    }
                return None

            elif version.version_type == VersionType.MAPPING:
                # Get mapping data
                mapping = await self.id_mapping_manager.get_mapping_by_id(
                    version.entity_id
                )
                return mapping.to_dict() if mapping else None

        except Exception as e:
            self.logger.error(f"Failed to get version content: {e}")

        return None

    async def _restore_version_content(
        self, version: VersionMetadata, content: dict[str, Any]
    ) -> bool:
        """Restore content for a version.

        Args:
            version: Version metadata
            content: Content to restore

        Returns:
            True if successful, False otherwise
        """
        try:
            if version.version_type == VersionType.DOCUMENT:
                # Restore document mapping
                mapping = IDMapping.from_dict(content)
                return (
                    await self.id_mapping_manager.update_mapping(
                        mapping.mapping_id, content
                    )
                    is not None
                )

            elif version.version_type == VersionType.ENTITY:
                # Restore entity using generic Neo4j update
                properties = content.get("properties", {})
                query = """
                MATCH (n) WHERE id(n) = $node_id OR n.uuid = $node_id
                SET n += $properties
                RETURN n
                """
                results = self.neo4j_manager.execute_write_query(
                    query, {"node_id": version.entity_id, "properties": properties}
                )
                return len(results) > 0

            elif version.version_type == VersionType.RELATIONSHIP:
                # Restore relationship using generic Neo4j update
                properties = content.get("properties", {})
                query = """
                MATCH ()-[r]-() WHERE id(r) = $rel_id
                SET r += $properties
                RETURN r
                """
                results = self.neo4j_manager.execute_write_query(
                    query, {"rel_id": version.entity_id, "properties": properties}
                )
                return len(results) > 0

            elif version.version_type == VersionType.MAPPING:
                # Restore mapping
                mapping = IDMapping.from_dict(content)
                return (
                    await self.id_mapping_manager.update_mapping(
                        mapping.mapping_id, content
                    )
                    is not None
                )

        except Exception as e:
            self.logger.error(f"Failed to restore version content: {e}")

        return False

    def _calculate_diff(
        self, from_content: dict[str, Any], to_content: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate differences between two content dictionaries.

        Args:
            from_content: Source content
            to_content: Target content

        Returns:
            Diff information
        """
        added = {}
        removed = {}
        modified = {}

        # Find added and modified fields
        for key, value in to_content.items():
            if key not in from_content:
                added[key] = value
            elif from_content[key] != value:
                modified[key] = (from_content[key], value)

        # Find removed fields
        for key, value in from_content.items():
            if key not in to_content:
                removed[key] = value

        total_changes = len(added) + len(removed) + len(modified)

        # Calculate similarity score (simple implementation)
        total_fields = len(set(from_content.keys()) | set(to_content.keys()))
        unchanged_fields = total_fields - total_changes
        similarity_score = unchanged_fields / total_fields if total_fields > 0 else 1.0

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "total_changes": total_changes,
            "similarity_score": similarity_score,
        }

    async def _get_entity_snapshot_data(
        self, entity_id: str
    ) -> dict[str, Any] | None:
        """Get snapshot data for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Entity snapshot data if found, None otherwise
        """
        try:
            # This would collect all relevant data for the entity
            # including its current state, relationships, etc.
            # Implementation would depend on specific requirements
            return {"entity_id": entity_id, "timestamp": datetime.now(UTC).isoformat()}

        except Exception as e:
            self.logger.error(f"Failed to get entity snapshot data: {e}")

        return None
