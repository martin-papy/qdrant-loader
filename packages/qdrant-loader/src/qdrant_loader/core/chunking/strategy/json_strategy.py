"""JSON-specific chunking strategy for structured data."""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Dict, List, Union

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# Performance constants to prevent timeouts
MAX_JSON_SIZE_FOR_PARSING = 1_000_000  # 1MB limit for JSON parsing
MAX_OBJECTS_TO_PROCESS = 200  # Reduced limit for objects to prevent timeouts
MAX_CHUNK_SIZE_FOR_NLP = 20_000  # 20KB limit for NLP processing
MAX_RECURSION_DEPTH = 5  # Limit recursion depth for nested structures
MAX_ARRAY_ITEMS_TO_PROCESS = 50  # Limit array items to process
MAX_OBJECT_KEYS_TO_PROCESS = 100  # Limit object keys to process
SIMPLE_CHUNKING_THRESHOLD = 500_000  # Use simple chunking for files larger than 500KB


class JSONElementType(Enum):
    """Types of JSON elements."""

    OBJECT = "object"
    ARRAY = "array"
    ARRAY_ITEM = "array_item"
    PROPERTY = "property"
    VALUE = "value"
    ROOT = "root"


@dataclass
class JSONElement:
    """Represents a JSON element with its metadata."""

    name: str
    element_type: JSONElementType
    content: str
    value: Any
    path: str  # JSON path like "root.users[0].name"
    level: int = 0
    parent: Optional["JSONElement"] = None
    children: list["JSONElement"] = field(default_factory=list)
    size: int = 0  # Size in characters
    item_count: int = 0  # Number of items for arrays/objects

    def add_child(self, child: "JSONElement"):
        """Add a child element."""
        self.children.append(child)
        child.parent = self


