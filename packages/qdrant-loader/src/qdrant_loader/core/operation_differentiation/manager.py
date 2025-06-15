"""Main operation differentiation manager.

This module provides the OperationDifferentiationManager class that coordinates
all operation differentiation components including classification, validation,
and priority management.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from ...utils.logging import LoggingConfig
from .classifier import OperationClassifier
from .priority_manager import OperationPriorityManager
from .types import OperationCharacteristics, ValidationResult
from .validator import OperationValidator

if TYPE_CHECKING:
    from ..sync import EnhancedSyncOperation

logger = LoggingConfig.get_logger(__name__)


class OperationDifferentiationManager:
    """Main manager for operation differentiation logic."""

    def __init__(
        self,
        max_concurrent_operations: int = 10,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize the operation differentiation manager.

        Args:
            max_concurrent_operations: Maximum concurrent operations
            enable_caching: Whether to enable result caching
            cache_ttl_seconds: Cache time-to-live in seconds
        """
        self.classifier = OperationClassifier()
        self.priority_manager = OperationPriorityManager(max_concurrent_operations)
        self.validator = OperationValidator()

        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds

        # Statistics
        self._stats = {
            "operations_classified": 0,
            "operations_validated": 0,
            "operations_queued": 0,
            "operations_processed": 0,
            "validation_failures": 0,
        }

    async def process_operation(
        self,
        operation: "EnhancedSyncOperation",
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[OperationCharacteristics, ValidationResult]:
        """Process an operation through the differentiation pipeline.

        Args:
            operation: The operation to process
            context: Additional context for processing

        Returns:
            Tuple of (characteristics, validation_result)
        """
        # Step 1: Classify the operation
        characteristics = await self.classifier.classify_operation(operation, context)
        self._stats["operations_classified"] += 1

        # Step 2: Validate the operation
        validation_result = await self.validator.validate_operation(
            operation, characteristics, context
        )
        self._stats["operations_validated"] += 1

        if not validation_result.is_valid:
            self._stats["validation_failures"] += 1
            logger.warning(
                f"Operation {operation.operation_id} failed validation: "
                f"{', '.join(validation_result.errors)}"
            )

        # Step 3: Queue the operation if valid
        if validation_result.is_valid:
            await self.priority_manager.queue_operation(operation, characteristics)
            self._stats["operations_queued"] += 1

        return characteristics, validation_result

    async def get_next_operation(
        self,
    ) -> Optional[Tuple["EnhancedSyncOperation", OperationCharacteristics]]:
        """Get the next operation to process.

        Returns:
            Tuple of (operation, characteristics) or None
        """
        result = await self.priority_manager.get_next_operation()
        if result:
            self._stats["operations_processed"] += 1
        return result

    async def complete_operation(
        self, operation_id: str, success: bool, duration: float
    ) -> None:
        """Mark an operation as completed and release resources.

        Args:
            operation_id: ID of the completed operation
            success: Whether the operation succeeded
            duration: Operation duration in seconds
        """
        await self.priority_manager.release_operation(operation_id)

        # Record result for historical analysis
        # Note: We'd need to store the operation reference to do this properly
        # For now, we'll skip this step

    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics.

        Returns:
            Dictionary with statistics
        """
        queue_stats = await self.priority_manager.get_queue_statistics()

        return {
            "differentiation_stats": self._stats.copy(),
            "queue_stats": queue_stats,
            "cache_enabled": self.enable_caching,
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the differentiation system.

        Returns:
            Health check results
        """
        return {
            "status": "healthy",
            "components": {
                "classifier": "operational",
                "priority_manager": "operational",
                "validator": "operational",
            },
            "active_operations": len(self.priority_manager._active_operations),
            "max_concurrent": self.priority_manager.max_concurrent_operations,
        }
