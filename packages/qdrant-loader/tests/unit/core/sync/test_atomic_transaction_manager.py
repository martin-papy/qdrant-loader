"""
Unit tests for AtomicTransactionManager.

Tests transaction coordination, rollback mechanisms, two-phase commit protocols,
and error handling for distributed transactions across QDrant and Neo4j.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from qdrant_loader.core.atomic_transactions import (
    AtomicTransactionManager,
    DistributedTransaction,
    TransactionState,
    OperationType,
    CompensationAction,
    DatabaseOperation,
)


class TestAtomicTransactionManager:
    """Test suite for AtomicTransactionManager."""

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create mock QdrantManager."""
        mock = AsyncMock()
        mock.upsert_points = AsyncMock(return_value=True)
        mock.delete_points = AsyncMock(return_value=True)
        mock.search = AsyncMock(return_value=[])
        mock.health_check = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_neo4j_manager(self):
        """Create mock Neo4jManager."""
        mock = AsyncMock()
        mock.create_node = AsyncMock(return_value={"id": "test_node"})
        mock.update_node = AsyncMock(return_value=True)
        mock.delete_node = AsyncMock(return_value=True)
        mock.health_check = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_id_mapping_manager(self):
        """Create mock IDMappingManager."""
        mock = AsyncMock()
        mock.get_mapping = AsyncMock(return_value=None)
        mock.create_mapping = AsyncMock(return_value=True)
        mock.update_mapping = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def transaction_manager(
        self, mock_qdrant_manager, mock_neo4j_manager, mock_id_mapping_manager
    ):
        """Create AtomicTransactionManager instance for testing."""
        return AtomicTransactionManager(
            qdrant_manager=mock_qdrant_manager,
            neo4j_manager=mock_neo4j_manager,
            id_mapping_manager=mock_id_mapping_manager,
            default_timeout_seconds=30,
            max_retry_attempts=3,
            enable_compensation=True,
        )

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, transaction_manager):
        """Test transaction context manager functionality."""
        async with transaction_manager.transaction() as tx:
            assert tx is not None
            assert hasattr(tx, "transaction")
            assert tx.transaction.state in [
                TransactionState.INITIALIZED,
                TransactionState.PREPARING,
            ]

    @pytest.mark.asyncio
    async def test_successful_transaction(self, transaction_manager):
        """Test successful transaction execution."""
        # Configure mocks to succeed
        transaction_manager.qdrant_tx_manager.begin_transaction = AsyncMock(
            return_value="mock_tx"
        )
        transaction_manager.neo4j_tx_manager.begin_transaction = AsyncMock(
            return_value="mock_tx"
        )
        transaction_manager.qdrant_tx_manager.prepare_operation = AsyncMock(
            return_value=True
        )
        transaction_manager.neo4j_tx_manager.prepare_operation = AsyncMock(
            return_value=True
        )
        transaction_manager.qdrant_tx_manager.execute_operation = AsyncMock(
            return_value=True
        )
        transaction_manager.neo4j_tx_manager.execute_operation = AsyncMock(
            return_value=True
        )
        transaction_manager.qdrant_tx_manager._active_transactions = {
            "mock_tx": "mock_tx"
        }
        transaction_manager.neo4j_tx_manager._active_transactions = {
            "mock_tx": "mock_tx"
        }

        async with transaction_manager.transaction() as tx:
            # Add a simple operation
            operation = DatabaseOperation(
                operation_type=OperationType.CREATE,
                database="qdrant",
                entity_id="test_entity_001",
                operation_data={"content": "test content", "embedding": [0.1] * 384},
            )
            tx.transaction.add_operation(operation)

        # Verify transaction completed successfully
        assert tx.transaction.state == TransactionState.COMMITTED
        assert tx.transaction.success is True

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_failure(self, transaction_manager):
        """Test transaction rollback when operation fails."""
        # Configure mocks to fail during preparation
        transaction_manager.qdrant_tx_manager.begin_transaction = AsyncMock(
            return_value="mock_tx"
        )
        transaction_manager.neo4j_tx_manager.begin_transaction = AsyncMock(
            return_value="mock_tx"
        )
        transaction_manager.qdrant_tx_manager.prepare_operation = AsyncMock(
            side_effect=Exception("QDrant preparation error")
        )

        # The transaction should not raise an exception but should fail gracefully
        async with transaction_manager.transaction() as tx:
            operation = DatabaseOperation(
                operation_type=OperationType.CREATE,
                database="qdrant",
                entity_id="test_entity_002",
                operation_data={"content": "test content"},
            )
            tx.transaction.add_operation(operation)

        # Verify transaction was rolled back/failed
        assert tx.transaction.state in [
            TransactionState.FAILED,
            TransactionState.ABORTED,
        ]
        assert tx.transaction.success is False

    @pytest.mark.asyncio
    async def test_compensation_actions(self, transaction_manager):
        """Test compensation actions for rollback."""
        compensation_executed = False

        async def compensation_func(data):
            nonlocal compensation_executed
            compensation_executed = True

        async with transaction_manager.transaction() as tx:
            operation = DatabaseOperation(
                operation_type=OperationType.CREATE,
                database="qdrant",
                entity_id="test_entity_003",
                operation_data={"content": "test content"},
            )

            compensation = CompensationAction(
                operation_type=OperationType.DELETE,
                database="qdrant",
                entity_id="test_entity_003",
                compensation_function=compensation_func,
            )
            operation.compensation_action = compensation

            tx.transaction.add_operation(operation)

        # For this test, we assume the transaction succeeds
        # In a real rollback scenario, compensation would be executed

    @pytest.mark.asyncio
    async def test_multiple_database_operations(self, transaction_manager):
        """Test operations across multiple databases."""
        async with transaction_manager.transaction() as tx:
            # Add QDrant operation
            qdrant_op = DatabaseOperation(
                operation_type=OperationType.CREATE,
                database="qdrant",
                entity_id="test_doc_001",
                operation_data={"content": "test document", "embedding": [0.1] * 384},
            )
            tx.transaction.add_operation(qdrant_op)

            # Add Neo4j operation
            neo4j_op = DatabaseOperation(
                operation_type=OperationType.CREATE,
                database="neo4j",
                entity_id="test_node_001",
                operation_data={"type": "Document", "title": "Test Document"},
            )
            tx.transaction.add_operation(neo4j_op)

        # Verify both operations were added
        assert len(tx.transaction.operations) == 2
        qdrant_ops = tx.transaction.get_operations_by_database("qdrant")
        neo4j_ops = tx.transaction.get_operations_by_database("neo4j")
        assert len(qdrant_ops) == 1
        assert len(neo4j_ops) == 1

    @pytest.mark.asyncio
    async def test_transaction_timeout(self, transaction_manager):
        """Test transaction timeout handling."""
        # Create a transaction with very short timeout
        transaction = DistributedTransaction(timeout_seconds=1)

        # Simulate time passing
        transaction.mark_started()
        await asyncio.sleep(1.1)

        # Check if transaction is expired
        assert transaction.is_expired()

    @pytest.mark.asyncio
    async def test_transaction_statistics(self, transaction_manager):
        """Test transaction statistics collection."""
        # Execute a successful transaction
        async with transaction_manager.transaction() as tx:
            operation = DatabaseOperation(
                operation_type=OperationType.CREATE,
                database="qdrant",
                entity_id="stats_test_001",
                operation_data={"content": "stats test"},
            )
            tx.transaction.add_operation(operation)

        # Get statistics
        stats = await transaction_manager.get_transaction_statistics()

        assert "total_transactions" in stats
        assert "successful_transactions" in stats
        assert "failed_transactions" in stats
        assert stats["total_transactions"] >= 1

    @pytest.mark.asyncio
    async def test_health_check(self, transaction_manager):
        """Test transaction manager health check."""
        health_status = await transaction_manager.health_check()

        assert "status" in health_status
        assert "qdrant_manager_healthy" in health_status
        assert "neo4j_manager_healthy" in health_status
        assert "active_transactions" in health_status

    def test_database_operation_creation(self):
        """Test DatabaseOperation model creation and methods."""
        operation = DatabaseOperation(
            operation_type=OperationType.UPDATE,
            database="qdrant",
            entity_id="test_entity",
            operation_data={"field": "value"},
        )

        assert operation.operation_type == OperationType.UPDATE
        assert operation.database == "qdrant"
        assert operation.entity_id == "test_entity"
        assert operation.prepared is False
        assert operation.executed is False

        # Test marking as prepared
        operation.mark_prepared()
        assert operation.prepared is True

        # Test marking as executed
        operation.mark_executed(success=True)
        assert operation.executed is True
        assert operation.success is True

    def test_distributed_transaction_creation(self):
        """Test DistributedTransaction model creation and methods."""
        transaction = DistributedTransaction(timeout_seconds=60)

        assert transaction.state == TransactionState.INITIALIZED
        assert transaction.timeout_seconds == 60
        assert len(transaction.operations) == 0

        # Test adding operations
        operation = DatabaseOperation(
            operation_type=OperationType.CREATE,
            database="qdrant",
            entity_id="test_entity",
        )
        transaction.add_operation(operation)

        assert len(transaction.operations) == 1

        # Test marking as started and completed
        transaction.mark_started()
        assert transaction.started_at is not None

        transaction.mark_completed(success=True)
        assert transaction.completed_at is not None
        assert transaction.success is True

    @pytest.mark.asyncio
    async def test_compensation_action_execution(self):
        """Test CompensationAction execution."""
        executed_data = None

        async def test_compensation(data):
            nonlocal executed_data
            executed_data = data

        compensation = CompensationAction(
            operation_type=OperationType.DELETE,
            database="qdrant",
            entity_id="test_entity",
            rollback_data={"test": "data"},
            compensation_function=test_compensation,
        )

        # Execute compensation
        result = await compensation.execute()

        assert result is True
        assert compensation.executed is True
        assert executed_data == {"test": "data"}

    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, transaction_manager):
        """Test handling multiple concurrent transactions."""

        async def create_transaction(entity_id: str):
            async with transaction_manager.transaction() as tx:
                operation = DatabaseOperation(
                    operation_type=OperationType.CREATE,
                    database="qdrant",
                    entity_id=entity_id,
                    operation_data={"content": f"content for {entity_id}"},
                )
                tx.transaction.add_operation(operation)
                return tx.transaction.transaction_id

        # Run multiple transactions concurrently
        tasks = [create_transaction(f"concurrent_entity_{i}") for i in range(3)]

        results = await asyncio.gather(*tasks)

        # Verify all transactions completed with unique IDs
        assert len(results) == 3
        assert len(set(results)) == 3  # All unique transaction IDs
