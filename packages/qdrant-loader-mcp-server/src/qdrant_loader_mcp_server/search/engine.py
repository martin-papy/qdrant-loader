"""
Search Engine Service - Re-export Module.

This module provides comprehensive search engine functionality through a clean,
modular architecture. The main SearchEngine class and its operations have been
extracted to the 'engine' sub-package for better maintainability and testability.

Architecture:
- engine.core: Main SearchEngine class with lifecycle management
- engine.search: Basic search operations
- engine.topic_chain: Topic-driven search chain functionality
- engine.faceted: Faceted search and suggestion capabilities
- engine.intelligence: Cross-document intelligence and analysis
- engine.strategies: Search strategy selection and optimization
"""

# Re-export the main SearchEngine class for backward compatibility
# Also re-export commonly used types for convenience
from .components.search_result_models import HybridSearchResult
from .engine.core import SearchEngine
from .enhanced.cdi import ClusteringStrategy, SimilarityMetric
from .enhanced.topic_search_chain import ChainStrategy, TopicSearchChain

__all__ = [
    "SearchEngine",
    "HybridSearchResult",
    "ClusteringStrategy",
    "SimilarityMetric",
    "ChainStrategy",
    "TopicSearchChain",
]
