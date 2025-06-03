"""Markdown-specific chunking strategy."""

import concurrent.futures
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.document import Document
from qdrant_loader.core.text_processing.semantic_analyzer import SemanticAnalyzer

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

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


class MarkdownChunkingStrategy(BaseChunkingStrategy):
    """Strategy for chunking markdown documents based on sections.

    This strategy splits markdown documents into chunks based on section headers,
    preserving the document structure and hierarchy. Each chunk includes:
    - The section header and its content
    - Parent section headers for context
    - Section-specific metadata
    - Semantic analysis results
    """

    def __init__(self, settings: Settings):
        """Initialize the Markdown chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Initialize semantic analyzer
        self.semantic_analyzer = SemanticAnalyzer(
            spacy_model="en_core_web_sm",
            num_topics=settings.global_config.semantic_analysis.num_topics,
            passes=settings.global_config.semantic_analysis.lda_passes,
        )

        # Cache for processed chunks to avoid recomputation
        self._processed_chunks: dict[str, dict[str, Any]] = {}

        # Initialize thread pool for parallel processing
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def _identify_section_type(self, content: str) -> SectionType:
        """Identify the type of section based on its content.

        Args:
            content: The section content to analyze

        Returns:
            SectionType enum indicating the type of section
        """
        if re.match(r"^#{1,6}\s+", content):
            return SectionType.HEADER
        elif re.match(r"^```", content):
            return SectionType.CODE_BLOCK
        elif re.match(r"^[*-]\s+", content):
            return SectionType.LIST
        elif re.match(r"^\|", content):
            return SectionType.TABLE
        elif re.match(r"^>", content):
            return SectionType.QUOTE
        return SectionType.PARAGRAPH

    def _extract_section_metadata(self, section: Section) -> dict[str, Any]:
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
                breadcrumb = self._build_section_breadcrumb(section)
                if breadcrumb:
                    metadata["breadcrumb"] = breadcrumb

        return metadata

    def _build_section_breadcrumb(self, section: Section) -> str:
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

    def _parse_document_structure(self, text: str) -> list[dict[str, Any]]:
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

    def _get_section_path(
        self, header_item: dict[str, Any], structure: list[dict[str, Any]]
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

    def _merge_related_sections(
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

    def _split_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into chunks at level 0 (title) and level 1 headers only.
        Returns list of dictionaries with chunk text and metadata.
        """
        structure = self._parse_document_structure(text)
        sections = []
        current_section = None
        current_level = None
        current_title = None
        current_path = []

        for item in structure:
            if item["type"] == "header":
                level = item["level"]
                if level == 1 or (level == 0 and not sections):
                    # Save previous section if exists
                    if current_section is not None:
                        sections.append(
                            {
                                "content": current_section,
                                "level": current_level,
                                "title": current_title,
                                "path": list(current_path),
                            }
                        )
                    # Start new section
                    current_section = item["text"] + "\n"
                    current_level = level
                    current_title = item["title"]
                    current_path = self._get_section_path(item, structure)
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
                    current_title = "Preamble"
                    current_path = []
        # Add the last section
        if current_section is not None:
            sections.append(
                {
                    "content": current_section,
                    "level": current_level,
                    "title": current_title,
                    "path": list(current_path),
                }
            )
        # Ensure each section has proper metadata
        for section in sections:
            if "level" not in section:
                section["level"] = 0
            if "title" not in section:
                section["title"] = self._extract_section_title(section["content"])
            if "path" not in section:
                section["path"] = []
        return sections

    def _split_large_section(self, content: str, max_size: int) -> list[str]:
        """Split a large section into smaller chunks while preserving markdown structure.

        Args:
            content: Section content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        chunks = []
        current_chunk = ""

        # Safety limit to prevent infinite loops
        MAX_CHUNKS_PER_SECTION = 100

        # Split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", content)

        for para in paragraphs:
            # Safety check
            if len(chunks) >= MAX_CHUNKS_PER_SECTION:
                logger.warning(
                    f"Reached maximum chunks per section limit ({MAX_CHUNKS_PER_SECTION}). "
                    f"Section may be truncated."
                )
                break

            # If adding this paragraph would exceed max_size
            if len(current_chunk) + len(para) + 2 > max_size:  # +2 for newlines
                # If current chunk is not empty, save it
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # If paragraph itself is too large, split by sentences
                if len(para) > max_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    current_chunk = ""

                    for sentence in sentences:
                        # Safety check
                        if len(chunks) >= MAX_CHUNKS_PER_SECTION:
                            break

                        # If sentence itself is too large, split by words
                        if len(sentence) > max_size:
                            words = sentence.split()
                            for word in words:
                                # Safety check
                                if len(chunks) >= MAX_CHUNKS_PER_SECTION:
                                    break

                                # Handle extremely long words by truncating them
                                if len(word) > max_size:
                                    logger.warning(
                                        f"Word longer than max_size ({len(word)} > {max_size}), truncating: {word[:50]}..."
                                    )
                                    word = (
                                        word[: max_size - 10] + "..."
                                    )  # Truncate with ellipsis

                                if len(current_chunk) + len(word) + 1 > max_size:
                                    if (
                                        current_chunk.strip()
                                    ):  # Only add non-empty chunks
                                        chunks.append(current_chunk.strip())
                                    current_chunk = word + " "
                                else:
                                    current_chunk += word + " "
                        # Normal sentence handling
                        elif len(current_chunk) + len(sentence) + 1 > max_size:
                            if current_chunk.strip():  # Only add non-empty chunks
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence + " "
                        else:
                            current_chunk += sentence + " "
                else:
                    current_chunk = para + "\n\n"
            else:
                current_chunk += para + "\n\n"

        # Add the last chunk if not empty
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Final safety check
        if len(chunks) > MAX_CHUNKS_PER_SECTION:
            logger.warning(
                f"Generated {len(chunks)} chunks for section, limiting to {MAX_CHUNKS_PER_SECTION}"
            )
            chunks = chunks[:MAX_CHUNKS_PER_SECTION]

        return chunks

    def _process_chunk(
        self, chunk: str, chunk_index: int, total_chunks: int
    ) -> dict[str, Any]:
        """Process a single chunk in parallel.

        Args:
            chunk: The chunk to process
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks

        Returns:
            Dictionary containing processing results
        """
        logger.debug(
            "Processing chunk",
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_length=len(chunk),
        )

        # Check cache first
        if chunk in self._processed_chunks:
            return self._processed_chunks[chunk]

        # Perform semantic analysis
        logger.debug("Starting semantic analysis for chunk", chunk_index=chunk_index)
        analysis_result = self.semantic_analyzer.analyze_text(
            chunk, doc_id=f"chunk_{chunk_index}"
        )

        # Cache results
        results = {
            "entities": analysis_result.entities,
            "pos_tags": analysis_result.pos_tags,
            "dependencies": analysis_result.dependencies,
            "topics": analysis_result.topics,
            "key_phrases": analysis_result.key_phrases,
            "document_similarity": analysis_result.document_similarity,
        }
        self._processed_chunks[chunk] = results

        logger.debug("Completed semantic analysis for chunk", chunk_index=chunk_index)
        return results

    def _extract_section_title(self, chunk: str) -> str:
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

    def shutdown(self):
        """Shutdown the thread pool executor."""
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a markdown document into semantic sections.

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
            # Split text into semantic chunks
            logger.debug("Parsing document structure")
            chunks_metadata = self._split_text(document.content)

            if not chunks_metadata:
                self.progress_tracker.finish_chunking(document.id, 0, "markdown")
                return []

            # Safety limit to prevent excessive chunking
            MAX_CHUNKS_PER_DOCUMENT = 500
            if len(chunks_metadata) > MAX_CHUNKS_PER_DOCUMENT:
                logger.warning(
                    f"Document generated {len(chunks_metadata)} chunks, limiting to {MAX_CHUNKS_PER_DOCUMENT}. "
                    f"Document may be truncated. Document: {document.title}"
                )
                chunks_metadata = chunks_metadata[:MAX_CHUNKS_PER_DOCUMENT]

            # Create chunk documents
            chunked_docs = []
            for i, chunk_meta in enumerate(chunks_metadata):
                chunk_content = chunk_meta["content"]
                logger.debug(
                    f"Processing chunk {i+1}/{len(chunks_metadata)}",
                    extra={
                        "chunk_size": len(chunk_content),
                        "section_type": chunk_meta.get("section_type", "unknown"),
                        "level": chunk_meta.get("level", 0),
                    },
                )

                # Create chunk document with enhanced metadata
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=i,
                    total_chunks=len(chunks_metadata),
                    skip_nlp=False,
                )

                # Add markdown-specific metadata
                chunk_doc.metadata.update(chunk_meta)
                chunk_doc.metadata["chunking_strategy"] = "markdown"
                chunk_doc.metadata["parent_document_id"] = document.id

                # Add additional metadata fields expected by tests
                section_title = chunk_meta.get("title")
                if not section_title:
                    section_title = self._extract_section_title(chunk_content)
                chunk_doc.metadata["section_title"] = section_title
                chunk_doc.metadata["cross_references"] = self._extract_cross_references(
                    chunk_content
                )
                chunk_doc.metadata["hierarchy"] = self._map_hierarchical_relationships(
                    chunk_content
                )
                chunk_doc.metadata["entities"] = self._extract_entities(chunk_content)

                # Add topic analysis
                topic_analysis = self._analyze_topic(chunk_content)
                chunk_doc.metadata["topic_analysis"] = topic_analysis

                logger.debug(
                    "Created chunk document",
                    extra={
                        "chunk_id": chunk_doc.id,
                        "chunk_size": len(chunk_content),
                        "metadata_keys": list(chunk_doc.metadata.keys()),
                    },
                )

                chunked_docs.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "markdown"
            )

            logger.info(
                f"Markdown chunking completed for document: {document.title}",
                extra={
                    "document_id": document.id,
                    "total_chunks": len(chunked_docs),
                    "document_size": len(document.content),
                    "avg_chunk_size": (
                        sum(len(d.content) for d in chunked_docs) // len(chunked_docs)
                        if chunked_docs
                        else 0
                    ),
                },
            )

            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            # Fallback to default chunking
            self.progress_tracker.log_fallback(
                document.id, f"Markdown parsing failed: {str(e)}"
            )
            return self._fallback_chunking(document)

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Simple fallback chunking when the main strategy fails.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        logger.info("Using fallback chunking strategy for document")

        # Simple chunking implementation based on fixed size
        chunk_size = self.settings.global_config.chunking.chunk_size

        text = document.content
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
            chunked_docs.append(chunk_doc)

        return chunked_docs

    def _extract_cross_references(self, text: str) -> list[dict[str, str]]:
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

    def _extract_entities(self, text: str) -> list[dict[str, str]]:
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

    def _map_hierarchical_relationships(self, text: str) -> dict[str, Any]:
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

    def _analyze_topic(self, text: str) -> dict[str, Any]:
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

    def __del__(self):
        self.shutdown()
        if hasattr(self, "semantic_analyzer"):
            self.semantic_analyzer.clear_cache()
