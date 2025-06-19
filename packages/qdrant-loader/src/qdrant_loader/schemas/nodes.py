"""Custom node schemas for QDrant Loader knowledge graph.

This module defines specialized node types that extend Graphiti's EntityNode
to support document processing, source tracking, and knowledge management.
"""

from datetime import datetime
from typing import Any

from graphiti_core.nodes import EntityNode
from pydantic import Field, field_validator


class DocumentNode(EntityNode):
    """Node representing a document in the knowledge graph.

    Extends EntityNode to include document-specific metadata like file type,
    size, processing status, and content summary.
    """

    # Document-specific fields
    file_path: str | None = Field(None, description="Original file path")
    file_type: str | None = Field(
        None, description="Document file type (pdf, docx, txt, etc.)"
    )
    file_size: int | None = Field(None, description="File size in bytes")
    mime_type: str | None = Field(None, description="MIME type of the document")

    # Content metadata
    title: str | None = Field(None, description="Document title")
    author: str | None = Field(None, description="Document author")
    language: str | None = Field(None, description="Document language")
    page_count: int | None = Field(None, description="Number of pages")
    word_count: int | None = Field(None, description="Approximate word count")

    # Processing metadata
    processing_status: str = Field(default="pending", description="Processing status")
    processed_at: datetime | None = Field(
        None, description="When document was processed"
    )
    chunk_count: int | None = Field(None, description="Number of chunks created")

    # Content summary
    content_summary: str | None = Field(
        None, description="AI-generated summary of document content"
    )
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    topics: list[str] = Field(default_factory=list, description="Identified topics")

    @field_validator("processing_status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["pending", "processing", "completed", "failed", "skipped"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class SourceNode(EntityNode):
    """Node representing a data source (repository, database, API, etc.).

    Tracks the origin of documents and provides metadata about the source system.
    """

    source_type: str = Field(
        ..., description="Type of source (git, confluence, jira, etc.)"
    )
    source_url: str | None = Field(None, description="URL or connection string")
    source_config: dict[str, Any] = Field(
        default_factory=dict, description="Source-specific configuration"
    )

    # Access metadata
    last_accessed: datetime | None = Field(
        None, description="Last time source was accessed"
    )
    access_method: str | None = Field(
        None, description="How source was accessed (API, clone, etc.)"
    )
    credentials_used: str | None = Field(None, description="Type of credentials used")

    # Source statistics
    total_documents: int | None = Field(
        None, description="Total documents from this source"
    )
    successful_imports: int | None = Field(
        None, description="Successfully imported documents"
    )
    failed_imports: int | None = Field(None, description="Failed import attempts")

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v):
        valid_types = [
            "git",
            "confluence",
            "jira",
            "sharepoint",
            "filesystem",
            "database",
            "api",
            "other",
        ]
        if v not in valid_types:
            raise ValueError(f"Source type must be one of {valid_types}")
        return v


