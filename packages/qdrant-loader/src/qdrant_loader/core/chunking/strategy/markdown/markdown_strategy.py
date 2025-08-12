"""Refactored Markdown-specific chunking strategy using modular architecture."""

from typing import TYPE_CHECKING

import structlog

from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document

from .chunk_processor import ChunkProcessor
from .document_parser import DocumentParser
from .metadata_extractor import MetadataExtractor
from .section_splitter import SectionSplitter

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
    - Semantic analysis results

    The strategy uses a modular architecture with focused components:
    - DocumentParser: Handles document structure analysis
    - SectionSplitter: Manages different splitting strategies
    - MetadataExtractor: Enriches chunks with metadata
    - ChunkProcessor: Coordinates parallel processing and semantic analysis
    """

    def __init__(self, settings: "Settings"):
        """Initialize the Markdown chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Initialize modular components
        self.document_parser = DocumentParser()
        self.section_splitter = SectionSplitter(settings)
        self.metadata_extractor = MetadataExtractor(settings)
        self.chunk_processor = ChunkProcessor(settings)

        # Apply any chunk overlap that was set before components were initialized
        if hasattr(self, "_chunk_overlap"):
            self.chunk_overlap = self._chunk_overlap

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a markdown document into semantic sections.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents
        """
        file_name = (
            document.metadata.get("file_name")
            or document.metadata.get("original_filename")
            or document.title
            or f"{document.source_type}:{document.source}"
        )

        # Start progress tracking
        self.progress_tracker.start_chunking(
            document.id,
            document.source,
            document.source_type,
            len(document.content),
            file_name,
        )

        # Provide user guidance on expected chunk count
        estimated_chunks = self.chunk_processor.estimate_chunk_count(document.content)
        logger.info(
            f"Processing document: {document.title} ({len(document.content):,} chars)",
            extra={
                "estimated_chunks": estimated_chunks,
                "chunk_size": self.settings.global_config.chunking.chunk_size,
                "max_chunks_allowed": self.settings.global_config.chunking.max_chunks_per_document,
            },
        )

        try:
            # Split text into semantic chunks using the section splitter
            logger.debug("Splitting document into sections")
            chunks_metadata = self.section_splitter.split_sections(
                document.content, document
            )

            if not chunks_metadata:
                self.progress_tracker.finish_chunking(document.id, 0, "markdown")
                return []

            # Apply configuration-driven safety limit
            max_chunks = self.settings.global_config.chunking.max_chunks_per_document
            if len(chunks_metadata) > max_chunks:
                logger.warning(
                    f"Document generated {len(chunks_metadata)} chunks, limiting to {max_chunks} per config. "
                    f"Consider increasing max_chunks_per_document in config or using larger chunk_size. "
                    f"Document: {document.title}"
                )
                chunks_metadata = chunks_metadata[:max_chunks]

            # Create chunk documents
            chunked_docs = []
            for i, chunk_meta in enumerate(chunks_metadata):
                chunk_content = chunk_meta["content"]
                logger.debug(
                    f"Processing chunk {i+1}/{len(chunks_metadata)}",
                    extra={
                        "chunk_size": len(chunk_content),
                        "section_type": chunk_meta.get("section_type", "unknown"),
                        "level": chunk_meta.get("level", 0),
                    },
                )

                # Extract section title
                section_title = chunk_meta.get("title")
                if not section_title:
                    section_title = self.document_parser.extract_section_title(
                        chunk_content
                    )
                chunk_meta["section_title"] = section_title

                # 🔥 ENHANCED: Use hierarchical metadata extraction
                enriched_metadata = (
                    self.metadata_extractor.extract_hierarchical_metadata(
                        chunk_content, chunk_meta, document
                    )
                )

                # Create chunk document using the chunk processor
                # 🔥 FIX: Skip NLP for small documents or documents that might cause LDA issues
                markdown_config = (
                    self.settings.global_config.chunking.strategies.markdown
                )
                skip_nlp = (
                    len(chunk_content) < markdown_config.min_content_length_for_nlp
                    or len(chunk_content.split())
                    < markdown_config.min_word_count_for_nlp
                    or chunk_content.count("\n")
                    < markdown_config.min_line_count_for_nlp
                )
                chunk_doc = self.chunk_processor.create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=i,
                    total_chunks=len(chunks_metadata),
                    chunk_metadata=enriched_metadata,
                    skip_nlp=skip_nlp,
                )

                logger.debug(
                    "Created chunk document",
                    extra={
                        "chunk_id": chunk_doc.id,
                        "chunk_size": len(chunk_content),
                        "metadata_keys": list(chunk_doc.metadata.keys()),
                    },
                )

                chunked_docs.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "markdown"
            )

            logger.info(
                f"Markdown chunking completed for document: {document.title}",
                extra={
                    "document_id": document.id,
                    "total_chunks": len(chunked_docs),
                    "document_size": len(document.content),
                    "avg_chunk_size": (
                        sum(len(d.content) for d in chunked_docs) // len(chunked_docs)
                        if chunked_docs
                        else 0
                    ),
                },
            )

            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            # Fallback to default chunking
            self.progress_tracker.log_fallback(
                document.id, f"Markdown parsing failed: {str(e)}"
            )
            return self._fallback_chunking(document)

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Simple fallback chunking when the main strategy fails.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        logger.info("Using fallback chunking strategy for document")

        # Use the fallback splitter from section splitter
        chunks = self.section_splitter.fallback_splitter.split_content(
            document.content, self.settings.global_config.chunking.chunk_size
        )

        # Create chunked documents
        chunked_docs = []
        for i, chunk_content in enumerate(chunks):
            chunk_doc = self.chunk_processor.create_chunk_document(
                original_doc=document,
                chunk_content=chunk_content,
                chunk_index=i,
                total_chunks=len(chunks),
                chunk_metadata={"chunking_strategy": "fallback"},
                skip_nlp=True,  # Skip NLP for fallback mode
            )
            chunked_docs.append(chunk_doc)

        return chunked_docs

    @property
    def chunk_overlap(self):
        """Get chunk overlap setting."""
        if hasattr(self, "section_splitter"):
            return self.section_splitter.standard_splitter.chunk_overlap
        return getattr(self, "_chunk_overlap", 200)

    @chunk_overlap.setter
    def chunk_overlap(self, value):
        """Set chunk overlap setting."""
        # Store the value for when components are initialized
        self._chunk_overlap = value

        if hasattr(self, "section_splitter"):
            self.section_splitter.standard_splitter.chunk_overlap = value
            self.section_splitter.excel_splitter.chunk_overlap = value
            self.section_splitter.fallback_splitter.chunk_overlap = value

    def shutdown(self):
        """Shutdown all components and clean up resources."""
        if hasattr(self, "chunk_processor"):
            self.chunk_processor.shutdown()

    def __del__(self):
        """Cleanup on deletion."""
        self.shutdown()
