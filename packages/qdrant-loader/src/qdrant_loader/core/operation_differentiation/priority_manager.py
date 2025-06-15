"""Operation priority manager for scheduling and resource management.

This module provides the OperationPriorityManager class that handles operation
queuing, priority-based scheduling, and resource allocation.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from ...utils.logging import LoggingConfig
from .types import OperationCharacteristics, OperationPriority

if TYPE_CHECKING:
    from ..sync import EnhancedSyncOperation

logger = LoggingConfig.get_logger(__name__)


class OperationPriorityManager:
    """Manager for operation priority and scheduling."""

    def __init__(self, max_concurrent_operations: int = 10):
        """Initialize the priority manager.

        Args:
            max_concurrent_operations: Maximum concurrent operations
        """
        self.max_concurrent_operations = max_concurrent_operations
        self._priority_queues: Dict[
            OperationPriority,
            List[Tuple[float, "EnhancedSyncOperation", OperationCharacteristics]],
        ] = {priority: [] for priority in OperationPriority}
        self._active_operations: Dict[
            str, Tuple["EnhancedSyncOperation", OperationCharacteristics]
        ] = {}
        self._resource_usage: Dict[str, float] = {
            "cpu": 0.0,
            "memory": 0.0,
            "network": 0.0,
        }
        self._max_resources: Dict[str, float] = {
            "cpu": 4.0,
            "memory": 8192.0,
            "network": 1024.0,
        }  # Default limits

    async def queue_operation(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
    ) -> None:
        """Queue an operation with its characteristics.

        Args:
            operation: The operation to queue
            characteristics: Operation characteristics
        """
        priority_score = characteristics.calculate_priority_score()

        # Add to appropriate priority queue
        self._priority_queues[characteristics.priority].append(
            (priority_score, operation, characteristics)
        )

        # Sort queue by priority score (highest first)
        self._priority_queues[characteristics.priority].sort(
            key=lambda x: x[0], reverse=True
        )

        logger.debug(
            f"Queued operation {operation.operation_id} with priority "
            f"{characteristics.priority.value} (score: {priority_score:.1f})"
        )

    async def get_next_operation(
        self,
    ) -> Optional[Tuple["EnhancedSyncOperation", OperationCharacteristics]]:
        """Get the next operation to process based on priority and resources.

        Returns:
            Tuple of (operation, characteristics) or None if no operation available
        """
        # Check if we're at capacity
        if len(self._active_operations) >= self.max_concurrent_operations:
            return None

        # Try each priority level in order
        for priority in OperationPriority:
            queue = self._priority_queues[priority]

            # Find first operation that fits resource constraints
            for i, (score, operation, characteristics) in enumerate(queue):
                if await self._can_allocate_resources(characteristics):
                    # Remove from queue
                    del queue[i]

                    # Allocate resources
                    await self._allocate_resources(operation, characteristics)

                    logger.debug(
                        f"Selected operation {operation.operation_id} for processing "
                        f"(priority: {priority.value}, score: {score:.1f})"
                    )

                    return operation, characteristics

        return None

    async def _can_allocate_resources(
        self, characteristics: OperationCharacteristics
    ) -> bool:
        """Check if resources can be allocated for the operation.

        Args:
            characteristics: Operation characteristics with resource requirements

        Returns:
            True if resources can be allocated
        """
        for resource, required in characteristics.resource_requirements.items():
            if self._resource_usage.get(
                resource, 0
            ) + required > self._max_resources.get(resource, float("inf")):
                return False
        return True

    async def _allocate_resources(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
    ) -> None:
        """Allocate resources for an operation.

        Args:
            operation: The operation
            characteristics: Operation characteristics
        """
        # Add to active operations
        self._active_operations[operation.operation_id] = (operation, characteristics)

        # Update resource usage
        for resource, required in characteristics.resource_requirements.items():
            self._resource_usage[resource] = (
                self._resource_usage.get(resource, 0) + required
            )

    async def release_operation(self, operation_id: str) -> None:
        """Release resources for a completed operation.

        Args:
            operation_id: ID of the completed operation
        """
        if operation_id in self._active_operations:
            operation, characteristics = self._active_operations[operation_id]

            # Release resources
            for resource, required in characteristics.resource_requirements.items():
                self._resource_usage[resource] = max(
                    0, self._resource_usage.get(resource, 0) - required
                )

            # Remove from active operations
            del self._active_operations[operation_id]

            logger.debug(f"Released resources for operation {operation_id}")

    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        stats = {
            "active_operations": len(self._active_operations),
            "max_concurrent": self.max_concurrent_operations,
            "resource_usage": self._resource_usage.copy(),
            "max_resources": self._max_resources.copy(),
            "queued_by_priority": {},
        }

        for priority, queue in self._priority_queues.items():
            stats["queued_by_priority"][priority.value] = len(queue)

        return stats
