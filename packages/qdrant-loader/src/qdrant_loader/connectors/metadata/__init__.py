"""Metadata extraction framework for data source connectors.

This module provides a common framework for extracting metadata from various
data sources to enrich the knowledge graph with relationship information.
"""

from .base import BaseMetadataExtractor, MetadataExtractionConfig
from .schemas import (
    AuthorMetadata,
    BaseMetadata,
    CrossReferenceMetadata,
    GitMetadata,
    MetadataCollection,
    RelationshipMetadata,
    TimestampMetadata,
)

__all__ = [
    "BaseMetadataExtractor",
    "MetadataExtractionConfig",
    "BaseMetadata",
    "AuthorMetadata",
    "TimestampMetadata",
    "CrossReferenceMetadata",
    "RelationshipMetadata",
    "GitMetadata",
    "MetadataCollection",
]
