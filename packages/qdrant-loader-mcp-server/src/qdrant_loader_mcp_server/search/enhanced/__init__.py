"""Enhanced search capabilities for Phase 2+ features.

This module contains advanced search intelligence including:
- Knowledge graph construction and traversal
- Intent-aware adaptive search strategies
- Topic-driven search chaining
- Dynamic faceted search interface
- Cross-document relationship analysis
- Multi-hop reasoning capabilities
"""

# 🔥 Cross-Document Intelligence
from .cross_document_intelligence import (
    CitationNetwork,
    CitationNetworkAnalyzer,
    ClusteringStrategy,
    ComplementaryContentFinder,
    ConflictAnalysis,
    ConflictDetector,
    CrossDocumentIntelligenceEngine,
    DocumentCluster,
    DocumentClusterAnalyzer,
    DocumentSimilarity,
    DocumentSimilarityCalculator,
    SimilarityMetric,
)
from .cross_document_intelligence import RelationshipType as CrossDocRelationshipType

# 🔥 Dynamic Faceted Search Interface
from .faceted_search import (
    DynamicFacetGenerator,
    Facet,
    FacetedSearchEngine,
    FacetedSearchResults,
    FacetFilter,
    FacetType,
    FacetValue,
)
from .intent_classifier import (
    AdaptiveSearchConfig,
    AdaptiveSearchStrategy,
    IntentClassifier,
    IntentType,
    SearchIntent,
)
from .knowledge_graph import (
    DocumentKnowledgeGraph,
    GraphBuilder,
    GraphEdge,
    GraphNode,
    GraphTraverser,
    KnowledgeGraph,
    RelationshipType,
    TraversalStrategy,
)

# 🔥 Topic-Driven Search Chaining
from .topic_search_chain import (
    ChainStrategy,
    TopicChainLink,
    TopicRelationshipMap,
    TopicSearchChain,
    TopicSearchChainGenerator,
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
    "CrossDocumentIntelligenceEngine",
]
