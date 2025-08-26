"""
Knowledge Graph for Search Enhancement.

This module re-exports the complete knowledge graph implementation from the kg package.
All classes have been modularized into focused, single-responsibility modules for better
maintainability and testability.

Architecture:
- kg.models: Core data types and enums
- kg.graph: Core KnowledgeGraph implementation
- kg.builder: Graph construction from search results
- kg.traverser: Graph traversal algorithms
- kg.document_graph: High-level document interface
- kg.utils: Shared utilities and constants
- kg.extractors: Result parsing helpers
"""

# Re-export the complete knowledge graph API
from .kg import (  # Main classes; Core data types
    DocumentKnowledgeGraph,
    GraphBuilder,
    GraphEdge,
    GraphNode,
    GraphTraverser,
    KnowledgeGraph,
    NodeType,
    RelationshipType,
    TraversalResult,
    TraversalStrategy,
)

# Provide convenient access to the main DocumentKnowledgeGraph class
__all__ = [
    "DocumentKnowledgeGraph",
    "KnowledgeGraph",
    "GraphBuilder",
    "GraphTraverser",
    "NodeType",
    "RelationshipType",
    "GraphNode",
    "GraphEdge",
    "TraversalStrategy",
    "TraversalResult",
]
