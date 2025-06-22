"""
Unit tests for OperationDifferentiationManager.

Tests comprehensive operation differentiation including classification, validation,
priority management, queuing, statistics tracking, and health monitoring.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from qdrant_loader.core.operation_differentiation import (
    OperationCharacteristics,
    OperationComplexity,
    OperationDifferentiationManager,
    OperationImpact,
    OperationPriority,
    ValidationLevel,
    ValidationResult,
)
from qdrant_loader.core.sync import (
    EnhancedSyncOperation,
    SyncOperationType,
)


@pytest.fixture
def mock_operation_classifier():
    """Create mock operation classifier."""
    mock = AsyncMock()
    mock.classify_operation = AsyncMock(
        return_value=OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            complexity=OperationComplexity.MODERATE,
            impact=OperationImpact.LOCAL,
            priority=OperationPriority.MEDIUM,
            average_duration=5.0,
            resource_requirements={"memory": 100, "cpu": 50},
            business_criticality=0.7,
        )
    )
    return mock


@pytest.fixture
def mock_priority_manager():
    """Create mock priority manager."""
    mock = AsyncMock()
    mock.queue_operation = AsyncMock()
    mock.get_next_operation = AsyncMock(return_value=None)
    mock.release_operation = AsyncMock()
    mock.get_queue_statistics = AsyncMock(
        return_value={
            "total_queued": 0,
            "active_operations": 0,
            "completed_operations": 0,
        }
    )
    mock.max_concurrent_operations = 10
    mock._active_operations = {}
    return mock


@pytest.fixture
def mock_operation_validator():
    """Create mock operation validator."""
    mock = AsyncMock()
    mock.validate_operation = AsyncMock(
        return_value=ValidationResult(
            is_valid=True,
            validation_level=ValidationLevel.STANDARD,
            errors=[],
            warnings=[],
            metadata={},
        )
    )
    return mock


@pytest.fixture
def operation_differentiation_manager(
    mock_operation_classifier, mock_priority_manager, mock_operation_validator
):
    """Create OperationDifferentiationManager instance with mocks."""
    manager = OperationDifferentiationManager(
        max_concurrent_operations=10,
        enable_caching=True,
        cache_ttl_seconds=3600,
    )

    # Replace components with mocks
    manager.classifier = mock_operation_classifier
    manager.priority_manager = mock_priority_manager
    manager.validator = mock_operation_validator

    return manager


@pytest.fixture
def sample_sync_operation():
    """Create sample sync operation."""
    return EnhancedSyncOperation(
        operation_type=SyncOperationType.CREATE_DOCUMENT,
        entity_id="doc_001",
        operation_data={"content": "test content"},
        metadata={"source": "test"},
    )


class TestOperationDifferentiationManager:
    """Test suite for OperationDifferentiationManager."""

    def test_initialization_basic(self):
        """Test basic initialization of operation differentiation manager."""
        manager = OperationDifferentiationManager()

        assert manager.enable_caching is True
        assert manager.cache_ttl_seconds == 3600
        assert manager.classifier is not None
        assert manager.priority_manager is not None
        assert manager.validator is not None
        assert manager._stats["operations_classified"] == 0
        assert manager._stats["operations_validated"] == 0
        assert manager._stats["operations_queued"] == 0
        assert manager._stats["operations_processed"] == 0
        assert manager._stats["validation_failures"] == 0

    def test_initialization_with_custom_settings(self):
        """Test initialization with custom settings."""
        manager = OperationDifferentiationManager(
            max_concurrent_operations=20,
            enable_caching=False,
            cache_ttl_seconds=7200,
        )

        assert manager.enable_caching is False
        assert manager.cache_ttl_seconds == 7200
        assert manager.priority_manager.max_concurrent_operations == 20

    @pytest.mark.asyncio
    async def test_process_operation_success(
        self, operation_differentiation_manager, sample_sync_operation
    ):
        """Test successful operation processing."""
        manager = operation_differentiation_manager
        operation = sample_sync_operation

        characteristics, validation_result = await manager.process_operation(operation)

        # Verify classification was called
        manager.classifier.classify_operation.assert_called_once_with(operation, None)

        # Verify validation was called
        manager.validator.validate_operation.assert_called_once()

        # Verify queuing was called (since validation passed)
        manager.priority_manager.queue_operation.assert_called_once()

        # Verify statistics were updated
        assert manager._stats["operations_classified"] == 1
        assert manager._stats["operations_validated"] == 1
        assert manager._stats["operations_queued"] == 1
        assert manager._stats["validation_failures"] == 0

        # Verify return values
        assert isinstance(characteristics, OperationCharacteristics)
        assert isinstance(validation_result, ValidationResult)
        assert validation_result.is_valid is True

    @pytest.mark.asyncio
    async def test_process_operation_with_context(
        self, operation_differentiation_manager, sample_sync_operation
    ):
        """Test operation processing with additional context."""
        manager = operation_differentiation_manager
        operation = sample_sync_operation
        context = {"priority_boost": True, "deadline": datetime.now(UTC)}

        characteristics, validation_result = await manager.process_operation(
            operation, context
        )

        # Verify context was passed to classifier and validator
        manager.classifier.classify_operation.assert_called_once_with(
            operation, context
        )
        manager.validator.validate_operation.assert_called_once()

        # Verify the context was passed to validator
        call_args = manager.validator.validate_operation.call_args
        assert call_args[0][2] == context  # Third argument should be context

    @pytest.mark.asyncio
    async def test_process_operation_validation_failure(
        self, operation_differentiation_manager, sample_sync_operation
    ):
        """Test operation processing with validation failure."""
        manager = operation_differentiation_manager
        operation = sample_sync_operation

        # Mock validation failure
        manager.validator.validate_operation.return_value = ValidationResult(
            is_valid=False,
            validation_level=ValidationLevel.STRICT,
            errors=["Invalid operation data"],
            warnings=["Performance concern"],
            metadata={},
        )

        characteristics, validation_result = await manager.process_operation(operation)

        # Verify classification and validation were called
        manager.classifier.classify_operation.assert_called_once()
        manager.validator.validate_operation.assert_called_once()

        # Verify queuing was NOT called (since validation failed)
        manager.priority_manager.queue_operation.assert_not_called()

        # Verify statistics were updated correctly
        assert manager._stats["operations_classified"] == 1
        assert manager._stats["operations_validated"] == 1
        assert manager._stats["operations_queued"] == 0
        assert manager._stats["validation_failures"] == 1

        # Verify return values
        assert validation_result.is_valid is False
        assert "Invalid operation data" in validation_result.errors

    @pytest.mark.asyncio
    async def test_get_next_operation_with_result(
        self, operation_differentiation_manager, sample_sync_operation
    ):
        """Test getting next operation when one is available."""
        manager = operation_differentiation_manager
        operation = sample_sync_operation

        # Mock characteristics
        characteristics = OperationCharacteristics(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            complexity=OperationComplexity.SIMPLE,
            impact=OperationImpact.MINIMAL,
            priority=OperationPriority.HIGH,
        )

        # Mock priority manager to return operation
        manager.priority_manager.get_next_operation.return_value = (
            operation,
            characteristics,
        )

        result = await manager.get_next_operation()

        # Verify priority manager was called
        manager.priority_manager.get_next_operation.assert_called_once()

        # Verify statistics were updated
        assert manager._stats["operations_processed"] == 1

        # Verify return value
        assert result is not None
        assert result[0] == operation
        assert result[1] == characteristics

    @pytest.mark.asyncio
    async def test_get_next_operation_no_result(
        self, operation_differentiation_manager
    ):
        """Test getting next operation when none is available."""
        manager = operation_differentiation_manager

        # Mock priority manager to return None
        manager.priority_manager.get_next_operation.return_value = None

        result = await manager.get_next_operation()

        # Verify priority manager was called
        manager.priority_manager.get_next_operation.assert_called_once()

        # Verify statistics were NOT updated
        assert manager._stats["operations_processed"] == 0

        # Verify return value
        assert result is None

    @pytest.mark.asyncio
    async def test_complete_operation(self, operation_differentiation_manager):
        """Test completing an operation."""
        manager = operation_differentiation_manager
        operation_id = "op_001"

        await manager.complete_operation(operation_id, success=True, duration=5.5)

        # Verify priority manager release was called
        manager.priority_manager.release_operation.assert_called_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_get_statistics(self, operation_differentiation_manager):
        """Test getting comprehensive statistics."""
        manager = operation_differentiation_manager

        # Update some statistics
        manager._stats["operations_classified"] = 10
        manager._stats["operations_validated"] = 8
        manager._stats["operations_queued"] = 7
        manager._stats["validation_failures"] = 2

        # Mock queue statistics
        queue_stats = {
            "total_queued": 5,
            "active_operations": 3,
            "completed_operations": 2,
        }
        manager.priority_manager.get_queue_statistics.return_value = queue_stats

        stats = await manager.get_statistics()

        # Verify priority manager was called
        manager.priority_manager.get_queue_statistics.assert_called_once()

        # Verify statistics structure
        assert "differentiation_stats" in stats
        assert "queue_stats" in stats
        assert "cache_enabled" in stats
        assert "cache_ttl_seconds" in stats

        # Verify differentiation stats
        diff_stats = stats["differentiation_stats"]
        assert diff_stats["operations_classified"] == 10
        assert diff_stats["operations_validated"] == 8
        assert diff_stats["operations_queued"] == 7
        assert diff_stats["validation_failures"] == 2

        # Verify queue stats
        assert stats["queue_stats"] == queue_stats

        # Verify configuration
        assert stats["cache_enabled"] is True
        assert stats["cache_ttl_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_health_check(self, operation_differentiation_manager):
        """Test health check functionality."""
        manager = operation_differentiation_manager

        health = await manager.health_check()

        # Verify health check structure
        assert "status" in health
        assert "components" in health
        assert "active_operations" in health
        assert "max_concurrent" in health

        # Verify status
        assert health["status"] == "healthy"

        # Verify components
        components = health["components"]
        assert components["classifier"] == "operational"
        assert components["priority_manager"] == "operational"
        assert components["validator"] == "operational"

        # Verify operational metrics
        assert health["active_operations"] == 0  # Empty dict length
        assert health["max_concurrent"] == 10

    @pytest.mark.asyncio
    async def test_multiple_operations_processing(
        self, operation_differentiation_manager
    ):
        """Test processing multiple operations."""
        manager = operation_differentiation_manager

        # Create multiple operations
        operations = [
            EnhancedSyncOperation(
                operation_type=SyncOperationType.CREATE_DOCUMENT,
                entity_id=f"doc_{i}",
                operation_data={"content": f"content {i}"},
            )
            for i in range(3)
        ]

        # Process all operations
        results = []
        for operation in operations:
            result = await manager.process_operation(operation)
            results.append(result)

        # Verify all operations were processed
        assert len(results) == 3
        assert manager._stats["operations_classified"] == 3
        assert manager._stats["operations_validated"] == 3
        assert manager._stats["operations_queued"] == 3

        # Verify each result
        for characteristics, validation_result in results:
            assert isinstance(characteristics, OperationCharacteristics)
            assert isinstance(validation_result, ValidationResult)
            assert validation_result.is_valid is True

    @pytest.mark.asyncio
    async def test_mixed_validation_results(self, operation_differentiation_manager):
        """Test processing operations with mixed validation results."""
        manager = operation_differentiation_manager

        # Create operations
        operations = [
            EnhancedSyncOperation(
                operation_type=SyncOperationType.CREATE_DOCUMENT,
                entity_id="doc_valid",
                operation_data={"content": "valid content"},
            ),
            EnhancedSyncOperation(
                operation_type=SyncOperationType.UPDATE_DOCUMENT,
                entity_id="doc_invalid",
                operation_data={"content": "invalid content"},
            ),
        ]

        # Mock validator to return different results
        validation_results = [
            ValidationResult(
                is_valid=True,
                validation_level=ValidationLevel.STANDARD,
                errors=[],
                warnings=[],
                metadata={},
            ),
            ValidationResult(
                is_valid=False,
                validation_level=ValidationLevel.STRICT,
                errors=["Invalid content"],
                warnings=[],
                metadata={},
            ),
        ]

        # Process operations with different validation results
        results = []
        for i, operation in enumerate(operations):
            manager.validator.validate_operation.return_value = validation_results[i]
            result = await manager.process_operation(operation)
            results.append(result)

        # Verify statistics
        assert manager._stats["operations_classified"] == 2
        assert manager._stats["operations_validated"] == 2
        assert manager._stats["operations_queued"] == 1  # Only valid operation queued
        assert manager._stats["validation_failures"] == 1

        # Verify results
        assert results[0][1].is_valid is True
        assert results[1][1].is_valid is False

    @pytest.mark.asyncio
    async def test_operation_lifecycle(self, operation_differentiation_manager):
        """Test complete operation lifecycle."""
        manager = operation_differentiation_manager
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_lifecycle",
            operation_data={"content": "lifecycle test"},
        )

        # Step 1: Process operation
        characteristics, validation_result = await manager.process_operation(operation)
        assert validation_result.is_valid is True

        # Step 2: Get next operation
        manager.priority_manager.get_next_operation.return_value = (
            operation,
            characteristics,
        )
        next_op = await manager.get_next_operation()
        assert next_op is not None

        # Step 3: Complete operation
        await manager.complete_operation(
            operation.operation_id, success=True, duration=3.5
        )

        # Verify all steps were executed
        manager.classifier.classify_operation.assert_called()
        manager.validator.validate_operation.assert_called()
        manager.priority_manager.queue_operation.assert_called()
        manager.priority_manager.get_next_operation.assert_called()
        manager.priority_manager.release_operation.assert_called_with(
            operation.operation_id
        )

    def test_statistics_initialization(self):
        """Test that statistics are properly initialized."""
        manager = OperationDifferentiationManager()

        expected_stats = {
            "operations_classified": 0,
            "operations_validated": 0,
            "operations_queued": 0,
            "operations_processed": 0,
            "validation_failures": 0,
        }

        assert manager._stats == expected_stats

    @pytest.mark.asyncio
    async def test_exception_handling_in_process_operation(
        self, operation_differentiation_manager, sample_sync_operation
    ):
        """Test exception handling during operation processing."""
        manager = operation_differentiation_manager
        operation = sample_sync_operation

        # Mock classifier to raise exception
        manager.classifier.classify_operation.side_effect = Exception(
            "Classification error"
        )

        # Process operation should handle exception gracefully
        with pytest.raises(Exception, match="Classification error"):
            await manager.process_operation(operation)

        # Verify statistics were still updated for classification attempt
        assert manager._stats["operations_classified"] == 0  # Failed before increment

    @pytest.mark.asyncio
    async def test_caching_configuration(self):
        """Test caching configuration options."""
        # Test with caching enabled
        manager_cached = OperationDifferentiationManager(
            enable_caching=True, cache_ttl_seconds=1800
        )
        assert manager_cached.enable_caching is True
        assert manager_cached.cache_ttl_seconds == 1800

        # Test with caching disabled
        manager_no_cache = OperationDifferentiationManager(
            enable_caching=False, cache_ttl_seconds=0
        )
        assert manager_no_cache.enable_caching is False
        assert manager_no_cache.cache_ttl_seconds == 0

    @pytest.mark.asyncio
    async def test_concurrent_operations_limit(self):
        """Test concurrent operations limit configuration."""
        manager = OperationDifferentiationManager(max_concurrent_operations=5)

        # Verify the limit was passed to priority manager
        assert manager.priority_manager.max_concurrent_operations == 5

        # Test health check reflects the limit
        health = await manager.health_check()
        assert health["max_concurrent"] == 5
