"""
Neo4j transaction manager for atomic operations.
"""

import asyncio
from typing import Any

from neo4j import Transaction

from ...utils.logging import LoggingConfig
from ..managers.neo4j_manager import Neo4jManager
from .base import DatabaseTransactionManager
from .enums import OperationType
from .models import DatabaseOperation

logger = LoggingConfig.get_logger(__name__)


class Neo4jTransactionManager(DatabaseTransactionManager):
    """Transaction manager for Neo4j operations."""

    def __init__(self, neo4j_manager: Neo4jManager):
        self.neo4j_manager = neo4j_manager
        self._active_transactions: dict[str, Transaction] = {}

    async def begin_transaction(self, transaction_id: str) -> Transaction:
        """Begin a Neo4j transaction."""
        if not self.neo4j_manager._driver:
            raise RuntimeError("Neo4j driver not initialized")

        # Use asyncio.to_thread to handle synchronous Neo4j operations
        def _begin_transaction():
            driver = self.neo4j_manager._driver
            if driver is None:
                raise RuntimeError("Neo4j driver not initialized")
            session = driver.session()
            transaction = session.begin_transaction()
            return transaction

        transaction = await asyncio.to_thread(_begin_transaction)
        self._active_transactions[transaction_id] = transaction
        return transaction

    async def prepare_operation(
        self, transaction: Transaction, operation: DatabaseOperation
    ) -> bool:
        """Prepare a Neo4j operation."""
        try:
            # For Neo4j, preparation involves validating the operation
            # and capturing current state for rollback
            if operation.operation_type in [OperationType.UPDATE, OperationType.DELETE]:
                if operation.entity_id:
                    current_state = await self._capture_node_state(
                        transaction, operation.entity_id
                    )
                    operation.pre_operation_state = current_state

            # Validate operation
            if not self._validate_operation(operation):
                return False

            operation.mark_prepared()
            return True

        except Exception as e:
            logger.error(
                f"Failed to prepare Neo4j operation {operation.operation_id}: {e}"
            )
            operation.mark_executed(success=False, error=str(e))
            return False

    async def execute_operation(
        self, transaction: Transaction, operation: DatabaseOperation
    ) -> bool:
        """Execute a Neo4j operation."""
        try:
            if operation.operation_type == OperationType.CREATE:
                await self._execute_create(transaction, operation)
            elif operation.operation_type == OperationType.UPDATE:
                await self._execute_update(transaction, operation)
            elif operation.operation_type == OperationType.DELETE:
                await self._execute_delete(transaction, operation)
            elif operation.operation_type == OperationType.UPSERT:
                await self._execute_upsert(transaction, operation)
            else:
                raise ValueError(
                    f"Unsupported operation type: {operation.operation_type}"
                )

            operation.mark_executed(success=True)
            return True

        except Exception as e:
            logger.error(
                f"Failed to execute Neo4j operation {operation.operation_id}: {e}"
            )
            operation.mark_executed(success=False, error=str(e))
            return False

    async def commit_transaction(self, transaction: Transaction) -> bool:
        """Commit Neo4j transaction."""
        try:

            def _commit_transaction():
                transaction.commit()
                transaction.close()
                return True

            return await asyncio.to_thread(_commit_transaction)
        except Exception as e:
            logger.error(f"Failed to commit Neo4j transaction: {e}")
            return False

    async def rollback_transaction(self, transaction: Transaction) -> bool:
        """Rollback Neo4j transaction."""
        try:

            def _rollback_transaction():
                transaction.rollback()
                transaction.close()
                return True

            return await asyncio.to_thread(_rollback_transaction)
        except Exception as e:
            logger.error(f"Failed to rollback Neo4j transaction: {e}")
            return False

    async def _capture_node_state(
        self, transaction: Transaction, node_id: str
    ) -> dict[str, Any] | None:
        """Capture current state of a node for rollback."""
        try:

            def _capture_state():
                query = """
                MATCH (n) WHERE id(n) = $node_id OR n.uuid = $node_id
                RETURN n, labels(n) as labels
                """
                result = transaction.run(query, node_id=node_id)
                record = result.single()

                if record:
                    node = record["n"]
                    labels = record["labels"]
                    return {"id": node.id, "labels": labels, "properties": dict(node)}
                return None

            return await asyncio.to_thread(_capture_state)
        except Exception as e:
            logger.warning(f"Failed to capture node state for {node_id}: {e}")
        return None

    def _validate_operation(self, operation: DatabaseOperation) -> bool:
        """Validate a Neo4j operation."""
        if not operation.entity_id:
            return False

        if operation.operation_type in [OperationType.CREATE, OperationType.UPSERT]:
            return operation.operation_data is not None

        return True

    async def _execute_create(
        self, transaction: Transaction, operation: DatabaseOperation
    ) -> None:
        """Execute Neo4j create operation."""
        node_data = operation.operation_data
        if not node_data:
            raise ValueError("Node data is required for create operation")

        labels = node_data.get("labels", ["Entity"])
        properties = node_data.get("properties", {})

        # Ensure UUID is set
        if "uuid" not in properties:
            properties["uuid"] = operation.entity_id

        def _execute_create():
            # Use MERGE with UUID to avoid LiteralString issues with dynamic labels
            query = "MERGE (n {uuid: $uuid}) SET n += $properties RETURN n"
            transaction.run(query, uuid=operation.entity_id, properties=properties)

        await asyncio.to_thread(_execute_create)

    async def _execute_update(
        self, transaction: Transaction, operation: DatabaseOperation
    ) -> None:
        """Execute Neo4j update operation."""
        update_data = operation.operation_data
        if not update_data:
            raise ValueError("Update data is required for update operation")

        properties = update_data.get("properties", {})

        def _execute_update():
            query = """
            MATCH (n) WHERE id(n) = $node_id OR n.uuid = $node_id
            SET n += $properties
            RETURN n
            """
            transaction.run(query, node_id=operation.entity_id, properties=properties)

        await asyncio.to_thread(_execute_update)

    async def _execute_delete(
        self, transaction: Transaction, operation: DatabaseOperation
    ) -> None:
        """Execute Neo4j delete operation."""

        def _execute_delete():
            query = """
            MATCH (n) WHERE id(n) = $node_id OR n.uuid = $node_id
            DETACH DELETE n
            """
            transaction.run(query, node_id=operation.entity_id)

        await asyncio.to_thread(_execute_delete)

    async def _execute_upsert(
        self, transaction: Transaction, operation: DatabaseOperation
    ) -> None:
        """Execute Neo4j upsert operation."""
        node_data = operation.operation_data
        if not node_data:
            raise ValueError("Node data is required for upsert operation")

        labels = node_data.get("labels", ["Entity"])
        properties = node_data.get("properties", {})

        # Ensure UUID is set
        if "uuid" not in properties:
            properties["uuid"] = operation.entity_id

        def _execute_upsert():
            # Use MERGE with UUID for upsert behavior
            query = "MERGE (n {uuid: $uuid}) SET n += $properties RETURN n"
            transaction.run(query, uuid=operation.entity_id, properties=properties)

        await asyncio.to_thread(_execute_upsert)
