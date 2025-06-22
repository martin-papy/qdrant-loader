"""Comprehensive tests for OperationPriorityManager."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from qdrant_loader.core.operation_differentiation.priority_manager import (
    OperationPriorityManager,
)
from qdrant_loader.core.operation_differentiation.types import (
    OperationCharacteristics,
    OperationComplexity,
    OperationImpact,
    OperationPriority,
)
from qdrant_loader.core.sync.types import SyncOperationType


@pytest.fixture
def priority_manager():
    """Create a priority manager instance for testing."""
    return OperationPriorityManager(max_concurrent_operations=5)


@pytest.fixture
def sample_operation():
    """Create a sample enhanced sync operation."""
    operation = Mock()
    operation.operation_id = "test-op-123"
    operation.operation_type = SyncOperationType.CREATE_DOCUMENT
    operation.entity_type = "document"
    operation.entity_id = "doc-123"
    operation.data = {"title": "Test Document", "content": "Sample content"}
    operation.metadata = {"source": "test", "timestamp": datetime.now(UTC)}
    return operation


@pytest.fixture
def sample_characteristics():
    """Create sample operation characteristics."""
    return OperationCharacteristics(
        operation_type=SyncOperationType.CREATE_DOCUMENT,
        priority=OperationPriority.MEDIUM,
        complexity=OperationComplexity.MODERATE,
        impact=OperationImpact.LOCAL,
        entity_count=1,
        relationship_count=2,
        data_size_bytes=1024,
        business_criticality=0.7,
        resource_requirements={
            "cpu": 0.5,
            "memory": 256.0,
            "network": 64.0,
        },
    )


@pytest.fixture
def high_priority_characteristics():
    """Create high priority operation characteristics."""
    return OperationCharacteristics(
        operation_type=SyncOperationType.UPDATE_DOCUMENT,
        priority=OperationPriority.HIGH,
        complexity=OperationComplexity.SIMPLE,
        impact=OperationImpact.REGIONAL,
        entity_count=1,
        relationship_count=0,
        data_size_bytes=512,
        business_criticality=0.9,
        deadline=datetime.now(UTC) + timedelta(minutes=30),
        resource_requirements={
            "cpu": 0.3,
            "memory": 128.0,
            "network": 32.0,
        },
    )


@pytest.fixture
def critical_characteristics():
    """Create critical priority operation characteristics."""
    return OperationCharacteristics(
        operation_type=SyncOperationType.DELETE_DOCUMENT,
        priority=OperationPriority.CRITICAL,
        complexity=OperationComplexity.COMPLEX,
        impact=OperationImpact.GLOBAL,
        entity_count=5,
        relationship_count=10,
        data_size_bytes=2048,
        business_criticality=1.0,
        deadline=datetime.now(UTC) + timedelta(minutes=15),
        resource_requirements={
            "cpu": 1.0,
            "memory": 512.0,
            "network": 128.0,
        },
    )


@pytest.fixture
def resource_intensive_characteristics():
    """Create resource-intensive operation characteristics."""
    return OperationCharacteristics(
        operation_type=SyncOperationType.CASCADE_DELETE,
        priority=OperationPriority.LOW,
        complexity=OperationComplexity.MASSIVE,
        impact=OperationImpact.GLOBAL,
        entity_count=100,
        relationship_count=500,
        data_size_bytes=10240,
        business_criticality=0.3,
        resource_requirements={
            "cpu": 3.0,
            "memory": 4096.0,
            "network": 512.0,
        },
    )


class TestOperationPriorityManagerInitialization:
    """Test priority manager initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        manager = OperationPriorityManager()

        assert manager.max_concurrent_operations == 10
        assert len(manager._priority_queues) == len(OperationPriority)
        assert len(manager._active_operations) == 0
        assert manager._resource_usage == {"cpu": 0.0, "memory": 0.0, "network": 0.0}
        assert manager._max_resources == {
            "cpu": 4.0,
            "memory": 8192.0,
            "network": 1024.0,
        }

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        manager = OperationPriorityManager(max_concurrent_operations=20)

        assert manager.max_concurrent_operations == 20
        assert len(manager._priority_queues) == len(OperationPriority)
        for queue in manager._priority_queues.values():
            assert queue == []

    def test_priority_queues_initialization(self):
        """Test that all priority levels have empty queues."""
        manager = OperationPriorityManager()

        for priority in OperationPriority:
            assert priority in manager._priority_queues
            assert manager._priority_queues[priority] == []


