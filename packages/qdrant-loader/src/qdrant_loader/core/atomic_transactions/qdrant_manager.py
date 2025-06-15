"""
QDrant transaction manager for atomic operations.
"""

import asyncio
from typing import Any, Dict, Optional

from qdrant_client.http.models import PointStruct

from ...utils.logging import LoggingConfig
from ..managers.qdrant_manager import QdrantManager
from .base import DatabaseTransactionManager
from .enums import OperationType
from .models import DatabaseOperation

logger = LoggingConfig.get_logger(__name__)


class QdrantTransactionManager(DatabaseTransactionManager):
    """Transaction manager for QDrant operations."""

    def __init__(self, qdrant_manager: QdrantManager):
        self.qdrant_manager = qdrant_manager
        self._active_transactions: Dict[str, Dict[str, Any]] = {}

    async def begin_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Begin a QDrant transaction (simulated with operation tracking)."""
        transaction_context = {
            "transaction_id": transaction_id,
            "operations": [],
            "rollback_data": {},
            "client": self.qdrant_manager._ensure_client_connected(),
        }
        self._active_transactions[transaction_id] = transaction_context
        return transaction_context

    async def prepare_operation(
        self, transaction: Dict[str, Any], operation: DatabaseOperation
    ) -> bool:
        """Prepare a QDrant operation."""
        try:
            # For QDrant, preparation involves validating the operation
            # and capturing current state for rollback
            if operation.operation_type in [OperationType.UPDATE, OperationType.DELETE]:
                # Capture current state for rollback
                if operation.entity_id:
                    current_state = await self._capture_point_state(operation.entity_id)
                    operation.pre_operation_state = current_state

            # Validate operation data
            if not self._validate_operation(operation):
                return False

            operation.mark_prepared()
            transaction["operations"].append(operation)
            return True

        except Exception as e:
            logger.error(
                f"Failed to prepare QDrant operation {operation.operation_id}: {e}"
            )
            operation.mark_executed(success=False, error=str(e))
            return False

    async def execute_operation(
        self, transaction: Dict[str, Any], operation: DatabaseOperation
    ) -> bool:
        """Execute a QDrant operation."""
        try:
            client = transaction["client"]

            if operation.operation_type == OperationType.CREATE:
                await self._execute_create(client, operation)
            elif operation.operation_type == OperationType.UPDATE:
                await self._execute_update(client, operation)
            elif operation.operation_type == OperationType.DELETE:
                await self._execute_delete(client, operation)
            elif operation.operation_type == OperationType.UPSERT:
                await self._execute_upsert(client, operation)
            else:
                raise ValueError(
                    f"Unsupported operation type: {operation.operation_type}"
                )

            operation.mark_executed(success=True)
            return True

        except Exception as e:
            logger.error(
                f"Failed to execute QDrant operation {operation.operation_id}: {e}"
            )
            operation.mark_executed(success=False, error=str(e))
            return False

    async def commit_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Commit QDrant transaction (cleanup tracking)."""
        transaction_id = transaction["transaction_id"]
        try:
            # QDrant operations are already executed, just cleanup
            if transaction_id in self._active_transactions:
                del self._active_transactions[transaction_id]
            return True
        except Exception as e:
            logger.error(f"Failed to commit QDrant transaction {transaction_id}: {e}")
            return False

    async def rollback_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Rollback QDrant transaction using compensation actions."""
        transaction_id = transaction["transaction_id"]
        try:
            client = transaction["client"]

            # Execute rollback for each operation in reverse order
            for operation in reversed(transaction["operations"]):
                if operation.executed and operation.success:
                    await self._rollback_operation(client, operation)

            # Cleanup
            if transaction_id in self._active_transactions:
                del self._active_transactions[transaction_id]
            return True

        except Exception as e:
            logger.error(f"Failed to rollback QDrant transaction {transaction_id}: {e}")
            return False

    async def _capture_point_state(self, point_id: str) -> Optional[Dict[str, Any]]:
        """Capture current state of a point for rollback."""
        try:
            client = self.qdrant_manager._ensure_client_connected()
            points = await asyncio.to_thread(
                client.retrieve,
                collection_name=self.qdrant_manager.collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=True,
            )

            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "payload": point.payload,
                    "vector": point.vector,
                }
        except Exception as e:
            logger.warning(f"Failed to capture point state for {point_id}: {e}")
        return None

    def _validate_operation(self, operation: DatabaseOperation) -> bool:
        """Validate a QDrant operation."""
        if not operation.entity_id:
            return False

        if operation.operation_type in [OperationType.CREATE, OperationType.UPSERT]:
            return operation.operation_data is not None

        return True

    async def _execute_create(self, client, operation: DatabaseOperation) -> None:
        """Execute QDrant create operation."""
        point_data = operation.operation_data or {}
        if not operation.entity_id:
            raise ValueError("Entity ID is required for create operation")

        point = PointStruct(
            id=operation.entity_id,
            vector=point_data.get("vector", []),
            payload=point_data.get("payload", {}),
        )

        await asyncio.to_thread(
            client.upsert,
            collection_name=self.qdrant_manager.collection_name,
            points=[point],
        )

    async def _execute_update(self, client, operation: DatabaseOperation) -> None:
        """Execute QDrant update operation."""
        update_data = operation.operation_data or {}

        if "payload" in update_data:
            await asyncio.to_thread(
                client.set_payload,
                collection_name=self.qdrant_manager.collection_name,
                payload=update_data["payload"],
                points=[operation.entity_id],
            )

    async def _execute_delete(self, client, operation: DatabaseOperation) -> None:
        """Execute QDrant delete operation."""
        await asyncio.to_thread(
            client.delete,
            collection_name=self.qdrant_manager.collection_name,
            points_selector=[operation.entity_id],
        )

    async def _execute_upsert(self, client, operation: DatabaseOperation) -> None:
        """Execute QDrant upsert operation."""
        await self._execute_create(client, operation)

    async def _rollback_operation(self, client, operation: DatabaseOperation) -> None:
        """Rollback a QDrant operation."""
        if not operation.pre_operation_state:
            # If no previous state, delete the point
            if operation.operation_type == OperationType.CREATE:
                await self._execute_delete(client, operation)
            return

        # Restore previous state
        state = operation.pre_operation_state
        point = PointStruct(
            id=state["id"], vector=state["vector"], payload=state["payload"]
        )

        await asyncio.to_thread(
            client.upsert,
            collection_name=self.qdrant_manager.collection_name,
            points=[point],
        )
