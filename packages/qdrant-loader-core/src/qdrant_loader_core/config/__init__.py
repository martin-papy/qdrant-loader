"""Shared runtime-config primitives used by both qdrant-loader packages."""

from .capabilities import CollectionVectorCapabilities, parse_collection_capabilities
from .sparse import SparseRuntimeConfig

__all__ = [
    "CollectionVectorCapabilities",
    "SparseRuntimeConfig",
    "parse_collection_capabilities",
]
