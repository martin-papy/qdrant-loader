"""Custom Graphiti schemas for QDrant Loader.

This module provides custom node and edge schemas tailored for document processing,
knowledge management, and the QDrant Loader application's specific use cases.
"""

from .nodes import (
    DocumentNode,
    SourceNode,
    ConceptNode,
    PersonNode,
    OrganizationNode,
    ProjectNode,
    ChunkNode,
)

from .edges import (
    DocumentRelationshipEdge,
    ContainsEdge,
    ReferencesEdge,
    AuthoredByEdge,
    BelongsToEdge,
    RelatedToEdge,
    DerivedFromEdge,
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
