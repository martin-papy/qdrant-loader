"""Default chunking strategy for text documents using modular architecture.

This strategy uses intelligent text-based chunking with enhanced metadata extraction.
It follows the modern modular architecture pattern established in MarkdownChunkingStrategy,
using specialized text-processing components for optimal text document handling.
"""

from typing import TYPE_CHECKING

import structlog

from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document

from .default import (
    TextChunkProcessor,
    TextDocumentParser,
    TextMetadataExtractor,
    TextSectionSplitter,
)

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)


class DefaultChunkingStrategy(BaseChunkingStrategy):
    """Modern default text chunking strategy using modular architecture.

    This strategy intelligently splits text documents into chunks while preserving
    semantic meaning and structure. Each chunk includes:
    - Intelligent text analysis and boundaries
    - Enhanced metadata with text-specific features
    - Content quality metrics and readability analysis
    - Semantic analysis results when appropriate

    The strategy uses a modular architecture with focused components:
    - TextDocumentParser: Handles text structure analysis
    - TextSectionSplitter: Manages intelligent text splitting strategies
    - TextMetadataExtractor: Enriches chunks with comprehensive text metadata
    - TextChunkProcessor: Coordinates processing and semantic analysis
    """

    def __init__(self, settings: "Settings"):
        """Initialize the default chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Initialize modular components
        self.document_parser = TextDocumentParser()
        self.section_splitter = TextSectionSplitter(settings)
        self.metadata_extractor = TextMetadataExtractor()
        self.chunk_processor = TextChunkProcessor(settings)

        # Give section splitter access to tokenizer
        self.section_splitter._parent_strategy = self

        # Apply any chunk overlap that was set before components were initialized
        if hasattr(self, "_chunk_overlap"):
            self.chunk_overlap = self._chunk_overlap

        # Log configuration for debugging
        logger.info(
            "DefaultChunkingStrategy initialized with modular architecture",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            tokenizer=self.tokenizer,
            has_encoding=self.encoding is not None,
            chunking_method="intelligent_text_processing",
        )

        # Warn about suspiciously small chunk sizes
        if self.chunk_size < 100:
            logger.warning(
                f"Very small chunk_size detected: {self.chunk_size} characters. "
                f"This may cause performance issues and excessive chunking. "
                f"Consider using a larger value (e.g., 1000-1500 characters)."
            )

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a text document into intelligent semantic sections.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents with enhanced metadata
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
            # Parse document structure and split into sections
            logger.debug("Analyzing document structure and splitting into sections")
            document_structure = self.document_parser.parse_document_structure(
                document.content
            )
            chunks_metadata = self.section_splitter.split_sections(
                document.content, document
            )

            if not chunks_metadata:
                self.progress_tracker.finish_chunking(document.id, 0, "default")
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
                        "section_type": chunk_meta.get("section_type", "text"),
                        "word_count": chunk_meta.get("word_count", 0),
                    },
                )

                # Add document structure info to chunk metadata
                chunk_meta.update(
                    {
                        "document_structure": document_structure,
                        "chunking_strategy": "default_modular",
                    }
                )

                # Enhanced: Use hierarchical metadata extraction
                enriched_metadata = (
                    self.metadata_extractor.extract_hierarchical_metadata(
                        chunk_content, chunk_meta, document
                    )
                )

                # Create chunk document using the chunk processor
                # Skip NLP for small documents or documents that might cause LDA issues
                skip_nlp = self.chunk_processor.should_skip_semantic_analysis(
                    chunk_content, enriched_metadata
                )

                chunk_doc = self.chunk_processor.create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=i,
                    total_chunks=len(chunks_metadata),
                    chunk_metadata=enriched_metadata,
                    skip_nlp=skip_nlp,
                )

                chunked_docs.append(chunk_doc)

                # Update progress
                self.progress_tracker.update_progress(document.id, i + 1)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "default"
            )

            logger.info(
                "Successfully chunked document with modular architecture",
                document_id=document.id,
                num_chunks=len(chunked_docs),
                strategy="default_modular",
                avg_chunk_size=(
                    sum(len(doc.content) for doc in chunked_docs) // len(chunked_docs)
                    if chunked_docs
                    else 0
                ),
            )

            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            logger.error(
                "Error chunking document with modular architecture",
                document_id=document.id,
                error=str(e),
                exc_info=True,
            )
            raise

    def shutdown(self):
        """Clean up resources used by the strategy."""
        logger.debug("Shutting down DefaultChunkingStrategy")
        try:
            # Clean up modular components
            if hasattr(self, "chunk_processor") and hasattr(
                self.chunk_processor, "shutdown"
            ):
                self.chunk_processor.shutdown()
        except Exception as e:
            logger.warning(f"Error during DefaultChunkingStrategy shutdown: {e}")

    def __del__(self):
        """Ensure cleanup on deletion."""
        try:
            self.shutdown()
        except Exception:
            # Ignore errors during cleanup in destructor
            pass
