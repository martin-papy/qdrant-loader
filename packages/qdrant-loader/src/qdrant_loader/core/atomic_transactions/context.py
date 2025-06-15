"""
Transaction context for building and executing atomic transactions.
"""

from typing import Any, Callable, Dict, Optional

from .enums import OperationType
from .models import CompensationAction, DatabaseOperation, DistributedTransaction


class TransactionContext:
    """Context for building and executing atomic transactions."""

    def __init__(self, manager, transaction: DistributedTransaction):
        """Initialize transaction context.

        Args:
            manager: The AtomicTransactionManager instance
            transaction: The DistributedTransaction being built
        """
        self.manager = manager
        self.transaction = transaction

    async def add_qdrant_operation(
        self,
        operation_type: OperationType,
        entity_id: str,
        operation_data: Optional[Dict[str, Any]] = None,
    ) -> DatabaseOperation:
        """Add a QDrant operation to the transaction."""
        operation = DatabaseOperation(
            operation_type=operation_type,
            database="qdrant",
            entity_id=entity_id,
            operation_data=operation_data,
        )
        self.transaction.add_operation(operation)
        return operation

    async def add_neo4j_operation(
        self,
        operation_type: OperationType,
        entity_id: str,
        operation_data: Optional[Dict[str, Any]] = None,
    ) -> DatabaseOperation:
        """Add a Neo4j operation to the transaction."""
        operation = DatabaseOperation(
            operation_type=operation_type,
            database="neo4j",
            entity_id=entity_id,
            operation_data=operation_data,
        )
        self.transaction.add_operation(operation)
        return operation

    async def add_compensation_action(
        self,
        database: str,
        entity_id: str,
        rollback_data: Dict[str, Any],
        compensation_function: Optional[Callable] = None,
    ) -> CompensationAction:
        """Add a compensation action for rollback."""
        action = CompensationAction(
            database=database,
            entity_id=entity_id,
            rollback_data=rollback_data,
            compensation_function=compensation_function,
        )
        self.transaction.add_compensation_action(action)
        return action

    def get_transaction_id(self) -> str:
        """Get the transaction ID."""
        return self.transaction.transaction_id

    def get_operations_count(self) -> int:
        """Get the number of operations in the transaction."""
        return len(self.transaction.operations)
