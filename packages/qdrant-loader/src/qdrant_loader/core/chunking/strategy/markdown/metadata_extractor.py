"""Metadata extraction for markdown chunks."""

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CrossReferenceExtractor:
    """Extracts cross-references from markdown text."""

    @staticmethod
    def extract_cross_references(text: str) -> list[dict[str, str]]:
        """Extract cross-references from text.

        Args:
            text: Text to analyze

        Returns:
            List of cross-references
        """
        # Simple implementation - extract markdown links
        references = []
        lines = text.split("\n")
        for line in lines:
            if "[" in line and "](" in line:
                # Extract link text and URL
                parts = line.split("](")
                if len(parts) == 2:
                    link_text = parts[0].split("[")[1]
                    url = parts[1].split(")")[0]
                    references.append({"text": link_text, "url": url})
        return references


class EntityExtractor:
    """Extracts named entities from markdown text."""

    @staticmethod
    def extract_entities(text: str) -> list[dict[str, str]]:
        """Extract named entities from text.

        Args:
            text: Text to analyze

        Returns:
            List of entities
        """
        # Simple implementation - extract capitalized phrases
        entities = []
        words = text.split()
        current_entity = []

        for word in words:
            if word[0].isupper():
                current_entity.append(word)
            elif current_entity:
                entities.append(
                    {
                        "text": " ".join(current_entity),
                        "type": "UNKNOWN",  # Could be enhanced with NER
                    }
                )
                current_entity = []

        if current_entity:
            entities.append({"text": " ".join(current_entity), "type": "UNKNOWN"})

        return entities


class HierarchyExtractor:
    """Extracts hierarchical relationships from markdown text."""

    @staticmethod
    def map_hierarchical_relationships(text: str) -> dict[str, Any]:
        """Map hierarchical relationships in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary of hierarchical relationships
        """
        hierarchy = {}
        current_path = []

        lines = text.split("\n")
        for line in lines:
            if line.startswith("#"):
                level = len(line.split()[0])
                title = line.lstrip("#").strip()

                # Update current path
                while len(current_path) >= level:
                    current_path.pop()
                current_path.append(title)

                # Add to hierarchy
                current = hierarchy
                for part in current_path[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[current_path[-1]] = {}

        return hierarchy


class TopicAnalyzer:
    """Analyzes topics in markdown text."""

    @staticmethod
    def analyze_topic(text: str) -> dict[str, Any]:
        """Analyze topic of text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with topic analysis results
        """
        # Simple implementation - return basic topic info
        return {
            "topics": ["general"],  # Could be enhanced with LDA
            "coherence": 0.5,  # Could be enhanced with topic coherence metrics
        }


class MetadataExtractor:
    """Main metadata extractor that coordinates all extraction components."""

    def __init__(self):
        """Initialize the metadata extractor."""
        self.cross_reference_extractor = CrossReferenceExtractor()
        self.entity_extractor = EntityExtractor()
        self.hierarchy_extractor = HierarchyExtractor()
        self.topic_analyzer = TopicAnalyzer()

    def extract_all_metadata(self, chunk_content: str, chunk_meta: dict[str, Any]) -> dict[str, Any]:
        """Extract all metadata for a chunk.

        Args:
            chunk_content: The chunk content
            chunk_meta: Existing chunk metadata

        Returns:
            Enhanced metadata dictionary
        """
        metadata = chunk_meta.copy()

        # Extract cross-references
        metadata["cross_references"] = self.cross_reference_extractor.extract_cross_references(
            chunk_content
        )

        # Extract entities
        metadata["entities"] = self.entity_extractor.extract_entities(chunk_content)

        # Extract hierarchical relationships
        metadata["hierarchy"] = self.hierarchy_extractor.map_hierarchical_relationships(
            chunk_content
        )

        # Analyze topics
        metadata["topic_analysis"] = self.topic_analyzer.analyze_topic(chunk_content)

        return metadata

    def extract_section_title(self, chunk: str) -> str:
        """Extract section title from a chunk.

        Args:
            chunk: The text chunk

        Returns:
            Section title or default title
        """
        # Try to find header at the beginning of the chunk
        header_match = re.match(r"^(#{1,6})\s+(.*?)(?:\n|$)", chunk)
        if header_match:
            return header_match.group(2).strip()

        # Try to find the first sentence if no header
        first_sentence_match = re.match(r"^([^\.!?]+[\.!?])", chunk)
        if first_sentence_match:
            title = first_sentence_match.group(1).strip()
            # Truncate if too long
            if len(title) > 50:
                title = title[:50] + "..."
            return title

        return "Untitled Section" 