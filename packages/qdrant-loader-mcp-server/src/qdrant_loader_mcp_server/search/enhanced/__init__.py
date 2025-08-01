"""Enhanced search capabilities for Phase 2+ features.

This module contains advanced search intelligence including:
- Knowledge graph construction and traversal
- Intent-aware adaptive search strategies
- Topic-driven search chaining
- Dynamic faceted search interface
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

# 🔥 Topic-Driven Search Chaining
from .topic_search_chain import (
    ChainStrategy,
    TopicChainLink,
    TopicSearchChain,
    TopicRelationshipMap,
    TopicSearchChainGenerator
)

# 🔥 Dynamic Faceted Search Interface
from .faceted_search import (
    FacetType,
    FacetValue,
    Facet,
    FacetFilter,
    FacetedSearchResults,
    DynamicFacetGenerator,
    FacetedSearchEngine
)

# 🔥 Cross-Document Intelligence
from .cross_document_intelligence import (
    SimilarityMetric,
    RelationshipType as CrossDocRelationshipType,
    ClusteringStrategy,
    DocumentSimilarity,
    DocumentCluster,
    CitationNetwork,
    ConflictAnalysis,
    DocumentSimilarityCalculator,
    DocumentClusterAnalyzer,
    CitationNetworkAnalyzer,
    ComplementaryContentFinder,
    ConflictDetector,
    CrossDocumentIntelligenceEngine
)

__all__ = [
    # Knowledge Graph
    "KnowledgeGraph",
    "DocumentKnowledgeGraph", 
    "GraphNode",
    "GraphEdge",
    "RelationshipType",
    "TraversalStrategy",
    "GraphTraverser",
    "GraphBuilder",
    
    # Intent-Aware Adaptive Search
    "IntentType",
    "SearchIntent", 
    "AdaptiveSearchConfig",
    "IntentClassifier",
    "AdaptiveSearchStrategy",
    
    # Topic-Driven Search Chaining
    "ChainStrategy",
    "TopicChainLink",
    "TopicSearchChain", 
    "TopicRelationshipMap",
    "TopicSearchChainGenerator",
    
    # Dynamic Faceted Search Interface
    "FacetType",
    "FacetValue",
    "Facet",
    "FacetFilter",
    "FacetedSearchResults",
    "DynamicFacetGenerator",
    "FacetedSearchEngine",
    
    # Cross-Document Intelligence
    "SimilarityMetric",
    "CrossDocRelationshipType", 
    "ClusteringStrategy",
    "DocumentSimilarity",
    "DocumentCluster",
    "CitationNetwork",
    "ConflictAnalysis",
    "DocumentSimilarityCalculator",
    "DocumentClusterAnalyzer",
    "CitationNetworkAnalyzer",
    "ComplementaryContentFinder",
    "ConflictDetector",
    "CrossDocumentIntelligenceEngine"
] 