class TestOperationQueuing:
    """Test operation queuing functionality."""

    @pytest.mark.asyncio
    async def test_queue_operation_basic(
        self, priority_manager, sample_operation, sample_characteristics
    ):
        """Test basic operation queuing."""
        await priority_manager.queue_operation(sample_operation, sample_characteristics)

        queue = priority_manager._priority_queues[OperationPriority.MEDIUM]
        assert len(queue) == 1

        score, operation, characteristics = queue[0]
        assert operation == sample_operation
        assert characteristics == sample_characteristics
        assert score > 0

    @pytest.mark.asyncio
    async def test_queue_multiple_operations_same_priority(
        self, priority_manager, sample_characteristics
    ):
        """Test queuing multiple operations with same priority."""
        operations = []
        for i in range(3):
            op = Mock()
            op.operation_id = f"test-op-{i}"
            operations.append(op)
            await priority_manager.queue_operation(op, sample_characteristics)

        queue = priority_manager._priority_queues[OperationPriority.MEDIUM]
        assert len(queue) == 3

        # Check that operations are sorted by priority score
        scores = [item[0] for item in queue]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_queue_operations_different_priorities(
        self,
        priority_manager,
        sample_operation,
        sample_characteristics,
        high_priority_characteristics,
    ):
        """Test queuing operations with different priorities."""
        high_op = Mock()
        high_op.operation_id = "high-priority-op"

        await priority_manager.queue_operation(sample_operation, sample_characteristics)
        await priority_manager.queue_operation(high_op, high_priority_characteristics)

        medium_queue = priority_manager._priority_queues[OperationPriority.MEDIUM]
        high_queue = priority_manager._priority_queues[OperationPriority.HIGH]

        assert len(medium_queue) == 1
        assert len(high_queue) == 1
        assert medium_queue[0][1] == sample_operation
        assert high_queue[0][1] == high_op

    @pytest.mark.asyncio
    async def test_queue_operation_priority_score_calculation(
        self, priority_manager, critical_characteristics
    ):
        """Test that priority score is calculated correctly."""
        operation = Mock()
        operation.operation_id = "critical-op"

        await priority_manager.queue_operation(operation, critical_characteristics)

        queue = priority_manager._priority_queues[OperationPriority.CRITICAL]
        score, _, _ = queue[0]

        # Critical operations should have high scores
        assert score > 1000

    @pytest.mark.asyncio
    async def test_queue_operation_with_deadline(
        self, priority_manager, sample_characteristics
    ):
        """Test queuing operation with urgent deadline."""
        urgent_characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            priority=OperationPriority.MEDIUM,
            deadline=datetime.now(UTC) + timedelta(minutes=30),  # Urgent deadline
            business_criticality=0.8,
        )

        operation = Mock()
        operation.operation_id = "urgent-op"

        await priority_manager.queue_operation(operation, urgent_characteristics)

        queue = priority_manager._priority_queues[OperationPriority.MEDIUM]
        score, _, _ = queue[0]

        # Should have higher score due to urgent deadline
        assert score > 600  # Base medium score (500) + deadline boost


