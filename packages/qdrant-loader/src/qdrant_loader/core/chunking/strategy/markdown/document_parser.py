"""Document parsing for markdown chunking strategy."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class SectionType(Enum):
    """Types of sections in a markdown document."""

    HEADER = "header"
    CODE_BLOCK = "code_block"
    LIST = "list"
    TABLE = "table"
    QUOTE = "quote"
    PARAGRAPH = "paragraph"


@dataclass
class Section:
    """Represents a section in a markdown document."""

    content: str
    level: int = 0
    type: SectionType = SectionType.PARAGRAPH
    parent: Optional["Section"] = None
    children: list["Section"] = field(default_factory=list)

    def add_child(self, child: "Section"):
        """Add a child section."""
        self.children.append(child)
        child.parent = self


class SectionIdentifier:
    """Identifies section types based on content patterns."""

    @staticmethod
    def identify_section_type(content: str) -> SectionType:
        """Identify the type of section based on its content.

        Args:
            content: The section content to analyze

        Returns:
            SectionType enum indicating the type of section
        """
        if not content.strip():
            return SectionType.PARAGRAPH

        # Headers: # followed by space
        if re.match(r"^#{1,6}\s+", content):
            return SectionType.HEADER

        # Code blocks: ``` or ~~~ (fenced) or 4+ spaces/tab indentation
        if (
            re.search(r"^```", content, re.MULTILINE)
            or re.search(r"^~~~", content, re.MULTILINE)
            or re.match(r"^    ", content)
            or re.match(r"^\t", content)
        ):
            return SectionType.CODE_BLOCK

        # Lists: -, *, + followed by space, or numbered lists
        if re.match(r"^[*+-]\s+", content) or re.match(r"^\d+[.)]\s+", content):
            return SectionType.LIST

        # Tables: lines with pipes or markdown table format
        if (
            re.search(r"^\|", content, re.MULTILINE)
            or re.search(r"\|.*\|", content)
            or re.search(r"^\s*[-:]+\s*\|\s*[-:]+", content, re.MULTILINE)
        ):
            return SectionType.TABLE

        # Quotes: > followed by space (or end of line)
        if re.match(r"^>\s", content):
            return SectionType.QUOTE

        return SectionType.PARAGRAPH


class HierarchyBuilder:
    """Builds hierarchical section relationships."""

    @staticmethod
    def build_section_breadcrumb(section: Section) -> str:
        """Build a breadcrumb path of section titles to capture hierarchy.

        Args:
            section: The section to build breadcrumb for

        Returns:
            String representing the hierarchical path
        """
        breadcrumb_parts = []
        current = section

        # Walk up the parent chain to build the breadcrumb
        while current.parent:
            header_match = re.match(r"^(#+)\s+(.*?)(?:\n|$)", current.parent.content)
            if header_match:
                parent_title = header_match.group(2).strip()
                breadcrumb_parts.insert(0, parent_title)
            current = current.parent

        # Add current section
        header_match = re.match(r"^(#+)\s+(.*?)(?:\n|$)", section.content)
        if header_match:
            title = header_match.group(2).strip()
            breadcrumb_parts.append(title)

        return " > ".join(breadcrumb_parts)

    @staticmethod
    def get_section_path(
        header_item: dict[str, Any], structure: list[dict[str, Any]]
    ) -> list[str]:
        """Get the path of parent headers for a section.

        Args:
            header_item: The header item
            structure: The document structure

        Returns:
            List of parent section titles
        """
        path = []
        current_level = header_item["level"]

        # Go backward through structure to find parent headers
        for item in reversed(structure[: structure.index(header_item)]):
            if item["type"] == "header" and item["level"] < current_level:
                path.insert(0, item["title"])
                current_level = item["level"]

        return path


class DocumentParser:
    """Parses markdown documents into structured representations."""

    def __init__(self):
        """Initialize the document parser."""
        self.section_identifier = SectionIdentifier()
        self.hierarchy_builder = HierarchyBuilder()

    def parse_document_structure(self, text: str) -> list[dict[str, Any]]:
        """Parse document into a structured representation.

        Args:
            text: The document text

        Returns:
            List of dictionaries representing document elements
        """
        elements = []
        lines = text.split("\n")
        current_block = []
        in_code_block = False

        for line in lines:
            # Check for code block markers
            if line.startswith("```"):
                in_code_block = not in_code_block
                current_block.append(line)
                continue

            # Inside code block, just accumulate lines
            if in_code_block:
                current_block.append(line)
                continue

            # Check for headers
            header_match = re.match(r"^(#{1,6})\s+(.*?)$", line)
            if header_match and not in_code_block:
                # If we have a current block, save it
                if current_block:
                    elements.append(
                        {
                            "type": "content",
                            "text": "\n".join(current_block),
                            "level": 0,
                        }
                    )
                    current_block = []

                # Save the header
                level = len(header_match.group(1))
                elements.append(
                    {
                        "type": "header",
                        "text": line,
                        "level": level,
                        "title": header_match.group(2).strip(),
                    }
                )
            else:
                current_block.append(line)

        # Save the last block if not empty
        if current_block:
            elements.append(
                {"type": "content", "text": "\n".join(current_block), "level": 0}
            )

        return elements

    def extract_section_metadata(self, section: Section) -> dict[str, Any]:
        """Extract metadata from a section.

        Args:
            section: The section to analyze

        Returns:
            Dictionary containing section metadata
        """
        metadata = {
            "type": section.type.value,
            "level": section.level,
            "word_count": len(section.content.split()),
            "char_count": len(section.content),
            "has_code": bool(re.search(r"```", section.content)),
            "has_links": bool(re.search(r"\[.*?\]\(.*?\)", section.content)),
            "has_images": bool(re.search(r"!\[.*?\]\(.*?\)", section.content)),
            "is_top_level": section.level <= 2,  # Mark top-level sections
        }

        # Add parent section info if available
        if section.parent:
            header_match = re.match(r"^(#+)\s+(.*?)(?:\n|$)", section.parent.content)
            if header_match:
                parent_title = header_match.group(2).strip()
                metadata["parent_title"] = parent_title
                metadata["parent_level"] = section.parent.level

                # Add breadcrumb path for hierarchical context
                breadcrumb = self.hierarchy_builder.build_section_breadcrumb(section)
                if breadcrumb:
                    metadata["breadcrumb"] = breadcrumb

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
