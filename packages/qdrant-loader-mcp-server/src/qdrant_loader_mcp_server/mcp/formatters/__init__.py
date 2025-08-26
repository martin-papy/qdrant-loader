"""
MCP Formatters Package - Modular Response Formatting.

This package provides comprehensive MCP response formatting through modular components:
- basic: Basic search result and attachment formatting
- intelligence: Analysis and intelligence result formatting
- lightweight: Efficient lightweight result construction
- structured: Complex structured data formatting
- utils: Shared utilities and helper functions
"""

# Re-export the main MCPFormatters class for backward compatibility
from .basic import BasicResultFormatters
from .intelligence import IntelligenceResultFormatters
from .lightweight import LightweightResultFormatters
from .structured import StructuredResultFormatters
from .utils import FormatterUtils


# Compatibility wrapper to maintain existing API
class MCPFormatters:
    """
    Unified formatter class maintaining backward compatibility.

    Delegates to specialized formatter modules while preserving
    the original static method interface.
    """

    # Basic formatting methods
    format_search_result = staticmethod(BasicResultFormatters.format_search_result)
    format_attachment_search_result = staticmethod(
        BasicResultFormatters.format_attachment_search_result
    )
    format_hierarchical_results = staticmethod(
        BasicResultFormatters.format_hierarchical_results
    )

    # Intelligence formatting methods
    format_relationship_analysis = staticmethod(
        IntelligenceResultFormatters.format_relationship_analysis
    )
    format_similar_documents = staticmethod(
        IntelligenceResultFormatters.format_similar_documents
    )
    format_conflict_analysis = staticmethod(
        IntelligenceResultFormatters.format_conflict_analysis
    )
    format_complementary_content = staticmethod(
        IntelligenceResultFormatters.format_complementary_content
    )
    format_document_clusters = staticmethod(
        IntelligenceResultFormatters.format_document_clusters
    )

    # Lightweight result methods
    create_lightweight_similar_documents_results = staticmethod(
        LightweightResultFormatters.create_lightweight_similar_documents_results
    )
    create_lightweight_conflict_results = staticmethod(
        LightweightResultFormatters.create_lightweight_conflict_results
    )
    create_lightweight_cluster_results = staticmethod(
        LightweightResultFormatters.create_lightweight_cluster_results
    )
    create_lightweight_hierarchy_results = staticmethod(
        LightweightResultFormatters.create_lightweight_hierarchy_results
    )
    create_lightweight_complementary_results = staticmethod(
        LightweightResultFormatters.create_lightweight_complementary_results
    )
    create_lightweight_attachment_results = staticmethod(
        LightweightResultFormatters.create_lightweight_attachment_results
    )

    # Structured result methods
    create_structured_search_results = staticmethod(
        StructuredResultFormatters.create_structured_search_results
    )
    create_structured_hierarchy_results = staticmethod(
        StructuredResultFormatters.create_structured_hierarchy_results
    )
    create_structured_attachment_results = staticmethod(
        StructuredResultFormatters.create_structured_attachment_results
    )

    # Utility methods
    _extract_minimal_doc_fields = staticmethod(
        FormatterUtils.extract_minimal_doc_fields
    )
    _extract_conflicting_statements = staticmethod(
        FormatterUtils.extract_conflicting_statements
    )
    _generate_clean_group_name = staticmethod(FormatterUtils.generate_clean_group_name)
    _get_group_key = staticmethod(FormatterUtils.get_group_key)
    _count_siblings = staticmethod(FormatterUtils.count_siblings)
    _extract_synthetic_depth = staticmethod(FormatterUtils.extract_synthetic_depth)
    _extract_synthetic_parent_id = staticmethod(
        FormatterUtils.extract_synthetic_parent_id
    )
    _extract_synthetic_parent_title = staticmethod(
        FormatterUtils.extract_synthetic_parent_title
    )
    _extract_synthetic_breadcrumb = staticmethod(
        FormatterUtils.extract_synthetic_breadcrumb
    )
    _extract_has_children = staticmethod(FormatterUtils.extract_has_children)
    _extract_children_count = staticmethod(FormatterUtils.extract_children_count)
    _extract_safe_filename = staticmethod(FormatterUtils.extract_safe_filename)
    _extract_file_type_minimal = staticmethod(FormatterUtils.extract_file_type_minimal)
    _organize_attachments_by_type = staticmethod(
        FormatterUtils.organize_attachments_by_type
    )
    _get_attachment_group_key = staticmethod(FormatterUtils.get_attachment_group_key)
    _generate_friendly_group_name = staticmethod(
        FormatterUtils.generate_friendly_group_name
    )
    _generate_conflict_resolution_suggestion = staticmethod(
        FormatterUtils.generate_conflict_resolution_suggestion
    )
    _extract_affected_sections = staticmethod(FormatterUtils.extract_affected_sections)


__all__ = [
    "MCPFormatters",
    "BasicResultFormatters",
    "IntelligenceResultFormatters",
    "LightweightResultFormatters",
    "StructuredResultFormatters",
    "FormatterUtils",
]
