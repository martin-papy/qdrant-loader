"""Code section splitter for intelligent code element extraction and merging."""

from typing import Any

import structlog

from qdrant_loader.core.chunking.strategy.base.section_splitter import (
    BaseSectionSplitter,
)
from qdrant_loader.core.chunking.strategy.code.parser.common import (
    CodeElement,
    CodeElementType,
)
from qdrant_loader.core.document import Document

from .code_document_parser import CodeDocumentParser

logger = structlog.get_logger(__name__)


class CodeSectionSplitter(BaseSectionSplitter):
    """Section splitter for code documents with intelligent element merging."""

    def __init__(self, settings):
        """Initialize the code section splitter.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.logger = logger
        self.document_parser = CodeDocumentParser(settings)

        # Code-specific configuration
        self.code_config = getattr(
            settings.global_config.chunking.strategies, "code", None
        )
        self.chunk_size_threshold = getattr(
            self.code_config, "max_file_size_for_ast", 40000
        )
        self.min_element_size = max(
            100, self.chunk_size // 10
        )  # Minimum size for standalone elements

    def split_sections(
        self, content: str, document: Document = None
    ) -> list[dict[str, Any]]:
        """Split code content into sections based on programming language structure.

        Args:
            content: Source code content
            document: Document being processed (for metadata)

        Returns:
            List of section dictionaries with content and metadata
        """
        if not content.strip():
            return [
                {
                    "content": content,
                    "metadata": {
                        "section_type": "empty",
                        "element_type": "empty",
                        "language": "unknown",
                        "parsing_method": "none",
                    },
                }
            ]

        # Performance check: use simple splitting for very large files
        if len(content) > self.chunk_size_threshold:
            self.logger.info(
                f"Code file too large ({len(content)} bytes), using simple text-based splitting"
            )
            return self._fallback_text_split(content)

        # Detect language from document metadata or filename
        language = "unknown"
        if document:
            file_path = (
                document.metadata.get("file_name")
                or document.source
                or document.title
                or ""
            )
            language = self.document_parser.detect_language(file_path, content)

        # Parse code elements using AST
        elements = self.document_parser.parse_code_elements(content, language)

        if not elements:
            self.logger.debug(f"No {language} elements found, using fallback splitting")
            return self._fallback_text_split(content)

        # Merge small elements to optimize chunk sizes
        merged_elements = self._merge_small_elements(elements)

        # Limit total number of sections
        if len(merged_elements) > self.max_chunks_per_document:
            self.logger.warning(
                f"Too many code elements ({len(merged_elements)}), "
                f"limiting to {self.max_chunks_per_document}"
            )
            merged_elements = merged_elements[: self.max_chunks_per_document]

        # Convert elements to section dictionaries
        sections = []
        for i, element in enumerate(merged_elements):
            section_metadata = self.document_parser.extract_section_metadata(element)
            section_metadata.update(
                {
                    "section_index": i,
                    "language": language,
                    "parsing_method": "ast",
                    "section_type": "code_element",
                }
            )

            sections.append({"content": element.content, "metadata": section_metadata})

        self.logger.debug(
            f"Split {language} code into {len(sections)} sections using AST parsing"
        )

        return sections

    def _merge_small_elements(self, elements: list[CodeElement]) -> list[CodeElement]:
        """Merge small elements to optimize chunk sizes.

        Args:
            elements: List of code elements to merge

        Returns:
            List of merged elements optimized for chunk size
        """
        if not elements:
            return []

        merged = []
        current_group = []
        current_size = 0

        for element in elements:
            element_size = len(element.content)

            # If element is large enough or is a significant code structure, keep it separate
            if (
                element_size >= self.min_element_size
                or element.element_type
                in [
                    CodeElementType.CLASS,
                    CodeElementType.FUNCTION,
                    CodeElementType.INTERFACE,
                    CodeElementType.ENUM,
                ]
                or (
                    element.element_type == CodeElementType.METHOD
                    and element_size > 100
                )
            ):
                # First, add any accumulated small elements
                if current_group:
                    merged_element = self._create_merged_element(current_group)
                    merged.append(merged_element)
                    current_group = []
                    current_size = 0

                # Add the large element
                merged.append(element)
            else:
                # Accumulate small elements
                current_group.append(element)
                current_size += element_size

                # If accumulated size is large enough, create a merged element
                if current_size >= self.min_element_size:
                    merged_element = self._create_merged_element(current_group)
                    merged.append(merged_element)
                    current_group = []
                    current_size = 0

        # Handle remaining small elements
        if current_group:
            merged_element = self._create_merged_element(current_group)
            merged.append(merged_element)

        return merged

    def _create_merged_element(self, elements: list[CodeElement]) -> CodeElement:
        """Create a merged element from a list of small elements.

        Args:
            elements: List of elements to merge

        Returns:
            Merged code element
        """
        if not elements:
            raise ValueError("Cannot merge empty list of elements")

        if len(elements) == 1:
            return elements[0]

        # Create merged element
        merged_content = "\n\n".join(element.content for element in elements)
        merged_names = [element.name for element in elements]

        merged_element = CodeElement(
            name=f"merged_({', '.join(merged_names[:3])}{'...' if len(merged_names) > 3 else ''})",
            element_type=CodeElementType.MODULE,  # Use module as generic container
            content=merged_content,
            start_line=elements[0].start_line,
            end_line=elements[-1].end_line,
            level=min(element.level for element in elements),
        )

        # Merge dependencies
        all_dependencies = []
        for element in elements:
            all_dependencies.extend(element.dependencies)
        merged_element.dependencies = list(set(all_dependencies))

        # Aggregate decorators
        all_decorators = []
        for element in elements:
            all_decorators.extend(element.decorators)
        merged_element.decorators = list(set(all_decorators))

        # Set merged element properties
        merged_element.is_async = any(element.is_async for element in elements)
        merged_element.is_static = any(element.is_static for element in elements)
        merged_element.complexity = sum(element.complexity for element in elements)

        return merged_element

    def _fallback_text_split(self, content: str) -> list[dict[str, Any]]:
        """Fallback to simple text-based splitting for large files or parsing failures.

        Args:
            content: Source code content

        Returns:
            List of section dictionaries
        """
        # Split by functions and classes using simple regex patterns
        import re

        sections = []
        lines = content.split("\n")
        current_section = []
        current_start_line = 1

        # Common patterns for different languages
        function_patterns = [
            r"^\s*(def\s+\w+|function\s+\w+|func\s+\w+)",  # Python, JS, Go
            r"^\s*(public|private|protected)?\s*(static\s+)?\w+\s+\w+\s*\(",  # Java, C#
            r"^\s*class\s+\w+",  # Class definitions
        ]

        pattern = "|".join(function_patterns)

        for i, line in enumerate(lines, 1):
            if re.match(pattern, line) and current_section:
                # Start of a new function/class, save current section
                section_content = "\n".join(current_section)
                if section_content.strip():
                    sections.append(
                        {
                            "content": section_content,
                            "metadata": {
                                "section_type": "code_block",
                                "element_type": "code_block",
                                "start_line": current_start_line,
                                "end_line": i - 1,
                                "line_count": len(current_section),
                                "parsing_method": "regex_fallback",
                                "language": "unknown",
                            },
                        }
                    )

                # Start new section
                current_section = [line]
                current_start_line = i
            else:
                current_section.append(line)

            # Limit section size to prevent overly large chunks
            if len("\n".join(current_section)) > self.chunk_size and current_section:
                section_content = "\n".join(current_section)
                sections.append(
                    {
                        "content": section_content,
                        "metadata": {
                            "section_type": "code_block",
                            "element_type": "code_block",
                            "start_line": current_start_line,
                            "end_line": i,
                            "line_count": len(current_section),
                            "parsing_method": "regex_fallback",
                            "language": "unknown",
                        },
                    }
                )
                current_section = []
                current_start_line = i + 1

        # Add remaining content
        if current_section:
            section_content = "\n".join(current_section)
            if section_content.strip():
                sections.append(
                    {
                        "content": section_content,
                        "metadata": {
                            "section_type": "code_block",
                            "element_type": "code_block",
                            "start_line": current_start_line,
                            "end_line": len(lines),
                            "line_count": len(current_section),
                            "parsing_method": "regex_fallback",
                            "language": "unknown",
                        },
                    }
                )

        # If no sections found, return the entire content as one section
        if not sections:
            sections.append(
                {
                    "content": content,
                    "metadata": {
                        "section_type": "code_block",
                        "element_type": "unknown",
                        "start_line": 1,
                        "end_line": len(lines),
                        "line_count": len(lines),
                        "parsing_method": "fallback_single",
                        "language": "unknown",
                    },
                }
            )

        return sections