class TestOperationSelection:
    """Test operation selection and resource allocation."""

    @pytest.mark.asyncio
    async def test_get_next_operation_empty_queue(self, priority_manager):
        """Test getting next operation from empty queue."""
        result = await priority_manager.get_next_operation()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_operation_single_operation(
        self, priority_manager, sample_operation, sample_characteristics
    ):
        """Test getting next operation with single queued operation."""
        await priority_manager.queue_operation(sample_operation, sample_characteristics)

        result = await priority_manager.get_next_operation()
        assert result is not None

        operation, characteristics = result
        assert operation == sample_operation
        assert characteristics == sample_characteristics

        # Operation should be moved to active operations
        assert sample_operation.operation_id in priority_manager._active_operations

        # Queue should be empty
        queue = priority_manager._priority_queues[OperationPriority.MEDIUM]
        assert len(queue) == 0

    @pytest.mark.asyncio
    async def test_get_next_operation_priority_order(
        self,
        priority_manager,
        sample_operation,
        sample_characteristics,
        high_priority_characteristics,
    ):
        """Test that operations are selected in priority order."""
        high_op = Mock()
        high_op.operation_id = "high-priority-op"

        # Queue medium priority first, then high priority
        await priority_manager.queue_operation(sample_operation, sample_characteristics)
        await priority_manager.queue_operation(high_op, high_priority_characteristics)

        # Should get high priority operation first
        result = await priority_manager.get_next_operation()
        operation, _ = result
        assert operation == high_op

    @pytest.mark.asyncio
    async def test_get_next_operation_resource_constraints(
        self, priority_manager, resource_intensive_characteristics
    ):
        """Test that resource constraints are respected."""
        operation = Mock()
        operation.operation_id = "resource-intensive-op"

        await priority_manager.queue_operation(
            operation, resource_intensive_characteristics
        )

        result = await priority_manager.get_next_operation()
        assert result is not None  # Should fit within default resource limits

        # Now try to queue another resource-intensive operation
        operation2 = Mock()
        operation2.operation_id = "resource-intensive-op-2"

        await priority_manager.queue_operation(
            operation2, resource_intensive_characteristics
        )

        # Should not be able to allocate resources for second operation
        result2 = await priority_manager.get_next_operation()
        assert result2 is None

    @pytest.mark.asyncio
    async def test_get_next_operation_concurrent_limit(
        self, priority_manager, sample_operation, sample_characteristics
    ):
        """Test concurrent operation limit."""
        # Fill up to maximum concurrent operations
        operations = []
        for i in range(priority_manager.max_concurrent_operations):
            op = Mock()
            op.operation_id = f"concurrent-op-{i}"
            operations.append(op)
            await priority_manager.queue_operation(op, sample_characteristics)

            result = await priority_manager.get_next_operation()
            assert result is not None

        # Try to get one more operation - should fail due to concurrent limit
        extra_op = Mock()
        extra_op.operation_id = "extra-op"
        await priority_manager.queue_operation(extra_op, sample_characteristics)

        result = await priority_manager.get_next_operation()
        assert result is None

    @pytest.mark.asyncio
    async def test_resource_allocation_tracking(
        self, priority_manager, sample_operation, sample_characteristics
    ):
        """Test that resource allocation is tracked correctly."""
        await priority_manager.queue_operation(sample_operation, sample_characteristics)

        # Check initial resource usage
        assert priority_manager._resource_usage["cpu"] == 0.0
        assert priority_manager._resource_usage["memory"] == 0.0
        assert priority_manager._resource_usage["network"] == 0.0

        # Get operation and check resource allocation
        result = await priority_manager.get_next_operation()
        assert result is not None

        expected_cpu = sample_characteristics.resource_requirements["cpu"]
        expected_memory = sample_characteristics.resource_requirements["memory"]
        expected_network = sample_characteristics.resource_requirements["network"]

        assert priority_manager._resource_usage["cpu"] == expected_cpu
        assert priority_manager._resource_usage["memory"] == expected_memory
        assert priority_manager._resource_usage["network"] == expected_network


