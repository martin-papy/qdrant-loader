"""JSON-specific chunking strategy for structured data using modular architecture."""

import json

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.chunking.strategy.json.json_chunk_processor import (
    JSONChunkProcessor,
)
from qdrant_loader.core.chunking.strategy.json.json_document_parser import (
    JSONDocumentParser,
)
from qdrant_loader.core.chunking.strategy.json.json_metadata_extractor import (
    JSONMetadataExtractor,
)
from qdrant_loader.core.chunking.strategy.json.json_section_splitter import (
    JSONSectionSplitter,
)
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)


class JSONChunkingStrategy(BaseChunkingStrategy):
    """Modern JSON chunking strategy using modular architecture.

    This strategy parses JSON structure and creates chunks based on:
    - Schema-aware structural boundaries
    - Intelligent element grouping and splitting
    - Enhanced metadata extraction with schema inference
    - JSON-specific optimization for NLP processing
    """

    def __init__(self, settings: Settings):
        """Initialize the JSON chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.logger = logger
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Initialize modular components
        self.document_parser = JSONDocumentParser(settings)
        self.section_splitter = JSONSectionSplitter(settings)
        self.metadata_extractor = JSONMetadataExtractor(settings)
        self.chunk_processor = JSONChunkProcessor(settings)

        # JSON-specific configuration
        self.json_config = settings.global_config.chunking.strategies.json_strategy
        self.simple_chunking_threshold = (
            500_000  # Use simple chunking for files larger than 500KB
        )

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a JSON document using modern modular approach.

        Args:
            document: Document to chunk

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

        try:
            # Performance check: for very large files, use simple chunking
            if len(document.content) > self.simple_chunking_threshold:
                self.progress_tracker.log_fallback(
                    document.id, f"Large JSON file ({len(document.content)} bytes)"
                )
                return self._fallback_chunking(document)

            # Step 1: Parse document structure using JSONDocumentParser
            document_structure = self.document_parser.parse_document_structure(
                document.content
            )

            if not document_structure.get("valid_json", False):
                self.progress_tracker.log_fallback(
                    document.id, "Invalid JSON structure"
                )
                return self._fallback_chunking(document)

            # Step 2: Parse JSON into element tree
            root_element = self.document_parser.parse_json_structure(document.content)

            if not root_element:
                self.progress_tracker.log_fallback(document.id, "JSON parsing failed")
                return self._fallback_chunking(document)

            # Step 3: Get elements to chunk
            elements_to_chunk = []
            if root_element.children:
                # Use top-level children as chunks
                elements_to_chunk = root_element.children
            else:
                # Use root element if no children
                elements_to_chunk = [root_element]

            # Step 4: Apply section splitter for grouping and splitting
            final_elements = self.section_splitter.split_json_elements(
                elements_to_chunk
            )

            if not final_elements:
                self.progress_tracker.finish_chunking(document.id, 0, "json")
                return []

            # Step 5: Create chunked documents using chunk processor
            chunked_docs = []
            for i, element in enumerate(final_elements):
                self.logger.debug(
                    f"Processing element {i+1}/{len(final_elements)}",
                    extra={
                        "element_name": element.name,
                        "element_type": element.element_type.value,
                        "content_size": element.size,
                    },
                )

                # Extract element-specific metadata
                element_metadata = (
                    self.metadata_extractor.extract_json_element_metadata(element)
                )

                # Extract hierarchical metadata from content
                hierarchical_metadata = (
                    self.metadata_extractor.extract_hierarchical_metadata(
                        element.content, element_metadata, document
                    )
                )

                # Create chunk document using processor
                chunk_doc = self.chunk_processor.create_json_element_chunk_document(
                    original_doc=document,
                    element=element,
                    chunk_index=i,
                    total_chunks=len(final_elements),
                    element_metadata=hierarchical_metadata,
                )

                chunked_docs.append(chunk_doc)

            # Log completion
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "json"
            )
            self.logger.info(
                f"Successfully chunked JSON document into {len(chunked_docs)} chunks using modular architecture",
                extra={
                    "document_id": document.id,
                    "original_size": len(document.content),
                    "chunks_created": len(chunked_docs),
                    "schema_inference_enabled": self.json_config.enable_schema_inference,
                },
            )

            return chunked_docs

        except Exception as e:
            self.logger.error(
                f"Error chunking JSON document: {e}",
                extra={"document_id": document.id, "error": str(e)},
                exc_info=True,
            )
            self.progress_tracker.log_fallback(document.id, f"Error: {e}")
            return self._fallback_chunking(document)

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Fallback to simple text-based chunking for problematic JSON.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents using simple strategy
        """
        try:
            # Use text-based chunking as fallback
            content = document.content
            chunks = []

            chunk_size = self.settings.global_config.chunking.chunk_size
            overlap = self.settings.global_config.chunking.chunk_overlap

            # Simple chunking by lines to preserve some JSON structure
            lines = content.split("\n")
            current_chunk_lines = []
            current_size = 0
            chunk_index = 0

            for line in lines:
                line_size = len(line) + 1  # +1 for newline

                if current_size + line_size > chunk_size and current_chunk_lines:
                    # Create chunk from current lines
                    chunk_content = "\n".join(current_chunk_lines)

                    # Create basic metadata for fallback chunk
                    fallback_metadata = {
                        "chunk_index": chunk_index,
                        "chunk_size": len(chunk_content),
                        "content_type": "json_fallback",
                        "processing_mode": "fallback",
                        "chunking_strategy": "json_fallback",
                    }

                    chunk_doc = self.chunk_processor.create_chunk_document(
                        original_doc=document,
                        chunk_content=chunk_content,
                        chunk_index=chunk_index,
                        total_chunks=-1,  # Unknown at this point
                        chunk_metadata=fallback_metadata,
                        skip_nlp=True,  # Skip NLP for fallback chunks
                    )

                    chunks.append(chunk_doc)

                    # Setup for next chunk with overlap
                    overlap_lines = (
                        current_chunk_lines[-overlap // 50 :] if overlap > 0 else []
                    )
                    current_chunk_lines = overlap_lines + [line]
                    current_size = sum(
                        len(line_item) + 1 for line_item in current_chunk_lines
                    )
                    chunk_index += 1
                else:
                    current_chunk_lines.append(line)
                    current_size += line_size

            # Add final chunk
            if current_chunk_lines:
                chunk_content = "\n".join(current_chunk_lines)
                fallback_metadata = {
                    "chunk_index": chunk_index,
                    "chunk_size": len(chunk_content),
                    "content_type": "json_fallback",
                    "processing_mode": "fallback",
                    "chunking_strategy": "json_fallback",
                }

                chunk_doc = self.chunk_processor.create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=chunk_index,
                    total_chunks=chunk_index + 1,
                    chunk_metadata=fallback_metadata,
                    skip_nlp=True,
                )
                chunks.append(chunk_doc)

            # Update total_chunks in all chunk metadata
            for chunk in chunks:
                chunk.metadata["total_chunks"] = len(chunks)

            self.logger.warning(
                f"Used fallback chunking for JSON document, created {len(chunks)} chunks",
                extra={"document_id": document.id, "chunks_created": len(chunks)},
            )

            return chunks

        except Exception as e:
            self.logger.error(
                f"Fallback chunking failed: {e}",
                extra={"document_id": document.id, "error": str(e)},
                exc_info=True,
            )
            # Ultimate fallback: return original document as single chunk
            return [document]

    def get_strategy_name(self) -> str:
        """Get the name of this chunking strategy.

        Returns:
            Strategy name
        """
        return "json_modular"

    def supports_document_type(self, document: Document) -> bool:
        """Check if this strategy supports the given document type.

        Args:
            document: Document to check

        Returns:
            True if this strategy can handle the document
        """
        # Check file extension
        if hasattr(document, "source") and document.source:
            if document.source.lower().endswith(".json"):
                return True

        # Check content type metadata
        content_type = document.metadata.get("content_type", "").lower()
        if "json" in content_type:
            return True

        # Try to parse as JSON
        try:
            json.loads(document.content[:1000])  # Test first 1KB
            return True
        except (json.JSONDecodeError, AttributeError):
            return False

    def estimate_chunk_count(self, document: Document) -> int:
        """Estimate the number of chunks this strategy will create.

        Args:
            document: Document to estimate for

        Returns:
            Estimated number of chunks
        """
        try:
            # Quick structure analysis for estimation
            structure = self.document_parser.parse_document_structure(document.content)

            if structure.get("valid_json", False):
                total_elements = structure.get("total_elements", 1)
                complexity_score = structure.get("complexity_score", 1.0)

                # Estimate based on elements and complexity
                estimated_chunks = max(1, int(total_elements * complexity_score / 10))

                # Apply limits
                max_chunks = self.json_config.max_objects_to_process
                return min(estimated_chunks, max_chunks)
            else:
                # Fallback estimation
                return max(
                    1,
                    len(document.content)
                    // self.settings.global_config.chunking.chunk_size,
                )

        except Exception:
            # Ultimate fallback
            return max(
                1,
                len(document.content)
                // self.settings.global_config.chunking.chunk_size,
            )

    def shutdown(self):
        """Clean up resources used by the strategy."""
        # Clean up any cached data
        if hasattr(self, "_processed_chunks"):
            self._processed_chunks.clear()

        # Log shutdown
        self.logger.debug("JSON chunking strategy (modular) shutdown completed")

    def __str__(self) -> str:
        """String representation of the strategy."""
        return f"JSONChunkingStrategy(modular, schema_inference={self.json_config.enable_schema_inference})"

    def __repr__(self) -> str:
        """Detailed string representation of the strategy."""
        return (
            f"JSONChunkingStrategy("
            f"modular=True, "
            f"max_objects={self.json_config.max_objects_to_process}, "
            f"max_chunk_size_for_nlp={self.json_config.max_chunk_size_for_nlp}, "
            f"schema_inference={self.json_config.enable_schema_inference}"
            f")"
        )
