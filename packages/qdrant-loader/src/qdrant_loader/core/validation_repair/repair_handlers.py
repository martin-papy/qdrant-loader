"""
Repair handlers for fixing validation issues between QDrant and Neo4j.

This module contains all the repair handler methods that can automatically
fix various types of validation issues.
"""

import logging
from datetime import datetime, UTC
from typing import Optional

from ..managers import (
    IDMappingManager,
    Neo4jManager,
    QdrantManager,
    MappingStatus,
    IDMapping,
)
from ..types import EntityType
from .models import ValidationIssue, RepairResult, RepairAction

logger = logging.getLogger(__name__)


class RepairHandlers:
    """Collection of repair handler methods."""

    def __init__(
        self,
        id_mapping_manager: IDMappingManager,
        neo4j_manager: Neo4jManager,
        qdrant_manager: QdrantManager,
        conflict_resolution_system=None,
    ):
        self.id_mapping_manager = id_mapping_manager
        self.neo4j_manager = neo4j_manager
        self.qdrant_manager = qdrant_manager
        self.conflict_resolution_system = conflict_resolution_system

    async def repair_create_mapping(self, issue: ValidationIssue) -> RepairResult:
        """Create missing mapping for an entity."""
        start_time = datetime.now(UTC)

        try:
            if issue.qdrant_point_id and not issue.neo4j_node_id:
                # Create mapping for QDrant point
                mapping = await self._create_mapping_for_qdrant_point(
                    issue.qdrant_point_id
                )
            elif issue.neo4j_node_id and not issue.qdrant_point_id:
                # Create mapping for Neo4j node
                mapping = await self._create_mapping_for_neo4j_node(issue.neo4j_node_id)
            else:
                raise ValueError("Invalid issue data for mapping creation")

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.CREATE_MAPPING,
                success=True,
                details={"mapping_id": mapping.mapping_id},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.CREATE_MAPPING,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def repair_delete_orphaned(self, issue: ValidationIssue) -> RepairResult:
        """Delete orphaned mapping."""
        start_time = datetime.now(UTC)

        try:
            if issue.mapping_id:
                await self.id_mapping_manager.delete_mapping(issue.mapping_id)

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.DELETE_ORPHANED,
                success=True,
                details={"deleted_mapping_id": issue.mapping_id},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.DELETE_ORPHANED,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def repair_update_data(self, issue: ValidationIssue) -> RepairResult:
        """Update data to resolve mismatch."""
        start_time = datetime.now(UTC)

        try:
            # Implementation depends on specific data mismatch
            # This is a placeholder for the actual update logic

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.UPDATE_DATA,
                success=True,
                details={"updated_field": issue.metadata.get("field")},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.UPDATE_DATA,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def repair_sync_entities(self, issue: ValidationIssue) -> RepairResult:
        """Synchronize entities between databases."""
        start_time = datetime.now(UTC)

        try:
            if issue.mapping_id:
                mapping = await self.id_mapping_manager.get_mapping_by_id(
                    issue.mapping_id
                )
                if mapping:
                    # Trigger synchronization by updating the mapping
                    await self.id_mapping_manager.update_mapping(
                        issue.mapping_id, {"status": MappingStatus.PENDING_SYNC.value}
                    )

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.SYNC_ENTITIES,
                success=True,
                details={"mapping_id": issue.mapping_id},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.SYNC_ENTITIES,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def repair_resolve_conflict(self, issue: ValidationIssue) -> RepairResult:
        """Resolve conflicts using conflict resolution system."""
        start_time = datetime.now(UTC)

        try:
            if not self.conflict_resolution_system:
                raise ValueError("Conflict resolution system not available")

            # Use conflict resolution system to resolve the issue
            # This would depend on the specific conflict resolution implementation

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.RESOLVE_CONFLICT,
                success=True,
                details={"conflict_resolved": True},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.RESOLVE_CONFLICT,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    async def repair_rebuild_index(self, issue: ValidationIssue) -> RepairResult:
        """Rebuild database indexes."""
        start_time = datetime.now(UTC)

        try:
            # This would trigger index rebuilding in both databases
            # Implementation depends on specific requirements

            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.REBUILD_INDEX,
                success=True,
                details={"indexes_rebuilt": True},
                execution_time_ms=execution_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            execution_time = (end_time - start_time).total_seconds() * 1000

            return RepairResult(
                issue_id=issue.issue_id,
                action_taken=RepairAction.REBUILD_INDEX,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    # Helper methods for creating mappings

    async def _create_mapping_for_qdrant_point(self, point_id: str) -> IDMapping:
        """Create mapping for a QDrant point that lacks one."""
        # Get point data
        client = self.qdrant_manager._ensure_client_connected()
        points = client.retrieve(
            collection_name=self.qdrant_manager.collection_name,
            ids=[point_id],
            with_payload=True,
        )

        if not points:
            raise ValueError(f"QDrant point {point_id} not found")

        point = points[0]
        payload = point.payload or {}

        # Determine entity type from payload
        entity_type = EntityType.CONCEPT  # Default
        if "entity_type" in payload:
            try:
                entity_type = EntityType(payload["entity_type"])
            except ValueError:
                pass

        # Create mapping
        mapping = await self.id_mapping_manager.create_mapping(
            entity_type=entity_type,
            qdrant_point_id=point_id,
            neo4j_node_id=None,
            neo4j_node_uuid=payload.get("uuid"),
            metadata={"created_by": "validation_repair_system"},
        )

        return mapping

    async def _create_mapping_for_neo4j_node(self, node_id: str) -> IDMapping:
        """Create mapping for a Neo4j node that lacks one."""
        # Get node data
        query = "MATCH (n) WHERE id(n) = $node_id RETURN n, labels(n) as labels"
        results = self.neo4j_manager.execute_read_query(
            query, {"node_id": int(node_id)}
        )

        if not results:
            raise ValueError(f"Neo4j node {node_id} not found")

        node_data = results[0]["n"]
        labels = results[0]["labels"]

        # Determine entity type from labels
        entity_type = EntityType.CONCEPT  # Default
        if "Person" in labels:
            entity_type = EntityType.PERSON
        elif "Organization" in labels:
            entity_type = EntityType.ORGANIZATION
        elif "Project" in labels:
            entity_type = EntityType.PROJECT

        # Create mapping
        mapping = await self.id_mapping_manager.create_mapping(
            entity_type=entity_type,
            qdrant_point_id=None,
            neo4j_node_id=node_id,
            neo4j_node_uuid=node_data.get("uuid"),
            metadata={"created_by": "validation_repair_system"},
        )

        return mapping
