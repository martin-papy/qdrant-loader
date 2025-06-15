"""Operation validator for comprehensive validation framework.

This module provides the OperationValidator class that performs multi-level
validation of synchronization operations based on their characteristics.
"""

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from ...utils.logging import LoggingConfig
from ..sync.types import SyncOperationType
from ..types import EntityType
from .types import OperationCharacteristics, ValidationLevel, ValidationResult

if TYPE_CHECKING:
    from ..sync import EnhancedSyncOperation

logger = LoggingConfig.get_logger(__name__)


class OperationValidator:
    """Comprehensive operation validator."""

    def __init__(self):
        """Initialize the operation validator."""
        self._validation_cache: Dict[str, ValidationResult] = {}
        self._validation_rules: Dict[ValidationLevel, List[Callable]] = {
            ValidationLevel.BASIC: [
                self._validate_basic_data_types,
                self._validate_required_fields,
            ],
            ValidationLevel.STANDARD: [
                self._validate_basic_data_types,
                self._validate_required_fields,
                self._validate_business_rules,
                self._validate_data_consistency,
            ],
            ValidationLevel.STRICT: [
                self._validate_basic_data_types,
                self._validate_required_fields,
                self._validate_business_rules,
                self._validate_data_consistency,
                self._validate_referential_integrity,
                self._validate_permissions,
            ],
            ValidationLevel.PARANOID: [
                self._validate_basic_data_types,
                self._validate_required_fields,
                self._validate_business_rules,
                self._validate_data_consistency,
                self._validate_referential_integrity,
                self._validate_permissions,
                self._validate_security_constraints,
                self._validate_performance_impact,
            ],
        }

    async def validate_operation(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate an operation based on its characteristics.

        Args:
            operation: The operation to validate
            characteristics: Operation characteristics
            context: Additional validation context

        Returns:
            ValidationResult with validation outcome
        """
        start_time = datetime.now(UTC)

        # Check cache first
        cache_key = self._generate_validation_cache_key(operation, characteristics)
        if cache_key in self._validation_cache:
            cached_result = self._validation_cache[cache_key]
            logger.debug(
                f"Using cached validation result for operation {operation.operation_id}"
            )
            return cached_result

        result = ValidationResult(
            is_valid=True, validation_level=characteristics.validation_level
        )

        # Run validation rules for the specified level
        validation_rules = self._validation_rules[characteristics.validation_level]

        for rule in validation_rules:
            try:
                rule_result = await rule(operation, characteristics, context)

                if not rule_result.get("valid", True):
                    result.is_valid = False
                    result.errors.extend(rule_result.get("errors", []))

                result.warnings.extend(rule_result.get("warnings", []))
                result.recommendations.extend(rule_result.get("recommendations", []))

            except Exception as e:
                logger.error(f"Validation rule {rule.__name__} failed: {e}")
                result.is_valid = False
                result.errors.append(
                    f"Validation rule {rule.__name__} failed: {str(e)}"
                )

        # Cross-database validation if required
        if characteristics.requires_cross_validation:
            cross_validation_result = await self._validate_cross_database_consistency(
                operation, characteristics, context
            )

            if not cross_validation_result.get("valid", True):
                result.is_valid = False
                result.errors.extend(cross_validation_result.get("errors", []))

            result.warnings.extend(cross_validation_result.get("warnings", []))

        # Integrity check if required
        if characteristics.requires_integrity_check:
            integrity_result = await self._validate_data_integrity(
                operation, characteristics, context
            )

            if not integrity_result.get("valid", True):
                result.is_valid = False
                result.errors.extend(integrity_result.get("errors", []))

            result.warnings.extend(integrity_result.get("warnings", []))

        # Calculate validation time
        result.validation_time = (datetime.now(UTC) - start_time).total_seconds()

        # Cache the result
        self._validation_cache[cache_key] = result

        logger.debug(
            f"Validated operation {operation.operation_id}: "
            f"{'VALID' if result.is_valid else 'INVALID'} "
            f"({len(result.errors)} errors, {len(result.warnings)} warnings)"
        )

        return result

    async def _validate_basic_data_types(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate basic data types and formats."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Validate operation ID
        if not operation.operation_id or not isinstance(operation.operation_id, str):
            result["valid"] = False
            result["errors"].append("Invalid operation ID")

        # Validate entity ID if present
        if operation.entity_id and not isinstance(operation.entity_id, str):
            result["valid"] = False
            result["errors"].append("Invalid entity ID format")

        # Validate timestamps
        if not isinstance(operation.timestamp, datetime):
            result["valid"] = False
            result["errors"].append("Invalid timestamp format")

        # Validate operation data structure
        if operation.operation_data and not isinstance(operation.operation_data, dict):
            result["warnings"].append("Operation data is not a dictionary")

        return result

    async def _validate_required_fields(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate required fields based on operation type."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Check required fields based on operation type
        if operation.operation_type in [
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.DELETE_DOCUMENT,
            SyncOperationType.UPDATE_ENTITY,
            SyncOperationType.DELETE_ENTITY,
        ]:
            if not operation.entity_id:
                result["valid"] = False
                result["errors"].append(
                    f"Entity ID required for {operation.operation_type.value}"
                )

        if operation.operation_type in [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.CREATE_ENTITY,
            SyncOperationType.UPDATE_ENTITY,
        ]:
            if not operation.operation_data:
                result["valid"] = False
                result["errors"].append(
                    f"Operation data required for {operation.operation_type.value}"
                )

        return result

    async def _validate_business_rules(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate business rules and constraints."""
        result = {"valid": True, "errors": [], "warnings": [], "recommendations": []}

        # Validate version consistency
        if operation.document_version < 1:
            result["valid"] = False
            result["errors"].append("Document version must be positive")

        # Validate retry limits
        if operation.retry_count > operation.max_retries:
            result["valid"] = False
            result["errors"].append("Operation has exceeded maximum retry count")

        # Validate operation data size
        if characteristics.data_size_bytes > 10 * 1024 * 1024:  # 10MB
            result["warnings"].append("Operation data size is very large")
            result["recommendations"].append("Consider breaking down large operations")

        # Validate entity type consistency
        if (
            operation.entity_type == EntityType.CONCEPT
            and characteristics.complexity.value == "massive"
        ):
            result["warnings"].append(
                "Massive operation on concept entity may be inefficient"
            )

        return result

    async def _validate_data_consistency(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate data consistency within the operation."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Validate version progression
        if (
            operation.previous_version
            and operation.document_version <= operation.previous_version
        ):
            result["valid"] = False
            result["errors"].append(
                "Document version must be greater than previous version"
            )

        # Validate content hash consistency
        if operation.content_hash and characteristics.content_hash:
            if operation.content_hash != characteristics.content_hash:
                result["warnings"].append("Content hash mismatch detected")

        return result

    async def _validate_referential_integrity(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate referential integrity constraints."""
        result = {"valid": True, "errors": [], "warnings": []}

        # This would typically involve database queries to check references
        # For now, we'll do basic validation

        # Validate related operations exist
        for related_op_id in operation.related_operations:
            if not related_op_id or not isinstance(related_op_id, str):
                result["warnings"].append(
                    f"Invalid related operation ID: {related_op_id}"
                )

        return result

    async def _validate_permissions(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate operation permissions and authorization."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Basic permission validation
        if context and context.get("user_context"):
            user_context = context["user_context"]

            # Check for delete permissions on critical operations
            if operation.operation_type in [SyncOperationType.CASCADE_DELETE]:
                if not user_context.get("can_cascade_delete", False):
                    result["valid"] = False
                    result["errors"].append(
                        "Insufficient permissions for cascade delete"
                    )

        return result

    async def _validate_security_constraints(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate security constraints and policies."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Check for sensitive data patterns
        if operation.operation_data:
            data_str = str(operation.operation_data).lower()
            sensitive_patterns = ["password", "secret", "token", "key", "credential"]

            for pattern in sensitive_patterns:
                if pattern in data_str:
                    result["warnings"].append(
                        f"Potential sensitive data detected: {pattern}"
                    )

        return result

    async def _validate_performance_impact(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate performance impact and resource usage."""
        result = {"valid": True, "errors": [], "warnings": [], "recommendations": []}

        # Check resource requirements
        cpu_req = characteristics.resource_requirements.get("cpu", 0)
        memory_req = characteristics.resource_requirements.get("memory", 0)

        if cpu_req > 2.0:  # High CPU usage
            result["warnings"].append("Operation requires high CPU resources")
            result["recommendations"].append(
                "Consider scheduling during low-traffic periods"
            )

        if memory_req > 1024:  # High memory usage (>1GB)
            result["warnings"].append("Operation requires high memory resources")
            result["recommendations"].append("Monitor memory usage during execution")

        # Check estimated duration
        if characteristics.average_duration > 300:  # >5 minutes
            result["warnings"].append("Operation has long average duration")
            result["recommendations"].append(
                "Consider breaking into smaller operations"
            )

        return result

    async def _validate_cross_database_consistency(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate consistency across QDrant and Neo4j databases."""
        result = {"valid": True, "errors": [], "warnings": []}

        # This would involve actual database queries in a real implementation
        # For now, we'll do basic validation

        if operation.operation_type in [
            SyncOperationType.DELETE_DOCUMENT,
            SyncOperationType.CASCADE_DELETE,
        ]:
            # Check if entity exists in both databases before deletion
            if not operation.entity_id:
                result["valid"] = False
                result["errors"].append(
                    "Cannot validate cross-database consistency without entity ID"
                )

        return result

    async def _validate_data_integrity(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate data integrity constraints."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Validate data structure integrity
        if operation.operation_data:
            # Check for required nested fields based on entity type
            if operation.entity_type == EntityType.SERVICE:
                if "name" not in operation.operation_data:
                    result["errors"].append("Service entity must have a name")
                    result["valid"] = False

        return result

    def _generate_validation_cache_key(
        self,
        operation: "EnhancedSyncOperation",
        characteristics: OperationCharacteristics,
    ) -> str:
        """Generate cache key for validation results."""
        key_components = [
            operation.operation_type.value,
            operation.entity_type.value,
            str(operation.document_version),
            characteristics.validation_level.value,
            operation.content_hash or "",
        ]
        return hashlib.md5("|".join(key_components).encode()).hexdigest()
