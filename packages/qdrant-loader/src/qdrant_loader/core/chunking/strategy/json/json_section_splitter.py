"""JSON section splitter for intelligent element grouping and splitting."""

import json
from typing import Any

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.section_splitter import (
    BaseSectionSplitter,
)
from qdrant_loader.core.chunking.strategy.json.json_document_parser import (
    JSONElement,
    JSONElementType,
)
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)


class JSONSectionSplitter(BaseSectionSplitter):
    """Section splitter for JSON documents."""

    def __init__(self, settings: Settings):
        """Initialize JSON section splitter.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.json_config = settings.global_config.chunking.strategies.json_strategy
        self.min_chunk_size = 200  # Minimum size for standalone chunks

    def split_sections(
        self, content: str, document: Document = None
    ) -> list[dict[str, Any]]:
        """Split JSON content into logical sections.

        Args:
            content: JSON content to split
            document: Source document (optional)

        Returns:
            List of section dictionaries with content and metadata
        """
        # This method is kept for base class compatibility
        # The real JSON splitting happens in split_json_elements
        return [{"content": content, "metadata": {}}]

    def split_json_elements(self, elements: list[JSONElement]) -> list[JSONElement]:
        """Split JSON elements into optimally-sized chunks.

        Args:
            elements: List of JSON elements to process

        Returns:
            List of optimally grouped/split elements
        """
        if not elements:
            return []

        # Step 1: Group small elements
        grouped_elements = self._group_small_elements(elements)

        # Step 2: Split large elements
        final_elements = []
        for element in grouped_elements:
            if element.size > self.chunk_size:
                split_elements = self._split_large_element(element)
                final_elements.extend(split_elements)
            else:
                final_elements.append(element)

        # Step 3: Apply limits
        final_elements = final_elements[: self.json_config.max_objects_to_process]

        return final_elements

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
                or element.item_count > self.json_config.max_object_keys_to_process
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
                    or len(current_group) >= self.json_config.max_array_items_per_chunk
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
            try:
                grouped_content = json.dumps(
                    grouped_value, indent=2, ensure_ascii=False
                )
            except (TypeError, ValueError):
                grouped_content = str(grouped_value)
            element_type = JSONElementType.ARRAY
            name = f"grouped_items_{len(elements)}"
        else:
            # Group mixed elements into an object
            grouped_value = {}
            for elem in elements:
                key = elem.name if elem.name != "root" else f"item_{len(grouped_value)}"
                grouped_value[key] = elem.value
            try:
                grouped_content = json.dumps(
                    grouped_value, indent=2, ensure_ascii=False
                )
            except (TypeError, ValueError):
                grouped_content = str(grouped_value)
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
            chunk_size = self.json_config.max_array_items_per_chunk

            for i in range(0, len(items), chunk_size):
                chunk_items = items[i : i + chunk_size]
                try:
                    chunk_content = json.dumps(
                        chunk_items, indent=2, ensure_ascii=False
                    )
                except (TypeError, ValueError):
                    chunk_content = str(chunk_items)

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
                try:
                    item_content = json.dumps(
                        {key: value}, indent=2, ensure_ascii=False
                    )
                except (TypeError, ValueError):
                    item_content = f'"{key}": {str(value)}'
                item_size = len(item_content)

                if current_size + item_size > self.chunk_size and current_chunk:
                    # Create chunk from current items
                    try:
                        chunk_content = json.dumps(
                            current_chunk, indent=2, ensure_ascii=False
                        )
                    except (TypeError, ValueError):
                        chunk_content = str(current_chunk)

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
                try:
                    chunk_content = json.dumps(
                        current_chunk, indent=2, ensure_ascii=False
                    )
                except (TypeError, ValueError):
                    chunk_content = str(current_chunk)

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

    def merge_small_sections(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge small JSON sections to optimize chunk sizes.

        Args:
            sections: List of section dictionaries

        Returns:
            List of merged sections
        """
        if not sections:
            return []

        merged = []
        current_merged = None
        current_size = 0

        for section in sections:
            section_size = len(section.get("content", ""))

            # If section is large enough or we have a full merged section, finalize current
            if (
                section_size >= self.min_chunk_size
                or current_size + section_size > self.chunk_size
            ) and current_merged:
                merged.append(current_merged)
                current_merged = None
                current_size = 0

            # Start new merged section if needed
            if current_merged is None:
                current_merged = section.copy()
                current_size = section_size
            else:
                # Merge into existing section
                current_merged["content"] += "\n" + section.get("content", "")
                # Merge metadata
                if "metadata" in section:
                    current_merged.setdefault("metadata", {}).update(
                        section["metadata"]
                    )
                current_size += section_size + 1  # +1 for newline

        # Add final merged section
        if current_merged:
            merged.append(current_merged)

        return merged
