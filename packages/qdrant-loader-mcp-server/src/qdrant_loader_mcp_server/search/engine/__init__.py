"""
Search Engine Package - Modular Search Architecture.

This package provides a comprehensive search engine through modular components:
- core: Core engine lifecycle and configuration management
- search: Main search operations and query processing
- topic_chain: Topic-driven search chain functionality
- faceted: Faceted search and suggestion capabilities
- intelligence: Cross-document intelligence and analysis
- strategies: Search strategy selection and optimization
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Re-export the main SearchEngine class for backward compatibility
from ..hybrid_search import HybridSearchEngine
from .core import SearchEngine

# Lazy re-exports for backward compatibility (only imported when accessed)
if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient

    AsyncOpenAI = None  # type: ignore[assignment]

__all__ = [
    "SearchEngine",
    "HybridSearchEngine",
]


def __getattr__(name: str):
    """Lazy import for backward compatibility."""
    if name == "AsyncQdrantClient":
        from qdrant_client import AsyncQdrantClient

        return AsyncQdrantClient
    if name == "AsyncOpenAI":
        # Return None as it was in core.py
        return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
