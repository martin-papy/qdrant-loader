"""Markdown-specific chunking strategy."""

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Tuple
import concurrent.futures
import structlog

import spacy
from spacy.cli.download import download

from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document
from qdrant_loader.core.text_processing.topic_modeler import TopicModeler
from qdrant_loader.config import Settings, GlobalConfig, SemanticAnalysisConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings, GlobalConfig

logger = structlog.get_logger(__name__)


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

        # Initialize spaCy for entity recognition
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.info("Downloading spaCy model...")
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

        # Initialize topic modeler
        self.topic_modeler = TopicModeler(
            num_topics=settings.global_config.semantic_analysis.num_topics,
            passes=settings.global_config.semantic_analysis.lda_passes
        )
        
        # Cache for processed chunks
        self._processed_chunks = {}
        
        # Initialize thread pool for parallel processing
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text using spaCy.

        Args:
            text: The text to analyze

        Returns:
            List of dictionaries containing entity information
        """
        self.logger.debug("Starting entity extraction", text_length=len(text))
        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            entities.append(
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "description": self.nlp.vocab.strings[ent.label_],
                }
            )

        self.logger.debug("Entity extraction completed", entity_count=len(entities))
        return entities

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

    def _analyze_topic(self, text: str) -> Dict[str, Any]:
        """Analyze the main topics in the text using LDA.

        Args:
            text: The text to analyze

        Returns:
            Dictionary containing topic analysis results
        """
        # Check cache first
        if text in self._processed_chunks:
            return self._processed_chunks[text]["topic_analysis"]
            
        result = self.topic_modeler.infer_topics(text)
        
        # Cache the result
        if text not in self._processed_chunks:
            self._processed_chunks[text] = {}
        self._processed_chunks[text]["topic_analysis"] = result
        
        return result

    def _map_hierarchical_relationships(self, headers: List[Tuple[int, str]]) -> Dict[str, Any]:
        """Map hierarchical relationships between sections.

        Args:
            headers: List of (level, text) tuples for each header

        Returns:
            Dictionary containing hierarchical relationship information
        """
        self.logger.debug("Starting hierarchical relationship mapping", header_count=len(headers))
        hierarchy = defaultdict(list)
        current_path = []

        for level, text in headers:
            # Pop levels until we find the parent
            while current_path and current_path[-1][0] >= level:
                current_path.pop()

            # Add current header to path
            current_path.append((level, text))

            # Add to hierarchy
            if len(current_path) > 1:
                parent = current_path[-2][1]
                hierarchy[parent].append(text)

        self.logger.debug("Completed hierarchical mapping", hierarchy_size=len(hierarchy))
        return dict(hierarchy)

    def _split_text(self, text: str) -> list[str]:
        """Split markdown text into chunks based on section headers.

        The strategy:
        1. Identifies all section headers (##, ###, etc.)
        2. Creates chunks that include:
           - The section header
           - All content until the next header of same or higher level
           - Parent section headers for context
           - Semantic analysis results

        Args:
            text: The markdown text to split

        Returns:
            List of text chunks, each containing a complete section
        """
        self.logger.debug("Starting text splitting", text_length=len(text))
        if not text:
            self.logger.debug("Empty text, returning empty chunk")
            return [""]

        # Split text into lines for processing
        lines = text.splitlines()
        chunks = []
        current_chunk = []
        header_stack = []  # Stack to track parent headers
        all_headers = []

        for line in lines:
            # Check if line is a header
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            
            if header_match:
                # If we have a current chunk, save it
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                
                # Update header stack
                level = len(header_match.group(1))
                text = header_match.group(2)
                
                # Pop headers until we find the parent
                while header_stack and header_stack[-1][0] >= level:
                    header_stack.pop()
                
                # Add current header to stack
                header_stack.append((level, text))
                all_headers.append((level, text))
                
                # Start new chunk with header
                current_chunk = [line]
            else:
                # Add non-header line to current chunk
                current_chunk.append(line)

        # Add the last chunk if it exists
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        self.logger.debug("Text splitting completed", num_chunks=len(chunks))
        return chunks

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
        entities = self._extract_entities(chunk)
        cross_refs = self._detect_cross_references(chunk)
        topic_analysis = self._analyze_topic(chunk)
        
        # Cache results
        results = {
            "entities": entities,
            "cross_refs": cross_refs,
            "topic_analysis": topic_analysis
        }
        self._processed_chunks[chunk] = results
        
        self.logger.debug("Completed semantic analysis for chunk", chunk_index=chunk_index)
        return results

    def chunk_document(self, document: Document) -> list[Document]:
        """Split a markdown document into chunks while preserving metadata.

        Args:
            document: The markdown document to chunk

        Returns:
            List of chunked documents with preserved metadata and section info
        """
        self.logger.debug(
            "Starting document chunking",
            document_id=document.id,
            content_length=len(document.content),
            source=document.source,
            source_type=document.source_type
        )

        chunks = self._split_text(document.content)
        chunked_documents = []

        # Extract all headers for hierarchical mapping
        headers = re.findall(r"^(#{1,6})\s+(.+)$", document.content, re.MULTILINE)
        header_info = [(len(h[0]), h[1]) for h in headers]
        hierarchy = self._map_hierarchical_relationships(header_info)

        # Train LDA model on all chunks if we have enough data
        if len(chunks) >= 5:
            self.logger.info("Training LDA model on document chunks", num_chunks=len(chunks))
            self.topic_modeler.train_model(chunks)
        else:
            self.logger.warning(
                "Skipping LDA training due to insufficient data",
                num_chunks=len(chunks)
            )

        # Process chunks in parallel
        futures = []
        for i, chunk in enumerate(chunks):
            future = self._executor.submit(self._process_chunk, chunk, i, len(chunks))
            futures.append((i, future))

        # Collect results and create documents
        for i, future in futures:
            try:
                chunk = chunks[i]
                results = future.result(timeout=30)  # 30 second timeout per chunk
                
                # Extract section information
                first_line = chunk.splitlines()[0] if chunk else ""
                header_match = re.match(r"^(#{1,6})\s+(.+)$", first_line)

                section_metadata = {
                    "section_level": len(header_match.group(1)) if header_match else 0,
                    "section_title": header_match.group(2) if header_match else "Introduction",
                    "is_section_start": True,
                    "entities": results["entities"],
                    "cross_references": results["cross_refs"],
                    "topic_analysis": results["topic_analysis"],
                    "hierarchy": hierarchy,
                }

                # Create chunk document with section metadata
                self.logger.debug("Creating chunk document", chunk_index=i)
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk,
                    chunk_index=i,
                    total_chunks=len(chunks)
                )

                # Add section-specific metadata
                chunk_doc.metadata.update(section_metadata)
                chunked_documents.append(chunk_doc)
                self.logger.debug("Chunk document created", chunk_index=i, chunk_id=chunk_doc.id)
                
            except concurrent.futures.TimeoutError:
                self.logger.error("Chunk processing timed out", chunk_index=i)
                continue
            except Exception as e:
                self.logger.error("Error processing chunk", chunk_index=i, error=str(e))
                continue

        return chunked_documents

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
