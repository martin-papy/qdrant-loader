"""JSON document parser for structure analysis and element extraction."""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.document_parser import BaseDocumentParser

logger = structlog.get_logger(__name__)


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
    """Represents a JSON element with metadata."""

    name: str
    element_type: JSONElementType
    content: str
    value: Any
    path: str
    level: int = 0
    size: int = 0
    item_count: int = 0
    children: list["JSONElement"] = field(default_factory=list)

    def add_child(self, child: "JSONElement"):
        """Add a child element."""
        self.children.append(child)


class JSONDocumentParser(BaseDocumentParser):
    """Parser for JSON document structure analysis."""

    def __init__(self, settings: Settings):
        """Initialize JSON document parser.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.json_config = settings.global_config.chunking.strategies.json_strategy
        self.chunk_size = settings.global_config.chunking.chunk_size

    def parse_document_structure(self, content: str) -> dict[str, Any]:
        """Parse JSON document structure and analyze composition.

        Args:
            content: JSON content to analyze

        Returns:
            Dictionary containing structure analysis
        """
        try:
            data = json.loads(content)

            structure = {
                "valid_json": True,
                "root_type": type(data).__name__,
                "total_size": len(content),
                "nesting_depth": self._calculate_nesting_depth(data),
                "total_elements": self._count_elements(data),
                "schema_summary": self._infer_basic_schema(data),
                "complexity_score": self._calculate_complexity_score(data),
                "data_types": self._analyze_data_types(data),
                "key_patterns": (
                    self._analyze_key_patterns(data) if isinstance(data, dict) else []
                ),
                "array_stats": (
                    self._analyze_arrays(data) if isinstance(data, list | dict) else {}
                ),
            }

        except json.JSONDecodeError as e:
            structure = {
                "valid_json": False,
                "error": str(e),
                "total_size": len(content),
                "estimated_elements": max(1, len(content) // 100),  # Rough estimate
            }

        return structure

    def extract_section_metadata(self, section: JSONElement) -> dict[str, Any]:
        """Extract metadata from a JSON section/element.

        Args:
            section: JSON element to analyze

        Returns:
            Dictionary containing section metadata
        """
        metadata = {
            "element_name": section.name,
            "element_type": section.element_type.value,
            "json_path": section.path,
            "nesting_level": section.level,
            "content_size": section.size,
            "item_count": section.item_count,
            "child_count": len(section.children),
            "has_nested_structures": any(
                child.element_type in [JSONElementType.OBJECT, JSONElementType.ARRAY]
                for child in section.children
            ),
        }

        # Analyze the actual value if available
        if hasattr(section, "value") and section.value is not None:
            metadata.update(
                {
                    "value_type": type(section.value).__name__,
                    "schema_info": self._infer_basic_schema(section.value),
                    "complexity_score": self._calculate_complexity_score(section.value),
                }
            )

        return metadata

    def parse_json_structure(self, content: str) -> JSONElement | None:
        """Parse JSON content into a structured element tree.

        Args:
            content: JSON content to parse

        Returns:
            Root JSONElement or None if parsing fails
        """
        try:
            data = json.loads(content)

            # Create root element
            root_type = (
                JSONElementType.OBJECT
                if isinstance(data, dict)
                else (
                    JSONElementType.ARRAY
                    if isinstance(data, list)
                    else JSONElementType.VALUE
                )
            )

            root_element = self._create_json_element("root", data, root_type, "$", 0)

            # Extract child elements
            if root_element.size < self.json_config.max_json_size_for_parsing:
                self._extract_json_elements(root_element, data, "$")

            return root_element

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON content")
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
        if level > self.json_config.max_recursion_depth:
            return
        if processed_count[0] >= self.json_config.max_objects_to_process:
            return
        if len(parent_element.children) >= self.json_config.max_array_items_per_chunk:
            return

        if isinstance(data, dict):
            for i, (key, value) in enumerate(data.items()):
                if processed_count[0] >= self.json_config.max_objects_to_process:
                    break
                if i >= self.json_config.max_object_keys_to_process:
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
                if processed_count[0] >= self.json_config.max_objects_to_process:
                    break
                if i >= self.json_config.max_array_items_per_chunk:
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

    def _calculate_nesting_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of JSON structure."""
        if not isinstance(data, dict | list):
            return current_depth

        max_depth = current_depth

        if isinstance(data, dict):
            for value in data.values():
                depth = self._calculate_nesting_depth(value, current_depth + 1)
                max_depth = max(max_depth, depth)
        elif isinstance(data, list):
            for item in data:
                depth = self._calculate_nesting_depth(item, current_depth + 1)
                max_depth = max(max_depth, depth)

        return max_depth

    def _count_elements(self, data: Any) -> int:
        """Count total number of elements in JSON structure."""
        if isinstance(data, dict):
            return 1 + sum(self._count_elements(value) for value in data.values())
        elif isinstance(data, list):
            return 1 + sum(self._count_elements(item) for item in data)
        else:
            return 1

    def _infer_basic_schema(self, data: Any) -> dict[str, Any]:
        """Infer basic schema information from JSON data."""
        if isinstance(data, dict):
            return {
                "type": "object",
                "properties": {
                    key: self._infer_basic_schema(value) for key, value in data.items()
                },
                "property_count": len(data),
            }
        elif isinstance(data, list):
            if data:
                # Analyze first few items to infer array schema
                sample_items = data[:5]
                item_types = [self._infer_basic_schema(item) for item in sample_items]
                return {
                    "type": "array",
                    "length": len(data),
                    "item_schema": item_types[0] if item_types else {"type": "unknown"},
                }
            else:
                return {"type": "array", "length": 0}
        else:
            return {"type": type(data).__name__}

    def _calculate_complexity_score(self, data: Any) -> float:
        """Calculate complexity score for JSON data."""
        if isinstance(data, dict):
            return (
                1.0
                + sum(
                    self._calculate_complexity_score(value) for value in data.values()
                )
                * 0.5
            )
        elif isinstance(data, list):
            return (
                1.0 + sum(self._calculate_complexity_score(item) for item in data) * 0.3
            )
        else:
            return 0.1

    def _analyze_data_types(self, data: Any) -> dict[str, int]:
        """Analyze distribution of data types in JSON structure."""
        type_counts = {}

        def count_types(obj):
            obj_type = type(obj).__name__
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

            if isinstance(obj, dict):
                for value in obj.values():
                    count_types(value)
            elif isinstance(obj, list):
                for item in obj:
                    count_types(item)

        count_types(data)
        return type_counts

    def _analyze_key_patterns(self, data: Any) -> list[str]:
        """Analyze patterns in JSON keys."""
        if not isinstance(data, dict):
            return []

        keys = list(data.keys())
        patterns = []

        # Check for common patterns
        if any(key.startswith("_") for key in keys):
            patterns.append("private_keys")
        if any(key.isupper() for key in keys):
            patterns.append("uppercase_keys")
        if any("_" in key for key in keys):
            patterns.append("snake_case")
        if any(key[0].isupper() for key in keys if key):
            patterns.append("camel_case")

        return patterns

    def _analyze_arrays(self, data: Any) -> dict[str, Any]:
        """Analyze array statistics in JSON structure."""
        arrays_found = []

        def find_arrays(obj, path="$"):
            if isinstance(obj, list):
                arrays_found.append(
                    {
                        "path": path,
                        "length": len(obj),
                        "item_types": [
                            type(item).__name__ for item in obj[:5]
                        ],  # Sample first 5
                    }
                )
                for i, item in enumerate(obj):
                    find_arrays(item, f"{path}[{i}]")
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    find_arrays(value, f"{path}.{key}")

        find_arrays(data)

        return {
            "total_arrays": len(arrays_found),
            "array_details": arrays_found[:10],  # Limit to first 10 for performance
            "max_array_length": max((arr["length"] for arr in arrays_found), default=0),
        }
