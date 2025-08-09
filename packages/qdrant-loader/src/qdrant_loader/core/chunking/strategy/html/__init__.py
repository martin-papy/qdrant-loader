"""HTML strategy package with modular components for HTML document chunking.

This package contains HTML-specific implementations of the chunking strategy components:
- HTMLDocumentParser: Parses HTML DOM structure and semantic elements
- HTMLSectionSplitter: Intelligently splits HTML content based on semantic boundaries
- HTMLMetadataExtractor: Extracts HTML-specific metadata (DOM paths, accessibility, etc.)
- HTMLChunkProcessor: Creates HTML chunk documents with enhanced metadata
"""

from .html_chunk_processor import HTMLChunkProcessor
from .html_document_parser import HTMLDocumentParser
from .html_metadata_extractor import HTMLMetadataExtractor
from .html_section_splitter import HTMLSectionSplitter

__all__ = [
    "HTMLDocumentParser",
    "HTMLSectionSplitter",
    "HTMLMetadataExtractor",
    "HTMLChunkProcessor",
]
