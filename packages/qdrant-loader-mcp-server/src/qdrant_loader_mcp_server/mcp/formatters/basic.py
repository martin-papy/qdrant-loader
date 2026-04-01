"""
Basic Result Formatters - Core Search Result Formatting.

This module handles basic formatting of search results, attachments,
and hierarchical results for display in the MCP interface.
"""

from ...search.components.search_result_models import HybridSearchResult


class BasicResultFormatters:
    """Handles basic result formatting operations."""

    # TODO [contextual_embeddings] STEP 6/8: Display contextual prefix properly
    #
    # After ingestion, result.text will contain the prefix prepended to the
    # actual chunk content, e.g.:
    #   "[Source: confluence | Document: Architecture Overview | Project: X]\n\nActual chunk text..."
    #
    # You need to handle this in _format_common_fields so the LLM/user sees
    # clean, well-structured output. Two options (pick one):
    #
    # OPTION A (recommended) - Strip prefix, show as structured metadata line:
    #   import re
    #   @staticmethod
    #   def _strip_contextual_prefix(text: str) -> tuple[str, str | None]:
    #       """Separate contextual prefix from chunk text.
    #       Returns (clean_text, prefix_or_None).
    #       """
    #       match = re.match(r'^\[(.+?)\]\n\n', text, re.DOTALL)
    #       if match:
    #           return text[match.end():], match.group(0).strip()
    #       return text, None
    #
    #   Then in _format_common_fields, call this before building the output:
    #       clean_text, prefix = BasicResultFormatters._strip_contextual_prefix(result.text)
    #       formatted_result = f"Score: {result.score}\n"
    #       if prefix:
    #           formatted_result += f"Context: {prefix}\n"
    #       formatted_result += f"Text: {clean_text}\n"
    #
    # OPTION B (simpler) - Show text as-is, the prefix is already human-readable:
    #   Just leave it. The "[Source: ... | Document: ...]" line is self-explanatory.
    #   The LLM consuming MCP results will understand it.
    #
    # WHY THIS MATTERS: Without this step, the prefix is invisible context that
    # helps embedding quality but the user/LLM never sees it. Displaying it
    # gives the consumer the same document-level context the embedding had.
    #
    # ALSO: Update format_hierarchical_results below -- it truncates result.text
    # to 150 chars for snippets. If the prefix is ~80 chars, the snippet might
    # show only the prefix and no actual content. Strip prefix before truncating.

    @staticmethod
    def _format_common_fields(
        result: HybridSearchResult, is_attachment_view: bool = False
    ) -> str:
        """Build the base formatted string for a search result.

        This consolidates shared formatting between standard search results and
        attachment-focused views while preserving the original output order and
        conditional branches.
        """
        formatted_result = f"Score: {result.score}\n"
        formatted_result += f"Source: {result.source_type}"
        
        text = result.text
        contextual_prefix = getattr(result, "contextual_prefix", None)
        if isinstance(contextual_prefix, str) and contextual_prefix:
            formatted_result += f"Context: {contextual_prefix}\n"
            if isinstance(text, str) and text.startswith(contextual_prefix):
                text = text[len(contextual_prefix):].lstrip()

        formatted_result += f"\nText: {text}"

        if result.source_title:
            formatted_result += f" - {result.source_title}"

        # Project information (only shown in non-attachment view to preserve behavior)
        if not is_attachment_view:
            project_info = result.get_project_info()
            if project_info:
                formatted_result += f"\n🏗️ {project_info}"

        # Attachment info (shown if viewing attachments or the result itself is an attachment)
        if is_attachment_view or result.is_attachment:
            formatted_result += "\n📎 Attachment"
            if result.original_filename:
                formatted_result += f": {result.original_filename}"
            if result.attachment_context:
                formatted_result += f"\n📋 {result.attachment_context}"
            if result.parent_document_title:
                formatted_result += f"\n📄 Attached to: {result.parent_document_title}"

        # Confluence breadcrumb path
        if result.source_type == "confluence" and result.breadcrumb_text:
            formatted_result += f"\n📍 Path: {result.breadcrumb_text}"

        # Source URL appended inline
        if result.source_url:
            formatted_result += f" ({result.source_url})"

        if result.file_path:
            formatted_result += f"\nFile: {result.file_path}"

        if result.repo_name:
            formatted_result += f"\nRepo: {result.repo_name}"

        # Additional hierarchy info for Confluence
        hierarchy_context = getattr(result, "hierarchy_context", None)
        if result.source_type == "confluence" and hierarchy_context:
            formatted_result += f"\n🏗️ {hierarchy_context}"

        # Parent info (for hierarchy, not for attachment items themselves)
        if result.parent_title and not result.is_attachment:
            formatted_result += f"\n⬆️ Parent: {result.parent_title}"

        # Children count
        if result.has_children():
            formatted_result += f"\n⬇️ Children: {result.children_count}"

        return formatted_result

    @staticmethod
    def format_search_result(result: HybridSearchResult) -> str:
        """Format a search result for display."""
        return BasicResultFormatters._format_common_fields(
            result, is_attachment_view=False
        )

    @staticmethod
    def format_attachment_search_result(result: HybridSearchResult) -> str:
        """Format an attachment search result for display."""
        return BasicResultFormatters._format_common_fields(
            result, is_attachment_view=True
        )

    @staticmethod
    def format_hierarchical_results(
        organized_results: dict[str, list[HybridSearchResult]],
    ) -> str:
        """Format hierarchically organized results for display."""
        formatted_sections = []

        for root_title, results in organized_results.items():
            section = f"📁 **{root_title}** ({len(results)} results)\n"

            for result in results:
                indent = "  " * (getattr(result, "depth", 0) or 0)
                section += f"{indent}📄 {result.source_title}"
                if hasattr(result, "hierarchy_context") and result.hierarchy_context:
                    section += f" | {result.hierarchy_context}"
                section += f" (Score: {result.score:.3f})\n"

                # Add a snippet of the content
                content_snippet = (
                    result.text[:150] + "..." if len(result.text) > 150 else result.text
                )
                section += f"{indent}   {content_snippet}\n"

                if result.source_url:
                    section += f"{indent}   🔗 {result.source_url}\n"
                section += "\n"

            formatted_sections.append(section)

        return (
            f"Found {sum(len(results) for results in organized_results.values())} results organized by hierarchy:\n\n"
            + "\n".join(formatted_sections)
        )
