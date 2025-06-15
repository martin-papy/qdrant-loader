"""Data models for conflict resolution system.

This module contains all the data models, enums, and dataclasses used
throughout the conflict resolution system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Optional

from ..sync import DatabaseType
from ..managers import IDMapping


class ConflictType(Enum):
    """Types of conflicts that can occur during synchronization."""

    VERSION_CONFLICT = "version_conflict"  # Different versions of same entity
    CONCURRENT_UPDATE = "concurrent_update"  # Simultaneous updates
    DATA_MISMATCH = "data_mismatch"  # Data inconsistency between databases
    MISSING_ENTITY = "missing_entity"  # Entity exists in one DB but not the other
    ORPHANED_MAPPING = "orphaned_mapping"  # Mapping exists but entity is missing
    SCHEMA_CONFLICT = "schema_conflict"  # Schema differences between databases


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""

    LAST_WRITE_WINS = "last_write_wins"  # Use the most recent update
    FIRST_WRITE_WINS = "first_write_wins"  # Use the earliest update
    MANUAL_INTERVENTION = "manual_intervention"  # Queue for manual review
    MERGE_STRATEGY = "merge_strategy"  # Attempt to merge changes
    SOURCE_PRIORITY = "source_priority"  # Prioritize specific database
    CUSTOM_RULES = "custom_rules"  # Use custom resolution rules


class ConflictStatus(Enum):
    """Status of conflict resolution."""

    DETECTED = "detected"  # Conflict has been detected
    PENDING = "pending"  # Awaiting resolution
    RESOLVING = "resolving"  # Currently being resolved
    RESOLVED = "resolved"  # Successfully resolved
    FAILED = "failed"  # Resolution failed
    MANUAL_REVIEW = "manual_review"  # Requires manual intervention


@dataclass
class EntityVersion:
    """Version information for an entity."""

    entity_id: str
    database_type: DatabaseType
    version_number: int = 1
    last_modified: datetime = field(default_factory=lambda: datetime.now(UTC))
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def increment_version(self) -> None:
        """Increment the version number and update timestamp."""
        self.version_number += 1
        self.last_modified = datetime.now(UTC)

    def is_newer_than(self, other: "EntityVersion") -> bool:
        """Check if this version is newer than another version."""
        if self.version_number != other.version_number:
            return self.version_number > other.version_number
        return self.last_modified > other.last_modified

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "entity_id": self.entity_id,
            "database_type": self.database_type.value,
            "version_number": self.version_number,
            "last_modified": self.last_modified.isoformat(),
            "checksum": self.checksum,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityVersion":
        """Create from dictionary."""
        return cls(
            entity_id=data["entity_id"],
            database_type=DatabaseType(data["database_type"]),
            version_number=data["version_number"],
            last_modified=datetime.fromisoformat(data["last_modified"]),
            checksum=data.get("checksum"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConflictRecord:
    """Record of a detected conflict."""

    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType = ConflictType.VERSION_CONFLICT
    entity_mapping: Optional[IDMapping] = None
    source_version: Optional[EntityVersion] = None
    target_version: Optional[EntityVersion] = None
    source_data: Optional[Dict[str, Any]] = None
    target_data: Optional[Dict[str, Any]] = None

    # Conflict metadata
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolution_strategy: Optional[ConflictResolutionStrategy] = None
    status: ConflictStatus = ConflictStatus.DETECTED
    resolution_attempts: int = 0
    max_resolution_attempts: int = 3

    # Resolution tracking
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # System or user ID
    resolution_data: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None
    error_message: Optional[str] = None

    def mark_resolving(self, strategy: ConflictResolutionStrategy) -> None:
        """Mark conflict as being resolved."""
        self.status = ConflictStatus.RESOLVING
        self.resolution_strategy = strategy
        self.resolution_attempts += 1

    def mark_resolved(
        self,
        resolved_by: str,
        resolution_data: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Mark conflict as resolved."""
        self.status = ConflictStatus.RESOLVED
        self.resolved_at = datetime.now(UTC)
        self.resolved_by = resolved_by
        self.resolution_data = resolution_data
        self.resolution_notes = notes

    def mark_failed(self, error: str) -> None:
        """Mark conflict resolution as failed."""
        self.status = ConflictStatus.FAILED
        self.error_message = error

    def requires_manual_review(self) -> bool:
        """Check if conflict requires manual review."""
        return (
            self.status == ConflictStatus.MANUAL_REVIEW
            or self.resolution_attempts >= self.max_resolution_attempts
            or self.resolution_strategy
            == ConflictResolutionStrategy.MANUAL_INTERVENTION
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "entity_mapping": (
                self.entity_mapping.to_dict() if self.entity_mapping else None
            ),
            "source_version": (
                self.source_version.to_dict() if self.source_version else None
            ),
            "target_version": (
                self.target_version.to_dict() if self.target_version else None
            ),
            "source_data": self.source_data,
            "target_data": self.target_data,
            "detected_at": self.detected_at.isoformat(),
            "resolution_strategy": (
                self.resolution_strategy.value if self.resolution_strategy else None
            ),
            "status": self.status.value,
            "resolution_attempts": self.resolution_attempts,
            "max_resolution_attempts": self.max_resolution_attempts,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_data": self.resolution_data,
            "resolution_notes": self.resolution_notes,
            "error_message": self.error_message,
        }


@dataclass
class ConflictResolutionConfig:
    """Configuration for conflict resolution."""

    default_strategy: ConflictResolutionStrategy = (
        ConflictResolutionStrategy.LAST_WRITE_WINS
    )
    enable_auto_resolution: bool = True
    max_resolution_attempts: int = 3
    manual_review_threshold: int = 2
    source_priority_database: Optional[DatabaseType] = None
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    enable_merge_strategy: bool = False
    conflict_retention_days: int = 30
    enable_conflict_logging: bool = True
