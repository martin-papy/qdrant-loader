"""JSON metadata extractor for comprehensive schema inference and analysis."""

import json
from typing import Any

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.metadata_extractor import (
    BaseMetadataExtractor,
)
from qdrant_loader.core.chunking.strategy.json.json_document_parser import (
    JSONElement,
    JSONElementType,
)
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)


class JSONMetadataExtractor(BaseMetadataExtractor):
    """Enhanced metadata extractor for JSON documents."""

    def __init__(self, settings: Settings):
        """Initialize JSON metadata extractor.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.json_config = settings.global_config.chunking.strategies.json_strategy

    def extract_hierarchical_metadata(
        self, content: str, chunk_metadata: dict[str, Any], document: Document
    ) -> dict[str, Any]:
        """Extract comprehensive JSON metadata including schema inference.

        Args:
            content: JSON chunk content
            chunk_metadata: Existing chunk metadata
            document: Source document

        Returns:
            Enhanced metadata dictionary
        """
        metadata = chunk_metadata.copy()

        try:
            # Parse JSON content for analysis
            data = json.loads(content)

            # Core JSON metadata
            metadata.update(
                {
                    "content_type": "json",
                    "is_valid_json": True,
                    "json_size": len(content),
                    "json_type": type(data).__name__,
                    "nesting_depth": self._calculate_nesting_depth(data),
                    "total_elements": self._count_elements(data),
                    "complexity_score": self._calculate_complexity_score(data),
                }
            )

            # Schema inference (if enabled)
            if self.json_config.enable_schema_inference:
                metadata["inferred_schema"] = self._infer_comprehensive_schema(data)
                metadata["schema_patterns"] = self._identify_schema_patterns(data)

            # Data analysis
            metadata.update(
                {
                    "data_types": self._analyze_data_types(data),
                    "value_distributions": self._analyze_value_distributions(data),
                    "key_patterns": (
                        self._analyze_key_patterns(data)
                        if isinstance(data, dict)
                        else []
                    ),
                    "array_statistics": self._analyze_array_statistics(data),
                    "null_analysis": self._analyze_null_values(data),
                    "uniqueness_analysis": self._analyze_uniqueness(data),
                }
            )

            # Structural analysis
            metadata.update(
                {
                    "structure_type": self._classify_structure_type(data),
                    "data_format_hints": self._detect_data_formats(data),
                    "relationship_indicators": self._detect_relationships(data),
                    "configuration_indicators": self._detect_configuration_patterns(
                        data
                    ),
                }
            )

        except json.JSONDecodeError:
            metadata.update(
                {
                    "content_type": "json_invalid",
                    "is_valid_json": False,
                    "json_error": "Invalid JSON format",
                    "estimated_size": len(content),
                }
            )

        return metadata

    def extract_entities(self, text: str) -> list[str]:
        """Extract entities from JSON text content.

        Args:
            text: JSON text content

        Returns:
            List of extracted entities
        """
        entities = []

        try:
            data = json.loads(text)
            entities.extend(self._extract_json_entities(data))
        except json.JSONDecodeError:
            # Fallback to text-based entity extraction
            entities.extend(self._extract_text_entities(text))

        return list(set(entities))  # Remove duplicates

    def extract_json_element_metadata(self, element: JSONElement) -> dict[str, Any]:
        """Extract metadata from a specific JSON element.

        Args:
            element: JSON element to analyze

        Returns:
            Dictionary containing element metadata
        """
        metadata = {
            "element_type": element.element_type.value,
            "element_name": element.name,
            "json_path": element.path,
            "nesting_level": element.level,
            "content_size": element.size,
            "item_count": element.item_count,
            "has_nested_objects": False,
            "has_arrays": False,
            "data_types": [],
            "element_significance": self._calculate_element_significance(element),
        }

        # Analyze value types and structure
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
            metadata["property_count"] = len(element.value)
            metadata["key_patterns"] = self._analyze_key_patterns(element.value)

        elif isinstance(element.value, list) and element.value:
            metadata["data_types"] = list({type(v).__name__ for v in element.value})
            metadata["has_nested_objects"] = any(
                isinstance(v, dict) for v in element.value
            )
            metadata["has_arrays"] = any(isinstance(v, list) for v in element.value)
            metadata["array_length"] = len(element.value)
            metadata["array_homogeneity"] = self._analyze_array_homogeneity(
                element.value
            )

        else:
            metadata["data_types"] = [type(element.value).__name__]
            metadata["value_analysis"] = self._analyze_simple_value(element.value)

        return metadata

    def _infer_comprehensive_schema(self, data: Any) -> dict[str, Any]:
        """Infer detailed JSON schema from data.

        Args:
            data: JSON data to analyze

        Returns:
            Comprehensive schema dictionary
        """
        if isinstance(data, dict):
            schema = {
                "type": "object",
                "properties": {},
                "required_properties": [],
                "property_count": len(data),
                "estimated_completeness": self._estimate_object_completeness(data),
            }

            for key, value in data.items():
                schema["properties"][key] = self._infer_comprehensive_schema(value)
                if value is not None and value != "":
                    schema["required_properties"].append(key)

        elif isinstance(data, list):
            schema = {
                "type": "array",
                "length": len(data),
                "min_length": len(data),
                "max_length": len(data),
                "item_schemas": [],
                "homogeneous": True,
            }

            if data:
                # Analyze first few items for schema inference
                sample_size = min(5, len(data))
                for item in data[:sample_size]:
                    schema["item_schemas"].append(
                        self._infer_comprehensive_schema(item)
                    )

                # Check homogeneity
                if len({type(item).__name__ for item in data}) > 1:
                    schema["homogeneous"] = False

        else:
            schema = {
                "type": type(data).__name__,
                "value": data,
                "nullable": data is None,
                "format_hints": self._detect_value_format(data),
            }

        return schema

    def _identify_schema_patterns(self, data: Any) -> list[str]:
        """Identify common schema patterns in JSON data.

        Args:
            data: JSON data to analyze

        Returns:
            List of identified patterns
        """
        patterns = []

        if isinstance(data, dict):
            # Common object patterns
            keys = set(data.keys())

            if {"id", "name"}.issubset(keys):
                patterns.append("entity_object")
            if {"type", "value"}.issubset(keys):
                patterns.append("typed_value")
            if {"data", "metadata"}.issubset(keys):
                patterns.append("data_with_metadata")
            if any(key.endswith("_at") or key.endswith("_time") for key in keys):
                patterns.append("timestamped_object")
            if {"config", "settings"} & keys:
                patterns.append("configuration_object")
            if len(keys) == 1 and any(isinstance(v, list) for v in data.values()):
                patterns.append("collection_wrapper")

        elif isinstance(data, list):
            if data and all(isinstance(item, dict) for item in data):
                patterns.append("object_array")
                # Check if all objects have similar structure
                if self._check_uniform_structure(data):
                    patterns.append("uniform_object_array")
            elif data and all(isinstance(item, str | int | float) for item in data):
                patterns.append("primitive_array")

        return patterns

    def _calculate_nesting_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth."""
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
        """Count total number of elements."""
        if isinstance(data, dict):
            return 1 + sum(self._count_elements(value) for value in data.values())
        elif isinstance(data, list):
            return 1 + sum(self._count_elements(item) for item in data)
        else:
            return 1

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
        """Analyze distribution of data types."""
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

    def _analyze_value_distributions(self, data: Any) -> dict[str, Any]:
        """Analyze value distributions and statistics."""
        distributions = {
            "null_count": 0,
            "empty_string_count": 0,
            "numeric_ranges": {},
            "string_length_stats": {},
            "boolean_distribution": {},
        }

        def analyze_value(value, path="$"):
            if value is None:
                distributions["null_count"] += 1
            elif value == "":
                distributions["empty_string_count"] += 1
            elif isinstance(value, int | float):
                if "min" not in distributions["numeric_ranges"]:
                    distributions["numeric_ranges"]["min"] = value
                    distributions["numeric_ranges"]["max"] = value
                else:
                    distributions["numeric_ranges"]["min"] = min(
                        distributions["numeric_ranges"]["min"], value
                    )
                    distributions["numeric_ranges"]["max"] = max(
                        distributions["numeric_ranges"]["max"], value
                    )
            elif isinstance(value, str):
                length = len(value)
                if "min_length" not in distributions["string_length_stats"]:
                    distributions["string_length_stats"]["min_length"] = length
                    distributions["string_length_stats"]["max_length"] = length
                else:
                    distributions["string_length_stats"]["min_length"] = min(
                        distributions["string_length_stats"]["min_length"], length
                    )
                    distributions["string_length_stats"]["max_length"] = max(
                        distributions["string_length_stats"]["max_length"], length
                    )
            elif isinstance(value, bool):
                distributions["boolean_distribution"][str(value)] = (
                    distributions["boolean_distribution"].get(str(value), 0) + 1
                )
            elif isinstance(value, dict):
                for k, v in value.items():
                    analyze_value(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    analyze_value(item, f"{path}[{i}]")

        analyze_value(data)
        return distributions

    def _analyze_key_patterns(self, data: Any) -> list[str]:
        """Analyze patterns in JSON keys."""
        if not isinstance(data, dict):
            return []

        keys = list(data.keys())
        patterns = []

        # Naming conventions
        if any(key.startswith("_") for key in keys):
            patterns.append("private_keys")
        if any(key.isupper() for key in keys):
            patterns.append("uppercase_keys")
        if any("_" in key for key in keys):
            patterns.append("snake_case")
        if any(key[0].isupper() for key in keys if key):
            patterns.append("pascal_case")
        if any(key[0].islower() and any(c.isupper() for c in key[1:]) for key in keys):
            patterns.append("camel_case")

        # Semantic patterns
        if any(key.endswith("_id") or key == "id" for key in keys):
            patterns.append("id_fields")
        if any(key.endswith("_at") or key.endswith("_time") for key in keys):
            patterns.append("timestamp_fields")
        if any(key.startswith("is_") or key.startswith("has_") for key in keys):
            patterns.append("boolean_flags")

        return patterns

    def _analyze_array_statistics(self, data: Any) -> dict[str, Any]:
        """Analyze array-specific statistics."""
        arrays_found = []

        def find_arrays(obj, path="$"):
            if isinstance(obj, list):
                array_info = {
                    "path": path,
                    "length": len(obj),
                    "item_types": [
                        type(item).__name__ for item in obj[:5]
                    ],  # Sample first 5
                    "homogeneous": (
                        len({type(item).__name__ for item in obj}) == 1 if obj else True
                    ),
                    "nested_arrays": any(isinstance(item, list) for item in obj),
                    "nested_objects": any(isinstance(item, dict) for item in obj),
                }
                arrays_found.append(array_info)

                for i, item in enumerate(obj):
                    find_arrays(item, f"{path}[{i}]")
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    find_arrays(value, f"{path}.{key}")

        find_arrays(data)

        return {
            "total_arrays": len(arrays_found),
            "array_details": arrays_found[:10],  # Limit for performance
            "max_array_length": max((arr["length"] for arr in arrays_found), default=0),
            "homogeneous_arrays": sum(1 for arr in arrays_found if arr["homogeneous"]),
            "nested_structure_complexity": sum(
                1
                for arr in arrays_found
                if arr["nested_arrays"] or arr["nested_objects"]
            ),
        }

    def _analyze_null_values(self, data: Any) -> dict[str, Any]:
        """Analyze null value patterns."""
        null_analysis = {"total_nulls": 0, "null_paths": [], "nullable_fields": []}

        def check_nulls(obj, path="$"):
            if obj is None:
                null_analysis["total_nulls"] += 1
                null_analysis["null_paths"].append(path)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    child_path = f"{path}.{key}"
                    if value is None:
                        null_analysis["nullable_fields"].append(key)
                    check_nulls(value, child_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_nulls(item, f"{path}[{i}]")

        check_nulls(data)
        return null_analysis

    def _analyze_uniqueness(self, data: Any) -> dict[str, Any]:
        """Analyze uniqueness patterns in data."""
        uniqueness = {
            "unique_strings": set(),
            "repeated_values": {},
            "potential_ids": [],
        }

        def check_uniqueness(obj, path="$"):
            if isinstance(obj, str):
                if obj in uniqueness["unique_strings"]:
                    uniqueness["repeated_values"][obj] = (
                        uniqueness["repeated_values"].get(obj, 1) + 1
                    )
                else:
                    uniqueness["unique_strings"].add(obj)

                # Check if looks like an ID
                if (
                    len(obj) >= 8
                    and (obj.isalnum() or "-" in obj or "_" in obj)
                    and any(c.isdigit() for c in obj)
                ):
                    uniqueness["potential_ids"].append(path)

            elif isinstance(obj, dict):
                for key, value in obj.items():
                    check_uniqueness(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_uniqueness(item, f"{path}[{i}]")

        check_uniqueness(data)

        # Convert set to count for serialization
        uniqueness["unique_string_count"] = len(uniqueness["unique_strings"])
        del uniqueness["unique_strings"]  # Remove set for JSON serialization

        return uniqueness

    def _classify_structure_type(self, data: Any) -> str:
        """Classify the overall structure type of JSON data."""
        if isinstance(data, dict):
            if len(data) == 1 and isinstance(list(data.values())[0], list):
                return "collection_wrapper"
            elif any(key in data for key in ["config", "settings", "configuration"]):
                return "configuration"
            elif any(key in data for key in ["data", "items", "results"]):
                return "data_container"
            else:
                return "object"
        elif isinstance(data, list):
            if data and all(isinstance(item, dict) for item in data):
                return "object_collection"
            elif data and all(isinstance(item, str | int | float) for item in data):
                return "primitive_collection"
            else:
                return "mixed_array"
        else:
            return "primitive_value"

    def _detect_data_formats(self, data: Any) -> list[str]:
        """Detect common data formats in JSON."""
        formats = []

        def check_formats(obj):
            if isinstance(obj, str):
                # Check common formats
                if self._is_email(obj):
                    formats.append("email")
                elif self._is_url(obj):
                    formats.append("url")
                elif self._is_iso_date(obj):
                    formats.append("iso_date")
                elif self._is_uuid(obj):
                    formats.append("uuid")
            elif isinstance(obj, dict):
                for value in obj.values():
                    check_formats(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_formats(item)

        check_formats(data)
        return list(set(formats))

    def _detect_relationships(self, data: Any) -> list[str]:
        """Detect relationship indicators in JSON data."""
        relationships = []

        if isinstance(data, dict):
            keys = set(data.keys())
            if any(key.endswith("_id") for key in keys):
                relationships.append("foreign_keys")
            if "parent" in keys or "parent_id" in keys:
                relationships.append("hierarchical")
            if "children" in keys:
                relationships.append("parent_child")
            if any(
                isinstance(value, list) and value and isinstance(value[0], dict)
                for value in data.values()
            ):
                relationships.append("one_to_many")

        return relationships

    def _detect_configuration_patterns(self, data: Any) -> list[str]:
        """Detect configuration-specific patterns."""
        patterns = []

        if isinstance(data, dict):
            keys = set(data.keys())
            if {"host", "port"} & keys:
                patterns.append("connection_config")
            if {"username", "password"} & keys:
                patterns.append("credentials")
            if {"enabled", "disabled"} & keys or any("enable" in key for key in keys):
                patterns.append("feature_flags")
            if {"timeout", "retry"} & keys:
                patterns.append("retry_config")
            if {"version", "api_version"} & keys:
                patterns.append("versioned_config")

        return patterns

    # Helper methods for format detection
    def _is_email(self, value: str) -> bool:
        """Check if string looks like an email."""
        return "@" in value and "." in value.split("@")[-1]

    def _is_url(self, value: str) -> bool:
        """Check if string looks like a URL."""
        return value.startswith(("http://", "https://", "ftp://"))

    def _is_iso_date(self, value: str) -> bool:
        """Check if string looks like an ISO date."""
        return len(value) >= 10 and value[4] == "-" and value[7] == "-"

    def _is_uuid(self, value: str) -> bool:
        """Check if string looks like a UUID."""
        return len(value) == 36 and value.count("-") == 4

    def _estimate_object_completeness(self, obj: dict) -> float:
        """Estimate how complete an object is (ratio of non-null values)."""
        if not obj:
            return 0.0
        total_fields = len(obj)
        non_null_fields = sum(
            1 for value in obj.values() if value is not None and value != ""
        )
        return non_null_fields / total_fields

    def _analyze_array_homogeneity(self, array: list) -> dict[str, Any]:
        """Analyze homogeneity of array items."""
        if not array:
            return {"homogeneous": True, "type_distribution": {}}

        type_counts = {}
        for item in array:
            item_type = type(item).__name__
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

        return {
            "homogeneous": len(type_counts) == 1,
            "type_distribution": type_counts,
            "dominant_type": (
                max(type_counts.keys(), key=type_counts.get) if type_counts else None
            ),
        }

    def _analyze_simple_value(self, value: Any) -> dict[str, Any]:
        """Analyze a simple (non-container) value."""
        analysis = {
            "type": type(value).__name__,
            "is_null": value is None,
            "is_empty": value == "" if isinstance(value, str) else False,
        }

        if isinstance(value, str):
            analysis.update(
                {"length": len(value), "format_hints": self._detect_value_format(value)}
            )
        elif isinstance(value, int | float):
            analysis.update(
                {
                    "numeric_value": value,
                    "is_positive": value > 0,
                    "is_zero": value == 0,
                }
            )

        return analysis

    def _detect_value_format(self, value: Any) -> list[str]:
        """Detect format hints for a single value."""
        if not isinstance(value, str):
            return []

        formats = []
        if self._is_email(value):
            formats.append("email")
        if self._is_url(value):
            formats.append("url")
        if self._is_iso_date(value):
            formats.append("iso_date")
        if self._is_uuid(value):
            formats.append("uuid")
        if value.isdigit():
            formats.append("numeric_string")
        if value.replace(".", "").replace("-", "").isdigit():
            formats.append("formatted_number")

        return formats

    def _calculate_element_significance(self, element: JSONElement) -> float:
        """Calculate significance score for an element."""
        significance = 0.0

        # Size-based significance
        significance += min(element.size / 1000.0, 1.0) * 0.3

        # Structure-based significance
        if element.element_type in [JSONElementType.OBJECT, JSONElementType.ARRAY]:
            significance += 0.4

        # Depth-based significance (deeper = less significant)
        significance += max(0, 1.0 - element.level * 0.1) * 0.2

        # Item count significance
        if element.item_count > 0:
            significance += min(element.item_count / 10.0, 0.3) * 0.1

        return min(significance, 1.0)

    def _check_uniform_structure(self, objects: list) -> bool:
        """Check if all objects in array have similar structure."""
        if not objects or not all(isinstance(obj, dict) for obj in objects):
            return False

        first_keys = set(objects[0].keys())
        return all(
            set(obj.keys()) == first_keys for obj in objects[1:5]
        )  # Check first 5

    def _extract_json_entities(self, data: Any, path: str = "$") -> list[str]:
        """Extract entity-like values from JSON data."""
        entities = []

        if isinstance(data, dict):
            for key, value in data.items():
                # Extract key names as potential entities
                if len(key) > 2 and key.replace("_", "").isalpha():
                    entities.append(key)

                # Extract string values that look like entities
                if (
                    isinstance(value, str)
                    and len(value) > 2
                    and not self._is_url(value)
                ):
                    entities.append(value)
                elif isinstance(value, dict | list):
                    entities.extend(self._extract_json_entities(value, f"{path}.{key}"))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str) and len(item) > 2:
                    entities.append(item)
                elif isinstance(item, dict | list):
                    entities.extend(self._extract_json_entities(item, f"{path}[{i}]"))

        return entities

    def _extract_text_entities(self, text: str) -> list[str]:
        """Fallback entity extraction from text content."""
        # Simple entity extraction for malformed JSON
        import re

        entities = []

        # Extract quoted strings that look like entities
        quoted_strings = re.findall(r'"([^"]{3,})"', text)
        entities.extend(
            [s for s in quoted_strings if s.replace("_", "").replace("-", "").isalpha()]
        )

        # Extract field names
        field_names = re.findall(r'"([a-zA-Z_][a-zA-Z0-9_]*)":', text)
        entities.extend(field_names)

        return entities
