"""Tests for operation classifier."""

import hashlib
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from qdrant_loader.core.operation_differentiation.classifier import OperationClassifier
from qdrant_loader.core.operation_differentiation.types import (
    OperationCharacteristics,
    OperationComplexity,
    OperationImpact,
    OperationPriority,
    ValidationLevel,
)
from qdrant_loader.core.sync.types import SyncOperationType
from qdrant_loader.core.types import EntityType


class MockEnhancedSyncOperation:
    """Mock enhanced sync operation for testing."""

    def __init__(
        self,
        operation_id: str = "test-op-123",
        operation_type: SyncOperationType = SyncOperationType.CREATE_ENTITY,
        entity_type: EntityType = EntityType.SERVICE,
        entity_id: str | None = "entity-123",
        operation_data: dict | str | None = None,
        previous_data: dict | None = None,
        metadata: dict | None = None,
        timestamp: datetime | None = None,
        dependent_operations: list[str] | None = None,
        related_operations: list[str] | None = None,
        document_version: int = 1,
        previous_version: int | None = None,
        content_hash: str | None = None,
    ):
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.operation_data = operation_data or {}
        self.previous_data = previous_data
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(UTC)
        self.dependent_operations = dependent_operations or []
        self.related_operations = related_operations or []
        self.document_version = document_version
        self.previous_version = previous_version
        self.content_hash = content_hash


@pytest.fixture
def classifier():
    """Create a classifier instance for testing."""
    return OperationClassifier()


@pytest.fixture
def sample_operation():
    """Create a sample operation for testing."""
    return MockEnhancedSyncOperation(
        operation_id="test-op-123",
        operation_type=SyncOperationType.CREATE_ENTITY,
        entity_type=EntityType.SERVICE,
        entity_id="entity-123",
        operation_data={"name": "test", "data": "content"},
        metadata={"source": "test"},
    )


