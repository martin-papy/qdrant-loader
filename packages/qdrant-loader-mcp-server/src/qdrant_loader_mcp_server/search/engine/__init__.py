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

# Re-export the main SearchEngine class for backward compatibility
from .core import SearchEngine

__all__ = [
    "SearchEngine",
]
