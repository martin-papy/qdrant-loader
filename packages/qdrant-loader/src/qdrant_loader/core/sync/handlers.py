"""Operation Handlers for Enhanced Sync Event System.

This module contains the specific handlers for different types of sync operations,
extracted from the main enhanced sync event system for better maintainability.
"""

import uuid
from datetime import UTC, datetime

from ...utils.logging import LoggingConfig
from ..atomic_transactions import OperationType, TransactionContext
from ..managers import (
    IDMapping,
    IDMappingManager,
    MappingType,
    Neo4jManager,
    QdrantManager,
)
from .event_system import DatabaseType
from .operations import EnhancedSyncOperation

logger = LoggingConfig.get_logger(__name__)


class SyncOperationHandlers:
    """Handlers for different types of sync operations."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        enable_cascading_deletes: bool = True,
        enable_versioned_updates: bool = True,
    ):
        """Initialize operation handlers.

        Args:
            qdrant_manager: QDrant manager instance
            neo4j_manager: Neo4j manager instance
            id_mapping_manager: ID mapping manager instance
            enable_cascading_deletes: Whether to enable cascading deletions
            enable_versioned_updates: Whether to enable versioned updates
        """
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.enable_cascading_deletes = enable_cascading_deletes
        self.enable_versioned_updates = enable_versioned_updates

    async def handle_create_document(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle CREATE document operation."""
        logger.debug(f"Handling CREATE document operation {operation.operation_id}")

        operation.mark_processing(tx.transaction.transaction_id)

        # Create mapping if it doesn't exist
        mapping = await self._ensure_mapping_exists(operation)

        # Add operations to both databases
        if DatabaseType.QDRANT in operation.target_databases:
            await self._add_qdrant_create_operation(tx, operation, mapping)

        if DatabaseType.NEO4J in operation.target_databases:
            await self._add_neo4j_create_operation(tx, operation, mapping)

        # Update mapping version
        if mapping:
            await self._update_mapping_version(mapping, operation)

    async def handle_update_document(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle UPDATE document operation with versioning."""
        logger.debug(f"Handling UPDATE document operation {operation.operation_id}")

        operation.mark_processing(tx.transaction.transaction_id)

        # Get existing mapping
        mapping = await self._get_mapping_for_operation(operation)
        if not mapping:
            raise ValueError(f"No mapping found for entity {operation.entity_id}")

        # Handle versioned updates if enabled
        if self.enable_versioned_updates:
            await self._handle_versioned_update(tx, operation, mapping)
        else:
            await self._handle_simple_update(tx, operation, mapping)

        # Update mapping version
        await self._update_mapping_version(mapping, operation)

    async def handle_delete_document(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle DELETE document operation with cascading."""
        logger.debug(f"Handling DELETE document operation {operation.operation_id}")
        logger.debug(f"Operation entity_id: {operation.entity_id}")
        logger.debug(f"Operation target_databases: {operation.target_databases}")

        operation.mark_processing(tx.transaction.transaction_id)

        # Get existing mapping
        mapping = await self._get_mapping_for_operation(operation)
        logger.debug(f"Found mapping: {mapping}")
        if not mapping:
            logger.warning(f"No mapping found for entity {operation.entity_id}")
            return

        # Handle cascading deletes if enabled
        if self.enable_cascading_deletes:
            await self._handle_cascading_delete(tx, operation, mapping)
        else:
            await self._handle_simple_delete(tx, operation, mapping)

        # Remove mapping
        await self.id_mapping_manager.delete_mapping(mapping.mapping_id)

    async def handle_create_entity(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle CREATE entity operation."""
        # Similar to create document but for entities
        await self.handle_create_document(tx, operation)

    async def handle_update_entity(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle UPDATE entity operation."""
        # Similar to update document but for entities
        await self.handle_update_document(tx, operation)

    async def handle_delete_entity(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle DELETE entity operation."""
        # Similar to delete document but for entities
        await self.handle_delete_document(tx, operation)

    async def handle_cascade_delete(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle CASCADE delete operation."""
        logger.debug(f"Handling CASCADE delete operation {operation.operation_id}")

        operation.mark_processing(tx.transaction.transaction_id)

        # Get existing mapping
        mapping = await self._get_mapping_for_operation(operation)
        if not mapping:
            logger.warning(
                f"No mapping found for cascade delete of entity {operation.entity_id}"
            )
            return

        # Perform cascading delete
        await self._handle_cascading_delete(tx, operation, mapping)

        # Remove mapping
        await self.id_mapping_manager.delete_mapping(mapping.mapping_id)

    async def handle_version_update(
        self, tx: TransactionContext, operation: EnhancedSyncOperation
    ) -> None:
        """Handle VERSION update operation."""
        logger.debug(f"Handling VERSION update operation {operation.operation_id}")

        operation.mark_processing(tx.transaction.transaction_id)

        # Get existing mapping
        mapping = await self._get_mapping_for_operation(operation)
        if not mapping:
            raise ValueError(
                f"No mapping found for version update of entity {operation.entity_id}"
            )

        # Handle versioned update
        await self._handle_versioned_update(tx, operation, mapping)

        # Update mapping version
        await self._update_mapping_version(mapping, operation)

    # Helper methods for operation processing

    async def _ensure_mapping_exists(
        self, operation: EnhancedSyncOperation
    ) -> IDMapping | None:
        """Ensure mapping exists for the operation."""
        if not operation.entity_id:
            return None

        # Try to get existing mapping
        mapping = await self._get_mapping_for_operation(operation)
        if mapping:
            return mapping

        # Create new mapping
        mapping = await self.id_mapping_manager.create_mapping(
            qdrant_point_id=(
                operation.entity_id
                if operation.source_event
                and operation.source_event.database_type == DatabaseType.QDRANT
                else None
            ),
            neo4j_node_id=(
                operation.entity_id
                if operation.source_event
                and operation.source_event.database_type == DatabaseType.NEO4J
                else None
            ),
            entity_type=operation.entity_type,
            mapping_type=operation.mapping_type,
            metadata=operation.metadata,
        )

        return mapping

    async def _get_mapping_for_operation(
        self, operation: EnhancedSyncOperation
    ) -> IDMapping | None:
        """Get mapping for the operation."""
        if not operation.entity_id:
            return None

        # Try different lookup methods based on source
        if operation.source_event:
            if operation.source_event.database_type == DatabaseType.QDRANT:
                return await self.id_mapping_manager.get_mapping_by_qdrant_id(
                    operation.entity_id
                )
            elif operation.source_event.database_type == DatabaseType.NEO4J:
                return await self.id_mapping_manager.get_mapping_by_neo4j_id(
                    operation.entity_id
                )

        # Try UUID lookup
        if operation.entity_uuid:
            mapping = await self.id_mapping_manager.get_mapping_by_neo4j_uuid(
                operation.entity_uuid
            )
            if mapping:
                return mapping

        # If no source event, try both QDrant and Neo4j ID lookups
        # Try QDrant ID first
        mapping = await self.id_mapping_manager.get_mapping_by_qdrant_id(
            operation.entity_id
        )
        if mapping:
            return mapping

        # Try Neo4j ID
        mapping = await self.id_mapping_manager.get_mapping_by_neo4j_id(
            operation.entity_id
        )
        if mapping:
            return mapping

        return None

    async def _add_qdrant_create_operation(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping | None,
    ) -> None:
        """Add QDrant create operation to transaction."""
        if not mapping or not mapping.qdrant_point_id:
            return

        await tx.add_qdrant_operation(
            operation_type=OperationType.CREATE,
            entity_id=mapping.qdrant_point_id,
            operation_data=operation.operation_data,
        )

    async def _add_neo4j_create_operation(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping | None,
    ) -> None:
        """Add Neo4j create operation to transaction."""
        if not mapping:
            return

        node_data = {
            "labels": (
                ["Document"]
                if operation.mapping_type == MappingType.DOCUMENT
                else ["Entity"]
            ),
            "properties": {
                "uuid": mapping.neo4j_node_uuid or mapping.mapping_id,
                **operation.operation_data,
            },
        }

        await tx.add_neo4j_operation(
            operation_type=OperationType.CREATE,
            entity_id=mapping.neo4j_node_uuid or mapping.mapping_id,
            operation_data=node_data,
        )

    async def _handle_versioned_update(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle versioned update with relationship preservation."""
        # Create new version node in Neo4j
        if DatabaseType.NEO4J in operation.target_databases:
            new_version_uuid = str(uuid.uuid4())
            node_data = {
                "labels": ["Document", "Version"],
                "properties": {
                    "uuid": new_version_uuid,
                    "version": mapping.document_version + 1,
                    "previous_version": mapping.document_version,
                    "original_uuid": mapping.neo4j_node_uuid,
                    **operation.operation_data,
                },
            }

            await tx.add_neo4j_operation(
                operation_type=OperationType.CREATE,
                entity_id=new_version_uuid,
                operation_data=node_data,
            )

            # Create relationship to previous version
            relationship_data = {
                "type": "PREVIOUS_VERSION",
                "from_uuid": new_version_uuid,
                "to_uuid": mapping.neo4j_node_uuid,
                "properties": {
                    "created_at": datetime.now(UTC).isoformat(),
                    "version_increment": 1,
                },
            }

            await tx.add_neo4j_operation(
                operation_type=OperationType.CREATE,
                entity_id=f"{new_version_uuid}_rel_{mapping.neo4j_node_uuid}",
                operation_data=relationship_data,
            )

        # Update QDrant if needed
        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            await tx.add_qdrant_operation(
                operation_type=OperationType.UPDATE,
                entity_id=mapping.qdrant_point_id,
                operation_data=operation.operation_data,
            )

    async def _handle_simple_update(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle simple update without versioning."""
        if DatabaseType.NEO4J in operation.target_databases and mapping.neo4j_node_uuid:
            await tx.add_neo4j_operation(
                operation_type=OperationType.UPDATE,
                entity_id=mapping.neo4j_node_uuid,
                operation_data={"properties": operation.operation_data},
            )

        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            await tx.add_qdrant_operation(
                operation_type=OperationType.UPDATE,
                entity_id=mapping.qdrant_point_id,
                operation_data=operation.operation_data,
            )

    async def _handle_cascading_delete(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle cascading delete with cleanup."""
        # Delete from Neo4j with all relationships
        if DatabaseType.NEO4J in operation.target_databases and mapping.neo4j_node_uuid:
            await tx.add_neo4j_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.neo4j_node_uuid,
                operation_data={"cascade": True},
            )

        # Delete from QDrant
        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            await tx.add_qdrant_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.qdrant_point_id,
                operation_data={},
            )

    async def _handle_simple_delete(
        self,
        tx: TransactionContext,
        operation: EnhancedSyncOperation,
        mapping: IDMapping,
    ) -> None:
        """Handle simple delete without cascading."""
        logger.debug(
            f"_handle_simple_delete called for operation {operation.operation_id}"
        )
        logger.debug(f"Target databases: {operation.target_databases}")
        logger.debug(f"Mapping neo4j_node_uuid: {mapping.neo4j_node_uuid}")
        logger.debug(f"Mapping qdrant_point_id: {mapping.qdrant_point_id}")

        if DatabaseType.NEO4J in operation.target_databases and mapping.neo4j_node_uuid:
            logger.debug("Adding Neo4j delete operation to transaction")
            await tx.add_neo4j_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.neo4j_node_uuid,
                operation_data={},
            )

        if (
            DatabaseType.QDRANT in operation.target_databases
            and mapping.qdrant_point_id
        ):
            logger.debug(
                f"Adding QDrant delete operation to transaction for point {mapping.qdrant_point_id}"
            )
            await tx.add_qdrant_operation(
                operation_type=OperationType.DELETE,
                entity_id=mapping.qdrant_point_id,
                operation_data={},
            )

    async def _update_mapping_version(
        self, mapping: IDMapping, operation: EnhancedSyncOperation
    ) -> None:
        """Update mapping version information."""
        source_db = "unknown"
        if operation.source_event:
            source_db = operation.source_event.database_type.value

        await self.id_mapping_manager.update_document_version(
            mapping_id=mapping.mapping_id,
            update_source=source_db,
            content_hash=operation.content_hash,
            metadata={
                "operation_id": operation.operation_id,
                "operation_type": operation.operation_type.value,
                "timestamp": operation.timestamp.isoformat(),
            },
        )