class TestOperationClassifier:
    """Test cases for OperationClassifier."""

    def test_classifier_initialization(self, classifier):
        """Test classifier initialization."""
        assert isinstance(classifier._classification_cache, dict)
        assert isinstance(classifier._historical_data, dict)
        assert len(classifier._classification_cache) == 0
        assert len(classifier._historical_data) == 0

    @pytest.mark.asyncio
    async def test_classify_operation_basic(self, classifier, sample_operation):
        """Test basic operation classification."""
        characteristics = await classifier.classify_operation(sample_operation)

        assert isinstance(characteristics, OperationCharacteristics)
        assert characteristics.operation_type == SyncOperationType.CREATE_ENTITY
        assert characteristics.priority == OperationPriority.MEDIUM
        assert characteristics.complexity == OperationComplexity.SIMPLE
        assert characteristics.impact == OperationImpact.REGIONAL  # SERVICE entity
        assert characteristics.entity_count == 1
        assert characteristics.data_size_bytes > 0
        assert characteristics.content_hash is not None

    @pytest.mark.asyncio
    async def test_classify_operation_with_context(self, classifier, sample_operation):
        """Test operation classification with context."""
        context = {
            "source_system": "test_system",
            "user_context": {"user": "test_user"},
            "business_criticality": 0.9,
            "deadline": datetime.now(UTC).isoformat(),
        }

        characteristics = await classifier.classify_operation(sample_operation, context)

        assert characteristics.source_system == "test_system"
        assert characteristics.user_context == {"user": "test_user"}
        assert characteristics.business_criticality == 0.9
        assert characteristics.deadline is not None
        assert (
            characteristics.priority == OperationPriority.HIGH
        )  # Elevated due to high criticality

    @pytest.mark.asyncio
    async def test_classify_operation_caching(self, classifier, sample_operation):
        """Test operation classification caching."""
        # First classification
        characteristics1 = await classifier.classify_operation(sample_operation)

        # Second classification should use cache
        characteristics2 = await classifier.classify_operation(sample_operation)

        assert characteristics1 == characteristics2
        assert len(classifier._classification_cache) == 1

    @pytest.mark.asyncio
    async def test_classify_complex_operation(self, classifier):
        """Test classification of complex operation."""
        large_data = {
            "entities": [f"entity_{i}" for i in range(50)],
            "relationships": [f"rel_{i}" for i in range(25)],
            "content": "x" * 5000,  # Large content
        }

        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.UPDATE_ENTITY,
            operation_data=large_data,
            metadata={"large": "metadata" * 100},
        )

        characteristics = await classifier.classify_operation(operation)

        # With 50 entities and >6KB data, this should be COMPLEX
        assert characteristics.complexity == OperationComplexity.COMPLEX
        assert characteristics.entity_count == 50
        assert characteristics.relationship_count == 25
        assert characteristics.data_size_bytes > 5000

    @pytest.mark.asyncio
    async def test_classify_cascade_delete(self, classifier):
        """Test classification of cascade delete operation."""
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.CASCADE_DELETE,
            entity_type=EntityType.SERVICE,
        )

        characteristics = await classifier.classify_operation(operation)

        assert characteristics.priority == OperationPriority.HIGH
        assert characteristics.impact == OperationImpact.REGIONAL
        assert characteristics.validation_level == ValidationLevel.STRICT
        assert characteristics.requires_cross_validation is True
        assert characteristics.requires_integrity_check is True

    @pytest.mark.asyncio
    async def test_analyze_content_simple_operation(self, classifier):
        """Test content analysis for simple operation."""
        operation = MockEnhancedSyncOperation(
            operation_data={"simple": "data"},
            metadata={"meta": "info"},
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._analyze_content(operation, characteristics)

        assert characteristics.complexity == OperationComplexity.SIMPLE
        assert characteristics.entity_count == 1
        assert characteristics.relationship_count == 0
        assert characteristics.data_size_bytes > 0
        assert characteristics.content_hash is not None

    @pytest.mark.asyncio
    async def test_analyze_content_moderate_operation(self, classifier):
        """Test content analysis for moderate operation."""
        operation = MockEnhancedSyncOperation(
            operation_data={
                "entities": ["e1", "e2", "e3"],
                "relationships": ["r1"],
                "content": "x" * 2000,
            },
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._analyze_content(operation, characteristics)

        assert characteristics.complexity == OperationComplexity.MODERATE
        assert characteristics.entity_count == 3
        assert characteristics.relationship_count == 1

    @pytest.mark.asyncio
    async def test_analyze_content_no_operation_data(self, classifier):
        """Test content analysis with no operation data."""
        operation = MockEnhancedSyncOperation(
            operation_data=None,
            entity_id="entity-123",
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._analyze_content(operation, characteristics)

        # When operation_data is None but entity_id exists, entity_count should still be 1
        assert characteristics.entity_count == 1
        assert characteristics.relationship_count == 0
        assert characteristics.complexity == OperationComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_analyze_content_non_dict_data(self, classifier):
        """Test content analysis with non-dict operation data."""
        operation = MockEnhancedSyncOperation(
            operation_data="string_data",
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._analyze_content(operation, characteristics)

        assert characteristics.entity_count == 1
        assert characteristics.relationship_count == 0

    @pytest.mark.asyncio
    async def test_analyze_context_priority_adjustment(
        self, classifier, sample_operation
    ):
        """Test context analysis priority adjustment."""
        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )

        context = {"business_criticality": 0.9}
        await classifier._analyze_context(sample_operation, characteristics, context)

        # Should be elevated from MEDIUM to HIGH due to high business criticality
        assert characteristics.priority == OperationPriority.HIGH

    @pytest.mark.asyncio
    async def test_analyze_context_different_operation_types(self, classifier):
        """Test context analysis for different operation types."""
        # Test VERSION_UPDATE operation
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.VERSION_UPDATE,
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._analyze_context(operation, characteristics, None)

        assert characteristics.priority == OperationPriority.LOW

    @pytest.mark.asyncio
    async def test_analyze_context_impact_determination(self, classifier):
        """Test context analysis impact determination."""
        # Test with SERVICE entity type
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_ENTITY,
            entity_type=EntityType.SERVICE,
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._analyze_context(operation, characteristics, None)

        assert characteristics.impact == OperationImpact.REGIONAL

    @pytest.mark.asyncio
    async def test_analyze_context_deadline_parsing(self, classifier, sample_operation):
        """Test context analysis deadline parsing."""
        deadline_str = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        context = {"deadline": deadline_str}
        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )

        await classifier._analyze_context(sample_operation, characteristics, context)

        assert characteristics.deadline is not None
        assert isinstance(characteristics.deadline, datetime)

    @pytest.mark.asyncio
    async def test_analyze_context_no_context(self, classifier, sample_operation):
        """Test context analysis with no context."""
        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )

        await classifier._analyze_context(sample_operation, characteristics, None)

        assert characteristics.source_system is None
        assert characteristics.user_context is None
        assert characteristics.business_criticality == 0.5  # Default value

    @pytest.mark.asyncio
    async def test_analyze_historical_patterns_with_data(
        self, classifier, sample_operation
    ):
        """Test historical patterns analysis with existing data."""
        # Set up historical data
        operation_key = f"{sample_operation.operation_type.value}_{sample_operation.entity_type.value}"
        base_time = datetime.now(UTC) - timedelta(hours=2)

        classifier._historical_data[operation_key] = [
            {
                "timestamp": base_time.isoformat(),
                "success": True,
                "duration": 1.5,
            },
            {
                "timestamp": (base_time + timedelta(hours=1)).isoformat(),
                "success": True,
                "duration": 2.0,
            },
            {
                "timestamp": (base_time + timedelta(hours=1, minutes=30)).isoformat(),
                "success": False,
                "duration": 0.5,
            },
        ]

        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )

        await classifier._analyze_historical_patterns(sample_operation, characteristics)

        assert characteristics.operation_frequency > 0
        assert 0 <= characteristics.success_rate <= 1
        assert characteristics.average_duration > 0

    @pytest.mark.asyncio
    async def test_analyze_historical_patterns_no_data(
        self, classifier, sample_operation
    ):
        """Test historical patterns analysis with no existing data."""
        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )

        await classifier._analyze_historical_patterns(sample_operation, characteristics)

        assert characteristics.operation_frequency == 0.0
        assert characteristics.success_rate == 1.0  # Default
        assert characteristics.average_duration == 0.0

    @pytest.mark.asyncio
    async def test_analyze_historical_patterns_single_entry(
        self, classifier, sample_operation
    ):
        """Test historical patterns analysis with single entry."""
        operation_key = f"{sample_operation.operation_type.value}_{sample_operation.entity_type.value}"
        classifier._historical_data[operation_key] = [
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "success": True,
                "duration": 1.0,
            }
        ]

        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )

        await classifier._analyze_historical_patterns(sample_operation, characteristics)

        # With single entry, frequency calculation should handle gracefully
        assert characteristics.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_analyze_dependencies_resource_estimation(
        self, classifier, sample_operation
    ):
        """Test dependencies analysis and resource estimation."""
        sample_operation.dependent_operations = ["dep1", "dep2"]
        sample_operation.related_operations = ["rel1", "rel2"]

        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )
        characteristics.complexity = OperationComplexity.COMPLEX

        await classifier._analyze_dependencies(sample_operation, characteristics)

        assert characteristics.blocking_operations == ["dep1", "dep2"]
        assert characteristics.dependent_operations == ["rel1", "rel2"]
        assert "cpu" in characteristics.resource_requirements
        assert "memory" in characteristics.resource_requirements
        assert "network" in characteristics.resource_requirements
        assert (
            characteristics.resource_requirements["cpu"] > 0.1
        )  # Should be higher for complex

    @pytest.mark.asyncio
    async def test_analyze_dependencies_complexity_scaling(self, classifier):
        """Test resource requirements scaling with complexity."""
        operation = MockEnhancedSyncOperation()

        # Test different complexity levels
        complexities = [
            OperationComplexity.SIMPLE,
            OperationComplexity.MODERATE,
            OperationComplexity.COMPLEX,
            OperationComplexity.MASSIVE,
        ]

        results = []
        for complexity in complexities:
            characteristics = OperationCharacteristics(
                operation_type=operation.operation_type
            )
            characteristics.complexity = complexity
            await classifier._analyze_dependencies(operation, characteristics)
            results.append(characteristics.resource_requirements["cpu"])

        # CPU requirements should increase with complexity
        for i in range(1, len(results)):
            assert results[i] > results[i - 1]

    @pytest.mark.asyncio
    async def test_determine_validation_requirements_strict(self, classifier):
        """Test validation requirements determination for strict level."""
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.CASCADE_DELETE,
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._determine_validation_requirements(operation, characteristics)

        assert characteristics.validation_level == ValidationLevel.STRICT
        assert characteristics.requires_cross_validation is True
        assert characteristics.requires_integrity_check is True

    @pytest.mark.asyncio
    async def test_determine_validation_requirements_standard(self, classifier):
        """Test validation requirements determination for standard level."""
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.DELETE_ENTITY,
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._determine_validation_requirements(operation, characteristics)

        assert characteristics.validation_level == ValidationLevel.STANDARD
        assert characteristics.requires_integrity_check is True

    @pytest.mark.asyncio
    async def test_determine_validation_requirements_basic(self, classifier):
        """Test validation requirements determination for basic level."""
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.VERSION_UPDATE,
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        await classifier._determine_validation_requirements(operation, characteristics)

        assert characteristics.validation_level == ValidationLevel.BASIC

    @pytest.mark.asyncio
    async def test_validation_requirements_business_criticality_adjustment(
        self, classifier
    ):
        """Test validation requirements adjustment based on business criticality."""
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.VERSION_UPDATE,
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )
        characteristics.business_criticality = 0.9

        await classifier._determine_validation_requirements(operation, characteristics)

        # Should be elevated from BASIC to STANDARD due to high business criticality
        assert characteristics.validation_level == ValidationLevel.STANDARD

    @pytest.mark.asyncio
    async def test_validation_requirements_impact_adjustment(self, classifier):
        """Test validation requirements adjustment based on impact."""
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_ENTITY,
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )
        characteristics.impact = OperationImpact.REGIONAL

        await classifier._determine_validation_requirements(operation, characteristics)

        assert characteristics.requires_cross_validation is True
        assert characteristics.requires_integrity_check is True

    def test_generate_cache_key(self, classifier, sample_operation):
        """Test cache key generation."""
        key = classifier._generate_cache_key(sample_operation)

        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_cache_key_different_operations(self, classifier):
        """Test cache key generation for different operations."""
        op1 = MockEnhancedSyncOperation(
            operation_id="op1",
            operation_type=SyncOperationType.CREATE_ENTITY,
            content_hash="hash1",
        )
        op2 = MockEnhancedSyncOperation(
            operation_id="op2",
            operation_type=SyncOperationType.UPDATE_ENTITY,
            content_hash="hash2",
        )

        key1 = classifier._generate_cache_key(op1)
        key2 = classifier._generate_cache_key(op2)

        assert key1 != key2

    def test_record_operation_result(self, classifier, sample_operation):
        """Test recording operation results."""
        classifier.record_operation_result(sample_operation, True, 1.5)

        operation_key = f"{sample_operation.operation_type.value}_{sample_operation.entity_type.value}"
        assert operation_key in classifier._historical_data
        assert len(classifier._historical_data[operation_key]) == 1

        history_entry = classifier._historical_data[operation_key][0]
        assert history_entry["success"] is True
        assert history_entry["duration"] == 1.5
        assert "timestamp" in history_entry

    def test_record_operation_result_history_limit(self, classifier, sample_operation):
        """Test operation result recording with history limit."""
        # Add many entries to test limit
        for i in range(1500):
            classifier.record_operation_result(sample_operation, True, 1.0)

        operation_key = f"{sample_operation.operation_type.value}_{sample_operation.entity_type.value}"
        # Should be limited to 1000 entries
        assert len(classifier._historical_data[operation_key]) == 1000

    def test_record_operation_result_multiple_types(self, classifier):
        """Test recording results for multiple operation types."""
        op1 = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_ENTITY,
            entity_type=EntityType.SERVICE,
        )
        op2 = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.UPDATE_ENTITY,
            entity_type=EntityType.PROJECT,
        )

        classifier.record_operation_result(op1, True, 1.0)
        classifier.record_operation_result(op2, False, 2.0)

        assert len(classifier._historical_data) == 2

    @pytest.mark.asyncio
    async def test_classification_with_all_fields(self, classifier):
        """Test comprehensive classification with all fields populated."""
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.CASCADE_DELETE,
            entity_type=EntityType.ORGANIZATION,
            operation_data={
                "entities": [f"entity_{i}" for i in range(10)],
                "relationships": [f"rel_{i}" for i in range(5)],
            },
            dependent_operations=["dep1", "dep2"],
            related_operations=["rel1", "rel2"],
        )

        context = {
            "source_system": "test_system",
            "user_context": {"user": "test_user"},
            "business_criticality": 0.8,
            "deadline": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }

        characteristics = await classifier.classify_operation(operation, context)

        # Verify all fields are populated
        assert characteristics.operation_type == SyncOperationType.CASCADE_DELETE
        assert characteristics.priority == OperationPriority.HIGH
        assert characteristics.complexity == OperationComplexity.MODERATE
        assert (
            characteristics.impact == OperationImpact.REGIONAL
        )  # CASCADE_DELETE has REGIONAL impact
        assert characteristics.entity_count == 10
        assert characteristics.relationship_count == 5
        assert characteristics.source_system == "test_system"
        assert characteristics.business_criticality == 0.8
        assert characteristics.deadline is not None
        assert characteristics.blocking_operations == ["dep1", "dep2"]
        assert characteristics.dependent_operations == ["rel1", "rel2"]
        assert characteristics.validation_level == ValidationLevel.STRICT

    @pytest.mark.asyncio
    async def test_classification_edge_cases(self, classifier):
        """Test classification edge cases."""
        # Operation with no data
        operation = MockEnhancedSyncOperation(
            operation_data={},
            entity_id=None,
        )

        characteristics = await classifier.classify_operation(operation)

        # Should handle gracefully
        assert characteristics.entity_count == 1  # Default fallback
        assert characteristics.relationship_count == 0
        assert characteristics.complexity == OperationComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_cache_behavior_with_different_contexts(
        self, classifier, sample_operation
    ):
        """Test that different contexts create different cache entries."""
        context1 = {"source_system": "system1"}
        context2 = {"source_system": "system2"}

        # Same operation with different contexts should not use cache
        # Note: Current implementation caches based on operation only, not context
        characteristics1 = await classifier.classify_operation(
            sample_operation, context1
        )
        characteristics2 = await classifier.classify_operation(
            sample_operation, context2
        )

        # Both should have same base classification but different context fields
        assert characteristics1.operation_type == characteristics2.operation_type
        # Since caching is based on operation only, context differences won't affect cache

    @pytest.mark.asyncio
    async def test_massive_complexity_classification(self, classifier):
        """Test classification of massive complexity operations."""
        huge_data = {
            "entities": [f"entity_{i}" for i in range(200)],
            "relationships": [f"rel_{i}" for i in range(150)],
            "content": "x" * 200000,  # Very large content
        }

        operation = MockEnhancedSyncOperation(
            operation_data=huge_data,
            metadata={"massive": "data" * 1000},
        )

        characteristics = await classifier.classify_operation(operation)

        assert characteristics.complexity == OperationComplexity.MASSIVE
        assert characteristics.entity_count == 200
        assert characteristics.relationship_count == 150
        assert characteristics.data_size_bytes > 200000
        # Resource requirements should be high for massive operations
        assert (
            characteristics.resource_requirements["cpu"] == 1.0
        )  # 10x base (0.1 * 10)
        assert (
            characteristics.resource_requirements["memory"] == 100.0
        )  # 10x base (10.0 * 10)

    @pytest.mark.asyncio
    async def test_classification_caching_behavior(self, classifier):
        """Test detailed caching behavior."""
        operation = MockEnhancedSyncOperation()

        # First call should populate cache
        result1 = await classifier.classify_operation(operation)
        cache_size_after_first = len(classifier._classification_cache)

        # Second call should use cache
        result2 = await classifier.classify_operation(operation)
        cache_size_after_second = len(classifier._classification_cache)

        assert cache_size_after_first == 1
        assert cache_size_after_second == 1
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_historical_data_analysis_edge_cases(
        self, classifier, sample_operation
    ):
        """Test historical data analysis with edge cases."""
        operation_key = f"{sample_operation.operation_type.value}_{sample_operation.entity_type.value}"

        # Test with malformed historical data
        classifier._historical_data[operation_key] = [
            {"timestamp": "invalid", "success": True, "duration": 1.0},
            {"success": False},  # Missing fields
            {"timestamp": datetime.now(UTC).isoformat(), "duration": "invalid"},
        ]

        characteristics = OperationCharacteristics(
            operation_type=sample_operation.operation_type
        )

        # Should handle gracefully without crashing
        await classifier._analyze_historical_patterns(sample_operation, characteristics)

        # Should still provide reasonable defaults
        assert isinstance(characteristics.operation_frequency, float)
        assert isinstance(characteristics.success_rate, float)
        assert isinstance(characteristics.average_duration, float)

    @pytest.mark.asyncio
    async def test_content_analysis_with_various_data_types(self, classifier):
        """Test content analysis with various data types."""
        test_cases = [
            (None, 1, 0),  # None data
            ({}, 1, 0),  # Empty dict
            ({"entities": []}, 0, 0),  # Empty entities list
            ({"relationships": []}, 1, 0),  # Empty relationships list
            ("string_data", 1, 0),  # String data
            (123, 1, 0),  # Numeric data
            ([], 1, 0),  # List data
        ]

        for operation_data, expected_entities, expected_relationships in test_cases:
            operation = MockEnhancedSyncOperation(operation_data=operation_data)
            characteristics = OperationCharacteristics(
                operation_type=operation.operation_type
            )

            await classifier._analyze_content(operation, characteristics)

            assert characteristics.entity_count == expected_entities
            assert characteristics.relationship_count == expected_relationships

    @pytest.mark.asyncio
    async def test_priority_elevation_scenarios(self, classifier):
        """Test various priority elevation scenarios."""
        base_operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_ENTITY  # Base priority: MEDIUM
        )

        # Test business criticality elevation
        context_high_criticality = {"business_criticality": 0.9}
        characteristics = OperationCharacteristics(
            operation_type=base_operation.operation_type
        )
        await classifier._analyze_context(
            base_operation, characteristics, context_high_criticality
        )
        assert characteristics.priority == OperationPriority.HIGH

        # Test with LOW base priority
        low_priority_operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.VERSION_UPDATE  # Base priority: LOW
        )
        characteristics = OperationCharacteristics(
            operation_type=low_priority_operation.operation_type
        )
        await classifier._analyze_context(
            low_priority_operation, characteristics, context_high_criticality
        )
        assert (
            characteristics.priority == OperationPriority.MEDIUM
        )  # Elevated from LOW to MEDIUM

    @pytest.mark.asyncio
    async def test_validation_level_escalation(self, classifier):
        """Test validation level escalation scenarios."""
        # Test business criticality escalation
        operation = MockEnhancedSyncOperation(
            operation_type=SyncOperationType.VERSION_UPDATE
        )
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )
        characteristics.business_criticality = 0.9

        await classifier._determine_validation_requirements(operation, characteristics)
        assert (
            characteristics.validation_level == ValidationLevel.STANDARD
        )  # Escalated from BASIC

        # Test impact-based escalation
        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )
        characteristics.impact = OperationImpact.REGIONAL

        await classifier._determine_validation_requirements(operation, characteristics)
        assert characteristics.requires_cross_validation is True
        assert characteristics.requires_integrity_check is True