class JSONChunkingStrategy(BaseChunkingStrategy):
    """Strategy for chunking JSON documents based on structure.

    This strategy parses JSON structure and creates chunks based on:
    - Top-level objects and arrays
    - Large nested objects
    - Array items (grouped when small)
    - Preserving JSON structure and hierarchy
    """

    def __init__(self, settings: Settings):
        """Initialize the JSON chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.logger = logger
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Cache for processed chunks
        self._processed_chunks = {}

        # Minimum size for standalone chunks
        self.min_chunk_size = 200

        # Maximum items to group together in arrays
        self.max_array_items_per_chunk = 50

    def _parse_json_structure(self, content: str) -> JSONElement | None:
        """Parse JSON content into structured elements.

        Args:
            content: JSON content to parse

        Returns:
            Root JSON element or None if parsing fails
        """
        # Performance check: skip parsing for very large files
        if len(content) > MAX_JSON_SIZE_FOR_PARSING:
            self.logger.info(
                f"JSON too large for structured parsing ({len(content)} bytes)"
            )
            return None

        try:
            data = json.loads(content)
            root_element = self._create_json_element(
                "root", data, JSONElementType.ROOT, "root"
            )
            # Initialize processed count for this document
            processed_count = [0]
            self._extract_json_elements(root_element, data, "root", 0, processed_count)
            self.logger.debug(
                f"Processed {processed_count[0]} JSON elements (limit: {MAX_OBJECTS_TO_PROCESS})"
            )
            return root_element

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Error parsing JSON structure: {e}")
            return None

    def _create_json_element(
        self,
        name: str,
        value: Any,
        element_type: JSONElementType,
        path: str,
        level: int = 0,
    ) -> JSONElement:
        """Create a JSON element from a value.

        Args:
            name: Element name
            value: JSON value
            element_type: Type of JSON element
            path: JSON path
            level: Nesting level

        Returns:
            JSONElement instance
        """
        # Convert value to JSON string for content
        try:
            content = json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            content = str(value)

        # Calculate size and item count
        size = len(content)
        item_count = 0

        if isinstance(value, dict):
            item_count = len(value)
        elif isinstance(value, list):
            item_count = len(value)

        return JSONElement(
            name=name,
            element_type=element_type,
            content=content,
            value=value,
            path=path,
            level=level,
            size=size,
            item_count=item_count,
        )

    def _extract_json_elements(
        self,
        parent_element: JSONElement,
        data: Any,
        path: str,
        level: int = 0,
        processed_count: list[int] | None = None,
    ):
        """Recursively extract JSON elements.

        Args:
            parent_element: Parent JSON element
            data: JSON data to process
            path: Current JSON path
            level: Current nesting level
            processed_count: Mutable list to track total processed objects
        """
        if processed_count is None:
            processed_count = [0]

        # Performance checks
        if level > MAX_RECURSION_DEPTH:  # Limit recursion depth
            return
        if processed_count[0] >= MAX_OBJECTS_TO_PROCESS:  # Global limit
            return
        if len(parent_element.children) >= MAX_ARRAY_ITEMS_TO_PROCESS:  # Local limit
            return

        if isinstance(data, dict):
            for i, (key, value) in enumerate(data.items()):
                if processed_count[0] >= MAX_OBJECTS_TO_PROCESS:
                    break
                if i >= MAX_OBJECT_KEYS_TO_PROCESS:  # Limit keys per object
                    break

                processed_count[0] += 1
                child_path = f"{path}.{key}"

                if isinstance(value, dict | list):
                    # Create element for complex values
                    element_type = (
                        JSONElementType.OBJECT
                        if isinstance(value, dict)
                        else JSONElementType.ARRAY
                    )
                    child_element = self._create_json_element(
                        key, value, element_type, child_path, level + 1
                    )
                    parent_element.add_child(child_element)

                    # Recursively process if not too large
                    if child_element.size < self.chunk_size:
                        self._extract_json_elements(
                            child_element, value, child_path, level + 1, processed_count
                        )
                else:
                    # Create element for simple values
                    child_element = self._create_json_element(
                        key, value, JSONElementType.PROPERTY, child_path, level + 1
                    )
                    parent_element.add_child(child_element)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if processed_count[0] >= MAX_OBJECTS_TO_PROCESS:
                    break
                if i >= MAX_ARRAY_ITEMS_TO_PROCESS:  # Limit array items
                    break

                processed_count[0] += 1
                child_path = f"{path}[{i}]"

                if isinstance(item, dict | list):
                    # Create element for complex array items
                    element_type = (
                        JSONElementType.OBJECT
                        if isinstance(item, dict)
                        else JSONElementType.ARRAY
                    )
                    child_element = self._create_json_element(
                        f"item_{i}", item, element_type, child_path, level + 1
                    )
                    parent_element.add_child(child_element)

                    # Recursively process if not too large
                    if child_element.size < self.chunk_size:
                        self._extract_json_elements(
                            child_element, item, child_path, level + 1, processed_count
                        )
                else:
                    # Create element for simple array items
                    child_element = self._create_json_element(
                        f"item_{i}",
                        item,
                        JSONElementType.ARRAY_ITEM,
                        child_path,
                        level + 1,
                    )
                    parent_element.add_child(child_element)

    def _group_small_elements(self, elements: list[JSONElement]) -> list[JSONElement]:
        """Group small JSON elements into larger chunks.

        Args:
            elements: List of JSON elements

        Returns:
            List of grouped elements
        """
        if not elements:
            return []

        grouped = []
        current_group = []
        current_size = 0

        for element in elements:
            # If element is large enough or is a significant structure, keep it separate
            if (
                element.size >= self.min_chunk_size
                or element.element_type
                in [JSONElementType.OBJECT, JSONElementType.ARRAY]
                or element.item_count > MAX_OBJECT_KEYS_TO_PROCESS
            ):

                # First, add any accumulated small elements
                if current_group:
                    grouped_element = self._create_grouped_element(current_group)
                    grouped.append(grouped_element)
                    current_group = []
                    current_size = 0

                # Add the large element
                grouped.append(element)
            else:
                # Accumulate small elements
                current_group.append(element)
                current_size += element.size

                # If accumulated size is large enough, create a grouped element
                if (
                    current_size >= self.min_chunk_size
                    or len(current_group) >= self.max_array_items_per_chunk
                ):
                    grouped_element = self._create_grouped_element(current_group)
                    grouped.append(grouped_element)
                    current_group = []
                    current_size = 0

        # Handle remaining small elements
        if current_group:
            grouped_element = self._create_grouped_element(current_group)
            grouped.append(grouped_element)

        return grouped

    def _create_grouped_element(self, elements: list[JSONElement]) -> JSONElement:
        """Create a grouped element from multiple small elements.

        Args:
            elements: List of elements to group

        Returns:
            Grouped JSON element
        """
        if not elements:
            raise ValueError("Cannot group empty list of elements")

        if len(elements) == 1:
            return elements[0]

        # Create grouped content
        if all(elem.element_type == JSONElementType.ARRAY_ITEM for elem in elements):
            # Group array items into an array
            grouped_value = [elem.value for elem in elements]
            grouped_content = json.dumps(grouped_value, indent=2, ensure_ascii=False)
            element_type = JSONElementType.ARRAY
            name = f"grouped_items_{len(elements)}"
        else:
            # Group mixed elements into an object
            grouped_value = {}
            for elem in elements:
                key = elem.name if elem.name != "root" else f"item_{len(grouped_value)}"
                grouped_value[key] = elem.value
            grouped_content = json.dumps(grouped_value, indent=2, ensure_ascii=False)
            element_type = JSONElementType.OBJECT
            name = f"grouped_elements_{len(elements)}"

        # Use the first element's path as base
        base_path = elements[0].path
        parent_path = (
            ".".join(base_path.split(".")[:-1]) if "." in base_path else "root"
        )
        grouped_path = f"{parent_path}.{name}"

        grouped_element = JSONElement(
            name=name,
            element_type=element_type,
            content=grouped_content,
            value=grouped_value,
            path=grouped_path,
            level=min(elem.level for elem in elements),
            size=len(grouped_content),
            item_count=len(elements),
        )

        return grouped_element

    def _split_large_element(self, element: JSONElement) -> list[JSONElement]:
        """Split a large JSON element into smaller chunks.

        Args:
            element: Large JSON element to split

        Returns:
            List of smaller elements
        """
        if element.size <= self.chunk_size:
            return [element]

        chunks = []

        if element.element_type == JSONElementType.ARRAY and isinstance(
            element.value, list
        ):
            # Split array into smaller arrays
            items = element.value
            chunk_size = self.max_array_items_per_chunk

            for i in range(0, len(items), chunk_size):
                chunk_items = items[i : i + chunk_size]
                chunk_content = json.dumps(chunk_items, indent=2, ensure_ascii=False)

                chunk_element = JSONElement(
                    name=f"{element.name}_chunk_{i//chunk_size + 1}",
                    element_type=JSONElementType.ARRAY,
                    content=chunk_content,
                    value=chunk_items,
                    path=f"{element.path}_chunk_{i//chunk_size + 1}",
                    level=element.level,
                    size=len(chunk_content),
                    item_count=len(chunk_items),
                )
                chunks.append(chunk_element)

        elif element.element_type == JSONElementType.OBJECT and isinstance(
            element.value, dict
        ):
            # Split object by grouping properties
            items = list(element.value.items())
            current_chunk = {}
            current_size = 0
            chunk_index = 1

            for key, value in items:
                item_content = json.dumps({key: value}, indent=2, ensure_ascii=False)
                item_size = len(item_content)

                if current_size + item_size > self.chunk_size and current_chunk:
                    # Create chunk from current items
                    chunk_content = json.dumps(
                        current_chunk, indent=2, ensure_ascii=False
                    )
                    chunk_element = JSONElement(
                        name=f"{element.name}_chunk_{chunk_index}",
                        element_type=JSONElementType.OBJECT,
                        content=chunk_content,
                        value=current_chunk.copy(),
                        path=f"{element.path}_chunk_{chunk_index}",
                        level=element.level,
                        size=len(chunk_content),
                        item_count=len(current_chunk),
                    )
                    chunks.append(chunk_element)

                    # Start new chunk
                    current_chunk = {key: value}
                    current_size = item_size
                    chunk_index += 1
                else:
                    current_chunk[key] = value
                    current_size += item_size

            # Add remaining items
            if current_chunk:
                chunk_content = json.dumps(current_chunk, indent=2, ensure_ascii=False)
                chunk_element = JSONElement(
                    name=f"{element.name}_chunk_{chunk_index}",
                    element_type=JSONElementType.OBJECT,
                    content=chunk_content,
                    value=current_chunk,
                    path=f"{element.path}_chunk_{chunk_index}",
                    level=element.level,
                    size=len(chunk_content),
                    item_count=len(current_chunk),
                )
                chunks.append(chunk_element)
        else:
            # For other types, split by lines as fallback
            lines = element.content.split("\n")
            current_chunk_lines = []
            current_size = 0
            chunk_index = 1

            for line in lines:
                line_size = len(line) + 1  # +1 for newline

                if current_size + line_size > self.chunk_size and current_chunk_lines:
                    chunk_content = "\n".join(current_chunk_lines)
                    chunk_element = JSONElement(
                        name=f"{element.name}_chunk_{chunk_index}",
                        element_type=element.element_type,
                        content=chunk_content,
                        value=chunk_content,  # Use content as value for text chunks
                        path=f"{element.path}_chunk_{chunk_index}",
                        level=element.level,
                        size=len(chunk_content),
                        item_count=len(current_chunk_lines),
                    )
                    chunks.append(chunk_element)

                    current_chunk_lines = [line]
                    current_size = line_size
                    chunk_index += 1
                else:
                    current_chunk_lines.append(line)
                    current_size += line_size

            # Add remaining lines
            if current_chunk_lines:
                chunk_content = "\n".join(current_chunk_lines)
                chunk_element = JSONElement(
                    name=f"{element.name}_chunk_{chunk_index}",
                    element_type=element.element_type,
                    content=chunk_content,
                    value=chunk_content,
                    path=f"{element.path}_chunk_{chunk_index}",
                    level=element.level,
                    size=len(chunk_content),
                    item_count=len(current_chunk_lines),
                )
                chunks.append(chunk_element)

        return chunks if chunks else [element]

    def _extract_json_metadata(self, element: JSONElement) -> dict[str, Any]:
        """Extract metadata from a JSON element.

        Args:
            element: JSON element to analyze

        Returns:
            Dictionary containing element metadata
        """
        metadata = {
            "element_type": element.element_type.value,
            "name": element.name,
            "path": element.path,
            "level": element.level,
            "size": element.size,
            "item_count": element.item_count,
            "has_nested_objects": False,
            "has_arrays": False,
            "data_types": [],
        }

        # Analyze value types
        if isinstance(element.value, dict):
            metadata["data_types"] = list(
                {type(v).__name__ for v in element.value.values()}
            )
            metadata["has_nested_objects"] = any(
                isinstance(v, dict) for v in element.value.values()
            )
            metadata["has_arrays"] = any(
                isinstance(v, list) for v in element.value.values()
            )
        elif isinstance(element.value, list) and element.value:
            metadata["data_types"] = list({type(v).__name__ for v in element.value})
            metadata["has_nested_objects"] = any(
                isinstance(v, dict) for v in element.value
            )
            metadata["has_arrays"] = any(isinstance(v, list) for v in element.value)
        else:
            metadata["data_types"] = [type(element.value).__name__]

        # Add parent context
        if element.parent:
            metadata.update(
                {
                    "parent_name": element.parent.name,
                    "parent_type": element.parent.element_type.value,
                    "parent_path": element.parent.path,
                }
            )

        return metadata

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a JSON document using structural boundaries.

        Args:
            document: Document to chunk

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
            # Performance check: for very large files, use simple chunking
            if len(document.content) > SIMPLE_CHUNKING_THRESHOLD:
                self.progress_tracker.log_fallback(
                    document.id, f"Large JSON file ({len(document.content)} bytes)"
                )
                return self._fallback_chunking(document)

            # Parse JSON structure
            root_element = self._parse_json_structure(document.content)

            if not root_element:
                self.progress_tracker.log_fallback(document.id, "JSON parsing failed")
                return self._fallback_chunking(document)

            # Get all elements to chunk
            elements_to_chunk = []

            if root_element.children:
                # Use top-level children as chunks
                elements_to_chunk = root_element.children
            else:
                # Use root element if no children
                elements_to_chunk = [root_element]

            # Group small elements and split large ones
            grouped_elements = self._group_small_elements(elements_to_chunk)
            final_elements = []

            for element in grouped_elements:
                if element.size > self.chunk_size:
                    # Split large elements
                    split_elements = self._split_large_element(element)
                    final_elements.extend(split_elements)
                else:
                    final_elements.append(element)

            # Limit total elements
            final_elements = final_elements[:MAX_OBJECTS_TO_PROCESS]

            if not final_elements:
                self.progress_tracker.finish_chunking(document.id, 0, "json")
                return []

            # Create chunked documents
            chunked_docs = []
            for i, element in enumerate(final_elements):
                self.logger.debug(
                    f"Processing element {i+1}/{len(final_elements)}",
                    extra={
                        "element_name": element.name,
                        "element_type": element.element_type.value,
                        "content_size": element.size,
                    },
                )

                # Create chunk document with optimized metadata processing
                skip_nlp = element.size > MAX_CHUNK_SIZE_FOR_NLP

                if skip_nlp:
                    # Create chunk without expensive NLP processing
                    chunk_doc = self._create_optimized_chunk_document(
                        original_doc=document,
                        chunk_content=element.content,
                        chunk_index=i,
                        total_chunks=len(final_elements),
                        skip_nlp=True,
                    )
                else:
                    # Use normal processing for smaller chunks
                    chunk_doc = self._create_chunk_document(
                        original_doc=document,
                        chunk_content=element.content,
                        chunk_index=i,
                        total_chunks=len(final_elements),
                    )

                # Add JSON-specific metadata
                json_metadata = self._extract_json_metadata(element)
                json_metadata["chunking_strategy"] = "json"
                json_metadata["chunking_method"] = "structured_json"
                json_metadata["parent_document_id"] = document.id
                chunk_doc.metadata.update(json_metadata)

                chunked_docs.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "json"
            )
            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            # Fallback to default chunking
            self.progress_tracker.log_fallback(
                document.id, f"JSON processing failed: {str(e)}"
            )
            return self._fallback_chunking(document)

    def _create_optimized_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        skip_nlp: bool = False,
    ) -> Document:
        """Create a chunk document with optimized processing.

        Args:
            original_doc: Original document
            chunk_content: Content of the chunk
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks
            skip_nlp: Whether to skip NLP processing

        Returns:
            Document: New document instance for the chunk
        """
        # Create enhanced metadata
        metadata = original_doc.metadata.copy()
        metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            }
        )

        if skip_nlp:
            # Skip expensive NLP processing for large chunks
            metadata.update(
                {
                    "entities": [],
                    "pos_tags": [],
                    "nlp_skipped": True,
                    "skip_reason": "chunk_too_large",
                }
            )
        else:
            try:
                # Process the chunk text to get additional features
                processed = self._process_text(chunk_content)
                metadata.update(
                    {
                        "entities": processed["entities"],
                        "pos_tags": processed["pos_tags"],
                        "nlp_skipped": False,
                    }
                )
            except Exception as e:
                self.logger.warning(
                    f"NLP processing failed for chunk {chunk_index}: {e}"
                )
                metadata.update(
                    {
                        "entities": [],
                        "pos_tags": [],
                        "nlp_skipped": True,
                        "skip_reason": "nlp_error",
                    }
                )

        return Document(
            content=chunk_content,
            metadata=metadata,
            source=original_doc.source,
            source_type=original_doc.source_type,
            url=original_doc.url,
            title=original_doc.title,
            content_type=original_doc.content_type,
        )

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Fallback to simple text-based chunking when JSON parsing fails.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.warning("Falling back to simple text chunking for JSON document")

        # Use simple line-based splitting for JSON
        lines = document.content.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1  # +1 for newline

            if current_size + line_size > self.chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size

        # Add remaining lines
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # Create chunk documents (limited)
        chunked_docs = []
        for i, chunk_content in enumerate(chunks[:MAX_OBJECTS_TO_PROCESS]):
            chunk_doc = self._create_optimized_chunk_document(
                original_doc=document,
                chunk_content=chunk_content,
                chunk_index=i,
                total_chunks=len(chunks),
                skip_nlp=len(chunk_content) > MAX_CHUNK_SIZE_FOR_NLP,
            )

            chunk_doc.id = Document.generate_chunk_id(document.id, i)
            chunk_doc.metadata["parent_document_id"] = document.id
            chunk_doc.metadata["chunking_method"] = "fallback_text"

            chunked_docs.append(chunk_doc)

        return chunked_docs

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks (required by base class).

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        # This method is required by the base class but not used in our implementation
        # We override chunk_document instead
        return [text]