class TestResourceManagement:
    """Test resource management functionality."""

    @pytest.mark.asyncio
    async def test_can_allocate_resources_sufficient(
        self, priority_manager, sample_characteristics
    ):
        """Test resource allocation check with sufficient resources."""
        result = await priority_manager._can_allocate_resources(sample_characteristics)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_allocate_resources_insufficient(self, priority_manager):
        """Test resource allocation check with insufficient resources."""
        # Create characteristics that exceed resource limits
        excessive_characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.CASCADE_DELETE,
            resource_requirements={
                "cpu": 10.0,  # Exceeds default limit of 4.0
                "memory": 16384.0,  # Exceeds default limit of 8192.0
                "network": 2048.0,  # Exceeds default limit of 1024.0
            },
        )

        result = await priority_manager._can_allocate_resources(
            excessive_characteristics
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_can_allocate_resources_partial_usage(
        self, priority_manager, sample_characteristics
    ):
        """Test resource allocation with partial resource usage."""
        # Allocate some resources first
        priority_manager._resource_usage["cpu"] = 2.0
        priority_manager._resource_usage["memory"] = 4096.0
        priority_manager._resource_usage["network"] = 512.0

        result = await priority_manager._can_allocate_resources(sample_characteristics)
        assert result is True  # Should still fit within limits

    @pytest.mark.asyncio
    async def test_can_allocate_resources_at_limit(self, priority_manager):
        """Test resource allocation at resource limits."""
        # Set resource usage to exactly at limits
        priority_manager._resource_usage["cpu"] = 4.0
        priority_manager._resource_usage["memory"] = 8192.0
        priority_manager._resource_usage["network"] = 1024.0

        characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            resource_requirements={
                "cpu": 0.1,  # Would exceed limit
                "memory": 1.0,  # Would exceed limit
                "network": 1.0,  # Would exceed limit
            },
        )

        result = await priority_manager._can_allocate_resources(characteristics)
        assert result is False

    @pytest.mark.asyncio
    async def test_allocate_resources(
        self, priority_manager, sample_operation, sample_characteristics
    ):
        """Test resource allocation functionality."""
        await priority_manager._allocate_resources(
            sample_operation, sample_characteristics
        )

        # Check that operation is added to active operations
        assert sample_operation.operation_id in priority_manager._active_operations

        # Check that resources are allocated
        expected_cpu = sample_characteristics.resource_requirements["cpu"]
        expected_memory = sample_characteristics.resource_requirements["memory"]
        expected_network = sample_characteristics.resource_requirements["network"]

        assert priority_manager._resource_usage["cpu"] == expected_cpu
        assert priority_manager._resource_usage["memory"] == expected_memory
        assert priority_manager._resource_usage["network"] == expected_network

    @pytest.mark.asyncio
    async def test_release_operation_resources(
        self, priority_manager, sample_operation, sample_characteristics
    ):
        """Test resource release functionality."""
        # First allocate resources
        await priority_manager._allocate_resources(
            sample_operation, sample_characteristics
        )

        # Verify resources are allocated
        assert priority_manager._resource_usage["cpu"] > 0
        assert priority_manager._resource_usage["memory"] > 0
        assert priority_manager._resource_usage["network"] > 0

        # Release resources
        await priority_manager.release_operation(sample_operation.operation_id)

        # Check that resources are released
        assert priority_manager._resource_usage["cpu"] == 0.0
        assert priority_manager._resource_usage["memory"] == 0.0
        assert priority_manager._resource_usage["network"] == 0.0

        # Check that operation is removed from active operations
        assert sample_operation.operation_id not in priority_manager._active_operations

    @pytest.mark.asyncio
    async def test_release_nonexistent_operation(self, priority_manager):
        """Test releasing resources for non-existent operation."""
        # Should not raise an error
        await priority_manager.release_operation("non-existent-op")

        # Resource usage should remain unchanged
        assert priority_manager._resource_usage["cpu"] == 0.0
        assert priority_manager._resource_usage["memory"] == 0.0
        assert priority_manager._resource_usage["network"] == 0.0

    @pytest.mark.asyncio
    async def test_release_operation_partial_resources(
        self, priority_manager, sample_characteristics
    ):
        """Test releasing resources with multiple active operations."""
        # Create two operations with different resource requirements
        op1 = Mock()
        op1.operation_id = "op1"

        op2 = Mock()
        op2.operation_id = "op2"

        characteristics2 = OperationCharacteristics(
            operation_type=SyncOperationType.UPDATE_ENTITY,
            resource_requirements={
                "cpu": 1.0,
                "memory": 512.0,
                "network": 128.0,
            },
        )

        # Allocate resources for both operations
        await priority_manager._allocate_resources(op1, sample_characteristics)
        await priority_manager._allocate_resources(op2, characteristics2)

        # Check total resource usage
        expected_cpu = (
            sample_characteristics.resource_requirements["cpu"]
            + characteristics2.resource_requirements["cpu"]
        )
        expected_memory = (
            sample_characteristics.resource_requirements["memory"]
            + characteristics2.resource_requirements["memory"]
        )
        expected_network = (
            sample_characteristics.resource_requirements["network"]
            + characteristics2.resource_requirements["network"]
        )

        assert priority_manager._resource_usage["cpu"] == expected_cpu
        assert priority_manager._resource_usage["memory"] == expected_memory
        assert priority_manager._resource_usage["network"] == expected_network

        # Release first operation
        await priority_manager.release_operation(op1.operation_id)

        # Check that only op2 resources remain
        assert (
            priority_manager._resource_usage["cpu"]
            == characteristics2.resource_requirements["cpu"]
        )
        assert (
            priority_manager._resource_usage["memory"]
            == characteristics2.resource_requirements["memory"]
        )
        assert (
            priority_manager._resource_usage["network"]
            == characteristics2.resource_requirements["network"]
        )


