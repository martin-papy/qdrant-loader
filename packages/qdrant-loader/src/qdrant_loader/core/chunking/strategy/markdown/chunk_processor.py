"""Chunk processing coordination for markdown strategy."""

import concurrent.futures
from typing import TYPE_CHECKING, Any

import structlog

from qdrant_loader.core.document import Document
from qdrant_loader.core.text_processing.semantic_analyzer import SemanticAnalyzer

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)


class ChunkProcessor:
    """Handles chunk processing coordination including parallel execution and semantic analysis."""

    def __init__(self, settings: "Settings"):
        """Initialize the chunk processor.

        Args:
            settings: Configuration settings
        """
        self.settings = settings

        # Initialize semantic analyzer
        self.semantic_analyzer = SemanticAnalyzer(
            spacy_model=settings.global_config.semantic_analysis.spacy_model,
            num_topics=settings.global_config.semantic_analysis.num_topics,
            passes=settings.global_config.semantic_analysis.lda_passes,
        )

        # Cache for processed chunks to avoid recomputation
        self._processed_chunks: dict[str, dict[str, Any]] = {}

        # Initialize thread pool for parallel processing
        max_workers = settings.global_config.chunking.strategies.markdown.max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def process_chunk(
        self, chunk: str, chunk_index: int, total_chunks: int
    ) -> dict[str, Any]:
        """Process a single chunk in parallel.

        Args:
            chunk: The chunk to process
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks

        Returns:
            Dictionary containing processing results
        """
        logger.debug(
            "Processing chunk",
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_length=len(chunk),
        )

        # Check cache first
        if chunk in self._processed_chunks:
            return self._processed_chunks[chunk]

        # Perform semantic analysis
        logger.debug("Starting semantic analysis for chunk", chunk_index=chunk_index)
        analysis_result = self.semantic_analyzer.analyze_text(
            chunk, doc_id=f"chunk_{chunk_index}"
        )

        # Cache results
        results = {
            "entities": analysis_result.entities,
            "pos_tags": analysis_result.pos_tags,
            "dependencies": analysis_result.dependencies,
            "topics": analysis_result.topics,
            "key_phrases": analysis_result.key_phrases,
            "document_similarity": analysis_result.document_similarity,
        }
        self._processed_chunks[chunk] = results

        logger.debug("Completed semantic analysis for chunk", chunk_index=chunk_index)
        return results

    def create_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        chunk_metadata: dict[str, Any],
        skip_nlp: bool = False,
    ) -> Document:
        """Create a chunk document with enhanced metadata.

        Args:
            original_doc: Original document being chunked
            chunk_content: Content of the chunk
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks
            chunk_metadata: Chunk-specific metadata
            skip_nlp: Whether to skip NLP processing

        Returns:
            Document representing the chunk
        """
        # Create base chunk document
        chunk_doc = Document(
            content=chunk_content,
            title=f"{original_doc.title} - Chunk {chunk_index + 1}",
            source=original_doc.source,
            source_type=original_doc.source_type,
            url=original_doc.url,
            content_type=original_doc.content_type,
            metadata=original_doc.metadata.copy(),
        )

        # 🔥 FIX: Manually assign chunk ID (following pattern from other strategies)
        chunk_doc.id = Document.generate_chunk_id(original_doc.id, chunk_index)

        # Add chunk-specific metadata
        chunk_doc.metadata.update(chunk_metadata)
        chunk_doc.metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "chunk_size": len(chunk_content),
                "parent_document_id": original_doc.id,
                "chunking_strategy": "markdown",
            }
        )

        # Perform semantic analysis if not skipped
        if not skip_nlp:
            semantic_results = self.process_chunk(
                chunk_content, chunk_index, total_chunks
            )
            chunk_doc.metadata.update(semantic_results)

        return chunk_doc

    def estimate_chunk_count(self, content: str) -> int:
        """Estimate the number of chunks that will be generated.

        Args:
            content: The content to estimate chunks for

        Returns:
            int: Estimated number of chunks
        """
        chunk_size = self.settings.global_config.chunking.chunk_size

        # Simple estimation: total chars / chunk_size
        # This is approximate since we split by paragraphs and have overlap
        estimated = len(content) // chunk_size

        # Add some buffer for overlap and paragraph boundaries
        # Apply estimation buffer from configuration
        buffer_factor = (
            1.0
            + self.settings.global_config.chunking.strategies.markdown.estimation_buffer
        )
        estimated = int(estimated * buffer_factor)

        return max(1, estimated)  # At least 1 chunk

    def shutdown(self):
        """Shutdown the thread pool executor and clean up resources."""
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        if hasattr(self, "semantic_analyzer"):
            self.semantic_analyzer.shutdown()  # Use shutdown() instead of clear_cache() for complete cleanup

    def __del__(self):
        """Cleanup on deletion."""
        self.shutdown()
