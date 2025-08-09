"""HTML-specific chunk processor for creating HTML documents with enhanced metadata."""

from typing import Any

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.chunk_processor import BaseChunkProcessor
from qdrant_loader.core.document import Document

from .html_metadata_extractor import HTMLMetadataExtractor


class HTMLChunkProcessor(BaseChunkProcessor):
    """Chunk processor for HTML documents with semantic and accessibility analysis."""

    def __init__(self, settings: Settings):
        """Initialize the HTML chunk processor."""
        super().__init__(settings)

        # Initialize HTML-specific metadata extractor
        self.metadata_extractor = HTMLMetadataExtractor()

        # Get HTML strategy configuration
        self.html_config = settings.global_config.chunking.strategies.html
        self.max_chunk_size_for_nlp = self.html_config.max_chunk_size_for_nlp

    def create_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_metadata: dict[str, Any],
        chunk_index: int,
        total_chunks: int,
        skip_nlp: bool = False,
    ) -> Document:
        """Create an HTML chunk document with enhanced metadata."""

        # Generate unique chunk ID
        chunk_id = Document.generate_chunk_id(original_doc.id, chunk_index)

        # Extract HTML-specific hierarchical metadata
        enriched_metadata = self.metadata_extractor.extract_hierarchical_metadata(
            chunk_content, chunk_metadata, original_doc
        )

        # Add chunk-specific metadata
        enriched_metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "parent_document_id": original_doc.id,
                "chunking_strategy": "html_modular",
                "chunk_size": len(chunk_content),
            }
        )

        # Determine if we should skip NLP processing
        should_skip_nlp = skip_nlp or self.should_skip_semantic_analysis(
            chunk_content, enriched_metadata
        )

        # Extract entities if NLP is enabled
        entities = []
        if not should_skip_nlp:
            entities = self.metadata_extractor.extract_entities(chunk_content)
            enriched_metadata["entities"] = entities
            enriched_metadata["nlp_skipped"] = False
        else:
            enriched_metadata["entities"] = []
            enriched_metadata["nlp_skipped"] = True
            enriched_metadata["skip_reason"] = self._determine_skip_reason(
                chunk_content, enriched_metadata
            )

        # Create the chunk document
        chunk_doc = Document(
            id=chunk_id,
            content=chunk_content,
            metadata=enriched_metadata,
            source=original_doc.source,
            source_type=original_doc.source_type,
            url=original_doc.url,
            content_type=original_doc.content_type,
            title=self._generate_chunk_title(chunk_content, chunk_index, original_doc),
        )

        return chunk_doc

    def should_skip_semantic_analysis(
        self, content: str, chunk_metadata: dict[str, Any]
    ) -> bool:
        """Determine if semantic analysis should be skipped for HTML content."""

        # Skip for very large chunks to prevent performance issues
        if len(content) > self.max_chunk_size_for_nlp:
            return True

        # Skip for very small chunks (likely not meaningful)
        if len(content.strip()) < 50:
            return True

        # Check if content is mostly HTML markup without substantial text
        text_content = chunk_metadata.get("text_content", "")
        if text_content and len(text_content) < len(content) * 0.3:
            # Less than 30% is actual text content
            return True

        # Skip for certain HTML section types that are typically non-semantic
        section_type = chunk_metadata.get("section_type", "")
        if section_type in ["nav", "aside", "footer"]:
            # Navigation, sidebars, and footers are usually not meaningful for NLP
            return True

        # Skip if content is primarily code or script blocks
        if section_type == "code_block":
            return True

        # Skip if content has very high markup-to-text ratio
        markup_ratio = self._calculate_markup_ratio(content, text_content)
        if markup_ratio > 0.8:  # More than 80% markup
            return True

        # Skip if accessibility score is very low (might indicate poor content)
        accessibility_score = chunk_metadata.get("accessibility_score", 1.0)
        if accessibility_score < 0.2:
            return True

        return False

    def _generate_chunk_title(
        self, content: str, chunk_index: int, original_doc: Document
    ) -> str:
        """Generate a descriptive title for the HTML chunk."""
        try:
            # Try to extract title from HTML content using metadata extractor
            section_title = (
                self.metadata_extractor.document_parser.extract_section_title(content)
            )

            if section_title and section_title != "Untitled Section":
                return f"{section_title} (Chunk {chunk_index + 1})"

            # Fallback to original document title with chunk number
            if original_doc.title:
                return f"{original_doc.title} - Chunk {chunk_index + 1}"

            # Ultimate fallback
            return f"HTML Content - Chunk {chunk_index + 1}"

        except Exception:
            return f"HTML Content - Chunk {chunk_index + 1}"

    def _determine_skip_reason(
        self, content: str, chunk_metadata: dict[str, Any]
    ) -> str:
        """Determine the specific reason why NLP was skipped."""

        if len(content) > self.max_chunk_size_for_nlp:
            return f"content_too_large ({len(content)} > {self.max_chunk_size_for_nlp})"

        if len(content.strip()) < 50:
            return "content_too_small"

        text_content = chunk_metadata.get("text_content", "")
        if text_content and len(text_content) < len(content) * 0.3:
            return "low_text_ratio"

        section_type = chunk_metadata.get("section_type", "")
        if section_type in ["nav", "aside", "footer"]:
            return f"non_semantic_section ({section_type})"

        if section_type == "code_block":
            return "code_content"

        markup_ratio = self._calculate_markup_ratio(content, text_content)
        if markup_ratio > 0.8:
            return f"high_markup_ratio ({markup_ratio:.2f})"

        accessibility_score = chunk_metadata.get("accessibility_score", 1.0)
        if accessibility_score < 0.2:
            return f"low_accessibility_score ({accessibility_score:.2f})"

        return "unknown"

    def _calculate_markup_ratio(self, content: str, text_content: str) -> float:
        """Calculate the ratio of markup to text content."""
        if not content:
            return 0.0

        if not text_content:
            return 1.0  # All markup, no text

        markup_length = len(content) - len(text_content)
        return markup_length / len(content) if len(content) > 0 else 0.0
