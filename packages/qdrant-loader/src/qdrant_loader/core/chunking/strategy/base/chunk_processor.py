"""Base class for chunk processing and analysis coordination."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qdrant_loader.config import Settings
    from qdrant_loader.core.document import Document


class BaseChunkProcessor(ABC):
    """Base class for chunk processing and analysis coordination.

    This class defines the interface for processing chunks, coordinating
    semantic analysis, and creating final chunk documents. Each strategy
    implements its own chunk processing logic while following common patterns.
    """

    def __init__(self, settings: "Settings"):
        """Initialize the chunk processor.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.chunk_size = settings.global_config.chunking.chunk_size
        self.max_chunks_per_document = (
            settings.global_config.chunking.max_chunks_per_document
        )

    @abstractmethod
    def create_chunk_document(
        self,
        original_doc: "Document",
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        chunk_metadata: dict[str, Any],
        skip_nlp: bool = False,
    ) -> "Document":
        """Create a document for a chunk with all necessary metadata and processing.

        This method should:
        1. Create a new Document instance for the chunk
        2. Apply semantic analysis if not skipped
        3. Add chunk-specific metadata (index, total chunks, etc.)
        4. Preserve original document metadata
        5. Generate unique chunk ID

        Args:
            original_doc: The original document being chunked
            chunk_content: The content of this chunk
            chunk_index: Index of this chunk (0-based)
            total_chunks: Total number of chunks
            chunk_metadata: Metadata specific to this chunk
            skip_nlp: Whether to skip semantic analysis for this chunk

        Returns:
            Document instance representing the chunk

        Raises:
            NotImplementedError: If the processor doesn't implement this method
        """
        raise NotImplementedError(
            "Chunk processor must implement create_chunk_document method"
        )

    def estimate_chunk_count(self, content: str) -> int:
        """Estimate the number of chunks that will be created from content.

        This is a utility method that provides a rough estimate of chunk count
        based on content size and chunk configuration.

        Args:
            content: The content to estimate chunks for

        Returns:
            Estimated number of chunks
        """
        if not content:
            return 0

        content_size = len(content)
        if content_size <= self.chunk_size:
            return 1

        # Account for overlap in estimation
        effective_chunk_size = max(
            1, self.chunk_size - self.settings.global_config.chunking.chunk_overlap
        )
        estimated = max(
            1, (content_size + effective_chunk_size - 1) // effective_chunk_size
        )

        # Cap at maximum allowed chunks
        return min(estimated, self.max_chunks_per_document)

    def generate_chunk_id(self, original_doc: "Document", chunk_index: int) -> str:
        """Generate a unique ID for a chunk.

        Args:
            original_doc: The original document
            chunk_index: Index of the chunk

        Returns:
            Unique chunk ID
        """
        import uuid

        # Create deterministic chunk ID based on original doc ID and chunk index
        base_id = f"{original_doc.id}_chunk_{chunk_index}"
        # Generate UUID5 for consistency
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, base_id))

    def create_base_chunk_metadata(
        self,
        original_doc: "Document",
        chunk_index: int,
        total_chunks: int,
        chunk_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Create base metadata that all chunks should have.

        Args:
            original_doc: The original document
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            chunk_metadata: Strategy-specific chunk metadata

        Returns:
            Combined metadata dictionary
        """
        # Start with original document metadata
        base_metadata = original_doc.metadata.copy()

        # Add chunk-specific metadata
        base_metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "is_chunk": True,
                "parent_document_id": original_doc.id,
                "chunk_creation_timestamp": self._get_current_timestamp(),
                "chunking_strategy": self._get_strategy_name(),
            }
        )

        # Merge with strategy-specific metadata
        base_metadata.update(chunk_metadata)

        return base_metadata

    def validate_chunk_content(self, content: str) -> bool:
        """Validate that chunk content meets quality requirements.

        Args:
            content: The chunk content to validate

        Returns:
            True if content is valid, False otherwise
        """
        if not content or not content.strip():
            return False

        # Check minimum content length
        if len(content.strip()) < 10:
            return False

        # Check maximum content length (safety check)
        if len(content) > self.chunk_size * 3:  # Allow up to 3x chunk size
            return False

        return True

    def should_skip_semantic_analysis(
        self, content: str, chunk_metadata: dict[str, Any]
    ) -> bool:
        """Determine if semantic analysis should be skipped for this chunk.

        This method provides default heuristics for when to skip expensive
        semantic analysis operations. Can be overridden by specific processors.

        Args:
            content: The chunk content
            chunk_metadata: Chunk metadata

        Returns:
            True if semantic analysis should be skipped
        """
        # Skip for very short content
        if len(content) < 100:
            return True

        # Skip for content with too few words
        if len(content.split()) < 20:
            return True

        # Skip for very simple structure
        if content.count("\n") < 3:
            return True

        # Skip if explicitly marked in metadata
        if chunk_metadata.get("skip_semantic_analysis", False):
            return True

        return False

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format.

        Returns:
            ISO formatted timestamp string
        """
        from datetime import datetime

        return datetime.now().isoformat()

    def _get_strategy_name(self) -> str:
        """Get the name of the chunking strategy.

        This should be overridden by specific processors to return
        the appropriate strategy name.

        Returns:
            Strategy name string
        """
        return self.__class__.__name__.replace("ChunkProcessor", "").lower()

    def calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content pieces.

        This is a utility method that can be used for overlap detection
        or duplicate content identification.

        Args:
            content1: First content piece
            content2: Second content piece

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Handle empty content cases
        if not content1 and not content2:
            return 1.0  # Both empty = identical

        if not content1 or not content2:
            return 0.0  # One empty, one not = different

        # Simple word-based similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 and not words2:
            return 1.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def optimize_chunk_boundaries(self, chunks: list[str]) -> list[str]:
        """Optimize chunk boundaries to improve content flow.

        This is a utility method that can be used by processors to
        post-process chunks and improve their boundaries.

        Args:
            chunks: List of chunk content strings

        Returns:
            Optimized list of chunks
        """
        if len(chunks) <= 1:
            return chunks

        optimized = []
        for i, chunk in enumerate(chunks):
            # Remove leading/trailing whitespace
            chunk = chunk.strip()

            # Skip empty chunks
            if not chunk:
                continue

            # Try to fix broken sentences at boundaries
            if i > 0 and optimized:
                # Check if this chunk starts with a lowercase word
                # indicating it might be a continuation
                words = chunk.split()
                if words and words[0][0].islower():
                    # Look for a good spot to move content to previous chunk
                    sentence_end = chunk.find(". ")
                    if sentence_end > 0 and sentence_end < len(chunk) // 2:
                        # Move the first sentence to previous chunk
                        optimized[-1] += " " + chunk[: sentence_end + 1]
                        chunk = chunk[sentence_end + 2 :].strip()

            if chunk:  # Only add non-empty chunks
                optimized.append(chunk)

        return optimized

    def shutdown(self):
        """Shutdown the processor and clean up resources.

        This method should be called when the processor is no longer needed
        to clean up any resources (thread pools, connections, etc.).
        """
        # Default implementation - can be overridden by specific processors
        # Null out any optional resource handles if present to avoid leaks
        if hasattr(self, "_resources"):
            try:
                resources = self._resources  # type: ignore[attr-defined]
                if resources and hasattr(resources, "shutdown"):
                    resources.shutdown()  # type: ignore[attr-defined]
            except Exception:
                # Best-effort cleanup in base implementation
                pass
            finally:
                self._resources = None  # type: ignore[attr-defined]

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except Exception:
            # Ignore errors during cleanup
            pass
