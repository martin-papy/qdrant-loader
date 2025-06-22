"""Simple delete sync test that bypasses the atomic transaction system."""

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from qdrant_loader.core.atomic_transactions.context import TransactionContext
from qdrant_loader.core.atomic_transactions.enums import OperationType
from qdrant_loader.core.atomic_transactions.models import (
    DatabaseOperation,
    DistributedTransaction,
)
from qdrant_loader.core.managers.id_mapping_manager import MappingType
from qdrant_loader.core.sync.event_system import DatabaseType
from qdrant_loader.core.sync.handlers import SyncOperationHandlers
from qdrant_loader.core.sync.operations import EnhancedSyncOperation
from qdrant_loader.core.sync.types import SyncOperationType
from qdrant_loader.core.types import EntityType


class MockTransactionContext(TransactionContext):
    """Mock transaction context for testing."""

    def __init__(self):
        # Create a mock transaction
        mock_transaction = DistributedTransaction()
        mock_manager = AsyncMock()

        # Initialize parent with mocks
        super().__init__(mock_manager, mock_transaction)

        # Track operations for verification
        self.qdrant_operations = []
        self.neo4j_operations = []

    async def add_qdrant_operation(
        self,
        operation_type: OperationType,
        entity_id: str,
        operation_data: dict[str, Any] | None = None,
    ) -> DatabaseOperation:
        """Mock add_qdrant_operation."""
        operation = DatabaseOperation(
            operation_type=operation_type,
            database="qdrant",
            entity_id=entity_id,
            operation_data=operation_data,
        )
        # Track for verification
        self.qdrant_operations.append(
            {
                "operation_type": operation_type,
                "entity_id": entity_id,
                "operation_data": operation_data,
            }
        )
        # Also call parent to maintain transaction state
        return await super().add_qdrant_operation(
            operation_type, entity_id, operation_data
        )

    async def add_neo4j_operation(
        self,
        operation_type: OperationType,
        entity_id: str,
        operation_data: dict[str, Any] | None = None,
    ) -> DatabaseOperation:
        """Mock add_neo4j_operation."""
        operation = DatabaseOperation(
            operation_type=operation_type,
            database="neo4j",
            entity_id=entity_id,
            operation_data=operation_data,
        )
        # Track for verification
        self.neo4j_operations.append(
            {
                "operation_type": operation_type,
                "entity_id": entity_id,
                "operation_data": operation_data,
            }
        )
        # Also call parent to maintain transaction state
        return await super().add_neo4j_operation(
            operation_type, entity_id, operation_data
        )


class TestSimpleDeleteSync:
    """Test delete sync operations directly."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_handlers(self, qdrant_manager, neo4j_manager, id_mapping_manager):
        """Set up the sync handlers for testing."""
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager

        # Initialize sync operation handlers
        self.handlers = SyncOperationHandlers(
            qdrant_manager=self.qdrant_manager,
            neo4j_manager=self.neo4j_manager,
            id_mapping_manager=self.id_mapping_manager,
            enable_cascading_deletes=True,
            enable_versioned_updates=True,
        )

    @pytest.mark.asyncio
    async def test_delete_document_handler_direct(self):
        """Test the delete document handler directly."""
        # Create test data
        document_id = str(uuid.uuid4())
        qdrant_point_id = f"point_{document_id}"

        # Create a mapping in the mock ID mapping manager
        mapping = await self.id_mapping_manager.create_mapping(
            qdrant_point_id=qdrant_point_id,
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            entity_name=document_id,
            metadata={"title": "Test Document"},
            validate_existence=False,
        )

        # Create delete operation
        delete_operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            entity_id=qdrant_point_id,  # Use qdrant_point_id for mapping lookup
            operation_data={
                "qdrant_point_id": qdrant_point_id,
                "reason": "test_deletion",
            },
            metadata={"reason": "test_deletion"},
            target_databases={DatabaseType.QDRANT, DatabaseType.NEO4J},
        )

        # Create mock transaction context
        tx_context = MockTransactionContext()

        # Call the delete handler directly
        await self.handlers.handle_delete_document(tx_context, delete_operation)

        # Verify that operations were added to the transaction
        assert len(tx_context.qdrant_operations) > 0, "No QDrant operations were added"
        assert len(tx_context.neo4j_operations) > 0, "No Neo4j operations were added"

        # Check QDrant delete operation
        qdrant_delete_ops = [
            op
            for op in tx_context.qdrant_operations
            if op["operation_type"].name == "DELETE"
        ]
        assert (
            len(qdrant_delete_ops) == 1
        ), f"Expected 1 QDrant delete operation, got {len(qdrant_delete_ops)}"
        assert qdrant_delete_ops[0]["entity_id"] == qdrant_point_id

        # Check Neo4j delete operation
        neo4j_delete_ops = [
            op
            for op in tx_context.neo4j_operations
            if op["operation_type"].name == "DELETE"
        ]
        assert (
            len(neo4j_delete_ops) == 1
        ), f"Expected 1 Neo4j delete operation, got {len(neo4j_delete_ops)}"

        print("✅ Delete operations added successfully:")
        print(f"   QDrant operations: {len(tx_context.qdrant_operations)}")
        print(f"   Neo4j operations: {len(tx_context.neo4j_operations)}")
        print(f"   QDrant delete entity_id: {qdrant_delete_ops[0]['entity_id']}")
        print(f"   Neo4j delete entity_id: {neo4j_delete_ops[0]['entity_id']}")

    @pytest.mark.asyncio
    async def test_delete_document_no_mapping(self):
        """Test delete operation when no mapping exists."""
        # Create delete operation with non-existent entity
        delete_operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            entity_id="non_existent_id",
            operation_data={"reason": "test_deletion"},
            metadata={"reason": "test_deletion"},
            target_databases={DatabaseType.QDRANT, DatabaseType.NEO4J},
        )

        # Create mock transaction context
        tx_context = MockTransactionContext()

        # Call the delete handler directly
        await self.handlers.handle_delete_document(tx_context, delete_operation)

        # Verify that no operations were added (since no mapping exists)
        assert (
            len(tx_context.qdrant_operations) == 0
        ), "QDrant operations were added despite no mapping"
        assert (
            len(tx_context.neo4j_operations) == 0
        ), "Neo4j operations were added despite no mapping"

        print("✅ No operations added when mapping doesn't exist (expected behavior)")
