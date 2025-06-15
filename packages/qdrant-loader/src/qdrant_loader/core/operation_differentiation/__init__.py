"""Operation Differentiation Package.

This package provides intelligent operation classification, priority management,
validation frameworks, and specialized handling strategies for synchronization
operations across QDrant and Neo4j databases.
"""

from .types import (
    OperationComplexity,
    OperationImpact,
    OperationPriority,
    ValidationLevel,
    OperationCharacteristics,
    ValidationResult,
)
from .classifier import OperationClassifier
from .priority_manager import OperationPriorityManager
from .validator import OperationValidator
from .manager import OperationDifferentiationManager

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
