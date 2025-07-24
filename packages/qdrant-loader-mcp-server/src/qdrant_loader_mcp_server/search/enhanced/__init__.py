"""Enhanced search capabilities for Phase 2+ features.

This module contains advanced search intelligence including:
- Knowledge graph construction and traversal (Phase 2.1) ✅
- Intent-aware adaptive search strategies (Phase 2.2) ✅
- Cross-document relationship analysis
- Multi-hop reasoning capabilities
"""

from .knowledge_graph import (
    KnowledgeGraph,
    DocumentKnowledgeGraph,
    GraphNode,
    GraphEdge,
    RelationshipType,
    TraversalStrategy,
    GraphTraverser,
    GraphBuilder
)

from .intent_classifier import (
    IntentType,
    SearchIntent,
    AdaptiveSearchConfig,
    IntentClassifier,
    AdaptiveSearchStrategy
)

__all__ = [
    # Phase 2.1: Knowledge Graph
    "KnowledgeGraph",
    "DocumentKnowledgeGraph", 
    "GraphNode",
    "GraphEdge",
    "RelationshipType",
    "TraversalStrategy",
    "GraphTraverser",
    "GraphBuilder",
    
    # Phase 2.2: Intent-Aware Adaptive Search
    "IntentType",
    "SearchIntent", 
    "AdaptiveSearchConfig",
    "IntentClassifier",
    "AdaptiveSearchStrategy"
] 