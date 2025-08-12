"""JSON chunk processor for creating optimized chunk documents."""

from typing import Any

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.chunk_processor import BaseChunkProcessor
from qdrant_loader.core.chunking.strategy.json.json_document_parser import JSONElement
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)


class JSONChunkProcessor(BaseChunkProcessor):
    """Chunk processor for JSON documents."""

    def __init__(self, settings: Settings):
        """Initialize JSON chunk processor.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.json_config = settings.global_config.chunking.strategies.json_strategy

    def create_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        chunk_metadata: dict[str, Any],
        skip_nlp: bool = False,
    ) -> Document:
        """Create a chunk document with JSON-specific optimizations.

        Args:
            original_doc: Original source document
            chunk_content: Content for this chunk
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            chunk_metadata: Metadata specific to this chunk
            skip_nlp: Whether to skip expensive NLP processing

        Returns:
            Document representing the chunk
        """
        # Determine if we should skip NLP based on content characteristics
        skip_nlp or self._should_skip_nlp_for_json(chunk_content, chunk_metadata)

        # Create base chunk document
        chunk_doc = Document(
            content=chunk_content,
            source=original_doc.source,
            source_type=original_doc.source_type,
            title=f"{original_doc.title}_chunk_{chunk_index + 1}",
            url=original_doc.url,
            content_type=original_doc.content_type,
            metadata=self._create_enhanced_metadata(
                original_doc, chunk_metadata, chunk_index, total_chunks
            ),
        )

        return chunk_doc

    def create_optimized_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        skip_nlp: bool = True,
    ) -> Document:
        """Create an optimized chunk document for large JSON elements.

        Args:
            original_doc: Original source document
            chunk_content: Content for this chunk
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            skip_nlp: Whether to skip NLP processing (default True for optimization)

        Returns:
            Optimized Document representing the chunk
        """
        # Create minimal metadata for large chunks
        minimal_metadata = {
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "chunk_size": len(chunk_content),
            "content_type": "json",
            "processing_mode": "optimized",
            "nlp_skipped": skip_nlp,
            "optimization_reason": "large_json_chunk",
        }

        enhanced_metadata = self._create_enhanced_metadata(
            original_doc, minimal_metadata, chunk_index, total_chunks
        )

        chunk_doc = Document(
            content=chunk_content,
            source=original_doc.source,
            source_type=original_doc.source_type,
            title=f"{original_doc.title}_chunk_{chunk_index + 1}",
            url=original_doc.url,
            content_type=original_doc.content_type,
            metadata=enhanced_metadata,
        )

        return chunk_doc

    def create_json_element_chunk_document(
        self,
        original_doc: Document,
        element: JSONElement,
        chunk_index: int,
        total_chunks: int,
        element_metadata: dict[str, Any] = None,
    ) -> Document:
        """Create a chunk document from a JSON element.

        Args:
            original_doc: Original source document
            element: JSON element to create chunk from
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            element_metadata: Additional metadata for the element

        Returns:
            Document representing the chunk
        """
        # Determine if we should skip NLP
        skip_nlp = element.size > self.json_config.max_chunk_size_for_nlp

        # Combine element metadata with chunk metadata
        chunk_metadata = {
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "chunk_size": len(element.content),
            "content_type": "json",
            "element_type": element.element_type.value,
            "element_name": element.name,
            "json_path": element.path,
            "nesting_level": element.level,
            "item_count": element.item_count,
            "nlp_skipped": skip_nlp,
        }

        if element_metadata:
            chunk_metadata.update(element_metadata)

        enhanced_metadata = self._create_enhanced_metadata(
            original_doc, chunk_metadata, chunk_index, total_chunks
        )

        chunk_doc = Document(
            content=element.content,
            source=original_doc.source,
            source_type=original_doc.source_type,
            title=f"{original_doc.title}_chunk_{chunk_index + 1}",
            url=original_doc.url,
            content_type=original_doc.content_type,
            metadata=enhanced_metadata,
        )

        return chunk_doc

    def _should_skip_nlp_for_json(self, content: str, metadata: dict[str, Any]) -> bool:
        """Determine if NLP processing should be skipped for JSON content.

        Args:
            content: JSON content to analyze
            metadata: Chunk metadata

        Returns:
            True if NLP should be skipped
        """
        # Skip NLP for large chunks
        if len(content) > self.json_config.max_chunk_size_for_nlp:
            return True

        # Skip NLP for certain JSON types that are primarily data
        json_type = metadata.get("json_type", "")
        if json_type in ["list", "dict"] and metadata.get("structure_type") in [
            "primitive_collection",
            "configuration",
            "data_container",
        ]:
            return True

        # Skip NLP for highly structured data with minimal text
        if self._is_minimal_text_content(content):
            return True

        # Skip NLP for configuration-like structures
        if self._is_configuration_structure(metadata):
            return True

        return False

    def _is_minimal_text_content(self, content: str) -> bool:
        """Check if JSON content has minimal natural language text.

        Args:
            content: JSON content to analyze

        Returns:
            True if content has minimal text suitable for NLP
        """
        try:
            import json

            data = json.loads(content)

            # Count text vs structural characters
            text_chars = 0
            (
                content.count("{")
                + content.count("}")
                + content.count("[")
                + content.count("]")
                + content.count(",")
                + content.count(":")
            )

            def count_text_in_values(obj):
                nonlocal text_chars
                if isinstance(obj, str):
                    # Only count strings that look like natural language
                    if len(obj) > 10 and any(c.isalpha() for c in obj) and " " in obj:
                        text_chars += len(obj)
                elif isinstance(obj, dict):
                    for value in obj.values():
                        count_text_in_values(value)
                elif isinstance(obj, list):
                    for item in obj:
                        count_text_in_values(item)

            count_text_in_values(data)

            # If text content is less than 20% of total, consider it minimal
            total_content_chars = len(content)
            text_ratio = text_chars / max(total_content_chars, 1)

            return text_ratio < 0.2

        except json.JSONDecodeError:
            # If not valid JSON, don't skip NLP
            return False

    def _is_configuration_structure(self, metadata: dict[str, Any]) -> bool:
        """Check if the structure represents configuration data.

        Args:
            metadata: Chunk metadata

        Returns:
            True if structure looks like configuration
        """
        structure_type = metadata.get("structure_type", "")
        if structure_type == "configuration":
            return True

        # Check for configuration patterns in metadata
        config_patterns = metadata.get("configuration_indicators", [])
        if len(config_patterns) >= 2:  # Multiple configuration indicators
            return True

        # Check for schema patterns that indicate configuration
        schema_patterns = metadata.get("schema_patterns", [])
        config_schema_patterns = [
            "configuration_object",
            "feature_flags",
            "typed_value",
        ]
        if any(pattern in config_schema_patterns for pattern in schema_patterns):
            return True

        return False

    def _create_enhanced_metadata(
        self,
        original_doc: Document,
        chunk_metadata: dict[str, Any],
        chunk_index: int,
        total_chunks: int,
    ) -> dict[str, Any]:
        """Create enhanced metadata for JSON chunk documents.

        Args:
            original_doc: Original source document
            chunk_metadata: Chunk-specific metadata
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks

        Returns:
            Enhanced metadata dictionary
        """
        # Start with original document metadata
        enhanced_metadata = original_doc.metadata.copy()

        # Add chunking information
        enhanced_metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "chunk_size": chunk_metadata.get(
                    "chunk_size", len(chunk_metadata.get("content", ""))
                ),
                "chunking_strategy": "json",
                "is_chunk": True,
                "parent_document_id": original_doc.id,
            }
        )

        # Add JSON-specific metadata
        enhanced_metadata.update(
            {
                "content_type": "json",
                "json_processing_mode": "modular_architecture",
                "supports_schema_inference": self.json_config.enable_schema_inference,
            }
        )

        # Merge chunk-specific metadata
        enhanced_metadata.update(chunk_metadata)

        # Add processing indicators
        enhanced_metadata.update(
            {
                "processed_with_json_components": True,
                "json_config_version": "modular_v1",
                "chunk_quality_indicators": self._calculate_chunk_quality_indicators(
                    chunk_metadata
                ),
            }
        )

        return enhanced_metadata

    def _calculate_chunk_quality_indicators(
        self, chunk_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate quality indicators for JSON chunks.

        Args:
            chunk_metadata: Chunk metadata

        Returns:
            Dictionary of quality indicators
        """
        indicators = {
            "size_appropriate": True,
            "structure_preserved": True,
            "schema_coherent": True,
            "nlp_suitable": True,
        }

        # Size appropriateness
        chunk_size = chunk_metadata.get("chunk_size", 0)
        if chunk_size < 100:
            indicators["size_appropriate"] = False
        elif chunk_size > self.settings.global_config.chunking.chunk_size * 2:
            indicators["size_appropriate"] = False

        # Structure preservation
        element_type = chunk_metadata.get("element_type", "")
        if element_type in ["grouped_elements", "chunk"]:
            indicators["structure_preserved"] = False

        # Schema coherence
        if not chunk_metadata.get("is_valid_json", True):
            indicators["schema_coherent"] = False

        # NLP suitability
        if chunk_metadata.get("nlp_skipped", False):
            indicators["nlp_suitable"] = False

        # Overall quality score
        quality_score = sum(indicators.values()) / len(indicators)
        indicators["overall_quality_score"] = quality_score

        return indicators
