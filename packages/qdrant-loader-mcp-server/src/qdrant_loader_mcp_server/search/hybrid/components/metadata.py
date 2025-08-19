from __future__ import annotations

from typing import Any, Dict


def extract_metadata_info(metadata_extractor: Any, metadata: dict) -> dict:
    """Extract and flatten metadata using the provided metadata_extractor."""
    components = metadata_extractor.extract_all_metadata(metadata)
    flattened: Dict[str, Any] = {}

    for _component_name, component in components.items():
        if component is None:
            continue
        if hasattr(component, "__dict__"):
            for key, value in component.__dict__.items():
                flattened[key] = value
        elif isinstance(component, dict):
            flattened.update(component)

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
    project_info = metadata_extractor.extract_project_info(metadata)
    if project_info:
        return project_info.__dict__
    return {
        "project_id": None,
        "project_name": None,
        "project_description": None,
        "collection_name": None,
    }


