"""
Formatter Utilities - Shared Helper Functions.

This module contains utility functions and helpers used across
different formatter modules for common operations like field extraction,
group generation, and data processing.
"""

from typing import Any

from ...search.components.search_result_models import HybridSearchResult


class FormatterUtils:
    """Shared utility functions for formatters."""

    @staticmethod
    def extract_minimal_doc_fields(
        result: HybridSearchResult, include_content: bool = False
    ) -> dict[str, Any]:
        """Extract minimal document fields for lightweight responses."""
        minimal = {
            "document_id": getattr(result, "document_id", ""),
            "title": getattr(result, "source_title", "Untitled"),
            "source_type": getattr(result, "source_type", "unknown"),
            "score": getattr(result, "score", 0.0),
        }

        if include_content:
            content = getattr(result, "text", "")
            minimal["snippet"] = (
                content[:200] + "..." if len(content) > 200 else content
            )

        # Add optional fields if available
        optional_fields = ["source_url", "file_path", "breadcrumb_text"]
        for field in optional_fields:
            value = getattr(result, field, None)
            if value:
                minimal[field] = value

        return minimal

    @staticmethod
    def extract_conflicting_statements(conflict_info: dict) -> list[dict[str, Any]]:
        """Extract conflicting statements from conflict information."""
        statements = []

        # Extract from structured indicators
        structured_indicators = conflict_info.get("structured_indicators", [])
        for indicator in structured_indicators:
            if (
                isinstance(indicator, dict)
                and "doc1_snippet" in indicator
                and "doc2_snippet" in indicator
            ):
                statements.append(
                    {
                        "document_1_statement": indicator["doc1_snippet"],
                        "document_2_statement": indicator["doc2_snippet"],
                        "context": indicator.get("context", ""),
                    }
                )

        # Fallback to basic conflict description if no structured indicators
        if not statements and "description" in conflict_info:
            statements.append(
                {
                    "document_1_statement": conflict_info.get("description", ""),
                    "document_2_statement": "",
                    "context": "General conflict detected",
                }
            )

        return statements

    @staticmethod
    def generate_clean_group_name(group_key: str, results: list) -> str:
        """Generate clear, short group names."""
        # Remove chunk/content prefixes from group names
        if group_key.startswith("Exists, limited clarity"):
            return "Technical Documentation"
        if group_key.startswith("Immediately begin compiling"):
            return "Product Management"
        if group_key.startswith("Purpose and Scope"):
            return "Project Overview"

        # Use first meaningful part of breadcrumb
        if " > " in group_key:
            return group_key.split(" > ")[0]

        # Truncate long names and add context
        if len(group_key) > 50:
            source_type = (
                getattr(results[0], "source_type", "unknown") if results else "unknown"
            )
            return f"{group_key[:47]}... ({source_type.title()})"

        return group_key

    @staticmethod
    def get_group_key(result) -> str:
        """Generate a stable group key for hierarchy organization."""
        # Try synthetic breadcrumb first
        synthetic_breadcrumb = FormatterUtils.extract_synthetic_breadcrumb(result)
        if synthetic_breadcrumb:
            if getattr(result, "source_type", None) == "confluence":
                return synthetic_breadcrumb
            elif getattr(result, "source_type", None) == "localfile":
                # Use root folder from breadcrumb
                return (
                    synthetic_breadcrumb.split(" > ")[0]
                    if " > " in synthetic_breadcrumb
                    else synthetic_breadcrumb
                )

        # Fallback to file path for localfiles
        if getattr(result, "source_type", None) == "localfile" and getattr(
            result, "file_path", None
        ):
            path_parts = [p for p in result.file_path.split("/") if p and p != "."]
            return path_parts[0] if path_parts else "Root"

        # Fallback to title
        return getattr(result, "source_title", None) or "Uncategorized"

    @staticmethod
    def count_siblings(result, all_results: list) -> int:
        """Count sibling documents at the same hierarchy level."""
        if not all_results:
            return 0

        # Get the parent of the current result
        parent_id = FormatterUtils.extract_synthetic_parent_id(result)
        if not parent_id:
            # If no parent, count documents at root level
            siblings = [
                r
                for r in all_results
                if not FormatterUtils.extract_synthetic_parent_id(r)
            ]
            return len(siblings)

        # Count documents with the same parent
        siblings = [
            r
            for r in all_results
            if FormatterUtils.extract_synthetic_parent_id(r) == parent_id
        ]
        return len(siblings)

    @staticmethod
    def extract_synthetic_depth(result) -> int:
        """Extract synthetic hierarchy depth from breadcrumb or file path."""
        # First try breadcrumb
        breadcrumb = FormatterUtils.extract_synthetic_breadcrumb(result)
        if breadcrumb and " > " in breadcrumb:
            return len(breadcrumb.split(" > "))

        # Try file path for local files
        if getattr(result, "source_type", None) == "localfile" and getattr(
            result, "file_path", None
        ):
            # Remove leading ./ and count path segments
            clean_path = result.file_path.lstrip("./")
            path_parts = [p for p in clean_path.split("/") if p]
            return len(path_parts)

        return 1  # Default depth

    @staticmethod
    def extract_synthetic_parent_id(result) -> str | None:
        """Extract synthetic parent ID from hierarchy information."""
        breadcrumb = FormatterUtils.extract_synthetic_breadcrumb(result)
        if breadcrumb and " > " in breadcrumb:
            # Parent is the second-to-last element in breadcrumb
            parts = breadcrumb.split(" > ")
            if len(parts) > 1:
                return parts[-2]  # Second to last is the parent

        # For file paths, parent is the directory
        if getattr(result, "source_type", None) == "localfile" and getattr(
            result, "file_path", None
        ):
            path_parts = [p for p in result.file_path.split("/") if p and p != "."]
            if len(path_parts) > 1:
                return path_parts[-2]  # Parent directory

        return None

    @staticmethod
    def extract_synthetic_parent_title(result) -> str | None:
        """Extract synthetic parent title from hierarchy information."""
        parent_id = FormatterUtils.extract_synthetic_parent_id(result)
        return parent_id  # In most cases, parent ID is the title

    @staticmethod
    def extract_synthetic_breadcrumb(result) -> str | None:
        """Extract synthetic breadcrumb from result metadata."""
        # First try the breadcrumb_text field
        if hasattr(result, "breadcrumb_text") and result.breadcrumb_text:
            return result.breadcrumb_text

        # Try to construct from file path
        if getattr(result, "source_type", None) == "localfile" and getattr(
            result, "file_path", None
        ):
            path_parts = [p for p in result.file_path.split("/") if p and p != "."]
            if path_parts:
                # Include filename without extension for local files
                filename = path_parts[-1]
                if "." in filename:
                    filename = filename.rsplit(".", 1)[0]
                path_parts[-1] = filename
                return " > ".join(path_parts)

        # Try hierarchy context for Confluence
        if hasattr(result, "hierarchy_context") and result.hierarchy_context:
            return result.hierarchy_context

        return None

    @staticmethod
    def extract_has_children(result) -> bool:
        """Extract whether the result has child documents."""
        # Check if result has a has_children method
        if hasattr(result, "has_children") and callable(result.has_children):
            return result.has_children()

        # Check for children_count attribute
        children_count = getattr(result, "children_count", 0)
        return children_count > 0

    @staticmethod
    def extract_children_count(result, all_results: list) -> int:
        """Extract children count for a result."""
        # First check if the result has a children_count attribute
        if hasattr(result, "children_count"):
            return getattr(result, "children_count", 0)

        # Calculate based on hierarchy if all_results provided
        if all_results:
            result_id = getattr(result, "document_id", None) or getattr(
                result, "source_title", ""
            )
            children = [
                r
                for r in all_results
                if FormatterUtils.extract_synthetic_parent_id(r) == result_id
            ]
            return len(children)

        return 0

    @staticmethod
    def extract_safe_filename(result: HybridSearchResult) -> str:
        """Extract a safe filename from result, handling various edge cases."""
        # First try original_filename (prioritize this for all results)
        original_filename = getattr(result, "original_filename", None)
        if original_filename:
            return original_filename

        # Then try file_path
        file_path = getattr(result, "file_path", None)
        if file_path:
            # Extract filename from path
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            return filename if filename else "Unknown"

        # Fallback to source_title
        return getattr(result, "source_title", "Unknown")

    @staticmethod
    def extract_file_type_minimal(result: HybridSearchResult) -> str:
        """Extract minimal file type information from result."""
        # First try mime_type for more detailed type information
        mime_type = getattr(result, "mime_type", None)
        if mime_type:
            # Convert common mime types to readable format
            if mime_type == "text/markdown":
                return "markdown"
            elif mime_type.startswith("text/"):
                return mime_type.replace("text/", "")
            elif mime_type.startswith("application/pdf"):
                return "pdf"
            elif mime_type.startswith("application/"):
                return mime_type.replace("application/", "")
            elif "/" in mime_type:
                return mime_type.split("/")[-1]

        # Fallback to filename extension
        filename = FormatterUtils.extract_safe_filename(result)
        if "." in filename:
            extension = filename.split(".")[-1].lower()
            return extension

        # Final fallback based on source_type
        source_type = getattr(result, "source_type", "")
        if source_type == "confluence":
            return "page"
        elif source_type == "jira":
            return "ticket"
        else:
            return "unknown"

    @staticmethod
    def organize_attachments_by_type(results: list[HybridSearchResult]) -> list[dict]:
        """Organize attachment results by file type for better presentation."""
        # Group by file type
        type_groups = {}
        for result in results:
            file_type = FormatterUtils.extract_file_type_minimal(result)
            source_type = getattr(result, "source_type", "unknown")

            group_key = FormatterUtils.get_attachment_group_key(file_type, source_type)

            if group_key not in type_groups:
                type_groups[group_key] = []
            type_groups[group_key].append(result)

        # Convert to list format with friendly names
        organized_groups = []
        for group_key, group_results in type_groups.items():
            organized_groups.append(
                {
                    "group_name": FormatterUtils.generate_friendly_group_name(
                        group_key
                    ),
                    "results": group_results,
                    "count": len(group_results),
                    "file_types": list(
                        {
                            FormatterUtils.extract_file_type_minimal(r)
                            for r in group_results
                        }
                    ),
                }
            )

        # Sort by count (descending)
        organized_groups.sort(key=lambda x: x["count"], reverse=True)
        return organized_groups

    @staticmethod
    def get_attachment_group_key(file_type: str, source_type: str) -> str:
        """Generate logical grouping keys for attachments."""
        # Map to broader categories for better UX
        document_types = {"pdf", "doc", "docx", "txt", "md"}
        spreadsheet_types = {"xls", "xlsx", "csv"}
        image_types = {"png", "jpg", "jpeg", "gif", "svg"}

        if file_type in document_types:
            return f"documents_{source_type}"
        elif file_type in spreadsheet_types:
            return f"spreadsheets_{source_type}"
        elif file_type in image_types:
            return f"images_{source_type}"
        else:
            return f"other_{source_type}"

    @staticmethod
    def generate_friendly_group_name(group_key: str) -> str:
        """Generate user-friendly group names."""
        # Parse the group key format: "type_source"
        if "_" in group_key:
            file_category, source_type = group_key.split("_", 1)

            # Capitalize and format
            category_map = {
                "documents": "Documents",
                "spreadsheets": "Spreadsheets",
                "images": "Images",
                "other": "Other Files",
            }

            source_map = {
                "confluence": "Confluence",
                "localfile": "Local Files",
                "git": "Git Repository",
                "jira": "Jira",
            }

            category = category_map.get(file_category, file_category.title())
            source = source_map.get(source_type, source_type.title())

            return f"{category} ({source})"

        return group_key.title()

    @staticmethod
    def generate_conflict_resolution_suggestion(conflict_info: dict) -> str:
        """Generate a resolution suggestion based on conflict type and information."""
        conflict_type = conflict_info.get("type", "unknown")

        if conflict_type == "version_conflict":
            return "Review documents for version consistency and update outdated information"
        elif conflict_type == "contradictory_guidance":
            return "Reconcile contradictory guidance by consulting authoritative sources or stakeholders"
        elif conflict_type == "procedural_conflict":
            return "Establish a single, authoritative procedure and deprecate conflicting processes"
        elif conflict_type == "requirement_conflict":
            return "Clarify requirements with stakeholders and update documentation to resolve ambiguity"
        elif conflict_type == "implementation_conflict":
            return "Review implementation approaches and standardize on the preferred solution"
        else:
            return (
                "Review conflicting information and establish a single source of truth"
            )

    @staticmethod
    def extract_affected_sections(conflict_info: dict) -> list:
        """Extract affected sections from conflict information."""
        affected_sections = []

        # Try to identify sections from structured indicators
        structured_indicators = conflict_info.get("structured_indicators", [])
        for indicator in structured_indicators:
            if isinstance(indicator, dict):
                # Look for section keywords in the snippets
                doc1_snippet = indicator.get("doc1_snippet", "")
                doc2_snippet = indicator.get("doc2_snippet", "")

                sections = set()
                for snippet in [doc1_snippet, doc2_snippet]:
                    # Common section patterns
                    if "introduction" in snippet.lower():
                        sections.add("Introduction")
                    elif "requirement" in snippet.lower():
                        sections.add("Requirements")
                    elif "procedure" in snippet.lower() or "process" in snippet.lower():
                        sections.add("Procedures")
                    elif "implementation" in snippet.lower():
                        sections.add("Implementation")
                    elif (
                        "configuration" in snippet.lower()
                        or "config" in snippet.lower()
                    ):
                        sections.add("Configuration")
                    elif "guideline" in snippet.lower() or "guide" in snippet.lower():
                        sections.add("Guidelines")

                affected_sections.extend(list(sections))

        # Remove duplicates and return
        return list(set(affected_sections)) if affected_sections else ["Content"]
