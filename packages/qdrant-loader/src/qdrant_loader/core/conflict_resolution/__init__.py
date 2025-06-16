"""Advanced Conflict Resolution Package.

This package provides sophisticated conflict resolution mechanisms including
advanced merge strategies, semantic conflict detection, machine learning-based
resolution suggestions, and workflow management for manual resolution.
"""

# Core models and configuration
# Core system components
from .detector import ConflictDetector

# Advanced merge strategies (Phase 1 - Implemented)
from .merge_strategies import (
    AdvancedMergeStrategy,
    FieldLevelMerger,
    MergeConflict,
    MergeResult,
    MergeStrategy,
    SemanticConflictDetector,
    ThreeWayMerger,
)
from .merge_strategies import (
    ConflictType as MergeConflictType,
)
from .models import (
    ConflictRecord,
    ConflictResolutionConfig,
    ConflictResolutionStrategy,
    ConflictStatus,
    ConflictType,
    EntityVersion,
)
from .persistence import ConflictPersistence, SyncProvider, VersionProvider
from .resolvers import ConflictResolver
from .statistics import ConflictStatistics
from .system import ConflictResolutionSystem

# TODO: Import these modules when they are implemented in future phases
# from .detection_algorithms import (
#     SchemaConflictDetector,
#     CascadingConflictDetector,
#     TemporalConflictDetector,
# )
# from .intelligent_resolution import (
#     MLBasedResolver,
#     ConfidenceScorer,
#     PatternRecognizer,
# )
# from .workflow_management import (
#     ApprovalWorkflow,
#     EscalationManager,
#     CollaborativeResolver,
# )

__all__ = [
    # Core models and enums
    "ConflictType",
    "ConflictResolutionStrategy",
    "ConflictStatus",
    "EntityVersion",
    "ConflictRecord",
    "ConflictResolutionConfig",
    # Advanced merge strategies (Phase 1)
    "AdvancedMergeStrategy",
    "FieldLevelMerger",
    "SemanticConflictDetector",
    "ThreeWayMerger",
    "MergeResult",
    "MergeConflict",
    "MergeStrategy",
    "MergeConflictType",
    # Core system components
    "ConflictDetector",
    "ConflictResolver",
    "ConflictPersistence",
    "VersionProvider",
    "SyncProvider",
    "ConflictStatistics",
    "ConflictResolutionSystem",
]
