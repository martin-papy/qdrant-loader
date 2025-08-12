"""Base components for modular chunking strategy architecture.

This package contains abstract base classes that define the interface for
the modular components used in chunking strategies.
"""

from .chunk_processor import BaseChunkProcessor
from .document_parser import BaseDocumentParser
from .metadata_extractor import BaseMetadataExtractor
from .section_splitter import BaseSectionSplitter

__all__ = [
    "BaseDocumentParser",
    "BaseSectionSplitter",
    "BaseMetadataExtractor",
    "BaseChunkProcessor",
]
