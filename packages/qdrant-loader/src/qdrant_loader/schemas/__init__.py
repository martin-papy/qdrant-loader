"""Custom Graphiti schemas for QDrant Loader.

This module provides custom node and edge schemas tailored for document processing,
knowledge management, and the QDrant Loader application's specific use cases.
"""

from .edges import (
    AuthoredByEdge,
    BelongsToEdge,
    ContainsEdge,
    DerivedFromEdge,
    DocumentRelationshipEdge,
    ReferencesEdge,
    RelatedToEdge,
)
from .nodes import (
    ChunkNode,
    ConceptNode,
    DocumentNode,
    OrganizationNode,
    PersonNode,
    ProjectNode,
    SourceNode,
)

__all__ = [
    # Nodes
    "DocumentNode",
    "SourceNode",
    "ConceptNode",
    "PersonNode",
    "OrganizationNode",
    "ProjectNode",
    "ChunkNode",
    # Edges
    "DocumentRelationshipEdge",
    "ContainsEdge",
    "ReferencesEdge",
    "AuthoredByEdge",
    "BelongsToEdge",
    "RelatedToEdge",
    "DerivedFromEdge",
]
