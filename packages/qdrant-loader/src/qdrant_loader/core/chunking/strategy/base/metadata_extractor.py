"""Base class for metadata extraction from document chunks."""

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qdrant_loader.core.document import Document


class BaseMetadataExtractor(ABC):
    """Base class for metadata extraction from document chunks.

    This class defines the interface for extracting rich metadata from chunks
    including hierarchical relationships, entities, cross-references, and
    semantic information. Each strategy implements its own metadata extraction
    logic based on the document type.
    """

    @abstractmethod
    def extract_hierarchical_metadata(
        self, content: str, chunk_metadata: dict[str, Any], document: "Document"
    ) -> dict[str, Any]:
        """Extract hierarchical metadata from chunk content.

        This method should analyze the chunk content and enrich the existing
        metadata with hierarchical information such as:
        - Document structure relationships
        - Section breadcrumbs and navigation
        - Parent-child relationships
        - Cross-references and links

        Args:
            content: The chunk content to analyze
            chunk_metadata: Existing chunk metadata to enrich
            document: The source document for context

        Returns:
            Enriched metadata dictionary with hierarchical information

        Raises:
            NotImplementedError: If the extractor doesn't implement this method
        """
        raise NotImplementedError(
            "Metadata extractor must implement extract_hierarchical_metadata method"
        )

    @abstractmethod
    def extract_entities(self, text: str) -> list[str]:
        """Extract entities from text content.

        This method should identify and extract relevant entities from the text
        such as names, places, organizations, technical terms, etc. The specific
        types of entities extracted depend on the document type and domain.

        Args:
            text: The text to extract entities from

        Returns:
            List of extracted entities

        Raises:
            NotImplementedError: If the extractor doesn't implement this method
        """
        raise NotImplementedError(
            "Metadata extractor must implement extract_entities method"
        )

    def extract_cross_references(self, text: str) -> list[dict[str, Any]]:
        """Extract cross-references from text content.

        This is a default implementation that can be overridden by specific
        extractors to provide better cross-reference extraction based on
        document type (e.g., markdown links, code imports, etc.).

        Args:
            text: The text to extract cross-references from

        Returns:
            List of cross-reference dictionaries
        """
        # Basic implementation - look for common reference patterns
        cross_refs = []

        # Look for simple references like "see Section X", "Chapter Y", etc.
        import re

        # Pattern for section references
        section_pattern = r"(?i)\b(?:see|refer to)\s+(?:section|chapter|part|appendix)\s+([A-Z0-9]+(?:\.[0-9]+)*)\b"
        section_matches = re.finditer(section_pattern, text)
        for match in section_matches:
            cross_refs.append(
                {
                    "type": "section_reference",
                    "reference": match.group(1),
                    "context": match.group(0),
                    "position": match.start(),
                }
            )

        # Additional pattern for standalone section references
        standalone_pattern = (
            r"(?i)\b(section|chapter|part|appendix)\s+([A-Z0-9]+(?:\.[0-9]+)*)\b"
        )
        standalone_matches = re.finditer(standalone_pattern, text)
        for match in standalone_matches:
            cross_refs.append(
                {
                    "type": "section_reference",
                    "reference": match.group(2),
                    "context": match.group(0),
                    "position": match.start(),
                }
            )

        # Pattern for figure/table references
        figure_pattern = r"(?i)\b(?:figure|fig|table|tbl)\s+([A-Z0-9]+(?:\.[0-9]+)*)\b"
        figure_matches = re.finditer(figure_pattern, text)
        for match in figure_matches:
            cross_refs.append(
                {
                    "type": "figure_reference",
                    "reference": match.group(1),
                    "context": match.group(0),
                    "position": match.start(),
                }
            )

        return cross_refs

    def analyze_content_type(self, content: str) -> dict[str, Any]:
        """Analyze the type and characteristics of the content.

        Args:
            content: The content to analyze

        Returns:
            Dictionary containing content type analysis
        """
        content.lower()

        # Basic content type indicators
        analysis = {
            "has_code": bool(
                re.search(r"```|def |class |function|import |#include", content)
            ),
            "has_math": bool(re.search(r"\$.*\$|\\[a-zA-Z]+|∑|∫|∆", content)),
            "has_lists": bool(
                re.search(r"^\s*[-*+]\s|^\s*\d+\.\s", content, re.MULTILINE)
            ),
            "has_headers": bool(
                re.search(r"^\s*#+\s|^={3,}|^-{3,}", content, re.MULTILINE)
            ),
            "has_links": bool(
                re.search(r"https?://|www\.|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
            ),
            "has_tables": bool(re.search(r"\|.*\|.*\|", content)),
            "has_quotes": bool(re.search(r"^>", content, re.MULTILINE)),
            "primary_language": self._detect_primary_language(content),
        }

        # Calculate content complexity score
        complexity_score = 0
        if analysis["has_code"]:
            complexity_score += 2
        if analysis["has_math"]:
            complexity_score += 2
        if analysis["has_tables"]:
            complexity_score += 1
        if analysis["has_lists"]:
            complexity_score += 1
        if analysis["has_headers"]:
            complexity_score += 1

        analysis["complexity_score"] = complexity_score
        analysis["content_category"] = self._categorize_content(analysis)

        return analysis

    def _detect_primary_language(self, content: str) -> str:
        """Detect the primary language of the content.

        This is a basic implementation that can be enhanced with
        proper language detection libraries.

        Args:
            content: The content to analyze

        Returns:
            Detected language code (defaults to 'en')
        """
        # Basic language detection based on common words
        # This could be enhanced with proper language detection libraries

        content_lower = content.lower()
        # Extract words using regex to remove punctuation
        words = re.findall(r"\b[a-zA-Z]+\b", content_lower)

        if not words:
            return "unknown"

        # Count common English words (need to be whole words)
        english_words = ["the", "and", "of", "to", "a", "in", "is", "it", "you", "that"]
        english_count = sum(1 for word in words if word in english_words)

        # Need at least 10% English words to consider it English
        if len(words) > 0 and english_count / len(words) >= 0.10:
            return "en"

        return "unknown"

    def _categorize_content(self, analysis: dict[str, Any]) -> str:
        """Categorize content based on analysis results.

        Args:
            analysis: Content analysis results

        Returns:
            Content category string
        """
        if analysis["has_code"]:
            return "technical"
        elif analysis["has_math"]:
            return "academic"
        elif analysis["has_tables"] and analysis["has_headers"]:
            return "structured"
        elif analysis["has_lists"]:
            return "informational"
        else:
            return "narrative"

    def extract_keyword_density(self, text: str, top_n: int = 10) -> dict[str, float]:
        """Extract keyword density information from text.

        Args:
            text: The text to analyze
            top_n: Number of top keywords to return

        Returns:
            Dictionary mapping keywords to their density scores
        """
        import re
        from collections import Counter

        # Clean and tokenize text
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "over",  # Add 'over' to stop words
        }

        # Filter words
        filtered_words = [
            word for word in words if len(word) > 2 and word not in stop_words
        ]

        # Calculate frequencies
        word_counts = Counter(filtered_words)
        total_words = len(filtered_words)

        # Calculate density and return top keywords
        if total_words == 0:
            return {}

        keyword_density = {}
        for word, count in word_counts.most_common(top_n):
            keyword_density[word] = count / total_words

        return keyword_density

    def create_breadcrumb_metadata(
        self, current_section: str, parent_sections: list[str]
    ) -> dict[str, Any]:
        """Create breadcrumb metadata for hierarchical navigation.

        Args:
            current_section: Current section title
            parent_sections: List of parent section titles (from root to immediate parent)

        Returns:
            Dictionary containing breadcrumb metadata
        """
        breadcrumb_path = (
            parent_sections + [current_section] if current_section else parent_sections
        )

        return {
            "breadcrumb_path": breadcrumb_path,
            "breadcrumb_string": " > ".join(breadcrumb_path),
            "section_depth": len(breadcrumb_path),
            "parent_section": parent_sections[-1] if parent_sections else None,
            "root_section": breadcrumb_path[0] if breadcrumb_path else None,
        }
