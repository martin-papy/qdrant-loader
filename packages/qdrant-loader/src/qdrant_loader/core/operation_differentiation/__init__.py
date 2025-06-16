"""Operation Differentiation Package.

This package provides intelligent operation classification, priority management,
validation frameworks, and specialized handling strategies for synchronization
operations across QDrant and Neo4j databases.
"""

from .classifier import OperationClassifier
from .manager import OperationDifferentiationManager
from .priority_manager import OperationPriorityManager
from .types import (
    OperationCharacteristics,
    OperationComplexity,
    OperationImpact,
    OperationPriority,
    ValidationLevel,
    ValidationResult,
)
from .validator import OperationValidator

__all__ = [
    # Types and enums
    "OperationComplexity",
    "OperationImpact",
    "OperationPriority",
    "ValidationLevel",
    "OperationCharacteristics",
    "ValidationResult",
    # Core components
    "OperationClassifier",
    "OperationPriorityManager",
    "OperationValidator",
    "OperationDifferentiationManager",
]
