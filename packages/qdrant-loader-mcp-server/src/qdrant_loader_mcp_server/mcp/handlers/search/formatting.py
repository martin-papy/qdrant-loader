from __future__ import annotations

from ...formatters import MCPFormatters


def format_lightweight_attachment_text(
    organized_results: dict[str, list], total_found: int
) -> str:
    if not organized_results:
        return (
            "📎 **Attachment Search Results**\n\nFound "
            f"{total_found} attachments. Use the structured data below to navigate and retrieve specific files."
        )

    formatted = f"📎 **Attachment Search Results** ({total_found} attachments)\n\n"
    formatters = MCPFormatters()
    for group_name, results in organized_results.items():
        formatted += f"📁 **{group_name}** ({len(results)} files)\n"
        for result in results[:3]:
            filename = formatters._extract_safe_filename(result)
            file_type = formatters._extract_file_type_minimal(result)
            formatted += f"  📄 {filename} ({file_type}) - Score: {result.score:.3f}\n"
        if len(results) > 3:
            formatted += f"  ... and {len(results) - 3} more files\n"
        formatted += "\n"
    formatted += "💡 **Usage:** Use the structured attachment data to:\n"
    formatted += "• Browse attachments by file type or source\n"
    formatted += "• Get document IDs for specific file content retrieval\n"
    formatted += "• Filter attachments by metadata (size, type, etc.)\n"
    return formatted


def format_lightweight_hierarchy_text(
    organized_results: dict[str, list], total_found: int
) -> str:
    if not organized_results:
        return (
            "📋 **Hierarchy Search Results**\n\nFound "
            f"{total_found} documents. Use the structured data below to navigate the hierarchy and retrieve specific documents."
        )

    formatted = f"📋 **Hierarchy Search Results** ({total_found} documents)\n\n"
    formatters = MCPFormatters()
    for group_name, results in organized_results.items():
        clean_name = formatters._generate_clean_group_name(group_name, results)
        formatted += f"📁 **{clean_name}** ({len(results)} documents)\n"
        for result in results[:3]:
            formatted += f"  📄 {result.source_title} (Score: {result.score:.3f})\n"
        if len(results) > 3:
            formatted += f"  ... and {len(results) - 3} more documents\n"
        formatted += "\n"
    formatted += "💡 **Usage:** Use the structured hierarchy data to:\n"
    formatted += "• Browse document groups and navigate hierarchy levels\n"
    formatted += "• Get document IDs for specific content retrieval\n"
    formatted += "• Understand document relationships and organization\n"
    return formatted
