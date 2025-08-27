"""
Cross-Document Intelligence - Re-export Module.

This module provides comprehensive cross-document relationship analysis through
a clean, modular architecture. The core components have been extracted to the
'cdi' sub-package for better maintainability and testability.

Key Features:
- Document similarity calculation using entity/topic/metadata overlap
- Intelligent document clustering based on shared concepts
- Citation network analysis from cross-references and hierarchical data
- Complementary content recommendation using knowledge graph
- Conflict detection between documents
- Cross-project relationship discovery
"""

# Re-export the main classes for convenience and backward compatibility
# Avoid importing engine here to prevent cyclic imports with CDI extractors
from .cdi.analyzers import DocumentClusterAnalyzer
from .cdi.calculators import DocumentSimilarityCalculator
from .cdi.citations import CitationNetworkAnalyzer
from .cdi.detectors import ConflictDetector
from .cdi.engine import CrossDocumentIntelligenceEngine
from .cdi.finders import ComplementaryContentFinder
from .cdi.models import (
    CitationNetwork,
    ClusteringStrategy,
    ComplementaryContent,
    ConflictAnalysis,
    DocumentCluster,
    DocumentSimilarity,
    RelationshipType,
    SimilarityMetric,
)

# Re-export NetworkX for test compatibility
try:
    import networkx as nx
except ImportError:
    nx = None  # Handle cases where NetworkX is not available

__all__ = [
    # Main Engine
    "CrossDocumentIntelligenceEngine",
    # Core Analysis Components
    "DocumentSimilarityCalculator",
    "DocumentClusterAnalyzer",
    "CitationNetworkAnalyzer",
    "ComplementaryContentFinder",
    "ConflictDetector",
    # Data Models and Enums
    "SimilarityMetric",
    "ClusteringStrategy",
    "RelationshipType",
    "DocumentSimilarity",
    "DocumentCluster",
    "CitationNetwork",
    "ComplementaryContent",
    "ConflictAnalysis",
    # External Dependencies (for test compatibility)
    "nx",
]
