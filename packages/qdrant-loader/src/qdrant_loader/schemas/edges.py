"""Custom edge schemas for QDrant Loader knowledge graph.

This module defines specialized edge types that extend Graphiti's EntityEdge
to support document relationships, organizational connections, and knowledge links.
"""

from datetime import datetime

from graphiti_core.edges import EntityEdge
from pydantic import Field, validator


class DocumentRelationshipEdge(EntityEdge):
    """Base edge for relationships between documents.

    Extends EntityEdge to include document-specific relationship metadata.
    """

    relationship_type: str = Field(
        ..., description="Type of relationship between documents"
    )
    confidence_score: float | None = Field(
        None, description="Confidence in the relationship"
    )

    # Context metadata
    context: str | None = Field(
        None, description="Context where relationship was identified"
    )
    evidence: str | None = Field(
        None, description="Evidence supporting the relationship"
    )

    # Processing metadata
    detected_by: str | None = Field(
        None, description="Method or model that detected relationship"
    )
    detected_at: datetime | None = Field(
        None, description="When relationship was detected"
    )

    @validator("confidence_score")
    def validate_confidence(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


class ContainsEdge(DocumentRelationshipEdge):
    """Edge representing containment relationships.

    Used when one document contains or includes another (e.g., document contains chunks).
    """

    relationship_type: str = Field(
        default="contains", description="Containment relationship"
    )

    # Containment metadata
    container_section: str | None = Field(
        None, description="Section of container that includes target"
    )
    position_index: int | None = Field(None, description="Position within container")
    size_ratio: float | None = Field(
        None, description="Size of contained item relative to container"
    )

    @validator("position_index")
    def validate_position(cls, v):
        if v is not None and v < 0:
            raise ValueError("Position index must be non-negative")
        return v


class ReferencesEdge(DocumentRelationshipEdge):
    """Edge representing reference relationships.

    Used when one document references, cites, or mentions another.
    """

    relationship_type: str = Field(
        default="references", description="Reference relationship"
    )

    # Reference metadata
    reference_type: str = Field(default="mention", description="Type of reference")
    reference_context: str | None = Field(None, description="Context of the reference")
    page_number: int | None = Field(None, description="Page where reference occurs")
    line_number: int | None = Field(None, description="Line where reference occurs")

    # Citation metadata
    citation_style: str | None = Field(None, description="Citation style used")
    is_formal_citation: bool = Field(
        default=False, description="Whether this is a formal citation"
    )

    @validator("reference_type")
    def validate_reference_type(cls, v):
        valid_types = [
            "mention",
            "citation",
            "link",
            "attachment",
            "dependency",
            "other",
        ]
        if v not in valid_types:
            raise ValueError(f"Reference type must be one of {valid_types}")
        return v


class AuthoredByEdge(EntityEdge):
    """Edge representing authorship relationships.

    Connects documents to their authors (persons or organizations).
    """

    # Authorship metadata
    author_role: str = Field(default="author", description="Role of the author")
    contribution_type: str | None = Field(None, description="Type of contribution")
    contribution_percentage: float | None = Field(
        None, description="Percentage of contribution"
    )

    # Temporal metadata
    authored_at: datetime | None = Field(None, description="When document was authored")
    last_modified_at: datetime | None = Field(
        None, description="Last modification by this author"
    )

    # Verification metadata
    verified: bool = Field(default=False, description="Whether authorship is verified")
    verification_method: str | None = Field(
        None, description="How authorship was verified"
    )

    @validator("author_role")
    def validate_author_role(cls, v):
        valid_roles = [
            "author",
            "co-author",
            "editor",
            "reviewer",
            "contributor",
            "translator",
            "other",
        ]
        if v not in valid_roles:
            raise ValueError(f"Author role must be one of {valid_roles}")
        return v

    @validator("contribution_percentage")
    def validate_contribution(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Contribution percentage must be between 0.0 and 1.0")
        return v


class BelongsToEdge(EntityEdge):
    """Edge representing ownership or membership relationships.

    Connects entities to their parent organizations, projects, or categories.
    """

    # Membership metadata
    membership_type: str = Field(default="belongs_to", description="Type of membership")
    start_date: datetime | None = Field(None, description="When membership started")
    end_date: datetime | None = Field(None, description="When membership ended")

    # Role and permissions
    role_in_group: str | None = Field(None, description="Role within the group")
    permissions: list[str] = Field(
        default_factory=list, description="Permissions granted"
    )
    access_level: str | None = Field(None, description="Access level within group")

    # Status
    is_active: bool = Field(
        default=True, description="Whether membership is currently active"
    )
    status: str = Field(default="active", description="Membership status")

    @validator("membership_type")
    def validate_membership_type(cls, v):
        valid_types = [
            "belongs_to",
            "member_o",
            "part_o",
            "assigned_to",
            "owned_by",
            "other",
        ]
        if v not in valid_types:
            raise ValueError(f"Membership type must be one of {valid_types}")
        return v

    @validator("status")
    def validate_status(cls, v):
        valid_statuses = ["active", "inactive", "pending", "suspended", "terminated"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class RelatedToEdge(DocumentRelationshipEdge):
    """Edge representing general semantic relationships.

    Used for documents or entities that are related but don't fit other specific edge types.
    """

    relationship_type: str = Field(
        default="related_to", description="General relationship"
    )

    # Semantic metadata
    semantic_similarity: float | None = Field(
        None, description="Semantic similarity score"
    )
    topic_overlap: list[str] = Field(
        default_factory=list, description="Overlapping topics"
    )
    keyword_overlap: list[str] = Field(
        default_factory=list, description="Overlapping keywords"
    )

    # Relationship strength
    relationship_strength: str | None = Field(
        None, description="Strength of relationship"
    )
    bidirectional: bool = Field(
        default=True, description="Whether relationship is bidirectional"
    )

    # Discovery metadata
    discovered_through: str | None = Field(
        None, description="How relationship was discovered"
    )
    discovery_algorithm: str | None = Field(
        None, description="Algorithm used for discovery"
    )

    @validator("semantic_similarity")
    def validate_similarity(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Semantic similarity must be between 0.0 and 1.0")
        return v

    @validator("relationship_strength")
    def validate_strength(cls, v):
        if v is not None:
            valid_strengths = ["weak", "moderate", "strong", "very_strong"]
            if v not in valid_strengths:
                raise ValueError(
                    f"Relationship strength must be one of {valid_strengths}"
                )
        return v


class DerivedFromEdge(DocumentRelationshipEdge):
    """Edge representing derivation relationships.

    Used when one document is derived from another (e.g., summary from original, translation).
    """

    relationship_type: str = Field(
        default="derived_from", description="Derivation relationship"
    )

    # Derivation metadata
    derivation_type: str = Field(..., description="Type of derivation")
    derivation_method: str | None = Field(
        None, description="Method used for derivation"
    )
    transformation_applied: str | None = Field(
        None, description="Transformation applied"
    )

    # Quality metadata
    fidelity_score: float | None = Field(
        None, description="Fidelity to original content"
    )
    completeness_score: float | None = Field(
        None, description="Completeness of derivation"
    )

    # Processing metadata
    derived_at: datetime | None = Field(None, description="When derivation was created")
    derived_by: str | None = Field(
        None, description="Who or what created the derivation"
    )
    processing_time: float | None = Field(
        None, description="Time taken for derivation (seconds)"
    )

    @validator("derivation_type")
    def validate_derivation_type(cls, v):
        valid_types = [
            "summary",
            "translation",
            "extraction",
            "transformation",
            "annotation",
            "enhancement",
            "compression",
            "other",
        ]
        if v not in valid_types:
            raise ValueError(f"Derivation type must be one of {valid_types}")
        return v

    @validator("fidelity_score")
    def validate_fidelity(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Fidelity score must be between 0.0 and 1.0")
        return v

    @validator("completeness_score")
    def validate_completeness(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Completeness score must be between 0.0 and 1.0")
        return v
