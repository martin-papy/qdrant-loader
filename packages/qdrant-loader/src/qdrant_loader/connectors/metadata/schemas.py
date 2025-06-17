"""Standardized metadata schemas for data source connectors.

This module defines Pydantic models for different types of metadata that can be
extracted from various data sources to enrich the knowledge graph.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MetadataType(str, Enum):
    """Types of metadata that can be extracted."""

    AUTHOR = "author"
    TIMESTAMP = "timestamp"
    RELATIONSHIP = "relationship"
    CROSS_REFERENCE = "cross_reference"
    SOURCE_SPECIFIC = "source_specific"


class BaseMetadata(BaseModel):
    """Base metadata schema with common fields."""

    type: MetadataType = Field(description="Type of metadata")
    source: str = Field(description="Source system that generated this metadata")
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now, description="When this metadata was extracted"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score for this metadata"
    )


class AuthorMetadata(BaseMetadata):
    """Metadata about authors/contributors."""

    type: MetadataType = Field(default=MetadataType.AUTHOR)
    name: str = Field(description="Author name")
    email: str | None = Field(default=None, description="Author email address")
    username: str | None = Field(default=None, description="Author username/handle")
    display_name: str | None = Field(default=None, description="Author display name")
    role: str | None = Field(
        default=None, description="Author role (e.g., creator, editor, reviewer)"
    )
    avatar_url: str | None = Field(
        default=None, description="URL to author's avatar image"
    )
    profile_url: str | None = Field(
        default=None, description="URL to author's profile"
    )


class TimestampMetadata(BaseMetadata):
    """Metadata about timestamps and temporal information."""

    type: MetadataType = Field(default=MetadataType.TIMESTAMP)
    created_at: datetime | None = Field(
        default=None, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    published_at: datetime | None = Field(
        default=None, description="Publication timestamp"
    )
    accessed_at: datetime | None = Field(
        default=None, description="Last access timestamp"
    )
    archived_at: datetime | None = Field(
        default=None, description="Archive timestamp"
    )
    version: str | None = Field(default=None, description="Version identifier")


class RelationshipType(str, Enum):
    """Types of relationships between entities."""

    PARENT_CHILD = "parent_child"
    DEPENDENCY = "dependency"
    REFERENCE = "reference"
    SIMILARITY = "similarity"
    SEQUENCE = "sequence"
    HIERARCHY = "hierarchy"
    ASSOCIATION = "association"
    COMPOSITION = "composition"
    AGGREGATION = "aggregation"


class RelationshipMetadata(BaseMetadata):
    """Metadata about relationships between entities."""

    type: MetadataType = Field(default=MetadataType.RELATIONSHIP)
    relationship_type: RelationshipType = Field(description="Type of relationship")
    source_entity: str = Field(description="Source entity identifier")
    target_entity: str = Field(description="Target entity identifier")
    source_entity_type: str | None = Field(
        default=None, description="Type of source entity"
    )
    target_entity_type: str | None = Field(
        default=None, description="Type of target entity"
    )
    relationship_strength: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Strength of the relationship"
    )
    bidirectional: bool = Field(
        default=False, description="Whether the relationship is bidirectional"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional relationship properties"
    )


class CrossReferenceType(str, Enum):
    """Types of cross-references."""

    LINK = "link"
    MENTION = "mention"
    CITATION = "citation"
    ATTACHMENT = "attachment"
    EMBED = "embed"
    INCLUDE = "include"
    IMPORT = "import"
    DEPENDENCY = "dependency"


class CrossReferenceMetadata(BaseMetadata):
    """Metadata about cross-references between documents/entities."""

    type: MetadataType = Field(default=MetadataType.CROSS_REFERENCE)
    reference_type: CrossReferenceType = Field(description="Type of cross-reference")
    target: str = Field(description="Target of the reference (URL, ID, path, etc.)")
    target_type: str | None = Field(
        default=None, description="Type of target (document, image, etc.)"
    )
    anchor_text: str | None = Field(
        default=None, description="Text used for the reference"
    )
    context: str | None = Field(
        default=None, description="Context around the reference"
    )
    position: int | None = Field(
        default=None, description="Position in the source document"
    )
    resolved: bool = Field(
        default=False, description="Whether the reference was successfully resolved"
    )
    resolved_url: str | None = Field(
        default=None, description="Resolved URL if different from target"
    )


class GitMetadata(BaseMetadata):
    """Git-specific metadata."""

    type: MetadataType = Field(default=MetadataType.SOURCE_SPECIFIC)
    commit_hash: str | None = Field(default=None, description="Git commit hash")
    branch: str | None = Field(default=None, description="Git branch name")
    tag: str | None = Field(default=None, description="Git tag")
    repository_url: str | None = Field(default=None, description="Repository URL")
    file_path: str | None = Field(
        default=None, description="File path in repository"
    )
    commit_message: str | None = Field(default=None, description="Commit message")
    committer: AuthorMetadata | None = Field(
        default=None, description="Committer information"
    )
    merge_commit: bool = Field(
        default=False, description="Whether this is a merge commit"
    )
    parent_commits: list[str] = Field(
        default_factory=list, description="Parent commit hashes"
    )


class ConfluenceMetadata(BaseMetadata):
    """Confluence-specific metadata."""

    type: MetadataType = Field(default=MetadataType.SOURCE_SPECIFIC)
    page_id: str | None = Field(default=None, description="Confluence page ID")
    space_key: str | None = Field(default=None, description="Confluence space key")
    space_name: str | None = Field(default=None, description="Confluence space name")
    parent_page_id: str | None = Field(default=None, description="Parent page ID")
    page_version: int | None = Field(default=None, description="Page version number")
    content_type: str | None = Field(
        default=None, description="Content type (page, blogpost)"
    )
    labels: list[str] = Field(default_factory=list, description="Page labels")
    restrictions: dict[str, Any] = Field(
        default_factory=dict, description="Page restrictions"
    )
    attachments: list[str] = Field(default_factory=list, description="Attachment IDs")


class JiraMetadata(BaseMetadata):
    """JIRA-specific metadata."""

    type: MetadataType = Field(default=MetadataType.SOURCE_SPECIFIC)
    issue_key: str | None = Field(default=None, description="JIRA issue key")
    issue_id: str | None = Field(default=None, description="JIRA issue ID")
    project_key: str | None = Field(default=None, description="JIRA project key")
    project_name: str | None = Field(default=None, description="JIRA project name")
    issue_type: str | None = Field(default=None, description="Issue type")
    status: str | None = Field(default=None, description="Issue status")
    priority: str | None = Field(default=None, description="Issue priority")
    resolution: str | None = Field(default=None, description="Issue resolution")
    reporter: AuthorMetadata | None = Field(
        default=None, description="Issue reporter"
    )
    assignee: AuthorMetadata | None = Field(
        default=None, description="Issue assignee"
    )
    epic_key: str | None = Field(
        default=None, description="Epic key if issue is part of an epic"
    )
    parent_key: str | None = Field(default=None, description="Parent issue key")
    subtasks: list[str] = Field(default_factory=list, description="Subtask keys")
    linked_issues: list[dict[str, str]] = Field(
        default_factory=list, description="Linked issues"
    )
    components: list[str] = Field(default_factory=list, description="Issue components")
    fix_versions: list[str] = Field(default_factory=list, description="Fix versions")
    affects_versions: list[str] = Field(
        default_factory=list, description="Affects versions"
    )
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    custom_fields: dict[str, Any] = Field(
        default_factory=dict, description="Custom field values"
    )


class MetadataCollection(BaseModel):
    """Collection of metadata for a single document/entity."""

    document_id: str = Field(description="Document identifier")
    source_type: str = Field(description="Source type (git, confluence, jira, etc.)")
    source: str = Field(description="Source identifier")
    authors: list[AuthorMetadata] = Field(
        default_factory=list, description="Author metadata"
    )
    timestamps: TimestampMetadata | None = Field(
        default=None, description="Timestamp metadata"
    )
    relationships: list[RelationshipMetadata] = Field(
        default_factory=list, description="Relationship metadata"
    )
    cross_references: list[CrossReferenceMetadata] = Field(
        default_factory=list, description="Cross-reference metadata"
    )
    source_specific: BaseMetadata | None = Field(
        default=None, description="Source-specific metadata"
    )
    extraction_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the extraction process"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for storage."""
        return {
            "document_id": self.document_id,
            "source_type": self.source_type,
            "source": self.source,
            "authors": [author.model_dump() for author in self.authors],
            "timestamps": self.timestamps.model_dump() if self.timestamps else None,
            "relationships": [rel.model_dump() for rel in self.relationships],
            "cross_references": [ref.model_dump() for ref in self.cross_references],
            "source_specific": (
                self.source_specific.model_dump() if self.source_specific else None
            ),
            "extraction_metadata": self.extraction_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetadataCollection":
        """Create from dictionary format."""
        return cls(
            document_id=data["document_id"],
            source_type=data["source_type"],
            source=data["source"],
            authors=[AuthorMetadata(**author) for author in data.get("authors", [])],
            timestamps=(
                TimestampMetadata(**data["timestamps"])
                if data.get("timestamps")
                else None
            ),
            relationships=[
                RelationshipMetadata(**rel) for rel in data.get("relationships", [])
            ],
            cross_references=[
                CrossReferenceMetadata(**ref)
                for ref in data.get("cross_references", [])
            ],
            source_specific=(
                BaseMetadata(**data["source_specific"])
                if data.get("source_specific")
                else None
            ),
            extraction_metadata=data.get("extraction_metadata", {}),
        )