class TestQueueStatistics:
    """Test queue statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_queue_statistics_empty(self, priority_manager):
        """Test queue statistics with empty queues."""
        stats = await priority_manager.get_queue_statistics()

        assert stats["active_operations"] == 0
        assert stats["max_concurrent"] == priority_manager.max_concurrent_operations
        assert stats["resource_usage"] == {"cpu": 0.0, "memory": 0.0, "network": 0.0}
        assert stats["max_resources"] == {
            "cpu": 4.0,
            "memory": 8192.0,
            "network": 1024.0,
        }
        assert stats["queued_by_priority"] == {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "deferred": 0,
        }

    @pytest.mark.asyncio
    async def test_get_queue_statistics_with_operations(
        self,
        priority_manager,
        sample_operation,
        sample_characteristics,
        high_priority_characteristics,
    ):
        """Test queue statistics with queued and active operations."""
        # Queue operations
        high_op = Mock()
        high_op.operation_id = "high-priority-op"

        await priority_manager.queue_operation(sample_operation, sample_characteristics)
        await priority_manager.queue_operation(high_op, high_priority_characteristics)

        # Activate one operation
        result = await priority_manager.get_next_operation()
        assert result is not None

        stats = await priority_manager.get_queue_statistics()

        assert stats["active_operations"] == 1
        assert stats["max_concurrent"] == priority_manager.max_concurrent_operations

        # Check resource usage
        assert stats["resource_usage"]["cpu"] > 0
        assert stats["resource_usage"]["memory"] > 0
        assert stats["resource_usage"]["network"] > 0

        # Check queue counts
        assert stats["queued_by_priority"]["medium"] == 1  # One operation still queued
        assert (
            stats["queued_by_priority"]["high"] == 0
        )  # High priority operation was activated

    @pytest.mark.asyncio
    async def test_get_queue_statistics_multiple_priorities(
        self, priority_manager, sample_characteristics
    ):
        """Test queue statistics with multiple priority levels."""
        # Create operations with different priorities
        priorities = [
            OperationPriority.CRITICAL,
            OperationPriority.HIGH,
            OperationPriority.MEDIUM,
            OperationPriority.LOW,
        ]

        for i, priority in enumerate(priorities):
            characteristics = OperationCharacteristics(
                operation_type=SyncOperationType.CREATE_ENTITY,
                priority=priority,
                resource_requirements={"cpu": 0.1, "memory": 64.0, "network": 16.0},
            )

            for j in range(i + 1):  # Queue different numbers for each priority
                op = Mock()
                op.operation_id = f"{priority.value}-op-{j}"
                await priority_manager.queue_operation(op, characteristics)

        stats = await priority_manager.get_queue_statistics()

        assert stats["queued_by_priority"]["critical"] == 1
        assert stats["queued_by_priority"]["high"] == 2
        assert stats["queued_by_priority"]["medium"] == 3
        assert stats["queued_by_priority"]["low"] == 4

    @pytest.mark.asyncio
    async def test_get_queue_statistics_resource_usage_tracking(
        self, priority_manager, sample_characteristics
    ):
        """Test that statistics correctly track resource usage."""
        # Create multiple operations with known resource requirements
        operations = []
        total_cpu = 0.0
        total_memory = 0.0
        total_network = 0.0

        for i in range(3):
            op = Mock()
            op.operation_id = f"resource-op-{i}"
            operations.append(op)

            await priority_manager.queue_operation(op, sample_characteristics)

            # Activate operation
            result = await priority_manager.get_next_operation()
            assert result is not None

            total_cpu += sample_characteristics.resource_requirements["cpu"]
            total_memory += sample_characteristics.resource_requirements["memory"]
            total_network += sample_characteristics.resource_requirements["network"]

        stats = await priority_manager.get_queue_statistics()

        assert stats["active_operations"] == 3
        assert stats["resource_usage"]["cpu"] == total_cpu
        assert stats["resource_usage"]["memory"] == total_memory
        assert stats["resource_usage"]["network"] == total_network


class TestComplexScenarios:
    """Test complex scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_priority_queue_ordering_complex(self, priority_manager):
        """Test complex priority queue ordering with multiple factors."""
        # Create operations with different characteristics
        operations = []

        # Critical operation with urgent deadline
        critical_op = Mock()
        critical_op.operation_id = "critical-urgent"
        critical_char = OperationCharacteristics(
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            priority=OperationPriority.CRITICAL,
            business_criticality=1.0,
            deadline=datetime.now(UTC) + timedelta(minutes=15),
            resource_requirements={"cpu": 0.5, "memory": 256.0, "network": 64.0},
        )
        operations.append((critical_op, critical_char))

        # High priority operation with high success rate
        high_op = Mock()
        high_op.operation_id = "high-reliable"
        high_char = OperationCharacteristics(
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            priority=OperationPriority.HIGH,
            business_criticality=0.8,
            success_rate=0.95,
            complexity=OperationComplexity.SIMPLE,
            resource_requirements={"cpu": 0.3, "memory": 128.0, "network": 32.0},
        )
        operations.append((high_op, high_char))

        # Medium priority operation with moderate characteristics
        medium_op = Mock()
        medium_op.operation_id = "medium-standard"
        medium_char = OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            priority=OperationPriority.MEDIUM,
            business_criticality=0.5,
            complexity=OperationComplexity.MODERATE,
            resource_requirements={"cpu": 0.4, "memory": 192.0, "network": 48.0},
        )
        operations.append((medium_op, medium_char))

        # Queue all operations
        for op, char in operations:
            await priority_manager.queue_operation(op, char)

        # Get operations in priority order
        selected_operations = []
        for _ in range(3):
            result = await priority_manager.get_next_operation()
            if result:
                selected_operations.append(result[0])

        # Should get critical first, then high, then medium
        assert selected_operations[0] == critical_op
        assert selected_operations[1] == high_op
        assert selected_operations[2] == medium_op

    @pytest.mark.asyncio
    async def test_resource_constraint_complex_scenario(self, priority_manager):
        """Test complex resource constraint scenarios."""
        # Create operations with different resource requirements

        # High CPU operation
        cpu_intensive_op = Mock()
        cpu_intensive_op.operation_id = "cpu-intensive"
        cpu_char = OperationCharacteristics(
            operation_type=SyncOperationType.CASCADE_DELETE,
            priority=OperationPriority.HIGH,
            resource_requirements={"cpu": 3.5, "memory": 512.0, "network": 128.0},
        )

        # High memory operation
        memory_intensive_op = Mock()
        memory_intensive_op.operation_id = "memory-intensive"
        memory_char = OperationCharacteristics(
            operation_type=SyncOperationType.VERSION_UPDATE,
            priority=OperationPriority.HIGH,
            resource_requirements={"cpu": 0.5, "memory": 7000.0, "network": 256.0},
        )

        # High network operation
        network_intensive_op = Mock()
        network_intensive_op.operation_id = "network-intensive"
        network_char = OperationCharacteristics(
            operation_type=SyncOperationType.UPDATE_ENTITY,
            priority=OperationPriority.HIGH,
            resource_requirements={"cpu": 0.5, "memory": 512.0, "network": 900.0},
        )

        # Queue all operations
        await priority_manager.queue_operation(cpu_intensive_op, cpu_char)
        await priority_manager.queue_operation(memory_intensive_op, memory_char)
        await priority_manager.queue_operation(network_intensive_op, network_char)

        # Should be able to get CPU intensive operation
        result1 = await priority_manager.get_next_operation()
        assert result1 is not None
        assert result1[0] == cpu_intensive_op

        # Should be able to get memory intensive operation (different resource)
        result2 = await priority_manager.get_next_operation()
        assert result2 is not None
        assert result2[0] == memory_intensive_op

        # Should NOT be able to get network intensive operation (would exceed network limit)
        result3 = await priority_manager.get_next_operation()
        assert result3 is None

    @pytest.mark.asyncio
    async def test_full_lifecycle_scenario(self, priority_manager):
        """Test full operation lifecycle scenario."""
        # Create operations
        operations = []
        characteristics = []

        for i in range(10):
            op = Mock()
            op.operation_id = f"lifecycle-op-{i}"
            operations.append(op)

            char = OperationCharacteristics(
                operation_type=SyncOperationType.CREATE_DOCUMENT,
                priority=OperationPriority.MEDIUM,
                resource_requirements={"cpu": 0.3, "memory": 128.0, "network": 32.0},
            )
            characteristics.append(char)

        # Queue all operations
        for op, char in zip(operations, characteristics, strict=False):
            await priority_manager.queue_operation(op, char)

        # Process operations up to concurrent limit
        active_operations = []
        for _ in range(priority_manager.max_concurrent_operations):
            result = await priority_manager.get_next_operation()
            assert result is not None
            active_operations.append(result[0])

        # Should not be able to get more operations
        result = await priority_manager.get_next_operation()
        assert result is None

        # Check statistics
        stats = await priority_manager.get_queue_statistics()
        assert stats["active_operations"] == priority_manager.max_concurrent_operations
        assert stats["queued_by_priority"]["medium"] == 5  # 5 operations still queued

        # Release some operations
        for i in range(2):
            await priority_manager.release_operation(active_operations[i].operation_id)

        # Should be able to get more operations now
        for _ in range(2):
            result = await priority_manager.get_next_operation()
            assert result is not None

        # Final statistics check
        final_stats = await priority_manager.get_queue_statistics()
        assert (
            final_stats["active_operations"]
            == priority_manager.max_concurrent_operations
        )
        assert (
            final_stats["queued_by_priority"]["medium"] == 3
        )  # 3 operations still queued

    @pytest.mark.asyncio
    async def test_edge_case_zero_resources(self, priority_manager):
        """Test edge case with zero resource requirements."""
        operation = Mock()
        operation.operation_id = "zero-resource-op"

        characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            priority=OperationPriority.MEDIUM,
            resource_requirements={},  # No resource requirements
        )

        await priority_manager.queue_operation(operation, characteristics)

        result = await priority_manager.get_next_operation()
        assert result is not None

        # Resource usage should remain zero
        assert priority_manager._resource_usage["cpu"] == 0.0
        assert priority_manager._resource_usage["memory"] == 0.0
        assert priority_manager._resource_usage["network"] == 0.0

    @pytest.mark.asyncio
    async def test_edge_case_unknown_resource_type(self, priority_manager):
        """Test edge case with unknown resource type."""
        operation = Mock()
        operation.operation_id = "unknown-resource-op"

        characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            priority=OperationPriority.MEDIUM,
            resource_requirements={
                "cpu": 0.5,
                "memory": 256.0,
                "unknown_resource": 100.0,  # Unknown resource type
            },
        )

        await priority_manager.queue_operation(operation, characteristics)

        result = await priority_manager.get_next_operation()
        assert result is not None

        # Should handle unknown resource type gracefully
        assert priority_manager._resource_usage["cpu"] == 0.5
        assert priority_manager._resource_usage["memory"] == 256.0
        # Priority manager tracks all resource types, including unknown ones
        assert priority_manager._resource_usage["unknown_resource"] == 100.0
