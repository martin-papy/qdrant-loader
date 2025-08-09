"""HTML-specific chunking strategy with modular architecture."""

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document

from .html import (
    HTMLChunkProcessor,
    HTMLDocumentParser,
    HTMLMetadataExtractor,
    HTMLSectionSplitter,
)

logger = structlog.get_logger(__name__)


class HTMLChunkingStrategy(BaseChunkingStrategy):
    """Strategy for chunking HTML documents using modular architecture.

    This strategy leverages HTML-specific components for intelligent document processing:
    - HTMLDocumentParser: Analyzes HTML DOM structure and semantic elements
    - HTMLSectionSplitter: Splits content based on semantic boundaries
    - HTMLMetadataExtractor: Extracts HTML-specific metadata and accessibility features
    - HTMLChunkProcessor: Creates enhanced chunk documents with DOM context

    The strategy preserves HTML semantic structure while providing intelligent
    fallbacks for large or malformed documents.
    """

    def __init__(self, settings: Settings):
        """Initialize the HTML chunking strategy with modular components.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.logger = logger
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Initialize HTML-specific modular components
        self.document_parser = HTMLDocumentParser()
        self.section_splitter = HTMLSectionSplitter(settings)
        self.metadata_extractor = HTMLMetadataExtractor()
        self.chunk_processor = HTMLChunkProcessor(settings)

        # Get configuration settings
        self.html_config = settings.global_config.chunking.strategies.html
        self.max_html_size_for_parsing = self.html_config.max_html_size_for_parsing

        self.logger.info(
            "HTMLChunkingStrategy initialized with modular architecture",
            extra={
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "max_html_size_for_parsing": self.max_html_size_for_parsing,
                "preserve_semantic_structure": self.html_config.preserve_semantic_structure,
            },
        )

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk an HTML document using modular architecture.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents with enhanced HTML metadata
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

        try:
            # Check for very large files that should use fallback chunking
            if len(document.content) > self.max_html_size_for_parsing:
                self.logger.info(
                    f"HTML file too large ({len(document.content)} bytes), using fallback chunking"
                )
                self.progress_tracker.log_fallback(
                    document.id, f"Large HTML file ({len(document.content)} bytes)"
                )
                return self._fallback_chunking(document)

            # Parse document structure for analysis
            self.logger.debug("Analyzing HTML document structure")
            document_structure = self.document_parser.parse_document_structure(
                document.content
            )

            # Split content into semantic sections
            self.logger.debug("Splitting HTML content into sections")
            sections = self.section_splitter.split_sections(document.content, document)

            if not sections:
                self.progress_tracker.finish_chunking(document.id, 0, "html_modular")
                return []

            # Create chunk documents using modular processor
            chunked_docs = []
            for i, section in enumerate(sections):
                chunk_content = section["content"]
                self.logger.debug(
                    f"Processing HTML section {i+1}/{len(sections)}",
                    extra={
                        "chunk_size": len(chunk_content),
                        "section_type": section.get("section_type", "unknown"),
                        "tag_name": section.get("tag_name", "unknown"),
                        "dom_path": section.get("dom_path", "unknown"),
                    },
                )

                # Create chunk document using the modular chunk processor
                chunk_doc = self.chunk_processor.create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_metadata=section,
                    chunk_index=i,
                    total_chunks=len(sections),
                    skip_nlp=False,  # Let the processor decide based on content analysis
                )

                # Add document structure context to metadata
                chunk_doc.metadata["document_structure"] = document_structure
                chunk_doc.metadata["chunking_strategy"] = "html_modular"

                chunked_docs.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "html_modular"
            )

            self.logger.info(
                "Successfully chunked HTML document with modular architecture",
                extra={
                    "document_id": document.id,
                    "total_chunks": len(chunked_docs),
                    "document_structure_type": document_structure.get(
                        "structure_type", "unknown"
                    ),
                    "has_semantic_elements": len(
                        document_structure.get("semantic_elements", [])
                    )
                    > 0,
                    "accessibility_features": len(
                        document_structure.get("accessibility_features", {})
                    )
                    > 0,
                },
            )

            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            self.logger.error(
                "HTML chunking failed, using fallback strategy",
                extra={"document_id": document.id, "error": str(e)},
            )
            # Fallback to simple chunking
            self.progress_tracker.log_fallback(
                document.id, f"HTML parsing failed: {str(e)}"
            )
            return self._fallback_chunking(document)

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Simple fallback chunking when the main strategy fails.

        This method provides a robust fallback by using the section splitter's
        fallback mechanism and basic chunk processing.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.info("Using fallback chunking strategy for HTML document")

        try:
            # Use section splitter's fallback mechanism
            sections = self.section_splitter._fallback_split(document.content)

            if not sections:
                # Ultimate fallback: single chunk
                return self._create_single_chunk_fallback(document)

            # Create chunked documents using basic processing
            chunked_docs = []
            for i, section in enumerate(sections):
                chunk_content = section["content"]

                # Validate chunk content
                if not chunk_content or not chunk_content.strip():
                    self.logger.warning(f"Skipping empty fallback chunk {i+1}")
                    continue

                # Create simple chunk document
                chunk_doc = self.chunk_processor.create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_metadata=section,
                    chunk_index=i,
                    total_chunks=len(sections),
                    skip_nlp=True,  # Skip NLP for fallback chunks
                )

                # Mark as fallback chunking
                chunk_doc.metadata.update(
                    {
                        "chunking_strategy": "html_fallback",
                        "chunking_method": "fallback_modular",
                    }
                )

                chunked_docs.append(chunk_doc)

            return chunked_docs

        except Exception as e:
            self.logger.error(f"Fallback chunking failed: {e}")
            return self._create_single_chunk_fallback(document)

    def _create_single_chunk_fallback(self, document: Document) -> list[Document]:
        """Ultimate fallback: return original document as single chunk.

        Args:
            document: Document to return as single chunk

        Returns:
            List containing single chunk document
        """
        try:
            # Create single chunk with minimal processing
            chunk_doc = Document(
                content=document.content,
                metadata=document.metadata.copy(),
                source=document.source,
                source_type=document.source_type,
                url=document.url,
                title=document.title,
                content_type=document.content_type,
            )

            chunk_doc.id = Document.generate_chunk_id(document.id, 0)
            chunk_doc.metadata.update(
                {
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "parent_document_id": document.id,
                    "chunking_strategy": "html_single_fallback",
                    "chunking_method": "fallback_single",
                    "entities": [],
                    "nlp_skipped": True,
                    "skip_reason": "fallback_error",
                    "content_type": "html",
                }
            )

            return [chunk_doc]

        except Exception as e:
            self.logger.error(f"Single chunk fallback failed: {e}")
            # If even this fails, return empty list
            return []

    def __del__(self):
        """Cleanup method."""
        # Call shutdown to clean up resources
        self.shutdown()

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks using the section splitter.

        This method implements the abstract method from BaseChunkingStrategy
        for backward compatibility, though the main chunking is handled by
        the modular chunk_document method.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        try:
            # Use the section splitter to split the text
            sections = self.section_splitter.split_sections(text)
            return [section.get("content", "") for section in sections]
        except Exception as e:
            self.logger.warning(f"Text splitting failed, using fallback: {e}")
            # Fallback to simple text splitting
            return [text]

    def shutdown(self):
        """Shutdown the strategy and clean up resources."""
        # Clean up any cached data from components
        if hasattr(self, "section_splitter"):
            # Section splitter cleanup if needed
            pass

        if hasattr(self, "chunk_processor"):
            # Chunk processor cleanup if needed
            pass

        self.logger.debug("HTMLChunkingStrategy shutdown completed")
