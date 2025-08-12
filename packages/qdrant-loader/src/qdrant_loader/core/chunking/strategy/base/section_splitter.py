"""Base class for section splitting strategies."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from qdrant_loader.config import Settings
    from qdrant_loader.core.document import Document


class BaseSectionSplitter(ABC):
    """Base class for section splitting strategies.

    This class defines the interface for splitting document content into sections
    based on different strategies (size-based, semantic, hybrid, etc.).
    Each strategy implements its own splitting logic while following common patterns.
    """

    def __init__(self, settings: "Settings"):
        """Initialize the section splitter.

        Args:
            settings: Configuration settings containing chunking parameters
        """
        self.settings = settings
        self.chunk_size = settings.global_config.chunking.chunk_size
        self.chunk_overlap = settings.global_config.chunking.chunk_overlap
        self.max_chunks_per_document = (
            settings.global_config.chunking.max_chunks_per_document
        )

    @abstractmethod
    def split_sections(
        self, content: str, document: Optional["Document"] = None
    ) -> list[dict[str, Any]]:
        """Split content into sections based on strategy-specific rules.

        This method should split the content into meaningful sections while preserving
        semantic structure and adding relevant metadata to each section.

        Args:
            content: The content to split into sections
            document: Optional document object for additional context

        Returns:
            List of dictionaries containing section content and metadata
            Each dictionary should have at least:
            - "content": The section content
            - "index": Section index
            - Additional strategy-specific metadata

        Raises:
            NotImplementedError: If the splitter doesn't implement this method
        """
        raise NotImplementedError(
            "Section splitter must implement split_sections method"
        )

    def validate_section_size(self, content: str) -> bool:
        """Validate that section content is within acceptable size limits.

        Args:
            content: The section content to validate

        Returns:
            True if section is within limits, False otherwise
        """
        return (
            len(content) <= self.chunk_size * 2
        )  # Allow up to 2x chunk size for sections

    def calculate_split_points(self, content: str, target_size: int) -> list[int]:
        """Calculate optimal split points for content.

        This is a default implementation that finds split points based on
        natural boundaries (sentences, paragraphs). Can be overridden by
        specific splitters for more sophisticated splitting.

        Args:
            content: The content to split
            target_size: Target size for each split

        Returns:
            List of character positions where content should be split
        """
        if len(content) <= target_size:
            return [len(content)]

        split_points = []
        current_pos = 0

        while current_pos < len(content):
            # Find the ideal split position
            ideal_end = min(current_pos + target_size, len(content))

            if ideal_end >= len(content):
                split_points.append(len(content))
                break

            # Look for natural boundaries within a reasonable range
            # Start search a bit before ideal end to find good boundaries
            search_start = max(current_pos + target_size // 2, current_pos + 1)
            search_end = min(ideal_end + target_size // 4, len(content))

            # Ensure search range is valid
            if search_start >= search_end:
                search_start = current_pos + 1
                search_end = ideal_end

            boundary_pos = self._find_natural_boundary(
                content, search_start, search_end
            )

            if boundary_pos > current_pos:
                split_points.append(boundary_pos)
                current_pos = boundary_pos
            else:
                # Fallback to ideal position if no good boundary found
                split_points.append(ideal_end)
                current_pos = ideal_end

        return split_points

    def _find_natural_boundary(self, content: str, start: int, end: int) -> int:
        """Find a natural boundary for splitting within a range.

        Args:
            content: The content to search
            start: Start position to search from
            end: End position to search to

        Returns:
            Position of the best boundary, or start if none found
        """
        # Look for paragraph breaks first (double newline)
        for i in range(end - 1, start - 1, -1):
            if i + 1 < len(content) and content[i : i + 2] == "\n\n":
                return i + 2

        # Look for sentence endings
        sentence_endings = [".", "!", "?"]
        for i in range(end - 1, start - 1, -1):
            if content[i] in sentence_endings and i + 1 < len(content):
                if content[i + 1] in [" ", "\n"]:
                    return i + 1

        # Look for line breaks
        for i in range(end - 1, start - 1, -1):
            if content[i] == "\n":
                return i + 1

        # Look for word boundaries (spaces)
        for i in range(end - 1, start - 1, -1):
            if content[i] == " ":
                return i + 1

        return start

    def create_section_metadata(
        self, content: str, index: int, section_type: str = "content"
    ) -> dict[str, Any]:
        """Create basic metadata for a section.

        Args:
            content: The section content
            index: Section index
            section_type: Type of section (content, header, code, etc.)

        Returns:
            Dictionary containing section metadata
        """
        return {
            "content": content,
            "index": index,
            "section_type": section_type,
            "length": len(content),
            "word_count": len(content.split()),
            "line_count": len(content.split("\n")),
        }

    def split_content_by_size(self, content: str, max_size: int) -> list[str]:
        """Split content into chunks based on size with overlap.

        This is a utility method that can be used by different splitters
        for fallback or hybrid splitting strategies.

        Args:
            content: Content to split
            max_size: Maximum size for each chunk

        Returns:
            List of content chunks
        """
        if len(content) <= max_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            # Calculate end position
            end = min(start + max_size, len(content))

            # Find a good boundary if not at the end
            if end < len(content):
                boundary_pos = self._find_natural_boundary(
                    content, end - max_size // 4, end
                )
                if boundary_pos > start:
                    end = boundary_pos

            chunk = content[start:end]
            chunks.append(chunk)

            # Calculate next start position with overlap
            if end >= len(content):
                break

            advance = max(1, max_size - self.chunk_overlap)
            start += advance

        return chunks
