"""Enhanced search capabilities for Phase 2+ features.

This module contains advanced search intelligence including:
- Knowledge graph construction and traversal (Phase 2.1) ✅
- Intent-aware adaptive search strategies (Phase 2.2) ✅
- Topic-driven search chaining (Phase 1.2) ✅
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

# 🔥 NEW: Phase 1.2 Topic-Driven Search Chaining
from .topic_search_chain import (
    ChainStrategy,
    TopicChainLink,
    TopicSearchChain,
    TopicRelationshipMap,
    TopicSearchChainGenerator
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
    "AdaptiveSearchStrategy",
    
    # Phase 1.2: Topic-Driven Search Chaining
    "ChainStrategy",
    "TopicChainLink",
    "TopicSearchChain", 
    "TopicRelationshipMap",
    "TopicSearchChainGenerator"
] 