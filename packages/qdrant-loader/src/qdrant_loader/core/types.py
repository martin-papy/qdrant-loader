"""Core types for entity extraction and relationship detection."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EntityType(Enum):
    """Supported entity types for extraction."""

    SERVICE = "Service"
    DATABASE = "Database"
    TEAM = "Team"
    PERSON = "Person"
    ORGANIZATION = "Organization"
    PROJECT = "Project"
    CONCEPT = "Concept"
    TECHNOLOGY = "Technology"
    API = "API"
    ENDPOINT = "Endpoint"


class RelationshipType(Enum):
    """Supported relationship types for extraction."""

    CONTAINS = "contains"
    REFERENCES = "references"
    AUTHORED_BY = "authored_by"
    BELONGS_TO = "belongs_to"
    RELATED_TO = "related_to"
    DERIVED_FROM = "derived_from"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    USES = "uses"
    MANAGES = "manages"


@dataclass
class TemporalInfo:
    """Container for temporal information used in entities and relationships."""

    # Valid time - when the information was true in the real world
    valid_from: datetime = field(default_factory=lambda: datetime.now(UTC))
    valid_to: datetime | None = None  # None means currently valid

    # Transaction time - when the information was recorded in the system
    transaction_time: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    # Version information for tracking changes
    version: int = 1
    superseded_by: str | None = (
        None  # UUID of the entity/relationship that supersedes this one
    )
    supersedes: str | None = (
        None  # UUID of the entity/relationship this one supersedes
    )

    def is_valid_at(self, timestamp: datetime) -> bool:
        """Check if this temporal info is valid at a given timestamp.

        Args:
            timestamp: The timestamp to check validity for

        Returns:
            True if valid at the given timestamp, False otherwise
        """
        if timestamp < self.valid_from:
            return False
        if self.valid_to is not None and timestamp >= self.valid_to:
            return False
        return True

    def is_currently_valid(self) -> bool:
        """Check if this temporal info is currently valid.

        Returns:
            True if currently valid, False otherwise
        """
        return self.is_valid_at(datetime.now(UTC))

    def invalidate_at(self, timestamp: datetime) -> None:
        """Mark this temporal info as invalid starting from the given timestamp.

        Args:
            timestamp: The timestamp when this becomes invalid
        """
        self.valid_to = timestamp

    def to_dict(self) -> dict[str, Any]:
        """Convert temporal info to dictionary format.

        Returns:
            Dictionary representation of temporal info
        """
        return {
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "transaction_time": self.transaction_time.isoformat(),
            "version": self.version,
            "superseded_by": self.superseded_by,
            "supersedes": self.supersedes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemporalInfo":
        """Create TemporalInfo from dictionary.

        Args:
            data: Dictionary containing temporal info data

        Returns:
            TemporalInfo instance
        """
        return cls(
            valid_from=datetime.fromisoformat(data["valid_from"]),
            valid_to=(
                datetime.fromisoformat(data["valid_to"])
                if data.get("valid_to")
                else None
            ),
            transaction_time=datetime.fromisoformat(data["transaction_time"]),
            version=data.get("version", 1),
            superseded_by=data.get("superseded_by"),
            supersedes=data.get("supersedes"),
        )


@dataclass
class ExtractedEntity:
    """Container for extracted entity information with temporal tracking."""

    name: str
    entity_type: EntityType
    confidence: float = 0.0
    context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # Temporal information
    temporal_info: TemporalInfo = field(default_factory=TemporalInfo)

    # Unique identifier for tracking across versions
    entity_uuid: str | None = None

    def is_valid_at(self, timestamp: datetime) -> bool:
        """Check if this entity is valid at a given timestamp.

        Args:
            timestamp: The timestamp to check validity for

        Returns:
            True if valid at the given timestamp, False otherwise
        """
        return self.temporal_info.is_valid_at(timestamp)

    def is_currently_valid(self) -> bool:
        """Check if this entity is currently valid.

        Returns:
            True if currently valid, False otherwise
        """
        return self.temporal_info.is_currently_valid()

    def create_new_version(
        self, updated_fields: dict[str, Any], valid_from: datetime | None = None
    ) -> "ExtractedEntity":
        """Create a new version of this entity with updated information.

        Args:
            updated_fields: Dictionary of fields to update
            valid_from: When the new version becomes valid (defaults to now)

        Returns:
            New ExtractedEntity instance representing the updated version
        """
        # Invalidate current version
        invalidation_time = valid_from or datetime.now(UTC)
        self.temporal_info.invalidate_at(invalidation_time)

        # Create new version
        new_entity = ExtractedEntity(
            name=updated_fields.get("name", self.name),
            entity_type=updated_fields.get("entity_type", self.entity_type),
            confidence=updated_fields.get("confidence", self.confidence),
            context=updated_fields.get("context", self.context),
            metadata=updated_fields.get("metadata", self.metadata.copy()),
            entity_uuid=self.entity_uuid,  # Keep same UUID for tracking
        )

        # Set up temporal info for new version
        new_entity.temporal_info = TemporalInfo(
            valid_from=invalidation_time,
            transaction_time=datetime.now(UTC),
            version=self.temporal_info.version + 1,
            supersedes=self.entity_uuid,
        )

        # Update current version to point to new version
        self.temporal_info.superseded_by = new_entity.entity_uuid

        return new_entity

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary format.

        Returns:
            Dictionary representation of the entity
        """
        return {
            "name": self.name,
            "entity_type": self.entity_type.value,
            "confidence": self.confidence,
            "context": self.context,
            "metadata": self.metadata,
            "temporal_info": self.temporal_info.to_dict(),
            "entity_uuid": self.entity_uuid,
        }


