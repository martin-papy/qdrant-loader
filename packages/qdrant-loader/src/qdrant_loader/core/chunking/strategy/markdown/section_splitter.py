"""Section splitting strategies for markdown chunking."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

# Re-export classes and local dependencies at top to satisfy E402
from .document_parser import DocumentParser, HierarchyBuilder  # noqa: F401
from .splitters.base import BaseSplitter  # re-export base class  # noqa: F401
from .splitters.excel import ExcelSplitter  # re-export  # noqa: F401
from .splitters.fallback import FallbackSplitter  # re-export  # noqa: F401
from .splitters.standard import StandardSplitter  # re-export  # noqa: F401

logger = structlog.get_logger(__name__)


# Markdown configuration placeholder - can be imported from settings if needed
class MarkdownConfig:
    """Configuration for markdown processing."""

    words_per_minute_reading = 200


markdown_config = MarkdownConfig()


@dataclass
class HeaderAnalysis:
    """Analysis of header distribution in a document."""

    h1: int = 0
    h2: int = 0
    h3: int = 0
    h4: int = 0
    h5: int = 0
    h6: int = 0
    total_headers: int = 0
    content_length: int = 0
    avg_section_size: int = 0

    def __post_init__(self):
        """Calculate derived metrics."""
        self.total_headers = self.h1 + self.h2 + self.h3 + self.h4 + self.h5 + self.h6
        if self.total_headers > 0:
            self.avg_section_size = self.content_length // self.total_headers


@dataclass
class SectionMetadata:
    """Enhanced section metadata with hierarchical relationships."""

    title: str
    level: int
    content: str
    order: int
    start_line: int
    end_line: int
    parent_section: str = None
    breadcrumb: str = ""
    anchor: str = ""
    previous_section: str = None
    next_section: str = None
    sibling_sections: list[str] = None
    subsections: list[str] = None
    content_analysis: dict = None

    def __post_init__(self):
        """Initialize default values."""
        if self.sibling_sections is None:
            self.sibling_sections = []
        if self.subsections is None:
            self.subsections = []
        if self.content_analysis is None:
            self.content_analysis = {}
        if not self.anchor:
            self.anchor = self._generate_anchor()

    def _generate_anchor(self) -> str:
        """Generate URL anchor from title."""
        import re

        # Convert title to lowercase, replace spaces and special chars with hyphens
        anchor = re.sub(r"[^\w\s-]", "", self.title.lower())
        anchor = re.sub(r"[-\s]+", "-", anchor)
        return anchor.strip("-")


class SectionSplitter:
    """Main section splitter that coordinates different splitting strategies."""

    def __init__(self, settings: "Settings"):
        """Initialize the section splitter.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.standard_splitter = StandardSplitter(settings)
        self.excel_splitter = ExcelSplitter(settings)
        self.fallback_splitter = FallbackSplitter(settings)

    def analyze_header_distribution(self, text: str) -> HeaderAnalysis:
        """Analyze header distribution to guide splitting decisions.

        Args:
            text: Document content to analyze

        Returns:
            HeaderAnalysis with distribution metrics
        """
        analysis = HeaderAnalysis()
        analysis.content_length = len(text)

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            header_match = re.match(r"^(#{1,6})\s+(.+)", line)
            if header_match:
                level = len(header_match.group(1))
                if level == 1:
                    analysis.h1 += 1
                elif level == 2:
                    analysis.h2 += 1
                elif level == 3:
                    analysis.h3 += 1
                elif level == 4:
                    analysis.h4 += 1
                elif level == 5:
                    analysis.h5 += 1
                elif level == 6:
                    analysis.h6 += 1

        # Let __post_init__ calculate derived metrics
        analysis.__post_init__()

        logger.debug(
            "Header distribution analysis",
            extra={
                "h1": analysis.h1,
                "h2": analysis.h2,
                "h3": analysis.h3,
                "total_headers": analysis.total_headers,
                "content_length": analysis.content_length,
                "avg_section_size": analysis.avg_section_size,
            },
        )

        return analysis

    def determine_optimal_split_levels(self, text: str, document=None) -> set[int]:
        """Intelligently determine optimal split levels based on document characteristics.

        Args:
            text: Document content
            document: Optional document for context

        Returns:
            Set of header levels to split on
        """
        header_analysis = self.analyze_header_distribution(text)

        # Check if this is a converted Excel file
        is_converted_excel = (
            document and document.metadata.get("original_file_type") == "xlsx"
        )

        if is_converted_excel:
            # Excel files: H1 (document) + H2 (sheets) + potentially H3 for large sheets
            if header_analysis.h3 > 10:
                return {1, 2, 3}
            else:
                return {1, 2}

        # Get configured thresholds
        markdown_config = self.settings.global_config.chunking.strategies.markdown
        h1_threshold = markdown_config.header_analysis_threshold_h1
        h3_threshold = markdown_config.header_analysis_threshold_h3

        # Regular markdown: Intelligent granularity based on structure
        if header_analysis.h1 <= 1 and header_analysis.h2 >= h1_threshold:
            # Single H1 with multiple H2s - the common case requiring granular splitting!
            logger.info(
                "Detected single H1 with multiple H2 sections - applying granular splitting",
                extra={
                    "h1_count": header_analysis.h1,
                    "h2_count": header_analysis.h2,
                    "h3_count": header_analysis.h3,
                },
            )
            # Split on H2 and H3 if there are many H3s
            if header_analysis.h3 >= h3_threshold:
                return {1, 2, 3}
            else:
                return {1, 2}
        elif header_analysis.h1 >= h1_threshold:
            # Multiple H1s - keep traditional splitting to avoid over-fragmentation
            logger.info(
                "Multiple H1 sections detected - using traditional H1-only splitting",
                extra={"h1_count": header_analysis.h1},
            )
            return {1}
        elif (
            header_analysis.h1 == 0
            and header_analysis.h2 == 0
            and header_analysis.h3 >= 1
        ):
            # 🔥 FIX: Converted documents often have only H3+ headers
            logger.info(
                "Detected document with H3+ headers only (likely converted DOCX) - applying H3+ splitting",
                extra={
                    "h1_count": header_analysis.h1,
                    "h2_count": header_analysis.h2,
                    "h3_count": header_analysis.h3,
                    "h4_count": header_analysis.h4,
                    "total_headers": header_analysis.total_headers,
                },
            )
            # 🔥 ENHANCED: Intelligent H3/H4 splitting based on document structure
            if header_analysis.h3 == 1 and header_analysis.h4 >= h1_threshold:
                # Single H3 with multiple H4s (common DOCX pattern) - split on both
                return {3, 4}
            elif header_analysis.h3 >= h1_threshold:
                # Multiple H3s - split on H3 primarily, H4 if many
                if header_analysis.h4 >= h3_threshold:
                    return {3, 4}
                else:
                    return {3}
            elif header_analysis.total_headers >= h3_threshold:
                # Many headers total - split on H3 and H4
                return {3, 4}
            else:
                # Default - split on H3 only
                return {3}
        elif header_analysis.total_headers <= 3:
            # Very small document - minimal splitting
            logger.info(
                "Small document detected - minimal splitting",
                extra={"total_headers": header_analysis.total_headers},
            )
            return {1, 2}
        else:
            # Default case - moderate granularity
            return {1, 2}

    def build_enhanced_section_metadata(
        self, sections: list[dict]
    ) -> list[SectionMetadata]:
        """Build enhanced section metadata with hierarchical relationships.

        Args:
            sections: Basic section data from split_sections

        Returns:
            List of enhanced SectionMetadata objects
        """
        enhanced_sections: list[SectionMetadata] = []

        for i, section in enumerate(sections):
            breadcrumb_parts = section.get("path", [])
            if section.get("title"):
                breadcrumb_parts = breadcrumb_parts + [section["title"]]
            breadcrumb = " > ".join(breadcrumb_parts)

            parent_section = None
            if section.get("path"):
                parent_section = section["path"][-1]

            current_level = section.get("level", 0)
            current_path = section.get("path", [])
            sibling_sections: list[str] = []

            for other_section in sections:
                if (
                    other_section != section
                    and other_section.get("level") == current_level
                    and other_section.get("path", []) == current_path
                ):
                    sibling_sections.append(other_section.get("title", ""))

            previous_section = sections[i - 1].get("title") if i > 0 else None
            next_section = (
                sections[i + 1].get("title") if i < len(sections) - 1 else None
            )

            subsections: list[str] = []
            current_title = section.get("title", "")
            for other_section in sections[i + 1 :]:
                other_path = other_section.get("path", [])
                if len(other_path) > len(current_path) and other_path[
                    :-1
                ] == current_path + [current_title]:
                    subsections.append(other_section.get("title", ""))
                elif len(other_path) <= len(current_path):
                    break

            content = section.get("content", "")
            content_analysis = {
                "has_code_blocks": bool(re.search(r"```", content)),
                "has_tables": bool(re.search(r"\|.*\|", content)),
                "has_images": bool(re.search(r"!\[.*?\]\(.*?\)", content)),
                "has_links": bool(re.search(r"\[.*?\]\(.*?\)", content)),
                "word_count": len(content.split()),
                "estimated_read_time": max(
                    1, len(content.split()) // markdown_config.words_per_minute_reading
                ),
                "char_count": len(content),
            }

            enhanced_section = SectionMetadata(
                title=section.get("title", "Untitled"),
                level=section.get("level", 0),
                content=content,
                order=i,
                start_line=0,
                end_line=0,
                parent_section=parent_section,
                breadcrumb=breadcrumb,
                previous_section=previous_section,
                next_section=next_section,
                sibling_sections=sibling_sections,
                subsections=subsections,
                content_analysis=content_analysis,
            )

            enhanced_sections.append(enhanced_section)

        return enhanced_sections

    def split_sections(self, text: str, document=None) -> list[dict[str, Any]]:
        """Split text into sections based on headers and document type.

        Args:
            text: Text to split
            document: Optional document for context

        Returns:
            List of section dictionaries
        """

        parser = DocumentParser()
        hierarchy_builder = HierarchyBuilder()

        structure = parser.parse_document_structure(text)
        sections: list[dict[str, Any]] = []
        current_section = None
        current_level = None
        current_title = None
        current_path: list[str] = []

        split_levels = self.determine_optimal_split_levels(text, document)

        logger.debug(
            "Determined optimal split levels",
            extra={
                "split_levels": list(split_levels),
                "document_type": (
                    "excel"
                    if document
                    and document.metadata.get("original_file_type") == "xlsx"
                    else "markdown"
                ),
            },
        )

        for item in structure:
            if item["type"] == "header":
                level = item["level"]

                if level in split_levels or (level == 0 and not sections):
                    if current_section is not None:
                        sections.append(
                            {
                                "content": current_section,
                                "level": current_level,
                                "title": current_title,
                                "path": list(current_path),
                                "is_excel_sheet": document
                                and document.metadata.get("original_file_type")
                                == "xlsx"
                                and level == 2,
                            }
                        )
                    current_section = item["text"] + "\n"
                    current_level = level
                    current_title = item["title"]
                    current_path = hierarchy_builder.get_section_path(item, structure)
                else:
                    if current_section is not None:
                        current_section += item["text"] + "\n"
            else:
                if current_section is not None:
                    current_section += item["text"] + "\n"
                else:
                    current_section = item["text"] + "\n"
                    current_level = 0
                    current_title = (
                        "Preamble"
                        if not (
                            document
                            and document.metadata.get("original_file_type") == "xlsx"
                        )
                        else "Sheet Data"
                    )
                    current_path = []

        if current_section is not None:
            sections.append(
                {
                    "content": current_section,
                    "level": current_level,
                    "title": current_title,
                    "path": list(current_path),
                    "is_excel_sheet": document
                    and document.metadata.get("original_file_type") == "xlsx"
                    and current_level == 2,
                }
            )

        chunk_size = self.settings.global_config.chunking.chunk_size
        final_sections: list[dict[str, Any]] = []

        for section in sections:
            if len(section["content"]) > chunk_size:
                logger.debug(
                    f"Section too large ({len(section['content'])} chars), splitting into smaller chunks",
                    extra={
                        "section_title": section.get("title", "Unknown"),
                        "section_size": len(section["content"]),
                        "chunk_size_limit": chunk_size,
                        "is_excel_sheet": section.get("is_excel_sheet", False),
                    },
                )

                if section.get("is_excel_sheet", False):
                    sub_chunks = self.excel_splitter.split_content(
                        section["content"], chunk_size
                    )
                else:
                    sub_chunks = self.standard_splitter.split_content(
                        section["content"], chunk_size
                    )

                for i, sub_chunk in enumerate(sub_chunks):
                    sub_section = {
                        "content": sub_chunk,
                        "level": section["level"],
                        "title": (
                            f"{section['title']} (Part {i+1})"
                            if section.get("title")
                            else f"Part {i+1}"
                        ),
                        "path": section["path"],
                        "parent_section": section.get("title", "Unknown"),
                        "sub_chunk_index": i,
                        "total_sub_chunks": len(sub_chunks),
                        "is_excel_sheet": section.get("is_excel_sheet", False),
                    }
                    final_sections.append(sub_section)
            else:
                final_sections.append(section)

        for section in final_sections:
            if "level" not in section:
                section["level"] = 0
            if "title" not in section:
                section["title"] = parser.extract_section_title(section["content"])
            if "path" not in section:
                section["path"] = []
            if "is_excel_sheet" not in section:
                section["is_excel_sheet"] = False

        return final_sections

    def merge_related_sections(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge small related sections to maintain context.

        Args:
            sections: List of section dictionaries

        Returns:
            List of merged section dictionaries
        """
        if not sections:
            return []

        merged: list[dict[str, Any]] = []
        current_section = sections[0].copy()
        min_section_size = (
            self.settings.global_config.chunking.strategies.markdown.min_section_size
        )

        for i in range(1, len(sections)):
            next_section = sections[i]

            if (
                len(current_section["content"]) < min_section_size
                and next_section["level"] > current_section["level"]
            ):
                current_section["content"] += "\n" + next_section["content"]
            else:
                merged.append(current_section)
                current_section = next_section.copy()

        merged.append(current_section)
        return merged
