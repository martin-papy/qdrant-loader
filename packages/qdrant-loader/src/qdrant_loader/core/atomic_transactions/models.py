"""
Data models for atomic transaction management.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional

from ...utils.logging import LoggingConfig
from .enums import OperationType, TransactionState

logger = LoggingConfig.get_logger(__name__)


@dataclass
class CompensationAction:
    """Represents a compensation action for rollback."""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: OperationType = OperationType.UPDATE
    database: str = ""  # "qdrant" or "neo4j"
    entity_id: Optional[str] = None
    rollback_data: Optional[Dict[str, Any]] = None
    compensation_function: Optional[Callable] = None
    executed: bool = False
    execution_error: Optional[str] = None

    async def execute(self) -> bool:
        """Execute the compensation action."""
        if self.executed:
            logger.warning(f"Compensation action {self.action_id} already executed")
            return True

        try:
            if self.compensation_function:
                await self.compensation_function(self.rollback_data)
            self.executed = True
            logger.info(f"Compensation action {self.action_id} executed successfully")
            return True
        except Exception as e:
            self.execution_error = str(e)
            logger.error(f"Failed to execute compensation action {self.action_id}: {e}")
            return False


@dataclass
class DatabaseOperation:
    """Represents a single database operation within a transaction."""

    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: OperationType = OperationType.UPDATE
    database: str = ""  # "qdrant" or "neo4j"
    entity_id: Optional[str] = None
    operation_data: Optional[Dict[str, Any]] = None

    # Execution tracking
    prepared: bool = False
    executed: bool = False
    success: bool = False
    error_message: Optional[str] = None

    # Rollback information
    compensation_action: Optional[CompensationAction] = None
    pre_operation_state: Optional[Dict[str, Any]] = None

    def mark_prepared(self) -> None:
        """Mark operation as prepared."""
        self.prepared = True

    def mark_executed(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark operation as executed."""
        self.executed = True
        self.success = success
        if error:
            self.error_message = error


@dataclass
class DistributedTransaction:
    """Represents a distributed transaction across QDrant and Neo4j."""

    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TransactionState = TransactionState.INITIALIZED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Operations
    operations: List[DatabaseOperation] = field(default_factory=list)
    compensation_actions: List[CompensationAction] = field(default_factory=list)

    # Execution tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300  # 5 minutes default

    # Results
    success: bool = False
    error_message: Optional[str] = None
    partial_success: bool = False

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_operation(self, operation: DatabaseOperation) -> None:
        """Add an operation to the transaction."""
        self.operations.append(operation)

    def add_compensation_action(self, action: CompensationAction) -> None:
        """Add a compensation action for rollback."""
        self.compensation_actions.append(action)

    def mark_started(self) -> None:
        """Mark transaction as started."""
        self.started_at = datetime.now(UTC)

    def mark_completed(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark transaction as completed."""
        self.completed_at = datetime.now(UTC)
        self.success = success
        if error:
            self.error_message = error

    def is_expired(self) -> bool:
        """Check if transaction has expired."""
        if not self.started_at:
            return False
        elapsed = (datetime.now(UTC) - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds

    def get_operations_by_database(self, database: str) -> List[DatabaseOperation]:
        """Get operations for a specific database."""
        return [op for op in self.operations if op.database == database]
