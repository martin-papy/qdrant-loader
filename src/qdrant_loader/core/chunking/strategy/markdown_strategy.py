"""Markdown-specific chunking strategy."""

import re
from typing import TYPE_CHECKING

import structlog

from qdrant_loader.core.document import Document
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)


class MarkdownChunkingStrategy(BaseChunkingStrategy):
    """Strategy for chunking markdown documents based on sections.
    
    This strategy splits markdown documents into chunks based on section headers,
    preserving the document structure and hierarchy. Each chunk includes:
    - The section header and its content
    - Parent section headers for context
    - Section-specific metadata
    """

    def __init__(self, settings: "Settings"):
        """Initialize the markdown chunking strategy.

        Args:
            settings: The application settings
        """
        super().__init__(settings)
        self.logger = structlog.get_logger(__name__)

    def _split_text(self, text: str) -> list[str]:
        """Split markdown text into chunks based on section headers.
        
        The strategy:
        1. Identifies all section headers (##, ###, etc.)
        2. Creates chunks that include:
           - The section header
           - All content until the next header of same or higher level
           - Parent section headers for context
        
        Args:
            text: The markdown text to split
            
        Returns:
            List of text chunks, each containing a complete section
        """
        if not text:
            return [""]

        # Split text into lines for processing
        lines = text.splitlines()
        chunks = []
        current_chunk = []
        current_level = 0
        header_stack = []  # Stack to track parent headers

        for line in lines:
            # Check if line is a header
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            
            if header_match:
                header_level = len(header_match.group(1))
                header_text = header_match.group(2)
                
                # If we have a current chunk, save it
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                
                # Update header stack
                while header_stack and header_stack[-1][0] >= header_level:
                    header_stack.pop()
                header_stack.append((header_level, header_text))
                
                # Start new chunk with parent headers for context
                for level, text in header_stack:
                    current_chunk.append(f"{'#' * level} {text}")
                
                current_level = header_level
            else:
                # Add non-header line to current chunk
                current_chunk.append(line)

        # Add the last chunk if it exists
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # If no chunks were created (no headers), return the whole text
        if not chunks:
            return [text]

        logger.debug(
            "Split markdown into chunks",
            total_chunks=len(chunks),
            avg_chunk_size=sum(len(c) for c in chunks) / len(chunks),
        )

        return chunks

    def chunk_document(self, document: Document) -> list[Document]:
        """Split a markdown document into chunks while preserving metadata.

        Args:
            document: The markdown document to chunk

        Returns:
            List of chunked documents with preserved metadata and section information
        """
        chunks = self._split_text(document.content)
        chunked_documents = []

        for i, chunk in enumerate(chunks):
            # Extract section information
            first_line = chunk.splitlines()[0] if chunk else ""
            header_match = re.match(r"^(#{1,6})\s+(.+)$", first_line)
            
            section_metadata = {
                "section_level": len(header_match.group(1)) if header_match else 0,
                "section_title": header_match.group(2) if header_match else "Introduction",
                "is_section_start": True,
            }
            
            # Create chunk document with section metadata
            chunk_doc = self._create_chunk_document(
                original_doc=document,
                chunk_content=chunk,
                chunk_index=i,
                total_chunks=len(chunks)
            )
            
            # Add section-specific metadata
            chunk_doc.metadata.update(section_metadata)
            chunked_documents.append(chunk_doc)

        logger.debug(
            "Chunked markdown document",
            source=document.source,
            total_chunks=len(chunks),
            sections=[d.metadata.get("section_title") for d in chunked_documents],
        )

        return chunked_documents 