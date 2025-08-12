"""Base class for document structure analysis."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class BaseDocumentParser(ABC):
    """Base class for document structure analysis.

    This class defines the interface for parsing document structure and
    extracting metadata from different document types (text, HTML, code, JSON, etc.).
    Each strategy should implement its own document parser based on the specific
    structure and characteristics of the document type.
    """

    @abstractmethod
    def parse_document_structure(self, content: str) -> dict[str, Any]:
        """Parse document structure and extract structural information.

        This method should analyze the document content and return a dictionary
        containing structural information such as:
        - Document type and format
        - Hierarchical structure (sections, headings, etc.)
        - Content statistics (word count, section count, etc.)
        - Structural metadata specific to the document type

        Args:
            content: The document content to analyze

        Returns:
            Dictionary containing structural information about the document

        Raises:
            NotImplementedError: If the parser doesn't implement this method
        """
        raise NotImplementedError(
            "Document parser must implement parse_document_structure method"
        )

    @abstractmethod
    def extract_section_metadata(self, section: Any) -> dict[str, Any]:
        """Extract metadata from a document section.

        This method should extract relevant metadata from a section of the document,
        such as:
        - Section type and level
        - Content characteristics
        - Structural relationships
        - Section-specific metadata

        Args:
            section: The section object to extract metadata from

        Returns:
            Dictionary containing section metadata

        Raises:
            NotImplementedError: If the parser doesn't implement this method
        """
        raise NotImplementedError(
            "Document parser must implement extract_section_metadata method"
        )

    def extract_section_title(self, content: str) -> str:
        """Extract section title from content.

        This is a default implementation that can be overridden by specific parsers
        to provide better title extraction based on document type.

        Args:
            content: The section content

        Returns:
            Extracted section title or empty string if none found
        """
        lines = content.strip().split("\n")
        if lines:
            # Return first non-empty line as title
            for line in lines:
                if line.strip():
                    return line.strip()[:100]  # Limit title length
        return ""

    def analyze_content_characteristics(self, content: str) -> dict[str, Any]:
        """Analyze general content characteristics.

        This method provides basic content analysis that can be used by all parsers
        and extended by specific implementations.

        Args:
            content: The content to analyze

        Returns:
            Dictionary containing content characteristics
        """
        lines = content.split("\n")
        words = content.split()

        return {
            "line_count": len(lines),
            "word_count": len(words),
            "character_count": len(content),
            "non_empty_line_count": len([line for line in lines if line.strip()]),
            "avg_line_length": (
                sum(len(line) for line in lines) / len(lines) if lines else 0
            ),
            "avg_word_length": (
                sum(len(word) for word in words) / len(words) if words else 0
            ),
            "has_unicode": any(ord(char) > 127 for char in content),
        }
