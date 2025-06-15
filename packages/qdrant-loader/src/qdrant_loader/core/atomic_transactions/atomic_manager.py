"""
Main atomic transaction manager coordinating QDrant and Neo4j operations.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from ...utils.logging import LoggingConfig
from ..managers.id_mapping_manager import IDMappingManager
from ..managers.neo4j_manager import Neo4jManager
from ..managers.qdrant_manager import QdrantManager
from .context import TransactionContext
from .enums import TransactionState
from .models import DistributedTransaction
from .neo4j_manager import Neo4jTransactionManager
from .qdrant_manager import QdrantTransactionManager

logger = LoggingConfig.get_logger(__name__)


class AtomicTransactionManager:
    """Main atomic transaction manager coordinating QDrant and Neo4j operations."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        default_timeout_seconds: int = 300,
        max_retry_attempts: int = 3,
        enable_compensation: bool = True,
    ):
        """Initialize the atomic transaction manager.

        Args:
            qdrant_manager: QDrant manager instance
            neo4j_manager: Neo4j manager instance
            id_mapping_manager: ID mapping manager instance
            default_timeout_seconds: Default transaction timeout
            max_retry_attempts: Maximum retry attempts for failed operations
            enable_compensation: Whether to enable compensation actions
        """
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.default_timeout_seconds = default_timeout_seconds
        self.max_retry_attempts = max_retry_attempts
        self.enable_compensation = enable_compensation

        # Database transaction managers
        self.qdrant_tx_manager = QdrantTransactionManager(qdrant_manager)
        self.neo4j_tx_manager = Neo4jTransactionManager(neo4j_manager)

        # Active transactions
        self._active_transactions: Dict[str, DistributedTransaction] = {}

        # Statistics
        self._total_transactions = 0
        self._successful_transactions = 0
        self._failed_transactions = 0
        self._rollback_count = 0

    @asynccontextmanager
    async def transaction(
        self,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for atomic transactions across both databases.

        Usage:
            async with transaction_manager.transaction() as tx:
                await tx.add_qdrant_operation(...)
                await tx.add_neo4j_operation(...)
                # Transaction automatically commits on success or rolls back on failure
        """
        transaction = DistributedTransaction(
            timeout_seconds=timeout_seconds or self.default_timeout_seconds,
            metadata=metadata or {},
        )

        self._active_transactions[transaction.transaction_id] = transaction
        self._total_transactions += 1

        try:
            transaction.mark_started()
            transaction.state = TransactionState.PREPARING

            # Yield transaction context
            tx_context = TransactionContext(self, transaction)
            yield tx_context

            # Commit transaction
            success = await self._commit_transaction(transaction)
            if success:
                self._successful_transactions += 1
                transaction.mark_completed(success=True)
            else:
                self._failed_transactions += 1
                transaction.mark_completed(success=False, error="Commit failed")

        except Exception as e:
            logger.error(f"Transaction {transaction.transaction_id} failed: {e}")
            self._failed_transactions += 1
            transaction.mark_completed(success=False, error=str(e))

            # Rollback transaction
            await self._rollback_transaction(transaction)
            raise

        finally:
            # Cleanup
            if transaction.transaction_id in self._active_transactions:
                del self._active_transactions[transaction.transaction_id]

    async def _commit_transaction(self, transaction: DistributedTransaction) -> bool:
        """Commit a distributed transaction using two-phase commit protocol."""
        try:
            transaction.state = TransactionState.PREPARING

            # Phase 1: Prepare all operations
            if not await self._prepare_all_operations(transaction):
                transaction.state = TransactionState.FAILED
                return False

            transaction.state = TransactionState.PREPARED

            # Phase 2: Commit all operations
            transaction.state = TransactionState.COMMITTING

            if not await self._execute_all_operations(transaction):
                transaction.state = TransactionState.FAILED
                await self._rollback_transaction(transaction)
                return False

            transaction.state = TransactionState.COMMITTED
            return True

        except Exception as e:
            logger.error(
                f"Failed to commit transaction {transaction.transaction_id}: {e}"
            )
            transaction.state = TransactionState.FAILED
            await self._rollback_transaction(transaction)
            return False

    async def _prepare_all_operations(
        self, transaction: DistributedTransaction
    ) -> bool:
        """Prepare all operations in the transaction."""
        try:
            # Start database transactions
            qdrant_tx = await self.qdrant_tx_manager.begin_transaction(
                transaction.transaction_id
            )
            neo4j_tx = await self.neo4j_tx_manager.begin_transaction(
                transaction.transaction_id
            )

            # Prepare QDrant operations
            qdrant_ops = transaction.get_operations_by_database("qdrant")
            for operation in qdrant_ops:
                if not await self.qdrant_tx_manager.prepare_operation(
                    qdrant_tx, operation
                ):
                    return False

            # Prepare Neo4j operations
            neo4j_ops = transaction.get_operations_by_database("neo4j")
            for operation in neo4j_ops:
                if not await self.neo4j_tx_manager.prepare_operation(
                    neo4j_tx, operation
                ):
                    return False

            return True

        except Exception as e:
            logger.error(
                f"Failed to prepare operations for transaction {transaction.transaction_id}: {e}"
            )
            return False

    async def _execute_all_operations(
        self, transaction: DistributedTransaction
    ) -> bool:
        """Execute all prepared operations."""
        try:
            # Get database transactions
            qdrant_tx = self.qdrant_tx_manager._active_transactions.get(
                transaction.transaction_id
            )
            neo4j_tx = self.neo4j_tx_manager._active_transactions.get(
                transaction.transaction_id
            )

            # Execute QDrant operations
            qdrant_ops = transaction.get_operations_by_database("qdrant")
            for operation in qdrant_ops:
                if qdrant_tx and not await self.qdrant_tx_manager.execute_operation(
                    qdrant_tx, operation
                ):
                    return False

            # Execute Neo4j operations
            neo4j_ops = transaction.get_operations_by_database("neo4j")
            for operation in neo4j_ops:
                if neo4j_tx and not await self.neo4j_tx_manager.execute_operation(
                    neo4j_tx, operation
                ):
                    return False

            # Commit database transactions
            if qdrant_tx and not await self.qdrant_tx_manager.commit_transaction(
                qdrant_tx
            ):
                return False

            if neo4j_tx and not await self.neo4j_tx_manager.commit_transaction(
                neo4j_tx
            ):
                return False

            return True

        except Exception as e:
            logger.error(
                f"Failed to execute operations for transaction {transaction.transaction_id}: {e}"
            )
            return False

    async def _rollback_transaction(self, transaction: DistributedTransaction) -> None:
        """Rollback a distributed transaction."""
        try:
            transaction.state = TransactionState.ABORTING
            self._rollback_count += 1

            # Rollback database transactions
            qdrant_tx = self.qdrant_tx_manager._active_transactions.get(
                transaction.transaction_id
            )
            if qdrant_tx:
                await self.qdrant_tx_manager.rollback_transaction(qdrant_tx)

            neo4j_tx = self.neo4j_tx_manager._active_transactions.get(
                transaction.transaction_id
            )
            if neo4j_tx:
                await self.neo4j_tx_manager.rollback_transaction(neo4j_tx)

            # Execute compensation actions if enabled
            if self.enable_compensation:
                await self._execute_compensation_actions(transaction)

            transaction.state = TransactionState.ABORTED

        except Exception as e:
            logger.error(
                f"Failed to rollback transaction {transaction.transaction_id}: {e}"
            )
            transaction.state = TransactionState.FAILED

    async def _execute_compensation_actions(
        self, transaction: DistributedTransaction
    ) -> None:
        """Execute compensation actions for rollback."""
        for action in reversed(transaction.compensation_actions):
            try:
                await action.execute()
            except Exception as e:
                logger.error(
                    f"Failed to execute compensation action {action.action_id}: {e}"
                )

    async def get_transaction_statistics(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        return {
            "total_transactions": self._total_transactions,
            "successful_transactions": self._successful_transactions,
            "failed_transactions": self._failed_transactions,
            "rollback_count": self._rollback_count,
            "success_rate": (
                self._successful_transactions / self._total_transactions
                if self._total_transactions > 0
                else 0.0
            ),
            "active_transactions": len(self._active_transactions),
            "active_transaction_ids": list(self._active_transactions.keys()),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the transaction manager."""
        return {
            "status": "healthy",
            "active_transactions": len(self._active_transactions),
            "statistics": await self.get_transaction_statistics(),
            "qdrant_manager_healthy": await self.qdrant_manager.health_check(),
            "neo4j_manager_healthy": self.neo4j_manager.health_check(),
        }
