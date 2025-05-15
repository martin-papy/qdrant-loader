"""Markdown-specific chunking strategy."""

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Optional
import concurrent.futures
import structlog
from dataclasses import dataclass, field
from enum import Enum

from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document
from qdrant_loader.core.text_processing.semantic_analyzer import SemanticAnalyzer
from qdrant_loader.config import Settings, GlobalConfig, SemanticAnalysisConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings, GlobalConfig

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
    type: SectionType
    level: int
    content: str
    parent: Optional['Section'] = None
    children: List['Section'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}

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
        """Initialize the markdown chunking strategy.

        Args:
            settings: The application settings
        """
        super().__init__(settings)
        self.logger = structlog.get_logger(__name__)

        # Initialize semantic analyzer
        self.semantic_analyzer = SemanticAnalyzer(
            spacy_model="en_core_web_sm",
            num_topics=settings.global_config.semantic_analysis.num_topics,
            passes=settings.global_config.semantic_analysis.lda_passes
        )
        
        # Cache for processed chunks
        self._processed_chunks = {}
        
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

    def _extract_section_metadata(self, section: Section) -> Dict[str, Any]:
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
        }

        # Add parent section info if available
        if section.parent:
            metadata["parent_title"] = section.parent.content.split("\n")[0].strip("# ")
            metadata["parent_level"] = section.parent.level

        return metadata

    def _build_section_tree(self, text: str) -> List[Section]:
        """Build a tree of sections from markdown text.

        Args:
            text: The markdown text to analyze

        Returns:
            List of root sections with their hierarchy
        """
        lines = text.splitlines()
        sections = []
        current_section = None
        section_stack = []

        for line in lines:
            # Check for headers
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1))
                content = line
                
                # Create new section
                new_section = Section(
                    type=SectionType.HEADER,
                    level=level,
                    content=content,
                    metadata={}
                )
                
                # Find parent section
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                
                if section_stack:
                    parent = section_stack[-1]
                    new_section.parent = parent
                    parent.children.append(new_section)
                else:
                    sections.append(new_section)
                
                section_stack.append(new_section)
                current_section = new_section
            else:
                # Add content to current section or create new paragraph section
                if current_section:
                    current_section.content += "\n" + line
                else:
                    new_section = Section(
                        type=SectionType.PARAGRAPH,
                        level=0,
                        content=line,
                        metadata={}
                    )
                    sections.append(new_section)
                    current_section = new_section

        # Process all sections to identify their types and extract metadata
        for section in sections:
            section.type = self._identify_section_type(section.content)
            section.metadata = self._extract_section_metadata(section)

        return sections

    def _analyze_section_relationships(self, sections: List[Section]) -> Dict[str, Any]:
        """Analyze relationships between sections.

        Args:
            sections: List of sections to analyze

        Returns:
            Dictionary containing relationship information
        """
        relationships = {
            "hierarchy": defaultdict(list),
            "cross_references": [],
            "related_sections": defaultdict(list)
        }

        # Build hierarchy
        for section in sections:
            if section.parent:
                relationships["hierarchy"][section.parent.content].append(section.content)

        # Find cross-references
        for section in sections:
            refs = self._detect_cross_references(section.content)
            if refs:
                relationships["cross_references"].extend(refs)

        # Find related sections based on content similarity
        for i, section1 in enumerate(sections):
            for section2 in sections[i+1:]:
                if self._are_sections_related(section1, section2):
                    relationships["related_sections"][section1.content].append(section2.content)

        return relationships

    def _are_sections_related(self, section1: Section, section2: Section) -> bool:
        """Determine if two sections are related based on content similarity.

        Args:
            section1: First section to compare
            section2: Second section to compare

        Returns:
            Boolean indicating if sections are related
        """
        # Use semantic analyzer for similarity comparison
        analysis1 = self.semantic_analyzer.analyze_text(section1.content)
        analysis2 = self.semantic_analyzer.analyze_text(section2.content)
        
        # Compare document similarities
        similarity = analysis1.document_similarity.get(section2.content, 0.0)
        return similarity > 0.3

    def _detect_cross_references(self, text: str) -> List[Dict[str, Any]]:
        """Detect cross-references in markdown text.

        Args:
            text: The text to analyze

        Returns:
            List of dictionaries containing cross-reference information
        """
        self.logger.debug("Starting cross-reference detection", text_length=len(text))
        cross_refs = []

        # Find markdown links
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(link_pattern, text):
            cross_refs.append(
                {
                    "text": match.group(1),
                    "link": match.group(2),
                    "start": match.start(),
                    "end": match.end(),
                }
            )

        self.logger.debug("Cross-reference detection completed", ref_count=len(cross_refs))
        return cross_refs

    def _process_chunk(self, chunk: str, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
        """Process a single chunk in parallel.

        Args:
            chunk: The chunk to process
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks

        Returns:
            Dictionary containing processing results
        """
        self.logger.debug(
            "Processing chunk",
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_length=len(chunk)
        )

        # Check cache first
        if chunk in self._processed_chunks:
            return self._processed_chunks[chunk]

        # Perform semantic analysis
        self.logger.debug("Starting semantic analysis for chunk", chunk_index=chunk_index)
        analysis_result = self.semantic_analyzer.analyze_text(chunk, doc_id=f"chunk_{chunk_index}")
        
        # Cache results
        results = {
            "entities": analysis_result.entities,
            "pos_tags": analysis_result.pos_tags,
            "dependencies": analysis_result.dependencies,
            "topics": analysis_result.topics,
            "key_phrases": analysis_result.key_phrases,
            "document_similarity": analysis_result.document_similarity
        }
        self._processed_chunks[chunk] = results
        
        self.logger.debug("Completed semantic analysis for chunk", chunk_index=chunk_index)
        return results

    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks based on Markdown headers.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        # Split by headers (lines starting with #)
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_header = None

        for line in lines:
            if line.startswith('#'):
                # If we have a current chunk, save it
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                current_header = line
                current_chunk.append(line)
            else:
                current_chunk.append(line)

        # Add the last chunk if it exists
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def chunk_document(self, document: Document) -> List[Document]:
        """Chunk a Markdown document.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.debug(
            "Starting Markdown chunking",
            extra={
                "source": document.source,
                "source_type": document.source_type
            }
        )

        try:
            # Split text into chunks
            text_chunks = self._split_text(document.content)
            
            # Create chunked documents
            chunked_docs = []
            for i, chunk in enumerate(text_chunks):
                # Extract header if present
                header = None
                lines = chunk.split('\n')
                if lines and lines[0].startswith('#'):
                    header = lines[0].lstrip('#').strip()
                
                # Create chunk document with metadata
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk,
                    chunk_index=i,
                    total_chunks=len(text_chunks)
                )
                
                # Add Markdown-specific metadata
                chunk_doc.metadata.update({
                    "section_title": header or "Introduction",
                    "cross_references": self._extract_cross_references(chunk),
                    "entities": self._extract_entities(chunk),
                    "hierarchy": self._map_hierarchical_relationships(chunk),
                    "topic_analysis": self._analyze_topic(chunk)
                })
                
                chunked_docs.append(chunk_doc)
            
            self.logger.debug(
                "Completed Markdown chunking",
                extra={
                    "source": document.source,
                    "chunk_count": len(chunked_docs)
                }
            )
            
            return chunked_docs

        except Exception as e:
            self.logger.error(
                "Error in Markdown chunking",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "source": document.source
                }
            )
            raise

    def _extract_cross_references(self, text: str) -> List[Dict[str, str]]:
        """Extract cross-references from text.

        Args:
            text: Text to analyze

        Returns:
            List of cross-references
        """
        # Simple implementation - extract markdown links
        references = []
        lines = text.split('\n')
        for line in lines:
            if '[' in line and '](' in line:
                # Extract link text and URL
                parts = line.split('](')
                if len(parts) == 2:
                    link_text = parts[0].split('[')[1]
                    url = parts[1].split(')')[0]
                    references.append({
                        "text": link_text,
                        "url": url
                    })
        return references

    def _extract_entities(self, text: str) -> List[Dict[str, str]]:
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
                entities.append({
                    "text": " ".join(current_entity),
                    "type": "UNKNOWN"  # Could be enhanced with NER
                })
                current_entity = []
        
        if current_entity:
            entities.append({
                "text": " ".join(current_entity),
                "type": "UNKNOWN"
            })
        
        return entities

    def _map_hierarchical_relationships(self, text: str) -> Dict[str, Any]:
        """Map hierarchical relationships in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary of hierarchical relationships
        """
        hierarchy = {}
        current_level = 0
        current_path = []
        
        lines = text.split('\n')
        for line in lines:
            if line.startswith('#'):
                level = len(line.split()[0])
                title = line.lstrip('#').strip()
                
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

    def _analyze_topic(self, text: str) -> Dict[str, Any]:
        """Analyze topic of text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with topic analysis results
        """
        # Simple implementation - return basic topic info
        return {
            "topics": ["general"],  # Could be enhanced with LDA
            "coherence": 0.5  # Could be enhanced with topic coherence metrics
        }

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        if hasattr(self, 'semantic_analyzer'):
            self.semantic_analyzer.clear_cache()
