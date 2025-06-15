"""
Base abstract class for database transaction managers.
"""

from abc import ABC, abstractmethod
from typing import Any

from .models import DatabaseOperation


class DatabaseTransactionManager(ABC):
    """Abstract base class for database-specific transaction managers."""

    @abstractmethod
    async def begin_transaction(self, transaction_id: str) -> Any:
        """Begin a database transaction."""
        pass

    @abstractmethod
    async def prepare_operation(
        self, transaction: Any, operation: DatabaseOperation
    ) -> bool:
        """Prepare an operation for execution."""
        pass

    @abstractmethod
    async def execute_operation(
        self, transaction: Any, operation: DatabaseOperation
    ) -> bool:
        """Execute a prepared operation."""
        pass

    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> bool:
        """Commit the transaction."""
        pass

    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Rollback the transaction."""
        pass
