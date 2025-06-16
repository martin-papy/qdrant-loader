"""
Test utilities for sync testing.

Provides data generators, assertion helpers, performance measurement tools,
and event collection utilities for comprehensive sync testing.
"""

import time
import asyncio
import random
import string
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from qdrant_loader.core.sync.types import SyncOperationType, SyncOperationStatus


@dataclass
class PerformanceMeasurement:
    """Performance measurement utilities for sync operations."""

    operation_name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_usage: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self):
        """Start performance measurement."""
        self.start_time = time.perf_counter()

    def stop(self):
        """Stop performance measurement and calculate duration."""
        if self.start_time is None:
            raise ValueError("Performance measurement not started")

        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


@dataclass
class TestEvent:
    """Test event for event collection."""

    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "test"


class TestEventCollector:
    """Collect and analyze events during testing."""

    def __init__(self):
        self.events: List[TestEvent] = []
        self.event_counts: Dict[str, int] = {}

    def add_event(self, event_type: str, data: Dict[str, Any], source: str = "test"):
        """Add an event to the collection."""
        event = TestEvent(
            event_type=event_type, timestamp=datetime.now(), data=data, source=source
        )
        self.events.append(event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

    def get_events_by_type(self, event_type: str) -> List[TestEvent]:
        """Get all events of a specific type."""
        return [event for event in self.events if event.event_type == event_type]

    def get_event_count(self, event_type: str) -> int:
        """Get count of events by type."""
        return self.event_counts.get(event_type, 0)

    def clear(self):
        """Clear all collected events."""
        self.events.clear()
        self.event_counts.clear()

    def get_events_in_timerange(
        self, start_time: datetime, end_time: datetime
    ) -> List[TestEvent]:
        """Get events within a specific time range."""
        return [
            event for event in self.events if start_time <= event.timestamp <= end_time
        ]


class SyncTestDataGenerator:
    """Generate test data for sync operations."""

    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate a random string."""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def generate_document_data(
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate document data for testing."""
        return {
            "id": doc_id or f"doc_{SyncTestDataGenerator.random_string(8)}",
            "title": title or f"Test Document {SyncTestDataGenerator.random_string(5)}",
            "content": content
            or f"Test content {SyncTestDataGenerator.random_string(20)}",
            "metadata": {
                "author": f"user_{SyncTestDataGenerator.random_string(5)}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "source": "test_generator",
                "tags": [f"tag_{i}" for i in range(random.randint(1, 5))],
            },
            "embedding": [random.random() for _ in range(384)],
        }

    @staticmethod
    def generate_entity_data(
        entity_id: Optional[str] = None, entity_type: str = "Person"
    ) -> Dict[str, Any]:
        """Generate entity data for testing."""
        return {
            "id": entity_id or f"entity_{SyncTestDataGenerator.random_string(8)}",
            "type": entity_type,
            "properties": {
                "name": f"Test {entity_type} {SyncTestDataGenerator.random_string(5)}",
                "description": f"Test {entity_type.lower()} for sync testing",
                "created_at": datetime.now().isoformat(),
            },
            "relationships": [],
        }

    @staticmethod
    def generate_sync_operation(
        operation_type: SyncOperationType = SyncOperationType.CREATE_DOCUMENT,
        entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate sync operation data for testing."""
        return {
            "operation_id": f"op_{SyncTestDataGenerator.random_string(8)}",
            "operation_type": operation_type,
            "entity_id": entity_id
            or f"entity_{SyncTestDataGenerator.random_string(8)}",
            "entity_type": "document",
            "status": SyncOperationStatus.PENDING,
            "data": SyncTestDataGenerator.generate_document_data(),
            "metadata": {
                "source": "test_generator",
                "timestamp": datetime.now().isoformat(),
                "priority": random.choice(["low", "medium", "high"]),
            },
        }

    @staticmethod
    def generate_batch_operations(
        count: int = 10, operation_types: Optional[List[SyncOperationType]] = None
    ) -> List[Dict[str, Any]]:
        """Generate a batch of sync operations."""
        if operation_types is None:
            operation_types = [
                SyncOperationType.CREATE_DOCUMENT,
                SyncOperationType.UPDATE_DOCUMENT,
                SyncOperationType.DELETE_DOCUMENT,
            ]

        operations = []
        for _ in range(count):
            op_type = random.choice(operation_types)
            operations.append(SyncTestDataGenerator.generate_sync_operation(op_type))

        return operations


class SyncAssertionHelpers:
    """Assertion helpers for sync testing."""

    @staticmethod
    def assert_operation_completed(operation: Dict[str, Any]):
        """Assert that a sync operation completed successfully."""
        assert (
            operation.get("status") == SyncOperationStatus.COMPLETED
        ), f"Operation {operation.get('operation_id')} not completed: {operation.get('status')}"

    @staticmethod
    def assert_operation_failed(operation: Dict[str, Any]):
        """Assert that a sync operation failed."""
        assert (
            operation.get("status") == SyncOperationStatus.FAILED
        ), f"Operation {operation.get('operation_id')} did not fail: {operation.get('status')}"

    @staticmethod
    def assert_operations_in_order(operations: List[Dict[str, Any]]):
        """Assert that operations are processed in the correct order."""
        timestamps = []
        for op in operations:
            if "completed_at" in op.get("metadata", {}):
                timestamps.append(op["metadata"]["completed_at"])

        # Check if timestamps are in ascending order
        assert timestamps == sorted(
            timestamps
        ), "Operations were not processed in chronological order"

    @staticmethod
    def assert_no_data_loss(
        original_data: List[Dict[str, Any]], synced_data: List[Dict[str, Any]]
    ):
        """Assert that no data was lost during synchronization."""
        original_ids = {item.get("id") for item in original_data}
        synced_ids = {item.get("id") for item in synced_data}

        missing_ids = original_ids - synced_ids
        assert not missing_ids, f"Data loss detected. Missing IDs: {missing_ids}"

    @staticmethod
    def assert_conflict_resolved(conflict_data: Dict[str, Any]):
        """Assert that a conflict was properly resolved."""
        assert (
            "resolution_strategy" in conflict_data
        ), "Conflict resolution strategy not recorded"
        assert (
            "resolved_at" in conflict_data
        ), "Conflict resolution timestamp not recorded"
        assert (
            conflict_data.get("status") == "resolved"
        ), f"Conflict not resolved: {conflict_data.get('status')}"

    @staticmethod
    async def assert_async_operation_timeout(
        async_func: Callable, timeout_seconds: float = 5.0
    ):
        """Assert that an async operation completes within timeout."""
        try:
            await asyncio.wait_for(async_func(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            raise AssertionError(
                f"Operation did not complete within {timeout_seconds} seconds"
            )


class MockSyncComponentFactory:
    """Factory for creating mock sync components."""

    @staticmethod
    def create_mock_atomic_transaction_manager():
        """Create a mock atomic transaction manager."""
        mock_manager = AsyncMock()
        mock_manager.create_transaction.return_value = AsyncMock()
        mock_manager.commit_transaction.return_value = True
        mock_manager.rollback_transaction.return_value = True
        mock_manager.get_transaction_status.return_value = "committed"
        return mock_manager

    @staticmethod
    def create_mock_enhanced_sync_event_system():
        """Create a mock enhanced sync event system."""
        mock_system = AsyncMock()
        mock_system.queue_operation.return_value = True
        mock_system.process_operations.return_value = []
        mock_system.get_operation_statistics.return_value = {
            "total_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
        }
        mock_system.health_check.return_value = True
        return mock_system

    @staticmethod
    def create_mock_sync_conflict_monitor():
        """Create a mock sync conflict monitor."""
        mock_monitor = AsyncMock()
        mock_monitor.detect_conflicts.return_value = []
        mock_monitor.resolve_conflict.return_value = True
        mock_monitor.get_conflict_statistics.return_value = {
            "total_conflicts": 0,
            "resolved_conflicts": 0,
            "pending_conflicts": 0,
        }
        return mock_monitor


async def wait_for_condition(
    condition_func: Callable[[], bool],
    timeout_seconds: float = 10.0,
    check_interval: float = 0.1,
) -> bool:
    """Wait for a condition to become true within a timeout."""
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        if condition_func():
            return True
        await asyncio.sleep(check_interval)

    return False


def create_test_batch_generator(
    batch_size: int = 10, total_items: int = 100
) -> AsyncGenerator[List[Dict[str, Any]], None]:
    """Create an async generator for batch testing."""

    async def generator():
        for i in range(0, total_items, batch_size):
            batch = []
            for j in range(i, min(i + batch_size, total_items)):
                batch.append(
                    SyncTestDataGenerator.generate_document_data(
                        doc_id=f"batch_doc_{j}"
                    )
                )
            yield batch

    return generator()
