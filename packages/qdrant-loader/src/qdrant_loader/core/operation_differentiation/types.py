"""Types and data structures for operation differentiation.

This module contains the core types, enums, and dataclasses used throughout
the operation differentiation system.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from qdrant_loader.core.sync.types import SyncOperationType


class OperationPriority(Enum):
    """Priority levels for synchronization operations."""

    CRITICAL = "critical"  # System-critical operations (data integrity, security)
    HIGH = "high"  # High-impact operations (user-facing, business-critical)
    MEDIUM = "medium"  # Standard operations (regular sync, updates)
    LOW = "low"  # Background operations (cleanup, optimization)
    DEFERRED = "deferred"  # Non-urgent operations (analytics, reporting)


class OperationComplexity(Enum):
    """Complexity levels for operations."""

    SIMPLE = "simple"  # Single entity, minimal relationships
    MODERATE = "moderate"  # Multiple entities, some relationships
    COMPLEX = "complex"  # Many entities, complex relationships
    MASSIVE = "massive"  # Bulk operations, extensive relationships


class OperationImpact(Enum):
    """Impact levels for operations."""

    MINIMAL = "minimal"  # Affects single record
    LOCAL = "local"  # Affects related records
    REGIONAL = "regional"  # Affects subsystem or domain
    GLOBAL = "global"  # Affects entire system


class ValidationLevel(Enum):
    """Validation levels for operations."""

    BASIC = "basic"  # Basic data type and format validation
    STANDARD = "standard"  # Standard business rule validation
    STRICT = "strict"  # Comprehensive validation with cross-checks
    PARANOID = "paranoid"  # Maximum validation with full integrity checks


@dataclass
class OperationCharacteristics:
    """Characteristics of a synchronization operation."""

    # Classification
    operation_type: SyncOperationType
    priority: OperationPriority = OperationPriority.MEDIUM
    complexity: OperationComplexity = OperationComplexity.MODERATE
    impact: OperationImpact = OperationImpact.LOCAL

    # Content analysis
    entity_count: int = 1
    relationship_count: int = 0
    data_size_bytes: int = 0
    content_hash: Optional[str] = None

    # Context metadata
    source_system: Optional[str] = None
    user_context: Optional[str] = None
    business_criticality: float = 0.5  # 0.0 to 1.0
    deadline: Optional[datetime] = None

    # Historical patterns
    operation_frequency: float = 0.0  # Operations per hour
    success_rate: float = 1.0  # Historical success rate
    average_duration: float = 0.0  # Average processing time in seconds

    # Dependencies
    blocking_operations: List[str] = field(default_factory=list)
    dependent_operations: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, float] = field(default_factory=dict)

    # Validation requirements
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    requires_cross_validation: bool = False
    requires_integrity_check: bool = False

    def calculate_priority_score(self) -> float:
        """Calculate numeric priority score for ordering."""
        base_scores = {
            OperationPriority.CRITICAL: 1000,
            OperationPriority.HIGH: 800,
            OperationPriority.MEDIUM: 500,
            OperationPriority.LOW: 200,
            OperationPriority.DEFERRED: 50,
        }

        score = base_scores[self.priority]

        # Adjust for business criticality
        score += self.business_criticality * 200

        # Adjust for deadline urgency
        if self.deadline:
            time_to_deadline = (self.deadline - datetime.now(UTC)).total_seconds()
            if time_to_deadline < 3600:  # Less than 1 hour
                score += 300
            elif time_to_deadline < 86400:  # Less than 1 day
                score += 100

        # Adjust for success rate (prefer reliable operations)
        score += self.success_rate * 50

        # Adjust for complexity (simpler operations get slight boost)
        complexity_adjustments = {
            OperationComplexity.SIMPLE: 20,
            OperationComplexity.MODERATE: 0,
            OperationComplexity.COMPLEX: -10,
            OperationComplexity.MASSIVE: -30,
        }
        score += complexity_adjustments[self.complexity]

        return score


@dataclass
class ValidationResult:
    """Result of operation validation."""

    is_valid: bool
    validation_level: ValidationLevel
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validation_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
