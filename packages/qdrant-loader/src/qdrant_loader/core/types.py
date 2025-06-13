"""Core types for entity extraction and relationship detection."""

from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass, field


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
class ExtractedEntity:
    """Container for extracted entity information."""

    name: str
    entity_type: EntityType
    confidence: float = 0.0
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedRelationship:
    """Container for extracted relationship information."""

    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    confidence: float = 0.0
    context: str = ""
    evidence: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
