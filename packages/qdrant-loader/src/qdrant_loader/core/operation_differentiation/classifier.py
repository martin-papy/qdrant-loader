"""Operation classifier for intelligent operation analysis.

This module provides the OperationClassifier class that analyzes synchronization
operations to determine their characteristics, complexity, and requirements.
"""

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ...utils.logging import LoggingConfig
from qdrant_loader.core.sync.types import SyncOperationType
from ..types import EntityType
from .types import (
    OperationCharacteristics,
    OperationComplexity,
    OperationImpact,
    OperationPriority,
    ValidationLevel,
)

if TYPE_CHECKING:
    from ..sync import EnhancedSyncOperation

logger = LoggingConfig.get_logger(__name__)


class OperationClassifier:
    """Intelligent operation classifier for synchronization operations."""

    def __init__(self):
        """Initialize the operation classifier."""
        self._classification_cache: Dict[str, OperationCharacteristics] = {}
        self._historical_data: Dict[str, List[Dict[str, Any]]] = {}

    async def classify_operation(
        self,
        operation: "EnhancedSyncOperation",
        context: Optional[Dict[str, Any]] = None,
    ) -> OperationCharacteristics:
        """Classify an operation and determine its characteristics.

        Args:
            operation: The operation to classify
            context: Additional context for classification

        Returns:
            OperationCharacteristics with detailed classification
        """
        # Check cache first
        cache_key = self._generate_cache_key(operation)
        if cache_key in self._classification_cache:
            return self._classification_cache[cache_key]

        characteristics = OperationCharacteristics(
            operation_type=operation.operation_type
        )

        # Analyze content
        await self._analyze_content(operation, characteristics)

        # Analyze context
        await self._analyze_context(operation, characteristics, context)

        # Analyze historical patterns
        await self._analyze_historical_patterns(operation, characteristics)

        # Analyze dependencies
        await self._analyze_dependencies(operation, characteristics)

        # Determine validation requirements
        await self._determine_validation_requirements(operation, characteristics)

        # Cache the result
        self._classification_cache[cache_key] = characteristics

        logger.debug(
            f"Classified operation {operation.operation_id} as "
            f"{characteristics.priority.value} priority, "
            f"{characteristics.complexity.value} complexity"
        )

        return characteristics

    async def _analyze_content(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
    ) -> None:
        """Analyze operation content to determine characteristics."""
        # Calculate content size
        data_size = 0
        if operation.operation_data:
            data_size += len(str(operation.operation_data))
        if operation.previous_data:
            data_size += len(str(operation.previous_data))
        if operation.metadata:
            data_size += len(str(operation.metadata))

        characteristics.data_size_bytes = data_size

        # Generate content hash
        content_str = f"{operation.operation_data}{operation.metadata}"
        characteristics.content_hash = hashlib.sha256(content_str.encode()).hexdigest()[
            :16
        ]

        # Estimate entity and relationship counts
        if operation.operation_data:
            # Simple heuristic based on data structure
            if isinstance(operation.operation_data, dict):
                characteristics.entity_count = len(
                    operation.operation_data.get(
                        "entities", [operation.entity_id] if operation.entity_id else []
                    )
                )
                characteristics.relationship_count = len(
                    operation.operation_data.get("relationships", [])
                )
            else:
                characteristics.entity_count = 1

        # Determine complexity based on content
        if data_size < 1024 and characteristics.entity_count <= 1:
            characteristics.complexity = OperationComplexity.SIMPLE
        elif data_size < 10240 and characteristics.entity_count <= 10:
            characteristics.complexity = OperationComplexity.MODERATE
        elif data_size < 102400 and characteristics.entity_count <= 100:
            characteristics.complexity = OperationComplexity.COMPLEX
        else:
            characteristics.complexity = OperationComplexity.MASSIVE

    async def _analyze_context(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Analyze operation context to determine characteristics."""
        # Extract context information
        if context:
            characteristics.source_system = context.get("source_system")
            characteristics.user_context = context.get("user_context")
            characteristics.business_criticality = context.get(
                "business_criticality", 0.5
            )

            if context.get("deadline"):
                characteristics.deadline = datetime.fromisoformat(context["deadline"])

        # Determine priority based on operation type and context
        if operation.operation_type in [SyncOperationType.CASCADE_DELETE]:
            characteristics.priority = OperationPriority.HIGH
        elif operation.operation_type in [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.CREATE_ENTITY,
        ]:
            characteristics.priority = OperationPriority.MEDIUM
        elif operation.operation_type in [SyncOperationType.VERSION_UPDATE]:
            characteristics.priority = OperationPriority.LOW

        # Adjust priority based on business criticality
        if characteristics.business_criticality > 0.8:
            if characteristics.priority == OperationPriority.MEDIUM:
                characteristics.priority = OperationPriority.HIGH
            elif characteristics.priority == OperationPriority.LOW:
                characteristics.priority = OperationPriority.MEDIUM

        # Determine impact based on operation type and entity type
        if operation.operation_type in [SyncOperationType.CASCADE_DELETE]:
            characteristics.impact = OperationImpact.REGIONAL
        elif operation.entity_type in [EntityType.SERVICE, EntityType.DATABASE]:
            characteristics.impact = OperationImpact.REGIONAL
        elif operation.entity_type in [EntityType.ORGANIZATION, EntityType.PROJECT]:
            characteristics.impact = OperationImpact.LOCAL
        else:
            characteristics.impact = OperationImpact.MINIMAL

    async def _analyze_historical_patterns(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
    ) -> None:
        """Analyze historical patterns for the operation type."""
        operation_key = (
            f"{operation.operation_type.value}_{operation.entity_type.value}"
        )

        if operation_key in self._historical_data:
            history = self._historical_data[operation_key]

            # Calculate frequency (operations per hour)
            if len(history) > 1:
                time_span = (
                    datetime.now(UTC) - datetime.fromisoformat(history[0]["timestamp"])
                ).total_seconds() / 3600
                characteristics.operation_frequency = len(history) / max(time_span, 1.0)

            # Calculate success rate
            successful = sum(1 for h in history if h.get("success", True))
            characteristics.success_rate = successful / len(history)

            # Calculate average duration
            durations = [h.get("duration", 0) for h in history if h.get("duration")]
            if durations:
                characteristics.average_duration = sum(durations) / len(durations)

    async def _analyze_dependencies(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
    ) -> None:
        """Analyze operation dependencies."""
        characteristics.blocking_operations = operation.dependent_operations.copy()
        characteristics.dependent_operations = operation.related_operations.copy()

        # Estimate resource requirements based on complexity
        base_cpu = 0.1
        base_memory = 10.0  # MB

        complexity_multipliers = {
            OperationComplexity.SIMPLE: 1.0,
            OperationComplexity.MODERATE: 2.0,
            OperationComplexity.COMPLEX: 5.0,
            OperationComplexity.MASSIVE: 10.0,
        }

        multiplier = complexity_multipliers[characteristics.complexity]
        characteristics.resource_requirements = {
            "cpu": base_cpu * multiplier,
            "memory": base_memory * multiplier,
            "network": characteristics.data_size_bytes / 1024.0,  # KB
        }

    async def _determine_validation_requirements(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
    ) -> None:
        """Determine validation requirements for the operation."""
        # Base validation level on operation type
        if operation.operation_type in [SyncOperationType.CASCADE_DELETE]:
            characteristics.validation_level = ValidationLevel.STRICT
            characteristics.requires_cross_validation = True
            characteristics.requires_integrity_check = True
        elif operation.operation_type in [
            SyncOperationType.DELETE_DOCUMENT,
            SyncOperationType.DELETE_ENTITY,
        ]:
            characteristics.validation_level = ValidationLevel.STANDARD
            characteristics.requires_integrity_check = True
        elif operation.operation_type in [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.CREATE_ENTITY,
        ]:
            characteristics.validation_level = ValidationLevel.STANDARD
        else:
            characteristics.validation_level = ValidationLevel.BASIC

        # Adjust based on business criticality
        if characteristics.business_criticality > 0.8:
            if characteristics.validation_level == ValidationLevel.BASIC:
                characteristics.validation_level = ValidationLevel.STANDARD
            elif characteristics.validation_level == ValidationLevel.STANDARD:
                characteristics.validation_level = ValidationLevel.STRICT

        # Adjust based on impact
        if characteristics.impact in [OperationImpact.REGIONAL, OperationImpact.GLOBAL]:
            characteristics.requires_cross_validation = True
            characteristics.requires_integrity_check = True

    def _generate_cache_key(self, operation: "EnhancedSyncOperation") -> str:
        """Generate cache key for operation classification."""
        key_components = [
            operation.operation_type.value,
            operation.entity_type.value,
            str(operation.document_version),
            operation.content_hash or "",
        ]
        return hashlib.md5("|".join(key_components).encode()).hexdigest()

    def record_operation_result(
        self, operation: "EnhancedSyncOperation", success: bool, duration: float
    ) -> None:
        """Record operation result for historical analysis."""
        operation_key = (
            f"{operation.operation_type.value}_{operation.entity_type.value}"
        )

        if operation_key not in self._historical_data:
            self._historical_data[operation_key] = []

        self._historical_data[operation_key].append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "success": success,
                "duration": duration,
                "operation_id": operation.operation_id,
            }
        )

        # Keep only recent history (last 1000 operations)
        if len(self._historical_data[operation_key]) > 1000:
            self._historical_data[operation_key] = self._historical_data[operation_key][
                -1000:
            ]
