"""Advanced Merge Strategies for Conflict Resolution.

This module provides sophisticated merge strategies including field-level merging,
semantic conflict detection, and three-way merging with common ancestor detection.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ...utils.logging import LoggingConfig
from ..types import EntityType

logger = LoggingConfig.get_logger(__name__)


class MergeStrategy(Enum):
    """Available merge strategies."""

    FIELD_LEVEL = "field_level"  # Merge at field level
    SEMANTIC_AWARE = "semantic_aware"  # Consider semantic conflicts
    THREE_WAY = "three_way"  # Use common ancestor
    PRIORITY_BASED = "priority_based"  # Use field priorities
    TIMESTAMP_BASED = "timestamp_based"  # Use field timestamps
    CUSTOM_RULES = "custom_rules"  # Use custom merge rules


class ConflictType(Enum):
    """Types of merge conflicts."""

    VALUE_CONFLICT = "value_conflict"  # Different values for same field
    TYPE_CONFLICT = "type_conflict"  # Different data types
    STRUCTURE_CONFLICT = "structure_conflict"  # Different structure
    SEMANTIC_CONFLICT = "semantic_conflict"  # Semantic inconsistency
    TEMPORAL_CONFLICT = "temporal_conflict"  # Time-based conflict
    BUSINESS_RULE_CONFLICT = "business_rule_conflict"  # Business logic conflict


@dataclass
class MergeConflict:
    """Represents a conflict during merge operation."""

    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType = ConflictType.VALUE_CONFLICT
    field_path: str = ""  # Dot-notation path to conflicting field
    source_value: Any = None
    target_value: Any = None
    ancestor_value: Optional[Any] = None

    # Metadata
    source_timestamp: Optional[datetime] = None
    target_timestamp: Optional[datetime] = None
    field_priority: int = 0  # Higher number = higher priority
    semantic_context: Optional[Dict[str, Any]] = None
    business_rules: List[str] = field(default_factory=list)

    # Resolution
    suggested_resolution: Optional[Any] = None
    resolution_confidence: float = 0.0
    requires_manual_review: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/logging."""
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "field_path": self.field_path,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "ancestor_value": self.ancestor_value,
            "source_timestamp": (
                self.source_timestamp.isoformat() if self.source_timestamp else None
            ),
            "target_timestamp": (
                self.target_timestamp.isoformat() if self.target_timestamp else None
            ),
            "field_priority": self.field_priority,
            "semantic_context": self.semantic_context,
            "business_rules": self.business_rules,
            "suggested_resolution": self.suggested_resolution,
            "resolution_confidence": self.resolution_confidence,
            "requires_manual_review": self.requires_manual_review,
        }


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool = False
    merged_data: Optional[Dict[str, Any]] = None
    conflicts: List[MergeConflict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Statistics
    fields_merged: int = 0
    conflicts_resolved: int = 0
    conflicts_requiring_manual_review: int = 0
    merge_duration_seconds: float = 0.0

    # Metadata
    merge_strategy: Optional[MergeStrategy] = None
    merge_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    merge_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_conflict(self, conflict: MergeConflict) -> None:
        """Add a conflict to the merge result."""
        self.conflicts.append(conflict)
        if conflict.requires_manual_review:
            self.conflicts_requiring_manual_review += 1
        else:
            self.conflicts_resolved += 1

    def add_warning(self, warning: str) -> None:
        """Add a warning to the merge result."""
        self.warnings.append(f"{datetime.now(UTC).isoformat()}: {warning}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/logging."""
        return {
            "success": self.success,
            "merged_data": self.merged_data,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "warnings": self.warnings,
            "fields_merged": self.fields_merged,
            "conflicts_resolved": self.conflicts_resolved,
            "conflicts_requiring_manual_review": self.conflicts_requiring_manual_review,
            "merge_duration_seconds": self.merge_duration_seconds,
            "merge_strategy": (
                self.merge_strategy.value if self.merge_strategy else None
            ),
            "merge_timestamp": self.merge_timestamp.isoformat(),
            "merge_id": self.merge_id,
        }


class FieldLevelMerger:
    """Sophisticated field-level merging with conflict detection."""

    def __init__(self):
        """Initialize the field-level merger."""
        self._field_priorities: Dict[str, int] = {}
        self._semantic_rules: Dict[str, List[str]] = {}
        self._business_rules: Dict[str, List[str]] = {}

    async def merge_fields(
        self,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        ancestor_data: Optional[Dict[str, Any]] = None,
        field_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> MergeResult:
        """Perform field-level merge with conflict detection.

        Args:
            source_data: Source data to merge
            target_data: Target data to merge into
            ancestor_data: Optional common ancestor data
            field_metadata: Optional metadata for fields (timestamps, priorities, etc.)

        Returns:
            MergeResult with merged data and conflicts
        """
        start_time = datetime.now(UTC)
        result = MergeResult(merge_strategy=MergeStrategy.FIELD_LEVEL)

        try:
            # Initialize merged data with target as base
            merged_data = target_data.copy()

            # Get all field paths from both datasets
            source_paths = self._get_field_paths(source_data)
            target_paths = self._get_field_paths(target_data)
            all_paths = source_paths | target_paths

            # Process each field path
            for field_path in all_paths:
                await self._merge_field(
                    field_path,
                    source_data,
                    target_data,
                    ancestor_data,
                    field_metadata,
                    merged_data,
                    result,
                )

            result.success = True
            result.merged_data = merged_data
            result.fields_merged = len(all_paths)

        except Exception as e:
            logger.error(f"Error during field-level merge: {e}")
            result.success = False
            result.add_warning(f"Merge failed: {str(e)}")

        finally:
            result.merge_duration_seconds = (
                datetime.now(UTC) - start_time
            ).total_seconds()

        return result

    async def _merge_field(
        self,
        field_path: str,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        ancestor_data: Optional[Dict[str, Any]],
        field_metadata: Optional[Dict[str, Dict[str, Any]]],
        merged_data: Dict[str, Any],
        result: MergeResult,
    ) -> None:
        """Merge a specific field with conflict detection."""
        source_value = self._get_nested_value(source_data, field_path)
        target_value = self._get_nested_value(target_data, field_path)
        ancestor_value = (
            self._get_nested_value(ancestor_data, field_path) if ancestor_data else None
        )

        # Get field metadata
        metadata = field_metadata.get(field_path, {}) if field_metadata else {}
        source_timestamp = metadata.get("source_timestamp")
        target_timestamp = metadata.get("target_timestamp")
        field_priority = metadata.get("priority", 0)

        # Check for conflicts
        if source_value is not None and target_value is not None:
            if source_value != target_value:
                # We have a conflict
                conflict = MergeConflict(
                    field_path=field_path,
                    source_value=source_value,
                    target_value=target_value,
                    ancestor_value=ancestor_value,
                    source_timestamp=source_timestamp,
                    target_timestamp=target_timestamp,
                    field_priority=field_priority,
                )

                # Determine conflict type and resolution
                await self._resolve_field_conflict(conflict, merged_data, result)
            else:
                # No conflict, values are the same
                self._set_nested_value(merged_data, field_path, source_value)
        elif source_value is not None:
            # Only source has value
            self._set_nested_value(merged_data, field_path, source_value)
        elif target_value is not None:
            # Only target has value (already in merged_data)
            pass

    async def _resolve_field_conflict(
        self,
        conflict: MergeConflict,
        merged_data: Dict[str, Any],
        result: MergeResult,
    ) -> None:
        """Resolve a field-level conflict."""
        # Determine conflict type
        conflict.conflict_type = self._determine_conflict_type(conflict)

        # Apply resolution strategy based on conflict type
        if conflict.conflict_type == ConflictType.TYPE_CONFLICT:
            # Type conflicts require manual review
            conflict.requires_manual_review = True
            conflict.suggested_resolution = conflict.target_value  # Keep target
        elif conflict.conflict_type == ConflictType.TEMPORAL_CONFLICT:
            # Use timestamp-based resolution
            if conflict.source_timestamp and conflict.target_timestamp:
                if conflict.source_timestamp > conflict.target_timestamp:
                    conflict.suggested_resolution = conflict.source_value
                    conflict.resolution_confidence = 0.9
                else:
                    conflict.suggested_resolution = conflict.target_value
                    conflict.resolution_confidence = 0.9
            else:
                conflict.requires_manual_review = True
        elif conflict.field_priority > 0:
            # Use priority-based resolution
            conflict.suggested_resolution = conflict.source_value
            conflict.resolution_confidence = 0.8
        else:
            # Default to last-write-wins (source)
            conflict.suggested_resolution = conflict.source_value
            conflict.resolution_confidence = 0.6

        # Apply resolution if confident enough
        if not conflict.requires_manual_review and conflict.resolution_confidence > 0.7:
            self._set_nested_value(
                merged_data, conflict.field_path, conflict.suggested_resolution
            )

        result.add_conflict(conflict)

    def _determine_conflict_type(self, conflict: MergeConflict) -> ConflictType:
        """Determine the type of conflict."""
        if type(conflict.source_value) != type(conflict.target_value):
            return ConflictType.TYPE_CONFLICT
        elif conflict.source_timestamp and conflict.target_timestamp:
            return ConflictType.TEMPORAL_CONFLICT
        else:
            return ConflictType.VALUE_CONFLICT

    def _get_field_paths(self, data: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Get all field paths in a nested dictionary."""
        paths = set()

        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.add(current_path)

            if isinstance(value, dict):
                paths.update(self._get_field_paths(value, current_path))

        return paths

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        if not data:
            return None

        keys = path.split(".")
        current = data

        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except (KeyError, TypeError):
            return None

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation."""
        keys = path.split(".")
        current = data

        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value


class SemanticConflictDetector:
    """Detects semantic conflicts in merged data."""

    def __init__(self):
        """Initialize the semantic conflict detector."""
        self._semantic_rules: Dict[str, List[str]] = {
            # Example semantic rules
            "status": ["active", "inactive", "pending", "archived"],
            "priority": ["low", "medium", "high", "critical"],
            "type": ["document", "entity", "relationship", "concept"],
        }
        self._incompatible_combinations: List[Tuple[str, str, str, str]] = [
            # (field1, value1, field2, value2) - incompatible combinations
            ("status", "archived", "priority", "critical"),
            ("status", "inactive", "last_accessed", "recent"),
        ]

    async def detect_semantic_conflicts(
        self, merged_data: Dict[str, Any]
    ) -> List[MergeConflict]:
        """Detect semantic conflicts in merged data.

        Args:
            merged_data: The merged data to check

        Returns:
            List of semantic conflicts found
        """
        conflicts = []

        # Check for incompatible field combinations
        for field1, value1, field2, value2 in self._incompatible_combinations:
            if (
                self._get_nested_value(merged_data, field1) == value1
                and self._get_nested_value(merged_data, field2) == value2
            ):
                conflict = MergeConflict(
                    conflict_type=ConflictType.SEMANTIC_CONFLICT,
                    field_path=f"{field1}+{field2}",
                    source_value=f"{field1}={value1}",
                    target_value=f"{field2}={value2}",
                    requires_manual_review=True,
                )
                conflicts.append(conflict)

        # Check for invalid enum values
        for field, valid_values in self._semantic_rules.items():
            current_value = self._get_nested_value(merged_data, field)
            if current_value and current_value not in valid_values:
                conflict = MergeConflict(
                    conflict_type=ConflictType.SEMANTIC_CONFLICT,
                    field_path=field,
                    source_value=current_value,
                    target_value=valid_values[0],  # Suggest first valid value
                    requires_manual_review=True,
                )
                conflicts.append(conflict)

        return conflicts

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        if not data:
            return None

        keys = path.split(".")
        current = data

        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except (KeyError, TypeError):
            return None


class ThreeWayMerger:
    """Three-way merge with common ancestor detection."""

    def __init__(self, field_merger: FieldLevelMerger):
        """Initialize the three-way merger.

        Args:
            field_merger: Field-level merger instance
        """
        self.field_merger = field_merger

    async def three_way_merge(
        self,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        ancestor_data: Dict[str, Any],
        field_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> MergeResult:
        """Perform three-way merge using common ancestor.

        Args:
            source_data: Source data
            target_data: Target data
            ancestor_data: Common ancestor data
            field_metadata: Optional field metadata

        Returns:
            MergeResult with three-way merge results
        """
        start_time = datetime.now(UTC)
        result = MergeResult(merge_strategy=MergeStrategy.THREE_WAY)

        try:
            # Analyze changes from ancestor
            source_changes = self._analyze_changes(ancestor_data, source_data)
            target_changes = self._analyze_changes(ancestor_data, target_data)

            # Find conflicting changes
            conflicting_fields = set(source_changes.keys()) & set(target_changes.keys())

            # Start with ancestor as base
            merged_data = ancestor_data.copy()

            # Apply non-conflicting changes
            for field_path, value in source_changes.items():
                if field_path not in conflicting_fields:
                    self._set_nested_value(merged_data, field_path, value)
                    result.fields_merged += 1

            for field_path, value in target_changes.items():
                if field_path not in conflicting_fields:
                    self._set_nested_value(merged_data, field_path, value)
                    result.fields_merged += 1

            # Handle conflicting changes
            for field_path in conflicting_fields:
                conflict = MergeConflict(
                    conflict_type=ConflictType.VALUE_CONFLICT,
                    field_path=field_path,
                    source_value=source_changes[field_path],
                    target_value=target_changes[field_path],
                    ancestor_value=self._get_nested_value(ancestor_data, field_path),
                )

                # Three-way conflict resolution
                await self._resolve_three_way_conflict(conflict, merged_data, result)

            result.success = True
            result.merged_data = merged_data

        except Exception as e:
            logger.error(f"Error during three-way merge: {e}")
            result.success = False
            result.add_warning(f"Three-way merge failed: {str(e)}")

        finally:
            result.merge_duration_seconds = (
                datetime.now(UTC) - start_time
            ).total_seconds()

        return result

    def _analyze_changes(
        self, ancestor: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze changes between ancestor and current version."""
        changes = {}

        # Get all field paths
        ancestor_paths = self._get_field_paths(ancestor)
        current_paths = self._get_field_paths(current)
        all_paths = ancestor_paths | current_paths

        for field_path in all_paths:
            ancestor_value = self._get_nested_value(ancestor, field_path)
            current_value = self._get_nested_value(current, field_path)

            if ancestor_value != current_value:
                changes[field_path] = current_value

        return changes

    async def _resolve_three_way_conflict(
        self,
        conflict: MergeConflict,
        merged_data: Dict[str, Any],
        result: MergeResult,
    ) -> None:
        """Resolve a three-way merge conflict."""
        # If both sides made the same change, no conflict
        if conflict.source_value == conflict.target_value:
            self._set_nested_value(
                merged_data, conflict.field_path, conflict.source_value
            )
            return

        # If one side didn't change from ancestor, use the other
        if conflict.source_value == conflict.ancestor_value:
            conflict.suggested_resolution = conflict.target_value
            conflict.resolution_confidence = 0.9
        elif conflict.target_value == conflict.ancestor_value:
            conflict.suggested_resolution = conflict.source_value
            conflict.resolution_confidence = 0.9
        else:
            # Both sides changed differently - requires manual review
            conflict.requires_manual_review = True
            conflict.suggested_resolution = conflict.source_value  # Default to source
            conflict.resolution_confidence = 0.3

        # Apply resolution if confident
        if not conflict.requires_manual_review and conflict.resolution_confidence > 0.7:
            self._set_nested_value(
                merged_data, conflict.field_path, conflict.suggested_resolution
            )

        result.add_conflict(conflict)

    def _get_field_paths(self, data: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Get all field paths in a nested dictionary."""
        paths = set()

        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.add(current_path)

            if isinstance(value, dict):
                paths.update(self._get_field_paths(value, current_path))

        return paths

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        if not data:
            return None

        keys = path.split(".")
        current = data

        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except (KeyError, TypeError):
            return None

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation."""
        keys = path.split(".")
        current = data

        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value


class AdvancedMergeStrategy:
    """Main class coordinating all advanced merge strategies."""

    def __init__(self):
        """Initialize the advanced merge strategy system."""
        self.field_merger = FieldLevelMerger()
        self.semantic_detector = SemanticConflictDetector()
        self.three_way_merger = ThreeWayMerger(self.field_merger)

    async def merge_data(
        self,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        strategy: MergeStrategy = MergeStrategy.FIELD_LEVEL,
        ancestor_data: Optional[Dict[str, Any]] = None,
        field_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> MergeResult:
        """Perform advanced merge using specified strategy.

        Args:
            source_data: Source data to merge
            target_data: Target data to merge into
            strategy: Merge strategy to use
            ancestor_data: Optional common ancestor data
            field_metadata: Optional field metadata

        Returns:
            MergeResult with merge results and conflicts
        """
        logger.info(f"Starting advanced merge with strategy: {strategy.value}")

        if strategy == MergeStrategy.THREE_WAY and ancestor_data:
            result = await self.three_way_merger.three_way_merge(
                source_data, target_data, ancestor_data, field_metadata
            )
        else:
            result = await self.field_merger.merge_fields(
                source_data, target_data, ancestor_data, field_metadata
            )

        # Always check for semantic conflicts
        if result.success and result.merged_data:
            semantic_conflicts = await self.semantic_detector.detect_semantic_conflicts(
                result.merged_data
            )
            for conflict in semantic_conflicts:
                result.add_conflict(conflict)

        logger.info(
            f"Merge completed: {result.fields_merged} fields merged, "
            f"{len(result.conflicts)} conflicts detected"
        )

        return result
