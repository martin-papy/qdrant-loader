"""Cross-Document Intelligence (CDI) subpackage.

This package hosts extracted models, interfaces, utilities, and the pipeline
scaffolding for cross-document intelligence. The initial extraction focuses on
value types and contracts only, with no behavioral changes.
"""

from .models import (
    CitationNetwork,
    ClusteringStrategy,
    ComplementaryContent,
    ConflictAnalysis,
    DocumentCluster,
    DocumentSimilarity,
    RelationshipType,
    SimilarityMetric,
)

__all__ = [
    "SimilarityMetric",
    "ClusteringStrategy",
    "RelationshipType",
    "DocumentSimilarity",
    "DocumentCluster",
    "CitationNetwork",
    "ComplementaryContent",
    "ConflictAnalysis",
]
