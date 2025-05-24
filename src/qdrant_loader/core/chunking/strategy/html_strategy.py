"""HTML-specific chunking strategy."""

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Optional
import concurrent.futures
import structlog
from dataclasses import dataclass, field
from enum import Enum

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning
from bs4.element import NavigableString
import warnings

from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document
from qdrant_loader.core.text_processing.semantic_analyzer import SemanticAnalyzer
from qdrant_loader.config import Settings, GlobalConfig, SemanticAnalysisConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings, GlobalConfig

# Suppress XML parsing warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = structlog.get_logger(__name__)


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
    children: List["HTMLSection"] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
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
            settings: The application settings
        """
        super().__init__(settings)
        self.logger = structlog.get_logger(__name__)

        # Initialize semantic analyzer
        self.semantic_analyzer = SemanticAnalyzer(
            spacy_model="en_core_web_sm",
            num_topics=settings.global_config.semantic_analysis.num_topics,
            passes=settings.global_config.semantic_analysis.lda_passes,
        )

        # Cache for processed chunks
        self._processed_chunks = {}

        # Initialize thread pool for parallel processing
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

        # Define semantic HTML elements that should be treated as section boundaries
        self.section_elements = {"article", "section", "main", "header", "footer", "nav", "aside"}

        # Define heading elements for hierarchy
        self.heading_elements = {"h1", "h2", "h3", "h4", "h5", "h6"}

        # Define block-level elements that can form chunks
        self.block_elements = {"div", "p", "blockquote", "pre", "ul", "ol", "li", "table", "figure"}

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

    def _extract_section_metadata(self, section: HTMLSection) -> Dict[str, Any]:
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

            # Add breadcrumb path for hierarchical context
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
        current = section

        # Walk up the parent chain to build the breadcrumb
        while current.parent:
            parent_title = self._extract_title_from_content(current.parent.text_content)
            if parent_title:
                breadcrumb_parts.insert(0, parent_title)
            current = current.parent

        # Add current section title
        current_title = self._extract_title_from_content(section.text_content)
        if current_title:
            breadcrumb_parts.append(current_title)

        return " > ".join(breadcrumb_parts)

    def _extract_title_from_content(self, content: str) -> str:
        """Extract a title from content text.

        Args:
            content: The content text

        Returns:
            Extracted title or empty string
        """
        if not content:
            return ""

        # Take the first sentence or first 50 characters
        first_sentence = content.split(".")[0].strip()
        if len(first_sentence) <= 50:
            return first_sentence

        # If first sentence is too long, truncate
        return content[:50].strip() + "..." if len(content) > 50 else content.strip()

    def _parse_html_structure(self, html: str) -> List[Dict[str, Any]]:
        """Parse HTML into a structured representation.

        Args:
            html: The HTML content

        Returns:
            List of dictionaries representing HTML elements
        """
        soup = BeautifulSoup(html, "html.parser")
        elements = []

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        def process_element(element, level=0):
            """Recursively process HTML elements."""
            if isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    elements.append(
                        {"type": "text", "content": text, "level": level, "tag_name": "text"}
                    )
                return

            if isinstance(element, Tag):
                tag_name = element.name.lower()

                # Skip certain elements
                if tag_name in ["script", "style", "meta", "link"]:
                    return

                # Get element attributes
                attributes = dict(element.attrs) if element.attrs else {}

                # Get text content
                text_content = element.get_text(separator=" ", strip=True)

                # Determine if this should be a section boundary
                is_section_boundary = (
                    tag_name in self.section_elements
                    or tag_name in self.heading_elements
                    or (tag_name in self.block_elements and len(text_content) > 50)
                    or (tag_name == "div" and len(text_content) > 200)  # Include larger divs
                )

                if is_section_boundary:
                    elements.append(
                        {
                            "type": "section",
                            "content": str(element),
                            "text_content": text_content,
                            "level": (
                                self._get_heading_level(element)
                                if tag_name in self.heading_elements
                                else level
                            ),
                            "tag_name": tag_name,
                            "attributes": attributes,
                            "section_type": self._identify_section_type(element),
                        }
                    )
                else:
                    # Process children for non-section elements
                    for child in element.children:
                        process_element(child, level + 1)

        # Process the entire document
        for child in soup.children:
            process_element(child)

        return elements

    def _merge_small_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
        min_section_size = 200  # Reduced minimum size for more granular chunks

        for i in range(1, len(sections)):
            next_section = sections[i]

            # If current section is small and next section is related, merge them
            # But be more conservative to avoid creating overly large chunks
            should_merge = (
                len(current_section["text_content"]) < min_section_size
                and len(current_section["text_content"]) + len(next_section["text_content"])
                < self.chunk_size * 0.8
                and (
                    # Same parent context
                    next_section["level"] > current_section["level"]
                    or
                    # Sequential paragraphs only (not divs to avoid large merges)
                    (current_section["tag_name"] == "p" and next_section["tag_name"] == "p")
                )
            )

            if should_merge:
                current_section["content"] += "\n" + next_section["content"]
                current_section["text_content"] += " " + next_section["text_content"]
            else:
                merged.append(current_section)
                current_section = next_section.copy()

        # Add the last section
        merged.append(current_section)
        return merged

    def _split_text(self, html: str) -> List[Dict[str, Any]]:
        """Split HTML into chunks based on semantic structure.

        Args:
            html: The HTML content to split

        Returns:
            List of dictionaries with chunk content and metadata
        """
        structure = self._parse_html_structure(html)

        if not structure:
            return []

        # Filter out very small sections and merge related ones
        filtered_sections = [s for s in structure if len(s.get("text_content", "")) > 50]
        merged_sections = self._merge_small_sections(filtered_sections)

        # Split large sections that exceed chunk size
        final_sections = []
        for section in merged_sections:
            section_size = len(section.get("content", ""))

            # If section is larger than chunk size, split it
            if section_size > self.chunk_size:
                self.logger.debug(
                    f"Splitting large section of {section_size} characters",
                    section_tag=section.get("tag_name", "unknown"),
                    chunk_size=self.chunk_size,
                )

                # Split the large section into smaller chunks
                sub_chunks = self._split_large_section(section["content"], self.chunk_size)

                for i, sub_chunk in enumerate(sub_chunks):
                    # Create a new section for each sub-chunk
                    sub_section = section.copy()
                    sub_section["content"] = sub_chunk
                    sub_section["text_content"] = BeautifulSoup(sub_chunk, "html.parser").get_text(
                        strip=True
                    )
                    sub_section["title"] = f"{section.get('title', 'Section')} (Part {i+1})"
                    final_sections.append(sub_section)
            else:
                final_sections.append(section)

        # Ensure each section has proper metadata
        for section in final_sections:
            if "level" not in section:
                section["level"] = 0
            if "title" not in section:
                section["title"] = self._extract_title_from_content(section.get("text_content", ""))
            if "attributes" not in section:
                section["attributes"] = {}

        return final_sections

    def _split_large_section(self, content: str, max_size: int) -> List[str]:
        """Split a large section into smaller chunks while preserving HTML structure.

        Args:
            content: Section content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        # Parse the HTML content
        soup = BeautifulSoup(content, "html.parser")
        chunks = []
        current_chunk = ""

        def add_element_to_chunk(element):
            nonlocal current_chunk, chunks
            element_str = str(element)

            # If adding this element would exceed max_size
            if len(current_chunk) + len(element_str) > max_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # If the element itself is too large, split it further
                if len(element_str) > max_size:
                    # For very large elements, split by text content
                    if isinstance(element, Tag):
                        text_content = element.get_text()
                        if len(text_content) > max_size:
                            # Split text into smaller pieces
                            words = text_content.split()
                            current_text = ""

                            for word in words:
                                if (
                                    len(current_text) + len(word) + 1 > max_size * 0.8
                                ):  # Leave some room for HTML tags
                                    if current_text:
                                        # Create a simple HTML wrapper for the text chunk
                                        tag_name = (
                                            element.name if hasattr(element, "name") else "div"
                                        )
                                        chunk_html = (
                                            f"<{tag_name}>{current_text.strip()}</{tag_name}>"
                                        )
                                        chunks.append(chunk_html)
                                        current_text = word + " "
                                    else:
                                        # Single word is too long, just add it
                                        tag_name = (
                                            element.name if hasattr(element, "name") else "div"
                                        )
                                        chunk_html = f"<{tag_name}>{word}</{tag_name}>"
                                        chunks.append(chunk_html)
                                else:
                                    current_text += word + " "

                            # Add remaining text
                            if current_text.strip():
                                tag_name = element.name if hasattr(element, "name") else "div"
                                chunk_html = f"<{tag_name}>{current_text.strip()}</{tag_name}>"
                                chunks.append(chunk_html)

                            current_chunk = ""
                            return

                current_chunk = element_str
            else:
                current_chunk += element_str

        # Process elements in order
        for element in soup.children:
            if isinstance(element, Tag):
                add_element_to_chunk(element)
            elif isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    add_element_to_chunk(element)

        # Add the last chunk if not empty
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [content]

    def _extract_section_title(self, chunk: str) -> str:
        """Extract section title from an HTML chunk.

        Args:
            chunk: The HTML chunk

        Returns:
            Section title or default title
        """
        soup = BeautifulSoup(chunk, "html.parser")

        # Try to find a heading element
        for heading_tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            heading = soup.find(heading_tag)
            if heading:
                return heading.get_text(strip=True)

        # Try to find title in common title attributes
        for element in soup.find_all(attrs={"title": True}):
            if isinstance(element, Tag) and "title" in element.attrs:
                title = element.attrs["title"]
                if isinstance(title, str) and len(title) < 100:
                    return title
                elif isinstance(title, list) and title and isinstance(title[0], str):
                    return title[0]

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

    def shutdown(self):
        """Shutdown the thread pool executor."""
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def chunk_document(self, document: Document) -> List[Document]:
        """Chunk an HTML document using semantic boundaries.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.info(
            "Starting HTML chunking",
            extra={
                "source": document.source,
                "source_type": document.source_type,
                "content_length": len(document.content),
                "file_name": document.metadata.get("file_name", "unknown"),
            },
        )

        try:
            # Split HTML into semantic chunks
            self.logger.debug("Parsing HTML structure")
            chunks_metadata = self._split_text(document.content)
            self.logger.info(f"Split document into {len(chunks_metadata)} initial sections")

            if not chunks_metadata:
                # Fallback for empty or problematic HTML
                return self._fallback_chunking(document)

            # Create chunked documents
            chunked_docs = []
            for i, chunk_meta in enumerate(chunks_metadata):
                chunk_content = chunk_meta["content"]
                self.logger.debug(
                    f"Processing chunk {i+1}/{len(chunks_metadata)}",
                    extra={
                        "chunk_size": len(chunk_content),
                        "chunk_title": chunk_meta.get("title", "unknown"),
                        "chunk_tag": chunk_meta.get("tag_name", "unknown"),
                    },
                )

                # Create chunk document with metadata
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=i,
                    total_chunks=len(chunks_metadata),
                )

                # Generate unique chunk ID
                chunk_doc.id = Document.generate_chunk_id(document.id, i)

                # Add HTML-specific metadata
                section_title = chunk_meta.get("title", self._extract_section_title(chunk_content))
                chunk_doc.metadata.update(
                    {
                        "section_title": section_title,
                        "section_tag": chunk_meta.get("tag_name", "div"),
                        "section_type": chunk_meta.get("section_type", SectionType.DIV).value,
                        "section_level": chunk_meta.get("level", 0),
                        "section_attributes": chunk_meta.get("attributes", {}),
                        "is_semantic": chunk_meta.get("tag_name", "") in self.section_elements,
                        "is_heading": chunk_meta.get("tag_name", "") in self.heading_elements,
                        "text_content": chunk_meta.get("text_content", ""),
                        "chunk_index": i,
                        "total_chunks": len(chunks_metadata),
                        "parent_document_id": document.id,
                    }
                )

                self.logger.debug(
                    f"Created chunk document",
                    extra={
                        "chunk_id": chunk_doc.id,
                        "section_title": section_title,
                        "section_tag": chunk_meta.get("tag_name"),
                        "content_length": len(chunk_content),
                    },
                )

                chunked_docs.append(chunk_doc)

            self.logger.info(
                "Completed HTML chunking",
                extra={
                    "source": document.source,
                    "chunk_count": len(chunked_docs),
                    "avg_chunk_size": (
                        sum(len(d.content) for d in chunked_docs) / len(chunked_docs)
                        if chunked_docs
                        else 0
                    ),
                },
            )

            return chunked_docs

        except Exception as e:
            self.logger.error(
                f"Error chunking HTML document",
                exc_info=True,
                extra={
                    "error": str(e),
                    "source": document.source,
                    "source_type": document.source_type,
                },
            )
            # Fallback to simple chunking on error
            return self._fallback_chunking(document)
        finally:
            self.shutdown()

    def _fallback_chunking(self, document: Document) -> List[Document]:
        """Simple fallback chunking when the main strategy fails.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.info("Using fallback chunking strategy for HTML document")

        # Clean HTML and convert to text for simple chunking
        soup = BeautifulSoup(document.content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Simple chunking implementation based on fixed size
        chunk_size = self.settings.global_config.chunking.chunk_size

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

        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(current_chunk.strip())

        # Create chunked documents
        chunked_docs = []
        for i, chunk_content in enumerate(chunks):
            chunk_doc = self._create_chunk_document(
                original_doc=document,
                chunk_content=chunk_content,
                chunk_index=i,
                total_chunks=len(chunks),
            )

            # Generate unique chunk ID
            chunk_doc.id = Document.generate_chunk_id(document.id, i)
            chunk_doc.metadata["parent_document_id"] = document.id

            chunked_docs.append(chunk_doc)

        return chunked_docs

    def __del__(self):
        self.shutdown()
        if hasattr(self, "semantic_analyzer"):
            self.semantic_analyzer.clear_cache()
