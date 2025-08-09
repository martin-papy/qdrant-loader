"""Code strategy package with modular components for code document chunking.

This package contains code-specific implementations of the chunking strategy components:
- CodeDocumentParser: AST parsing and language detection for code documents
- CodeSectionSplitter: Intelligent code element extraction and merging
- CodeMetadataExtractor: Enhanced code metadata including complexity and dependencies
- CodeChunkProcessor: Creates code chunk documents with programming language context
"""

from .code_chunk_processor import CodeChunkProcessor
from .code_document_parser import CodeDocumentParser
from .code_metadata_extractor import CodeMetadataExtractor
from .code_section_splitter import CodeSectionSplitter

__all__ = [
    "CodeDocumentParser",
    "CodeSectionSplitter",
    "CodeMetadataExtractor",
    "CodeChunkProcessor",
]
