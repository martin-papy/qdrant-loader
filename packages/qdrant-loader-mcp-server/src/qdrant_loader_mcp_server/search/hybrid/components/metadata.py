from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from typing import Any

logger = logging.getLogger(__name__)


def extract_metadata_info(metadata_extractor: Any, metadata: dict) -> dict:
    """Extract and flatten metadata using the provided metadata_extractor."""
    # Validate extractor interface defensively (mirrors extract_project_info approach)
    if not hasattr(metadata_extractor, "extract_all_metadata"):
        logger.warning(
            "Metadata extractor missing 'extract_all_metadata'; returning empty metadata"
        )
        return {}
    extract_callable = metadata_extractor.extract_all_metadata
    if not callable(extract_callable):
        logger.warning(
            "Metadata extractor 'extract_all_metadata' is not callable; returning empty metadata"
        )
        return {}
    try:
        components = extract_callable(metadata)
    except Exception:
        # Log full traceback and return safe default
        logger.exception("Error calling extract_all_metadata; returning empty metadata")
        return {}

    if not isinstance(components, dict):
        components = {}
    flattened: dict[str, Any] = {}

    for _component_name, component in components.items():
        if component is None:
            continue
        # Handle dataclasses explicitly
        if is_dataclass(component):
            component_dict = asdict(component)
        # Handle regular objects by inspecting vars and filtering private/callable
        elif hasattr(component, "__dict__"):
            component_dict = {
                k: v
                for k, v in vars(component).items()
                if not k.startswith("_") and not callable(v)
            }
        # Handle dictionaries
        elif isinstance(component, dict):
            component_dict = component
        else:
            # Fallback: skip unsupported component types
            continue

        # Merge without overwriting existing keys
        for key, value in component_dict.items():
            if key in flattened:
                continue
            flattened[key] = value

    expected_keys = [
        # Project info
        "project_id",
        "project_name",
        "project_description",
        "collection_name",
        # Hierarchy info
        "parent_id",
        "parent_title",
        "breadcrumb_text",
        "depth",
        "children_count",
        "hierarchy_context",
        # Attachment info
        "is_attachment",
        "parent_document_id",
        "parent_document_title",
        "attachment_id",
        "original_filename",
        "file_size",
        "mime_type",
        "attachment_author",
        "attachment_context",
        # Section info
        "section_title",
        "section_type",
        "section_level",
        "section_anchor",
        "section_breadcrumb",
        "section_depth",
        # Content analysis
        "has_code_blocks",
        "has_tables",
        "has_images",
        "has_links",
        "word_count",
        "char_count",
        "estimated_read_time",
        "paragraph_count",
        # Semantic analysis
        "entities",
        "topics",
        "key_phrases",
        "pos_tags",
        # Navigation context
        "previous_section",
        "next_section",
        "sibling_sections",
        "subsections",
        "document_hierarchy",
        # Chunking context
        "chunk_index",
        "total_chunks",
        "chunking_strategy",
        # Conversion info
        "original_file_type",
        "conversion_method",
        "is_excel_sheet",
        "is_converted",
        # Cross-reference info
        "cross_references",
        "topic_analysis",
        "content_type_context",
    ]

    for key in expected_keys:
        if key not in flattened:
            if key in [
                "is_attachment",
                "has_code_blocks",
                "has_tables",
                "has_images",
                "has_links",
                "is_excel_sheet",
                "is_converted",
            ]:
                flattened[key] = False
            elif key in [
                "entities",
                "topics",
                "key_phrases",
                "pos_tags",
                "sibling_sections",
                "subsections",
                "document_hierarchy",
                "cross_references",
            ]:
                flattened[key] = []
            else:
                flattened[key] = None

    return flattened


def extract_project_info(metadata_extractor: Any, metadata: dict) -> dict:
    """Safely extract project info using a provided extractor.

    Ensures extractor has a callable `extract_project_info` attribute and guards against
    exceptions thrown by the extractor. Always returns a mapping with expected keys.
    """
    # Default safe shape
    safe_empty: dict[str, Any] = {
        "project_id": None,
        "project_name": None,
        "project_description": None,
        "collection_name": None,
    }

    # Validate extractor interface
    if not hasattr(metadata_extractor, "extract_project_info"):
        return safe_empty
    extract_callable = metadata_extractor.extract_project_info
    if not callable(extract_callable):
        return safe_empty

    try:
        project_info = extract_callable(metadata)
    except Exception:
        # Fail closed to safe shape if extractor raises
        return safe_empty

    data: dict[str, Any] = {}
    if project_info:
        if isinstance(project_info, dict):
            data = project_info
        else:
            data = getattr(project_info, "__dict__", {}) or {}

    # Remove private keys
    data = {k: v for k, v in data.items() if not k.startswith("_")}

    return {
        "project_id": data.get("project_id"),
        "project_name": data.get("project_name"),
        "project_description": data.get("project_description"),
        "collection_name": data.get("collection_name"),
    }
