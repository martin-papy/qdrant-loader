"""HTML-specific section splitter for semantic boundary-based chunking."""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.section_splitter import (
    BaseSectionSplitter,
)
from qdrant_loader.core.document import Document

from .html_document_parser import HTMLDocumentParser, SectionType


class HTMLSectionSplitter(BaseSectionSplitter):
    """Section splitter for HTML documents with semantic boundary detection."""

    def __init__(self, settings: Settings):
        super().__init__(settings)

        # Get strategy-specific configuration
        self.html_config = settings.global_config.chunking.strategies.html
        self.simple_parsing_threshold = self.html_config.simple_parsing_threshold
        self.max_html_size_for_parsing = self.html_config.max_html_size_for_parsing
        self.preserve_semantic_structure = self.html_config.preserve_semantic_structure

        # Initialize HTML document parser for semantic analysis
        self.document_parser = HTMLDocumentParser()

        # Performance limits
        self.max_sections_to_process = 200
        self.max_recursion_depth = 10

    def split_sections(
        self, content: str, document: Document | None = None
    ) -> list[dict[str, Any]]:
        """Split HTML content into semantic sections."""
        if not content.strip():
            return []

        # Performance check: use simple parsing for very large files
        if len(content) > self.max_html_size_for_parsing:
            return self._simple_html_split(content)

        try:
            # Use semantic parsing for manageable files
            if (
                len(content) <= self.simple_parsing_threshold
                and self.preserve_semantic_structure
            ):
                sections = self._semantic_html_split(content)
            else:
                sections = self._simple_html_split(content)

            if not sections:
                return self._fallback_split(content)

            # Merge small sections and split large ones
            merged_sections = self._merge_small_sections(sections)
            final_sections = self._split_large_sections(merged_sections)

            return final_sections[: self.max_chunks_per_document]

        except Exception:
            # Fallback to simple text-based splitting
            return self._fallback_split(content)

    def _semantic_html_split(self, content: str) -> list[dict[str, Any]]:
        """Split HTML using semantic structure analysis."""
        try:
            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements for cleaner processing
            for script in soup(["script", "style"]):
                script.decompose()

            sections = []
            section_count = 0

            def process_element(element, level=0, parent_path=""):
                nonlocal section_count

                # Performance limits
                if section_count >= self.max_sections_to_process:
                    return
                if level > self.max_recursion_depth:
                    return

                if isinstance(element, Tag):
                    tag_name = element.name.lower()

                    # Check if this is a meaningful semantic element
                    if self._is_meaningful_element(element, tag_name):
                        text_content = element.get_text(strip=True)

                        # Skip empty or very small sections
                        if len(text_content) < 10:
                            return

                        # Build DOM path for context
                        current_path = (
                            f"{parent_path}/{tag_name}" if parent_path else tag_name
                        )
                        if element.get("id"):
                            current_path += f"#{element.get('id')}"
                        elif element.get("class"):
                            classes = " ".join(element.get("class", []))
                            current_path += f".{classes.replace(' ', '.')}"

                        # Extract section metadata
                        section_metadata = (
                            self.document_parser.extract_section_metadata(element)
                        )

                        # Add HTML-specific context
                        section_metadata.update(
                            {
                                "content": str(element),
                                "dom_path": current_path,
                                "depth_level": level,
                                "parent_path": parent_path,
                                "text_content": text_content,
                                "element_position": section_count,
                            }
                        )

                        sections.append(section_metadata)
                        section_count += 1

                        # Don't process children of certain container elements to avoid duplication
                        if tag_name in self.document_parser.section_elements:
                            return

                # Process children with depth limit
                if hasattr(element, "children") and level < self.max_recursion_depth:
                    for child in element.children:
                        process_element(
                            child,
                            level + 1,
                            current_path if isinstance(element, Tag) else parent_path,
                        )

            # Start processing from body or root
            body = soup.find("body")
            if body:
                process_element(body)
            else:
                process_element(soup)

            return sections

        except Exception:
            # Fallback to simple parsing
            return self._simple_html_split(content)

    def _simple_html_split(self, content: str) -> list[dict[str, Any]]:
        """Simple HTML splitting for large files or when semantic parsing fails."""
        try:
            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get clean text
            text = soup.get_text(separator="\n", strip=True)

            # Split into chunks by size
            sections = []
            chunks = self._split_text_by_size(text, self.chunk_size)

            for i, chunk in enumerate(chunks):
                section = {
                    "content": chunk,
                    "text_content": chunk,
                    "tag_name": "div",
                    "section_type": SectionType.DIV.value,
                    "level": 0,
                    "attributes": {},
                    "dom_path": f"body/div[{i}]",
                    "depth_level": 1,
                    "parent_path": "body",
                    "element_position": i,
                    "word_count": len(chunk.split()),
                    "char_count": len(chunk),
                    "parsing_method": "simple",
                }
                sections.append(section)

            return sections

        except Exception:
            return self._fallback_split(content)

    def _fallback_split(self, content: str) -> list[dict[str, Any]]:
        """Ultimate fallback: treat as plain text."""
        chunks = self._split_text_by_size(content, self.chunk_size)

        sections = []
        for i, chunk in enumerate(chunks):
            section = {
                "content": chunk,
                "text_content": chunk,
                "tag_name": "div",
                "section_type": SectionType.DIV.value,
                "level": 0,
                "attributes": {},
                "dom_path": f"fallback/div[{i}]",
                "depth_level": 0,
                "parent_path": "",
                "element_position": i,
                "word_count": len(chunk.split()),
                "char_count": len(chunk),
                "parsing_method": "fallback",
            }
            sections.append(section)

        return sections

    def _is_meaningful_element(self, element: Tag, tag_name: str) -> bool:
        """Check if an HTML element is meaningful for chunking."""
        # Always include semantic HTML5 elements
        if tag_name in self.document_parser.section_elements:
            return True

        # Include headings
        if tag_name in self.document_parser.heading_elements:
            return True

        # Include block-level content elements
        if tag_name in self.document_parser.block_elements:
            return True

        # Include elements with meaningful content
        text_content = element.get_text(strip=True)
        if len(text_content) >= 50:  # Minimum meaningful content
            return True

        # Include elements with specific roles or IDs
        if element.get("role") or element.get("id"):
            return True

        return False

    def _merge_small_sections(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge small adjacent sections for better chunk utilization."""
        if not sections:
            return []

        merged = []
        current_group = []
        current_size = 0
        min_section_size = 100  # Minimum size for standalone sections

        for section in sections:
            section_size = len(section.get("text_content", ""))

            # Large sections or important semantic elements should stand alone
            if (
                section_size >= min_section_size
                or section.get("tag_name") in self.document_parser.section_elements
                or section.get("tag_name") in self.document_parser.heading_elements
            ):
                # First, process any accumulated small sections
                if current_group:
                    merged_section = self._create_merged_section(current_group)
                    merged.append(merged_section)
                    current_group = []
                    current_size = 0

                # Add the large/important section
                merged.append(section)
            else:
                # Accumulate small sections
                current_group.append(section)
                current_size += section_size

                # If accumulated size is sufficient, create a merged section
                if current_size >= min_section_size:
                    merged_section = self._create_merged_section(current_group)
                    merged.append(merged_section)
                    current_group = []
                    current_size = 0

        # Handle remaining small sections
        if current_group:
            merged_section = self._create_merged_section(current_group)
            merged.append(merged_section)

        return merged

    def _create_merged_section(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        """Create a merged section from multiple small sections."""
        if not sections:
            return {}

        if len(sections) == 1:
            return sections[0]

        # Merge content and metadata
        merged_content = "\n\n".join(section.get("content", "") for section in sections)
        merged_text = "\n\n".join(
            section.get("text_content", "") for section in sections
        )

        # Build combined DOM path
        paths = [section.get("dom_path", "") for section in sections]
        merged_path = f"merged[{','.join(paths[:3])}{'...' if len(paths) > 3 else ''}]"

        # Use the first section as base and update
        merged_section = sections[0].copy()
        merged_section.update(
            {
                "content": merged_content,
                "text_content": merged_text,
                "tag_name": "div",  # Generic container
                "section_type": SectionType.DIV.value,
                "dom_path": merged_path,
                "word_count": len(merged_text.split()),
                "char_count": len(merged_text),
                "merged_sections_count": len(sections),
                "is_merged": True,
            }
        )

        return merged_section

    def _split_large_sections(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Split sections that are too large into smaller parts."""
        final_sections = []

        for section in sections:
            content_size = len(section.get("content", ""))

            if content_size > self.chunk_size:
                # Split large sections
                split_parts = self._split_large_content(
                    section.get("content", ""), self.chunk_size
                )

                for i, part in enumerate(split_parts):
                    split_section = section.copy()
                    split_section.update(
                        {
                            "content": part,
                            "text_content": self._extract_text_from_html(part),
                            "dom_path": f"{section.get('dom_path', 'unknown')}[part-{i+1}]",
                            "word_count": len(part.split()),
                            "char_count": len(part),
                            "is_split": True,
                            "split_part": i + 1,
                            "total_split_parts": len(split_parts),
                        }
                    )
                    final_sections.append(split_section)
            else:
                final_sections.append(section)

        return final_sections

    def _split_large_content(self, content: str, max_size: int) -> list[str]:
        """Split large HTML content while preserving structure where possible."""
        if len(content) <= max_size:
            return [content]

        try:
            # Try to split by HTML structure first
            soup = BeautifulSoup(content, "html.parser")
            parts = []
            current_part = ""

            # Process top-level elements
            for element in soup.children:
                element_str = str(element)

                if len(current_part) + len(element_str) <= max_size:
                    current_part += element_str
                else:
                    if current_part:
                        parts.append(current_part)
                    current_part = element_str

                    # If single element is too large, split it by text
                    if len(current_part) > max_size:
                        text_parts = self._split_text_by_size(current_part, max_size)
                        parts.extend(text_parts[:-1])  # Add all but last
                        current_part = text_parts[-1] if text_parts else ""

                # Limit number of parts
                if len(parts) >= 10:
                    break

            if current_part:
                parts.append(current_part)

            return parts

        except Exception:
            # Fallback to simple text splitting
            return self._split_text_by_size(content, max_size)

    def _split_text_by_size(self, text: str, max_size: int) -> list[str]:
        """Split text by size with word boundaries."""
        if len(text) <= max_size:
            return [text]

        parts = []
        current_part = ""

        # Split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", text)

        for para in paragraphs:
            if len(current_part) + len(para) + 2 <= max_size:  # +2 for \n\n
                current_part += para + "\n\n"
            else:
                if current_part:
                    parts.append(current_part.strip())

                # If single paragraph is too large, split by sentences
                if len(para) > max_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    current_part = ""

                    for sentence in sentences:
                        if len(current_part) + len(sentence) + 1 <= max_size:
                            current_part += sentence + " "
                        else:
                            if current_part:
                                parts.append(current_part.strip())
                            current_part = sentence + " "
                else:
                    current_part = para + "\n\n"

                # Limit number of parts
                if len(parts) >= 20:
                    break

        if current_part:
            parts.append(current_part.strip())

        return parts

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            # Fallback: remove HTML tags with regex
            text = re.sub(r"<[^>]+>", "", html_content)
            return re.sub(r"\s+", " ", text).strip()