class ConceptNode(EntityNode):
    """Node representing an abstract concept, idea, or topic.

    Used for semantic organization and topic modeling of document content.
    """

    concept_type: str = Field(default="general", description="Type of concept")
    definition: str | None = Field(
        None, description="Definition or description of the concept"
    )
    aliases: list[str] = Field(
        default_factory=list, description="Alternative names for the concept"
    )

    # Semantic metadata
    domain: str | None = Field(
        None, description="Domain or field this concept belongs to"
    )
    confidence_score: float | None = Field(
        None, description="Confidence in concept extraction"
    )
    frequency: int | None = Field(None, description="How often this concept appears")

    # Relationships
    parent_concepts: list[str] = Field(
        default_factory=list, description="Broader concepts"
    )
    child_concepts: list[str] = Field(
        default_factory=list, description="More specific concepts"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


class PersonNode(EntityNode):
    """Node representing a person mentioned in documents.

    Tracks individuals, their roles, and their relationships to documents and projects.
    """

    full_name: str | None = Field(None, description="Full name of the person")
    email: str | None = Field(None, description="Email address")
    role: str | None = Field(None, description="Role or job title")
    department: str | None = Field(None, description="Department or team")

    # Contact information
    phone: str | None = Field(None, description="Phone number")
    location: str | None = Field(None, description="Office location or city")

    # Professional metadata
    expertise_areas: list[str] = Field(
        default_factory=list, description="Areas of expertise"
    )
    projects: list[str] = Field(default_factory=list, description="Associated projects")

    # Activity tracking
    last_mentioned: datetime | None = Field(
        None, description="Last time mentioned in documents"
    )
    mention_count: int | None = Field(None, description="Number of times mentioned")


class OrganizationNode(EntityNode):
    """Node representing an organization, company, or team.

    Tracks organizational entities and their relationships to documents and people.
    """

    organization_type: str = Field(
        default="company", description="Type of organization"
    )
    industry: str | None = Field(None, description="Industry or sector")
    size: str | None = Field(
        None, description="Organization size (startup, small, medium, large)"
    )

    # Contact information
    website: str | None = Field(None, description="Organization website")
    headquarters: str | None = Field(None, description="Headquarters location")

    # Relationship metadata
    parent_organization: str | None = Field(
        None, description="Parent company or organization"
    )
    subsidiaries: list[str] = Field(
        default_factory=list, description="Subsidiary organizations"
    )

    # Activity tracking
    first_mentioned: datetime | None = Field(None, description="First time mentioned")
    last_mentioned: datetime | None = Field(None, description="Last time mentioned")

    @field_validator("organization_type")
    @classmethod
    def validate_org_type(cls, v):
        valid_types = [
            "company",
            "department",
            "team",
            "nonprofit",
            "government",
            "educational",
            "other",
        ]
        if v not in valid_types:
            raise ValueError(f"Organization type must be one of {valid_types}")
        return v


class ProjectNode(EntityNode):
    """Node representing a project, initiative, or work item.

    Tracks projects and their associated documents, people, and timelines.
    """

    project_status: str = Field(default="active", description="Current project status")
    start_date: datetime | None = Field(None, description="Project start date")
    end_date: datetime | None = Field(None, description="Project end date")
    deadline: datetime | None = Field(None, description="Project deadline")

    # Project metadata
    priority: str | None = Field(None, description="Project priority level")
    budget: float | None = Field(None, description="Project budget")
    progress: float | None = Field(None, description="Completion percentage (0.0-1.0)")

    # Relationships
    project_manager: str | None = Field(None, description="Project manager name")
    team_members: list[str] = Field(
        default_factory=list, description="Team member names"
    )
    stakeholders: list[str] = Field(
        default_factory=list, description="Project stakeholders"
    )

    # Documentation
    requirements: list[str] = Field(
        default_factory=list, description="Project requirements"
    )
    deliverables: list[str] = Field(
        default_factory=list, description="Project deliverables"
    )

    @field_validator("project_status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["planning", "active", "on-hold", "completed", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Project status must be one of {valid_statuses}")
        return v

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Progress must be between 0.0 and 1.0")
        return v


class ChunkNode(EntityNode):
    """Node representing a chunk of text from a document.

    Represents processed text chunks with their embeddings and metadata.
    """

    # Chunk identification
    document_id: str = Field(..., description="ID of the parent document")
    chunk_index: int = Field(..., description="Index of this chunk within the document")
    chunk_id: str | None = Field(None, description="Unique identifier for this chunk")

    # Content metadata
    content: str = Field(..., description="The actual text content of the chunk")
    content_length: int = Field(..., description="Length of content in characters")
    word_count: int = Field(..., description="Number of words in the chunk")

    # Position metadata
    start_position: int | None = Field(
        None, description="Start position in original document"
    )
    end_position: int | None = Field(
        None, description="End position in original document"
    )
    page_number: int | None = Field(None, description="Page number if applicable")

    # Processing metadata
    embedding_model: str | None = Field(None, description="Model used for embedding")
    embedding_dimension: int | None = Field(
        None, description="Dimension of the embedding vector"
    )
    processed_at: datetime | None = Field(None, description="When chunk was processed")

    # Semantic metadata
    topics: list[str] = Field(
        default_factory=list, description="Topics identified in this chunk"
    )
    entities: list[str] = Field(
        default_factory=list, description="Named entities in this chunk"
    )
    sentiment: str | None = Field(None, description="Sentiment analysis result")

    @field_validator("chunk_index")
    @classmethod
    def validate_chunk_index(cls, v):
        if v < 0:
            raise ValueError("Chunk index must be non-negative")
        return v

    @field_validator("content_length")
    @classmethod
    def validate_content_length(cls, v):
        if v < 0:
            raise ValueError("Content length must be non-negative")
        return v