@dataclass
class ExtractedRelationship:
    """Container for extracted relationship information with temporal tracking."""

    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    confidence: float = 0.0
    context: str = ""
    evidence: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # Temporal information
    temporal_info: TemporalInfo = field(default_factory=TemporalInfo)

    # Unique identifier for tracking across versions
    relationship_uuid: str | None = None

    # Entity UUIDs for better tracking
    source_entity_uuid: str | None = None
    target_entity_uuid: str | None = None

    def is_valid_at(self, timestamp: datetime) -> bool:
        """Check if this relationship is valid at a given timestamp.

        Args:
            timestamp: The timestamp to check validity for

        Returns:
            True if valid at the given timestamp, False otherwise
        """
        return self.temporal_info.is_valid_at(timestamp)

    def is_currently_valid(self) -> bool:
        """Check if this relationship is currently valid.

        Returns:
            True if currently valid, False otherwise
        """
        return self.temporal_info.is_currently_valid()

    def create_new_version(
        self, updated_fields: dict[str, Any], valid_from: datetime | None = None
    ) -> "ExtractedRelationship":
        """Create a new version of this relationship with updated information.

        Args:
            updated_fields: Dictionary of fields to update
            valid_from: When the new version becomes valid (defaults to now)

        Returns:
            New ExtractedRelationship instance representing the updated version
        """
        # Invalidate current version
        invalidation_time = valid_from or datetime.now(UTC)
        self.temporal_info.invalidate_at(invalidation_time)

        # Create new version
        new_relationship = ExtractedRelationship(
            source_entity=updated_fields.get("source_entity", self.source_entity),
            target_entity=updated_fields.get("target_entity", self.target_entity),
            relationship_type=updated_fields.get(
                "relationship_type", self.relationship_type
            ),
            confidence=updated_fields.get("confidence", self.confidence),
            context=updated_fields.get("context", self.context),
            evidence=updated_fields.get("evidence", self.evidence),
            metadata=updated_fields.get("metadata", self.metadata.copy()),
            relationship_uuid=self.relationship_uuid,  # Keep same UUID for tracking
            source_entity_uuid=updated_fields.get(
                "source_entity_uuid", self.source_entity_uuid
            ),
            target_entity_uuid=updated_fields.get(
                "target_entity_uuid", self.target_entity_uuid
            ),
        )

        # Set up temporal info for new version
        new_relationship.temporal_info = TemporalInfo(
            valid_from=invalidation_time,
            transaction_time=datetime.now(UTC),
            version=self.temporal_info.version + 1,
            supersedes=self.relationship_uuid,
        )

        # Update current version to point to new version
        self.temporal_info.superseded_by = new_relationship.relationship_uuid

        return new_relationship

    def to_dict(self) -> dict[str, Any]:
        """Convert relationship to dictionary format.

        Returns:
            Dictionary representation of the relationship
        """
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "context": self.context,
            "evidence": self.evidence,
            "metadata": self.metadata,
            "temporal_info": self.temporal_info.to_dict(),
            "relationship_uuid": self.relationship_uuid,
            "source_entity_uuid": self.source_entity_uuid,
            "target_entity_uuid": self.target_entity_uuid,
        }
