"""Custom node schemas for QDrant Loader knowledge graph.

This module defines specialized node types that extend Graphiti's EntityNode
to support document processing, source tracking, and knowledge management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from graphiti_core.nodes import EntityNode
from pydantic import Field, validator


class DocumentNode(EntityNode):
    """Node representing a document in the knowledge graph.

    Extends EntityNode to include document-specific metadata like file type,
    size, processing status, and content summary.
    """

    # Document-specific fields
    file_path: Optional[str] = Field(None, description="Original file path")
    file_type: Optional[str] = Field(
        None, description="Document file type (pdf, docx, txt, etc.)"
    )
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type of the document")

    # Content metadata
    title: Optional[str] = Field(None, description="Document title")
    author: Optional[str] = Field(None, description="Document author")
    language: Optional[str] = Field(None, description="Document language")
    page_count: Optional[int] = Field(None, description="Number of pages")
    word_count: Optional[int] = Field(None, description="Approximate word count")

    # Processing metadata
    processing_status: str = Field(default="pending", description="Processing status")
    processed_at: Optional[datetime] = Field(
        None, description="When document was processed"
    )
    chunk_count: Optional[int] = Field(None, description="Number of chunks created")

    # Content summary
    content_summary: Optional[str] = Field(
        None, description="AI-generated summary of document content"
    )
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    topics: List[str] = Field(default_factory=list, description="Identified topics")

    @validator("processing_status")
    def validate_status(cls, v):
        valid_statuses = ["pending", "processing", "completed", "failed", "skipped"]
        if v not in valid_statuses:
            raise ValueError("Status must be one of {valid_statuses}")
        return v


class SourceNode(EntityNode):
    """Node representing a data source (repository, database, API, etc.).

    Tracks the origin of documents and provides metadata about the source system.
    """

    source_type: str = Field(
        ..., description="Type of source (git, confluence, jira, etc.)"
    )
    source_url: Optional[str] = Field(None, description="URL or connection string")
    source_config: Dict[str, Any] = Field(
        default_factory=dict, description="Source-specific configuration"
    )

    # Access metadata
    last_accessed: Optional[datetime] = Field(
        None, description="Last time source was accessed"
    )
    access_method: Optional[str] = Field(
        None, description="How source was accessed (API, clone, etc.)"
    )
    credentials_used: Optional[str] = Field(
        None, description="Type of credentials used"
    )

    # Source statistics
    total_documents: Optional[int] = Field(
        None, description="Total documents from this source"
    )
    successful_imports: Optional[int] = Field(
        None, description="Successfully imported documents"
    )
    failed_imports: Optional[int] = Field(None, description="Failed import attempts")

    @validator("source_type")
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
            raise ValueError("Source type must be one of {valid_types}")
        return v


class ConceptNode(EntityNode):
    """Node representing an abstract concept, idea, or topic.

    Used for semantic organization and topic modeling of document content.
    """

    concept_type: str = Field(default="general", description="Type of concept")
    definition: Optional[str] = Field(
        None, description="Definition or description of the concept"
    )
    aliases: List[str] = Field(
        default_factory=list, description="Alternative names for the concept"
    )

    # Semantic metadata
    domain: Optional[str] = Field(
        None, description="Domain or field this concept belongs to"
    )
    confidence_score: Optional[float] = Field(
        None, description="Confidence in concept extraction"
    )
    frequency: Optional[int] = Field(None, description="How often this concept appears")

    # Relationships
    parent_concepts: List[str] = Field(
        default_factory=list, description="Broader concepts"
    )
    child_concepts: List[str] = Field(
        default_factory=list, description="More specific concepts"
    )

    @validator("confidence_score")
    def validate_confidence(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


class PersonNode(EntityNode):
    """Node representing a person mentioned in documents.

    Tracks individuals, their roles, and their relationships to documents and projects.
    """

    full_name: Optional[str] = Field(None, description="Full name of the person")
    email: Optional[str] = Field(None, description="Email address")
    role: Optional[str] = Field(None, description="Role or job title")
    department: Optional[str] = Field(None, description="Department or team")

    # Contact information
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Office location or city")

    # Professional metadata
    expertise_areas: List[str] = Field(
        default_factory=list, description="Areas of expertise"
    )
    projects: List[str] = Field(default_factory=list, description="Associated projects")

    # Activity tracking
    last_mentioned: Optional[datetime] = Field(
        None, description="Last time mentioned in documents"
    )
    mention_count: Optional[int] = Field(None, description="Number of times mentioned")


class OrganizationNode(EntityNode):
    """Node representing an organization, company, or team.

    Tracks organizational entities and their relationships to documents and people.
    """

    organization_type: str = Field(
        default="company", description="Type of organization"
    )
    industry: Optional[str] = Field(None, description="Industry or sector")
    size: Optional[str] = Field(
        None, description="Organization size (startup, small, medium, large)"
    )

    # Contact information
    website: Optional[str] = Field(None, description="Organization website")
    headquarters: Optional[str] = Field(None, description="Headquarters location")

    # Relationship metadata
    parent_organization: Optional[str] = Field(
        None, description="Parent company or organization"
    )
    subsidiaries: List[str] = Field(
        default_factory=list, description="Subsidiary organizations"
    )

    # Activity tracking
    first_mentioned: Optional[datetime] = Field(
        None, description="First time mentioned"
    )
    last_mentioned: Optional[datetime] = Field(None, description="Last time mentioned")

    @validator("organization_type")
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
            raise ValueError("Organization type must be one of {valid_types}")
        return v


class ProjectNode(EntityNode):
    """Node representing a project, initiative, or work item.

    Tracks projects and their associated documents, people, and timelines.
    """

    project_status: str = Field(default="active", description="Current project status")
    start_date: Optional[datetime] = Field(None, description="Project start date")
    end_date: Optional[datetime] = Field(None, description="Project end date")
    deadline: Optional[datetime] = Field(None, description="Project deadline")

    # Project metadata
    priority: Optional[str] = Field(None, description="Project priority level")
    budget: Optional[float] = Field(None, description="Project budget")
    progress: Optional[float] = Field(
        None, description="Completion percentage (0.0-1.0)"
    )

    # Relationships
    project_manager: Optional[str] = Field(None, description="Project manager name")
    team_members: List[str] = Field(
        default_factory=list, description="Team member names"
    )
    stakeholders: List[str] = Field(
        default_factory=list, description="Project stakeholders"
    )

    # Documentation
    requirements: List[str] = Field(
        default_factory=list, description="Project requirements"
    )
    deliverables: List[str] = Field(
        default_factory=list, description="Project deliverables"
    )

    @validator("project_status")
    def validate_status(cls, v):
        valid_statuses = ["planning", "active", "on-hold", "completed", "cancelled"]
        if v not in valid_statuses:
            raise ValueError("Project status must be one of {valid_statuses}")
        return v

    @validator("progress")
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
    chunk_id: Optional[str] = Field(
        None, description="Unique identifier for this chunk"
    )

    # Content metadata
    content: str = Field(..., description="The actual text content of the chunk")
    content_length: int = Field(..., description="Length of content in characters")
    word_count: int = Field(..., description="Number of words in the chunk")

    # Position metadata
    start_position: Optional[int] = Field(
        None, description="Start position in original document"
    )
    end_position: Optional[int] = Field(
        None, description="End position in original document"
    )
    page_number: Optional[int] = Field(None, description="Page number if applicable")

    # Processing metadata
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")
    embedding_dimension: Optional[int] = Field(
        None, description="Dimension of the embedding vector"
    )
    processed_at: Optional[datetime] = Field(
        None, description="When chunk was processed"
    )

    # Semantic metadata
    topics: List[str] = Field(
        default_factory=list, description="Topics identified in this chunk"
    )
    entities: List[str] = Field(
        default_factory=list, description="Named entities in this chunk"
    )
    sentiment: Optional[str] = Field(None, description="Sentiment analysis result")

    @validator("chunk_index")
    def validate_chunk_index(cls, v):
        if v < 0:
            raise ValueError("Chunk index must be non-negative")
        return v

    @validator("content_length")
    def validate_content_length(cls, v):
        if v < 0:
            raise ValueError("Content length must be non-negative")
        return v
