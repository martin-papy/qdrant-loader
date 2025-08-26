"""
Hybrid Search Implementation - Re-export Module.

This module provides the complete hybrid search functionality through a clean,
modular architecture. The HybridSearchEngine has been extracted to hybrid/engine.py
for better maintainability and testability.

Architecture:
- hybrid.engine: Main HybridSearchEngine implementation
- hybrid.models: Data types and constants
- hybrid.adapters: Component adapters for pipeline integration
- hybrid.pipeline: Modular search pipeline orchestration
"""

# Re-export the HybridSearchEngine from the hybrid package
# Also re-export commonly used types for convenience
from .components import HybridSearchResult
from .enhanced.cross_document_intelligence import ClusteringStrategy, SimilarityMetric
from .enhanced.faceted_search import FacetedSearchResults, FacetFilter
from .enhanced.topic_search_chain import ChainStrategy, TopicSearchChain
from .hybrid.engine import HybridSearchEngine

# Convenient access to the main class for backward compatibility
__all__ = [
    "HybridSearchEngine",
    "HybridSearchResult",
    "ClusteringStrategy",
    "SimilarityMetric",
    "FacetedSearchResults",
    "FacetFilter",
    "ChainStrategy",
    "TopicSearchChain",
]
