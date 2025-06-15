"""Version types and data classes for the versioning system.

This module contains all the enums, data classes, and type definitions
used throughout the versioning system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class VersionType(Enum):
    """Types of versioned entities."""

    DOCUMENT = "document"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    MAPPING = "mapping"
    SYSTEM = "system"


class VersionOperation(Enum):
    """Types of version operations."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    BRANCH = "branch"
    ROLLBACK = "rollback"


class VersionStatus(Enum):
    """Status of a version."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PENDING = "pending"


@dataclass
class VersionMetadata:
    """Metadata for version tracking."""

    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    version_type: VersionType = VersionType.DOCUMENT
    version_number: int = 1

    # Temporal information
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    valid_from: datetime = field(default_factory=lambda: datetime.now(UTC))
    valid_to: Optional[datetime] = None

    # Version relationships
    parent_version_id: Optional[str] = None
    child_version_ids: List[str] = field(default_factory=list)
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None

    # Operation tracking
    operation: VersionOperation = VersionOperation.CREATE
    operation_source: str = "system"
    operation_metadata: Dict[str, Any] = field(default_factory=dict)

    # Content tracking
    content_hash: Optional[str] = None
    content_size: int = 0

    # Status and flags
    status: VersionStatus = VersionStatus.ACTIVE
    is_milestone: bool = False
    tags: Set[str] = field(default_factory=set)

    # User information
    created_by: Optional[str] = None
    modified_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "version_id": self.version_id,
            "entity_id": self.entity_id,
            "version_type": self.version_type.value,
            "version_number": self.version_number,
            "created_at": self.created_at.isoformat(),
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "parent_version_id": self.parent_version_id,
            "child_version_ids": list(self.child_version_ids),
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "operation": self.operation.value,
            "operation_source": self.operation_source,
            "operation_metadata": self.operation_metadata,
            "content_hash": self.content_hash,
            "content_size": self.content_size,
            "status": self.status.value,
            "is_milestone": self.is_milestone,
            "tags": list(self.tags),
            "created_by": self.created_by,
            "modified_by": self.modified_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionMetadata":
        """Create from dictionary format."""
        metadata = cls(
            version_id=data["version_id"],
            entity_id=data["entity_id"],
            version_type=VersionType(data["version_type"]),
            version_number=data["version_number"],
            parent_version_id=data.get("parent_version_id"),
            supersedes=data.get("supersedes"),
            superseded_by=data.get("superseded_by"),
            operation=VersionOperation(data["operation"]),
            operation_source=data["operation_source"],
            operation_metadata=data.get("operation_metadata", {}),
            content_hash=data.get("content_hash"),
            content_size=data.get("content_size", 0),
            status=VersionStatus(data["status"]),
            is_milestone=data.get("is_milestone", False),
            created_by=data.get("created_by"),
            modified_by=data.get("modified_by"),
        )

        # Parse timestamps
        metadata.created_at = datetime.fromisoformat(data["created_at"])
        metadata.valid_from = datetime.fromisoformat(data["valid_from"])
        if data.get("valid_to"):
            metadata.valid_to = datetime.fromisoformat(data["valid_to"])

        # Parse lists and sets
        metadata.child_version_ids = data.get("child_version_ids", [])
        metadata.tags = set(data.get("tags", []))

        return metadata


@dataclass
class VersionDiff:
    """Represents differences between two versions."""

    from_version_id: str
    to_version_id: str
    diff_type: str  # "content", "metadata", "structure"

    # Change details
    added_fields: Dict[str, Any] = field(default_factory=dict)
    removed_fields: Dict[str, Any] = field(default_factory=dict)
    modified_fields: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)

    # Statistics
    total_changes: int = 0
    similarity_score: float = 0.0

    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    generated_by: str = "system"


@dataclass
class VersionSnapshot:
    """Represents a point-in-time snapshot of versioned data."""

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Snapshot content
    entities: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, Any] = field(default_factory=dict)
    mappings: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    description: str = ""
    tags: Set[str] = field(default_factory=set)
    created_by: Optional[str] = None

    # Statistics
    entity_count: int = 0
    relationship_count: int = 0
    mapping_count: int = 0


@dataclass
class VersionConfig:
    """Configuration for version management."""

    retention_days: int = 90
    max_versions_per_entity: int = 100
    enable_auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    enable_compression: bool = False
    compression_threshold_days: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "retention_days": self.retention_days,
            "max_versions_per_entity": self.max_versions_per_entity,
            "enable_auto_cleanup": self.enable_auto_cleanup,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "enable_compression": self.enable_compression,
            "compression_threshold_days": self.compression_threshold_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionConfig":
        """Create from dictionary format."""
        return cls(
            retention_days=data.get("retention_days", 90),
            max_versions_per_entity=data.get("max_versions_per_entity", 100),
            enable_auto_cleanup=data.get("enable_auto_cleanup", True),
            cleanup_interval_hours=data.get("cleanup_interval_hours", 24),
            enable_compression=data.get("enable_compression", False),
            compression_threshold_days=data.get("compression_threshold_days", 30),
        )


@dataclass
class VersionStatistics:
    """Statistics about version usage."""

    total_versions: int = 0
    total_entities: int = 0
    average_versions_per_entity: float = 0.0
    max_versions_per_entity: int = 0
    oldest_version: Optional[datetime] = None
    newest_version: Optional[datetime] = None
    version_types: Dict[str, int] = field(default_factory=dict)
    version_statuses: Dict[str, int] = field(default_factory=dict)
    cache_size: int = 0
    storage_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "total_versions": self.total_versions,
            "total_entities": self.total_entities,
            "average_versions_per_entity": self.average_versions_per_entity,
            "max_versions_per_entity": self.max_versions_per_entity,
            "oldest_version": (
                self.oldest_version.isoformat() if self.oldest_version else None
            ),
            "newest_version": (
                self.newest_version.isoformat() if self.newest_version else None
            ),
            "version_types": self.version_types,
            "version_statuses": self.version_statuses,
            "cache_size": self.cache_size,
            "storage_size_bytes": self.storage_size_bytes,
        }
