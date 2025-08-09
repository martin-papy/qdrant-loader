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

    def __init__(self, settings=None):
        """Initialize the metadata extractor.

        Args:
            settings: Configuration settings containing markdown strategy config
        """
        self.settings = settings
        self.cross_reference_extractor = CrossReferenceExtractor()
        self.entity_extractor = EntityExtractor()
        self.hierarchy_extractor = HierarchyExtractor()
        self.topic_analyzer = TopicAnalyzer()

    def extract_all_metadata(
        self, chunk_content: str, chunk_meta: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract all metadata for a chunk.

        Args:
            chunk_content: The chunk content
            chunk_meta: Existing chunk metadata

        Returns:
            Enhanced metadata dictionary
        """
        metadata = chunk_meta.copy()

        # Extract cross-references
        metadata["cross_references"] = (
            self.cross_reference_extractor.extract_cross_references(chunk_content)
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

    def extract_hierarchical_metadata(
        self, chunk_content: str, chunk_meta: dict[str, Any], document_context
    ) -> dict[str, Any]:
        """Extract rich hierarchical metadata following JIRA pattern.

        Args:
            chunk_content: The chunk content
            chunk_meta: Existing chunk metadata
            document_context: Original document for context

        Returns:
            Enhanced metadata with hierarchical relationships
        """
        metadata = self.extract_all_metadata(chunk_content, chunk_meta)

        # Calculate reading speed from configuration
        words_per_minute = (
            self.settings.global_config.chunking.strategies.markdown.words_per_minute_reading
            if self.settings
            else 200  # Default fallback
        )

        # 🔥 JIRA-style relationship metadata
        metadata.update(
            {
                "parent_document_id": document_context.id,
                "parent_document_title": document_context.title,
                "parent_document_url": document_context.url,
                # Enhanced hierarchical context
                "section_breadcrumb": " > ".join(
                    chunk_meta.get("path", []) + [chunk_meta.get("title", "")]
                ),
                "section_depth": len(chunk_meta.get("path", [])) + 1,
                "section_anchor": self._generate_anchor(chunk_meta.get("title", "")),
                # Content type analysis
                "content_type_analysis": {
                    "has_code_blocks": bool(re.search(r"```", chunk_content)),
                    "has_tables": bool(re.search(r"\|.*\|", chunk_content)),
                    "has_images": bool(re.search(r"!\[.*?\]\(.*?\)", chunk_content)),
                    "has_links": bool(re.search(r"\[.*?\]\(.*?\)", chunk_content)),
                    "word_count": len(chunk_content.split()),
                    "char_count": len(chunk_content),
                    "estimated_read_time": max(
                        1, len(chunk_content.split()) // words_per_minute
                    ),  # minutes
                    "paragraph_count": len(
                        [p for p in chunk_content.split("\n\n") if p.strip()]
                    ),
                },
                # Document hierarchy for search filtering
                "document_hierarchy": chunk_meta.get("path", [])
                + [chunk_meta.get("title", "")],
                # Section type classification
                "section_type": (
                    f"h{chunk_meta.get('level', 0)}"
                    if chunk_meta.get("level", 0) > 0
                    else "content"
                ),
                "section_level": chunk_meta.get("level", 0),
                "section_title": chunk_meta.get("title", ""),
                # Excel-specific metadata
                "is_excel_sheet": chunk_meta.get("is_excel_sheet", False),
                # Navigation hints (to be enhanced by caller with sibling info)
                "has_subsections": False,  # Will be updated by caller
                "total_subsections": 0,  # Will be updated by caller
            }
        )

        return metadata

    def _generate_anchor(self, title: str) -> str:
        """Generate URL anchor from section title.

        Args:
            title: Section title

        Returns:
            URL-safe anchor string
        """
        if not title:
            return ""

        # Convert to lowercase, replace spaces and special chars with hyphens
        anchor = re.sub(r"[^\w\s-]", "", title.lower())
        anchor = re.sub(r"[-\s]+", "-", anchor)
        return anchor.strip("-")

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
