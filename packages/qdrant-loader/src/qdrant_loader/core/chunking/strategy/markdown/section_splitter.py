"""Section splitting strategies for markdown chunking."""

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)


class BaseSplitter(ABC):
    """Base class for section splitting strategies."""

    def __init__(self, settings: "Settings"):
        """Initialize the splitter.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.chunk_size = settings.global_config.chunking.chunk_size
        self.chunk_overlap = settings.global_config.chunking.chunk_overlap

    @abstractmethod
    def split_content(self, content: str, max_size: int) -> list[str]:
        """Split content into chunks.

        Args:
            content: Content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        pass


class StandardSplitter(BaseSplitter):
    """Standard markdown text splitter that preserves structure."""

    def split_content(self, content: str, max_size: int) -> list[str]:
        """Split a large section into smaller chunks while preserving markdown structure.

        Args:
            content: Section content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        chunks = []
        
        # Calculate dynamic safety limit based on configuration
        # Allow up to 50% of max_chunks_per_document for a single section
        max_chunks_per_section = min(
            self.settings.global_config.chunking.max_chunks_per_document // 2,
            1000  # Absolute maximum to prevent runaway chunking
        )

        # Split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", content)
        
        # Flatten paragraphs into manageable text units
        text_units = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is too large, split by sentences
            if len(para) > max_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                text_units.extend([s.strip() for s in sentences if s.strip()])
            else:
                text_units.append(para)

        # Build chunks with overlap
        i = 0
        while i < len(text_units) and len(chunks) < max_chunks_per_section:
            current_chunk = ""
            units_in_chunk = 0
            
            # Build the current chunk
            j = i
            while j < len(text_units):
                unit = text_units[j]
                
                # Check if adding this unit would exceed max_size
                if current_chunk and len(current_chunk) + len(unit) + 2 > max_size:
                    break
                    
                # Add unit to chunk
                if current_chunk:
                    current_chunk += "\n\n" + unit
                else:
                    current_chunk = unit
                
                units_in_chunk += 1
                j += 1
            
            # Add chunk if it has content
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # Calculate overlap and advance position
            if units_in_chunk > 0:
                # When overlap is 0, advance by all units to avoid any overlap
                if self.chunk_overlap == 0:
                    advance = units_in_chunk
                else:
                    # Calculate how many characters of overlap we want
                    overlap_chars = min(self.chunk_overlap, len(current_chunk) // 4)  # Max 25% overlap
                    
                    # Find a good overlap point by counting back from the end
                    if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                        # Count how many text units should be included in overlap
                        overlap_units = 0
                        overlap_size = 0
                        for k in range(j - 1, i - 1, -1):  # Go backwards
                            unit_size = len(text_units[k])
                            if overlap_size + unit_size <= overlap_chars:
                                overlap_size += unit_size
                                overlap_units += 1
                            else:
                                break
                        
                        # Advance by total units minus overlap units, ensuring progress
                        advance = max(1, units_in_chunk - overlap_units)
                    else:
                        # No overlap possible, advance by all units
                        advance = max(1, units_in_chunk)
                
                i += advance
            else:
                # Safety: ensure we make progress even if no units were added
                i += 1

        # Handle remaining units if we hit the chunk limit
        if i < len(text_units) and len(chunks) >= max_chunks_per_section:
            logger.warning(
                f"Section reached maximum chunks limit ({max_chunks_per_section}), truncating remaining content",
                extra={
                    "remaining_units": len(text_units) - i,
                    "max_chunks_per_section": max_chunks_per_section,
                },
            )

        return chunks


class ExcelSplitter(BaseSplitter):
    """Excel-specific splitter that preserves table structure."""

    def split_content(self, content: str, max_size: int) -> list[str]:
        """Split Excel sheet content into chunks, preserving table structure where possible.

        Args:
            content: Excel sheet content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        chunks = []
        
        # Calculate dynamic safety limit
        max_chunks_per_section = min(
            self.settings.global_config.chunking.max_chunks_per_document // 2,
            1000
        )

        # Split content into logical units: headers, tables, and text blocks
        logical_units = []
        lines = content.split("\n")
        current_unit = []
        in_table = False
        
        for line in lines:
            line = line.strip()
            
            # Detect table boundaries
            is_table_line = bool(re.match(r"^\|.*\|$", line)) or bool(re.match(r"^[|\-\s:]+$", line))
            
            if is_table_line and not in_table:
                # Starting a new table
                if current_unit:
                    logical_units.append("\n".join(current_unit))
                    current_unit = []
                in_table = True
                current_unit.append(line)
            elif not is_table_line and in_table:
                # Ending a table
                if current_unit:
                    logical_units.append("\n".join(current_unit))
                    current_unit = []
                in_table = False
                if line:  # Don't add empty lines
                    current_unit.append(line)
            else:
                # Continue current unit
                if line or current_unit:  # Don't start with empty lines
                    current_unit.append(line)
        
        # Add final unit
        if current_unit:
            logical_units.append("\n".join(current_unit))

        # Split large logical units that exceed max_size
        split_logical_units = []
        for unit in logical_units:
            if len(unit) > max_size:
                # Split large unit by lines to preserve table structure
                lines = unit.split('\n')
                current_sub_unit = []
                
                for line in lines:
                    # Check if adding this line would exceed max_size
                    test_unit = '\n'.join(current_sub_unit + [line])
                    if current_sub_unit and len(test_unit) > max_size:
                        # Save current sub-unit and start new one
                        split_logical_units.append('\n'.join(current_sub_unit))
                        current_sub_unit = [line]
                    else:
                        current_sub_unit.append(line)
                
                # Add the last sub-unit
                if current_sub_unit:
                    split_logical_units.append('\n'.join(current_sub_unit))
            else:
                split_logical_units.append(unit)
        
        # Use the split logical units
        logical_units = split_logical_units

        # Group logical units into chunks
        i = 0
        while i < len(logical_units) and len(chunks) < max_chunks_per_section:
            current_chunk = ""
            units_in_chunk = 0
            
            # Build the current chunk
            j = i
            while j < len(logical_units):
                unit = logical_units[j]
                
                # Check if adding this unit would exceed max_size
                if current_chunk and len(current_chunk) + len(unit) + 2 > max_size:
                    break
                    
                # Add unit to chunk
                if current_chunk:
                    current_chunk += "\n\n" + unit
                else:
                    current_chunk = unit
                
                units_in_chunk += 1
                j += 1
            
            # Add chunk if it has content
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # Calculate overlap and advance position
            if units_in_chunk > 0:
                if self.chunk_overlap == 0:
                    advance = units_in_chunk
                else:
                    # For Excel content, use more conservative overlap (preserve table boundaries)
                    overlap_units = min(1, units_in_chunk // 2)  # At most 1 unit overlap
                    advance = max(1, units_in_chunk - overlap_units)
                
                i += advance
            else:
                i += 1

        # Handle remaining units if we hit the chunk limit
        if i < len(logical_units) and len(chunks) >= max_chunks_per_section:
            logger.warning(
                f"Excel sheet reached maximum chunks limit ({max_chunks_per_section}), truncating remaining content",
                extra={
                    "remaining_units": len(logical_units) - i,
                    "max_chunks_per_section": max_chunks_per_section,
                },
            )

        return chunks


class FallbackSplitter(BaseSplitter):
    """Simple fallback splitter for when other strategies fail."""

    def split_content(self, content: str, max_size: int) -> list[str]:
        """Simple chunking implementation based on fixed size.

        Args:
            content: Content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        chunks = []

        # Split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", content)
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


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

    def split_sections(self, text: str, document=None) -> list[dict[str, Any]]:
        """Split text into sections based on headers and document type.
        
        Args:
            text: Text to split
            document: Optional document for context
            
        Returns:
            List of section dictionaries
        """
        from .document_parser import DocumentParser, HierarchyBuilder
        
        parser = DocumentParser()
        hierarchy_builder = HierarchyBuilder()
        
        structure = parser.parse_document_structure(text)
        sections = []
        current_section = None
        current_level = None
        current_title = None
        current_path = []

        # Check if this is a converted Excel file that needs special handling
        is_converted_excel = (
            document and 
            document.metadata.get("original_file_type") == "xlsx"
        )
        
        # For converted Excel files, also split on H2 headers (sheet names)
        # For regular markdown, only split on H1 headers
        split_levels = {1} if not is_converted_excel else {1, 2}

        for item in structure:
            if item["type"] == "header":
                level = item["level"]
                
                # Create new section for split levels or first header (level 0)
                if level in split_levels or (level == 0 and not sections):
                    # Save previous section if exists
                    if current_section is not None:
                        sections.append(
                            {
                                "content": current_section,
                                "level": current_level,
                                "title": current_title,
                                "path": list(current_path),
                                "is_excel_sheet": is_converted_excel and level == 2,
                            }
                        )
                    # Start new section
                    current_section = item["text"] + "\n"
                    current_level = level
                    current_title = item["title"]
                    current_path = hierarchy_builder.get_section_path(item, structure)
                else:
                    # For deeper headers, just add to current section
                    if current_section is not None:
                        current_section += item["text"] + "\n"
            else:
                if current_section is not None:
                    current_section += item["text"] + "\n"
                else:
                    # If no section started yet, treat as preamble
                    current_section = item["text"] + "\n"
                    current_level = 0
                    current_title = "Preamble" if not is_converted_excel else "Sheet Data"
                    current_path = []
                    
        # Add the last section
        if current_section is not None:
            sections.append(
                {
                    "content": current_section,
                    "level": current_level,
                    "title": current_title,
                    "path": list(current_path),
                    "is_excel_sheet": is_converted_excel and current_level == 2,
                }
            )
        
        # Check if sections are too large and split them
        chunk_size = self.settings.global_config.chunking.chunk_size
        final_sections = []
        
        for section in sections:
            if len(section["content"]) > chunk_size:
                # Split large section into smaller chunks
                logger.debug(
                    f"Section too large ({len(section['content'])} chars), splitting into smaller chunks",
                    extra={
                        "section_title": section.get("title", "Unknown"),
                        "section_size": len(section["content"]),
                        "chunk_size_limit": chunk_size,
                        "is_excel_sheet": section.get("is_excel_sheet", False),
                    },
                )
                
                # Choose appropriate splitter
                if section.get("is_excel_sheet", False):
                    sub_chunks = self.excel_splitter.split_content(section["content"], chunk_size)
                else:
                    sub_chunks = self.standard_splitter.split_content(section["content"], chunk_size)
                
                # Create metadata for each sub-chunk
                for i, sub_chunk in enumerate(sub_chunks):
                    sub_section = {
                        "content": sub_chunk,
                        "level": section["level"],
                        "title": f"{section['title']} (Part {i+1})" if section.get("title") else f"Part {i+1}",
                        "path": section["path"],
                        "parent_section": section.get("title", "Unknown"),
                        "sub_chunk_index": i,
                        "total_sub_chunks": len(sub_chunks),
                        "is_excel_sheet": section.get("is_excel_sheet", False),
                    }
                    final_sections.append(sub_section)
            else:
                # Section is already small enough
                final_sections.append(section)
        
        # Ensure each section has proper metadata
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

        merged = []
        current_section = sections[0].copy()
        min_section_size = 500  # Minimum characters for a standalone section

        for i in range(1, len(sections)):
            next_section = sections[i]

            # If current section is small and next section is a subsection, merge them
            if (
                len(current_section["content"]) < min_section_size
                and next_section["level"] > current_section["level"]
            ):
                current_section["content"] += "\n" + next_section["content"]
                # Keep other metadata from the parent section
            else:
                merged.append(current_section)
                current_section = next_section.copy()

        # Add the last section
        merged.append(current_section)
        return merged 