"""HTML-specific chunking strategy."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog
from bs4 import BeautifulSoup, Tag

from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.document import Document
from qdrant_loader.config import Settings

logger = structlog.get_logger(__name__)

# Performance constants to prevent timeouts
MAX_HTML_SIZE_FOR_PARSING = 500_000  # 500KB limit for complex HTML parsing
MAX_SECTIONS_TO_PROCESS = 200  # Limit number of sections to prevent timeouts
MAX_CHUNK_SIZE_FOR_NLP = 20_000  # 20KB limit for NLP processing on chunks
SIMPLE_PARSING_THRESHOLD = 100_000  # Use simple parsing for files larger than 100KB


class SectionType(Enum):
    """Types of sections in an HTML document."""

    HEADER = "header"
    ARTICLE = "article"
    SECTION = "section"
    NAV = "nav"
    ASIDE = "aside"
    MAIN = "main"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    DIV = "div"


@dataclass
class HTMLSection:
    """Represents a section in an HTML document."""

    content: str
    tag_name: str
    level: int = 0
    type: SectionType = SectionType.DIV
    parent: Optional["HTMLSection"] = None
    children: list["HTMLSection"] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    text_content: str = ""

    def add_child(self, child: "HTMLSection"):
        """Add a child section."""
        self.children.append(child)
        child.parent = self


class HTMLChunkingStrategy(BaseChunkingStrategy):
    """Strategy for chunking HTML documents based on semantic structure.

    This strategy splits HTML documents into chunks based on semantic HTML elements,
    preserving the document structure and hierarchy. Each chunk includes:
    - The semantic element and its content
    - Parent element context for hierarchy
    - Element-specific metadata (tag, attributes, etc.)
    - Semantic analysis results
    """

    def __init__(self, settings: Settings):
        """Initialize the HTML chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.logger = logger
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Note: Semantic analyzer is now handled intelligently in base class
        # on a per-chunk basis based on content type and size

        # Cache for processed chunks
        self._processed_chunks = {}

        # Thread pool executor for parallel processing
        self._executor = None

        # Define semantic HTML elements that should be treated as section boundaries
        self.section_elements = {
            "article",
            "section",
            "main",
            "header",
            "footer",
            "nav",
            "aside",
        }

        # Define heading elements for hierarchy
        self.heading_elements = {"h1", "h2", "h3", "h4", "h5", "h6"}

        # Define block-level elements that can form chunks
        self.block_elements = {
            "div",
            "p",
            "blockquote",
            "pre",
            "ul",
            "ol",
            "li",
            "table",
            "figure",
        }

    def _identify_section_type(self, tag: Tag) -> SectionType:
        """Identify the type of section based on the HTML tag.

        Args:
            tag: The BeautifulSoup tag to analyze

        Returns:
            SectionType enum indicating the type of section
        """
        tag_name = tag.name.lower()

        if tag_name in self.heading_elements:
            return SectionType.HEADER
        elif tag_name == "article":
            return SectionType.ARTICLE
        elif tag_name == "section":
            return SectionType.SECTION
        elif tag_name == "nav":
            return SectionType.NAV
        elif tag_name == "aside":
            return SectionType.ASIDE
        elif tag_name == "main":
            return SectionType.MAIN
        elif tag_name in ["ul", "ol", "li"]:
            return SectionType.LIST
        elif tag_name == "table":
            return SectionType.TABLE
        elif tag_name in ["pre", "code"]:
            return SectionType.CODE_BLOCK
        elif tag_name == "blockquote":
            return SectionType.BLOCKQUOTE
        elif tag_name == "p":
            return SectionType.PARAGRAPH
        else:
            return SectionType.DIV

    def _get_heading_level(self, tag: Tag) -> int:
        """Get the heading level from an HTML heading tag.

        Args:
            tag: The heading tag

        Returns:
            Heading level (1-6)
        """
        if tag.name.lower() in self.heading_elements:
            return int(tag.name[1])  # Extract number from h1, h2, etc.
        return 0

    def _extract_section_metadata(self, section: HTMLSection) -> dict[str, Any]:
        """Extract metadata from an HTML section.

        Args:
            section: The section to analyze

        Returns:
            Dictionary containing section metadata
        """
        metadata = {
            "type": section.type.value,
            "tag_name": section.tag_name,
            "level": section.level,
            "attributes": section.attributes,
            "word_count": len(section.text_content.split()),
            "char_count": len(section.text_content),
            "has_code": section.type == SectionType.CODE_BLOCK,
            "has_links": bool(re.search(r"<a\s+[^>]*href", section.content)),
            "has_images": bool(re.search(r"<img\s+[^>]*src", section.content)),
            "is_semantic": section.tag_name in self.section_elements,
            "is_heading": section.tag_name in self.heading_elements,
        }

        # Add parent section info if available
        if section.parent:
            metadata["parent_tag"] = section.parent.tag_name
            metadata["parent_type"] = section.parent.type.value
            metadata["parent_level"] = section.parent.level

            # Add breadcrumb path for hierarchical context (simplified)
            breadcrumb = self._build_section_breadcrumb(section)
            if breadcrumb:
                metadata["breadcrumb"] = breadcrumb

        return metadata

    def _build_section_breadcrumb(self, section: HTMLSection) -> str:
        """Build a breadcrumb path of section titles to capture hierarchy.

        Args:
            section: The section to build breadcrumb for

        Returns:
            String representing the hierarchical path
        """
        breadcrumb_parts = []
        current = section.parent
        depth = 0

        # Limit breadcrumb depth to prevent performance issues
        while current and depth < 5:
            if (
                current.tag_name in self.heading_elements
                or current.tag_name in self.section_elements
            ):
                title = self._extract_title_from_content(current.text_content)
                if title and title != "Untitled Section":
                    breadcrumb_parts.append(title)
            current = current.parent
            depth += 1

        return " > ".join(reversed(breadcrumb_parts))

    def _extract_title_from_content(self, content: str) -> str:
        """Extract a title from content text.

        Args:
            content: Text content to extract title from

        Returns:
            Extracted title or "Untitled Section"
        """
        if not content:
            return "Untitled Section"

        # Take first line or first 50 characters, whichever is shorter
        lines = content.strip().split("\n")
        first_line = lines[0].strip() if lines else ""

        if first_line:
            # Limit title length for performance
            return first_line[:100] if len(first_line) > 100 else first_line

        return "Untitled Section"

    def _parse_html_structure(self, html: str) -> list[dict[str, Any]]:
        """Parse HTML structure into semantic sections with performance optimizations.

        Args:
            html: HTML content to parse

        Returns:
            List of section dictionaries
        """
        # Performance check: use simple parsing for very large files
        if len(html) > MAX_HTML_SIZE_FOR_PARSING:
            self.logger.info(
                f"HTML too large for complex parsing ({len(html)} bytes), using simple parsing"
            )
            return self._simple_html_parse(html)

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements for cleaner processing
            for script in soup(["script", "style"]):
                script.decompose()

            sections = []
            section_count = 0

            def process_element(element, level=0):
                nonlocal section_count

                # Performance check: limit total sections
                if section_count >= MAX_SECTIONS_TO_PROCESS:
                    return

                # Performance check: limit recursion depth
                if level > 10:
                    return

                if isinstance(element, Tag):
                    tag_name = element.name.lower()

                    # Only process meaningful elements
                    if (
                        tag_name in self.section_elements
                        or tag_name in self.heading_elements
                        or tag_name in self.block_elements
                    ):
                        text_content = element.get_text(strip=True)

                        # Skip empty or very small sections
                        if len(text_content) < 10:
                            return

                        section_type = self._identify_section_type(element)

                        # Get attributes (limited for performance)
                        attributes = {}
                        if element.attrs:
                            # Only keep essential attributes
                            for attr in ["id", "class", "role"]:
                                if attr in element.attrs:
                                    attributes[attr] = element.attrs[attr]

                        section = {
                            "content": str(element),
                            "text_content": text_content,
                            "tag_name": tag_name,
                            "level": level,
                            "section_type": section_type,
                            "attributes": attributes,
                            "title": self._extract_title_from_content(text_content),
                        }

                        sections.append(section)
                        section_count += 1

                # Process children (limited depth)
                if hasattr(element, "children") and level < 8:
                    for child in element.children:
                        process_element(child, level + 1)

            # Start processing from body or root
            body = soup.find("body")
            if body:
                process_element(body)
            else:
                process_element(soup)

            return sections[:MAX_SECTIONS_TO_PROCESS]  # Ensure we don't exceed limit

        except Exception as e:
            self.logger.warning(f"HTML parsing failed: {e}")
            return self._simple_html_parse(html)

    def _simple_html_parse(self, html: str) -> list[dict[str, Any]]:
        """Simple HTML parsing for large files or when complex parsing fails.

        Args:
            html: HTML content to parse

        Returns:
            List of simple section dictionaries
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get clean text
            text = soup.get_text(separator="\n", strip=True)

            # Simple chunking by size
            chunk_size = self.chunk_size
            chunks = []

            # Split by paragraphs first
            paragraphs = re.split(r"\n\s*\n", text)
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) <= chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"

                # Limit total chunks
                if len(chunks) >= MAX_SECTIONS_TO_PROCESS:
                    break

            # Add the last chunk if not empty
            if current_chunk and len(chunks) < MAX_SECTIONS_TO_PROCESS:
                chunks.append(current_chunk.strip())

            # Convert to section format
            sections = []
            for _i, chunk in enumerate(chunks):
                section = {
                    "content": chunk,
                    "text_content": chunk,
                    "tag_name": "div",
                    "level": 0,
                    "section_type": SectionType.DIV,
                    "attributes": {},
                    "title": self._extract_title_from_content(chunk),
                }
                sections.append(section)

            return sections

        except Exception as e:
            self.logger.error(f"Simple HTML parsing failed: {e}")
            # Ultimate fallback: return the entire content as one section
            return [
                {
                    "content": html,
                    "text_content": html,
                    "tag_name": "div",
                    "level": 0,
                    "section_type": SectionType.DIV,
                    "attributes": {},
                    "title": "HTML Document",
                }
            ]

    def _merge_small_sections(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge small sections to create more meaningful chunks.

        Args:
            sections: List of sections to merge

        Returns:
            List of merged sections
        """
        if not sections:
            return []

        merged = []
        current_group = []
        current_size = 0
        min_size = 200  # Minimum size for standalone sections

        for section in sections:
            section_size = len(section.get("text_content", ""))

            # If section is large enough or is a significant element, keep it separate
            if (
                section_size >= min_size
                or section.get("tag_name") in self.section_elements
                or section.get("tag_name") in self.heading_elements
            ):

                # First, add any accumulated small sections
                if current_group:
                    merged_section = self._create_merged_section(current_group)
                    merged.append(merged_section)
                    current_group = []
                    current_size = 0

                # Add the large section
                merged.append(section)
            else:
                # Accumulate small sections
                current_group.append(section)
                current_size += section_size

                # If accumulated size is large enough, create a merged section
                if current_size >= min_size:
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
        """Create a merged section from a list of small sections.

        Args:
            sections: List of sections to merge

        Returns:
            Merged section dictionary
        """
        if not sections:
            return {}

        if len(sections) == 1:
            return sections[0]

        # Merge content
        merged_content = "\n\n".join(section.get("content", "") for section in sections)
        merged_text = "\n\n".join(
            section.get("text_content", "") for section in sections
        )

        # Use the first section's metadata as base
        merged_section = sections[0].copy()
        merged_section.update(
            {
                "content": merged_content,
                "text_content": merged_text,
                "title": f"Merged Section ({len(sections)} parts)",
                "tag_name": "div",  # Generic container
                "section_type": SectionType.DIV,
            }
        )

        return merged_section

    def _split_text(self, html: str) -> list[dict[str, Any]]:
        """Split HTML text into chunks based on semantic structure.

        Args:
            html: The HTML content to split

        Returns:
            List of dictionaries with chunk content and metadata
        """
        # Performance check: use simple parsing for large files
        if len(html) > SIMPLE_PARSING_THRESHOLD:
            self.logger.info(
                f"Using simple parsing for large HTML file ({len(html)} bytes)"
            )
            return self._simple_html_parse(html)

        # Parse HTML structure
        sections = self._parse_html_structure(html)

        if not sections:
            return self._simple_html_parse(html)

        # Merge small sections
        merged_sections = self._merge_small_sections(sections)

        # Split large sections if needed
        final_sections = []
        for section in merged_sections:
            content_size = len(section.get("content", ""))
            if content_size > self.chunk_size:
                # Split large sections
                split_parts = self._split_large_section(
                    section.get("content", ""), self.chunk_size
                )
                for i, part in enumerate(split_parts):
                    split_section = section.copy()
                    split_section.update(
                        {
                            "content": part,
                            "text_content": part,
                            "title": f"{section.get('title', 'Section')} (Part {i+1})",
                        }
                    )
                    final_sections.append(split_section)
            else:
                final_sections.append(section)

        return final_sections[:MAX_SECTIONS_TO_PROCESS]  # Ensure we don't exceed limit

    def _split_large_section(self, content: str, max_size: int) -> list[str]:
        """Split a large section into smaller parts.

        Args:
            content: Content to split
            max_size: Maximum size per part

        Returns:
            List of content parts
        """
        if len(content) <= max_size:
            return [content]

        # Simple splitting by size with word boundaries
        parts = []
        current_part = ""
        words = content.split()

        for word in words:
            if len(current_part) + len(word) + 1 <= max_size:
                current_part += word + " "
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = word + " "

                # Limit number of parts
                if len(parts) >= 10:
                    break

        if current_part:
            parts.append(current_part.strip())

        return parts

    def _extract_section_title(self, chunk: str) -> str:
        """Extract a title from a chunk of HTML content.

        Args:
            chunk: HTML chunk content

        Returns:
            Extracted title
        """
        try:
            soup = BeautifulSoup(chunk, "html.parser")

            # Try to find title in various elements
            for tag in ["h1", "h2", "h3", "h4", "h5", "h6", "title"]:
                element = soup.find(tag)
                if element:
                    title = element.get_text(strip=True)
                    if title:
                        return title[:100]  # Limit title length

            # Try to find text in semantic elements
            for tag in ["article", "section", "main"]:
                element = soup.find(tag)
                if element:
                    text = element.get_text(strip=True)
                    if text:
                        return self._extract_title_from_content(text)

            # Fallback to first text content
            text = soup.get_text(strip=True)
            if text:
                return self._extract_title_from_content(text)

            return "Untitled Section"

        except Exception:
            return "Untitled Section"

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk an HTML document using semantic boundaries.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents
        """
        file_name = (
            document.metadata.get("file_name")
            or document.metadata.get("original_filename")
            or document.title
            or f"{document.source_type}:{document.source}"
        )

        # Start progress tracking
        self.progress_tracker.start_chunking(
            document.id,
            document.source,
            document.source_type,
            len(document.content),
            file_name,
        )

        try:
            # Check for very large files that should use fallback chunking
            if len(document.content) > MAX_HTML_SIZE_FOR_PARSING:
                self.logger.info(
                    f"HTML file too large ({len(document.content)} bytes), using fallback chunking"
                )
                self.progress_tracker.log_fallback(
                    document.id, f"Large HTML file ({len(document.content)} bytes)"
                )
                return self._fallback_chunking(document)

            # Parse HTML and extract semantic sections
            self.logger.debug("Parsing HTML structure")
            sections = self._split_text(document.content)

            if not sections:
                self.progress_tracker.finish_chunking(document.id, 0, "html")
                return []

            # Create chunk documents
            chunked_docs = []
            for i, section in enumerate(sections):
                chunk_content = section["content"]
                self.logger.debug(
                    f"Processing HTML section {i+1}/{len(sections)}",
                    extra={
                        "chunk_size": len(chunk_content),
                        "section_type": section.get("section_type", "unknown"),
                        "tag_name": section.get("tag_name", "unknown"),
                    },
                )

                # Create chunk document with enhanced metadata
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=i,
                    total_chunks=len(sections),
                    skip_nlp=False,
                )

                # Add HTML-specific metadata
                chunk_doc.metadata.update(section)
                chunk_doc.metadata["chunking_strategy"] = "html"
                chunk_doc.metadata["parent_document_id"] = document.id

                chunked_docs.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "html"
            )
            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            # Fallback to default chunking
            self.progress_tracker.log_fallback(
                document.id, f"HTML parsing failed: {str(e)}"
            )
            return self._fallback_chunking(document)

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Simple fallback chunking when the main strategy fails.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.info("Using fallback chunking strategy for HTML document")

        try:
            # Clean HTML and convert to text for simple chunking
            soup = BeautifulSoup(document.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator="\n", strip=True)

            # Simple chunking implementation based on fixed size
            chunk_size = self.chunk_size

            chunks = []
            # Split by paragraphs first
            paragraphs = re.split(r"\n\s*\n", text)
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) <= chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"

                # Limit total chunks
                if len(chunks) >= MAX_SECTIONS_TO_PROCESS:
                    break

            # Add the last chunk if not empty
            if current_chunk and len(chunks) < MAX_SECTIONS_TO_PROCESS:
                chunks.append(current_chunk.strip())

            # Create chunked documents
            chunked_docs = []
            valid_chunk_index = 0
            for i, chunk_content in enumerate(chunks):
                # Validate chunk content
                if not chunk_content or not chunk_content.strip():
                    self.logger.warning(f"Skipping empty fallback chunk {i+1}")
                    continue

                # Use base class chunk creation
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=valid_chunk_index,
                    total_chunks=len(chunks),  # Will be updated at the end
                    skip_nlp=False,  # Let base class decide
                )

                # Generate unique chunk ID
                chunk_doc.id = Document.generate_chunk_id(
                    document.id, valid_chunk_index
                )
                chunk_doc.metadata["parent_document_id"] = document.id
                chunk_doc.metadata["chunking_method"] = "fallback_html"

                chunked_docs.append(chunk_doc)
                valid_chunk_index += 1

            # Update total_chunks in all chunk metadata to reflect actual count
            for chunk_doc in chunked_docs:
                chunk_doc.metadata["total_chunks"] = len(chunked_docs)

            return chunked_docs

        except Exception as e:
            self.logger.error(f"Fallback chunking failed: {e}")
            # Ultimate fallback: return original document as single chunk
            chunk_doc = Document(
                content=document.content,
                metadata=document.metadata.copy(),
                source=document.source,
                source_type=document.source_type,
                url=document.url,
                title=document.title,
                content_type=document.content_type,
            )
            chunk_doc.id = Document.generate_chunk_id(document.id, 0)
            chunk_doc.metadata.update(
                {
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "parent_document_id": document.id,
                    "chunking_method": "fallback_single",
                    "entities": [],
                    "pos_tags": [],
                    "nlp_skipped": True,
                    "skip_reason": "fallback_error",
                }
            )
            return [chunk_doc]

    def __del__(self):
        """Cleanup method."""
        # Call shutdown to clean up resources
        self.shutdown()

    def shutdown(self):
        """Shutdown the strategy and clean up resources."""
        # Shutdown thread pool executor if it exists
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        # Clean up any cached data
        if hasattr(self, "_processed_chunks"):
            self._processed_chunks.clear()

        # Note: semantic_analyzer is now handled in base class
        # No additional cleanup needed for HTML strategy
