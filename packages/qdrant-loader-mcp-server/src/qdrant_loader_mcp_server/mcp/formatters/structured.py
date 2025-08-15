"""
Structured Result Formatters - Complex Data Structure Formatting.

This module handles the creation of complex, structured result formats
for MCP responses that require detailed organization and presentation.
"""

from typing import Any
from ...search.components.search_result_models import HybridSearchResult
from .utils import FormatterUtils


class StructuredResultFormatters:
    """Handles structured result formatting operations."""

    @staticmethod
    def create_structured_search_results(
        results: list[HybridSearchResult],
        query: str = "",
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Create structured search results as a list of formatted results."""
        return [
            {
                "document_id": getattr(result, "document_id", ""),
                "title": result.get_display_title() if hasattr(result, "get_display_title") else getattr(result, "source_title", "Untitled"),
                "content": result.text,
                "content_snippet": (
                    result.text[:300] + "..." if len(result.text) > 300 else result.text
                ),
                "source_type": getattr(result, "source_type", "unknown"),
                "source_url": getattr(result, "source_url", None),
                "file_path": getattr(result, "file_path", None),
                "score": getattr(result, "score", 0.0),
                "metadata": {
                    "breadcrumb": getattr(result, "breadcrumb_text", None),
                    "hierarchy_context": getattr(result, "hierarchy_context", None),
                    "project_info": result.get_project_info() if hasattr(result, "get_project_info") else None,
                    "project_id": getattr(result, "project_id", None),
                    "file_path": getattr(result, "file_path", None),
                    "word_count": getattr(result, "word_count", None),
                    "chunk_index": getattr(result, "chunk_index", None),
                    "total_chunks": getattr(result, "total_chunks", None),
                    "is_attachment": getattr(result, "is_attachment", False),
                    "depth": FormatterUtils.extract_synthetic_depth(result),
                    "has_children": FormatterUtils.extract_has_children(result),
                },
            }
            for result in results[:max_results]
        ]

    @staticmethod 
    def create_structured_hierarchy_results(
        organized_results: dict[str, list[HybridSearchResult]],
        query: str = "",
    ) -> dict[str, Any]:
        """Create structured hierarchical results with full organization."""
        hierarchy_data = []
        
        for group_name, results in organized_results.items():
            # Build hierarchical structure
            root_documents = []
            child_map = {}
            
            for result in results:
                parent_id = FormatterUtils.extract_synthetic_parent_id(result)
                doc_data = {
                    "document_id": getattr(result, "document_id", ""),
                    "title": getattr(result, "source_title", "Untitled"),
                    "content_snippet": (
                        result.text[:200] + "..." if len(result.text) > 200 else result.text
                    ),
                    "source_type": getattr(result, "source_type", "unknown"),
                    "score": getattr(result, "score", 0.0),
                    "depth": FormatterUtils.extract_synthetic_depth(result),
                    "parent_id": parent_id,
                    "has_children": FormatterUtils.extract_has_children(result),
                    "children": [],
                    "metadata": {
                        "breadcrumb": FormatterUtils.extract_synthetic_breadcrumb(result),
                        "hierarchy_context": getattr(result, "hierarchy_context", None),
                        "file_path": getattr(result, "file_path", None),
                    },
                }
                
                if parent_id:
                    if parent_id not in child_map:
                        child_map[parent_id] = []
                    child_map[parent_id].append(doc_data)
                else:
                    root_documents.append(doc_data)
            
            # Attach children to parents
            def attach_children(doc_list):
                for doc in doc_list:
                    doc_id = doc["document_id"]
                    if doc_id in child_map:
                        doc["children"] = child_map[doc_id]
                        attach_children(doc["children"])
            
            attach_children(root_documents)
            
            hierarchy_data.append({
                "group_name": FormatterUtils.generate_clean_group_name(group_name, results),
                "documents": root_documents,
                "total_documents": len(results),
                "max_depth": max((FormatterUtils.extract_synthetic_depth(r) for r in results), default=0),
            })
        
        return {
            "query": query,
            "hierarchy_groups": hierarchy_data,
            "total_groups": len(organized_results),
            "total_documents": sum(len(results) for results in organized_results.values()),
        }

    @staticmethod
    def create_structured_attachment_results(
        filtered_results: list[HybridSearchResult],
        attachment_filter: dict[str, Any],
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Create structured attachment results with detailed organization."""
        # Filter only attachment results
        attachment_results = [result for result in filtered_results if getattr(result, "is_attachment", False)]
        
        # Group by file type
        organized_attachments = {}
        for result in attachment_results:
            file_type = FormatterUtils.extract_file_type_minimal(result)
            if file_type not in organized_attachments:
                organized_attachments[file_type] = []
            organized_attachments[file_type].append(result)
        
        attachment_data = []
        for file_type, results in organized_attachments.items():
            attachments = []
            
            for result in results:
                attachment_info = {
                    "document_id": getattr(result, "document_id", ""),
                    "filename": FormatterUtils.extract_safe_filename(result),
                    "file_type": FormatterUtils.extract_file_type_minimal(result),
                    "source_type": getattr(result, "source_type", "unknown"),
                    "score": getattr(result, "score", 0.0),
                    "content_snippet": (
                        result.text[:150] + "..." if len(result.text) > 150 else result.text
                    ),
                }
                
                if include_metadata:
                    attachment_info["metadata"] = {
                        "original_filename": getattr(result, "original_filename", None),
                        "attachment_context": getattr(result, "attachment_context", None),
                        "parent_document_title": getattr(result, "parent_document_title", None),
                        "file_path": getattr(result, "file_path", None),
                        "source_url": getattr(result, "source_url", None),
                        "breadcrumb": getattr(result, "breadcrumb_text", None),
                    }
                
                attachments.append(attachment_info)
                
            attachment_data.append({
                "group_name": file_type,
                "file_types": [file_type],
                "attachments": attachments,
                "total_attachments": len(attachments),
                "metadata": {
                    "avg_score": sum(getattr(r, "score", 0) for r in results) / len(results) if results else 0,
                    "source_types": list(set(getattr(r, "source_type", "unknown") for r in results)),
                } if include_metadata else {},
            })
        
        return {
            "results": [
                {
                    "document_id": getattr(result, "document_id", ""),
                    "title": getattr(result, "source_title", "Untitled"),
                    "attachment_info": {
                        "filename": FormatterUtils.extract_safe_filename(result),
                        "file_type": FormatterUtils.extract_file_type_minimal(result),
                        "file_size": getattr(result, "file_size", None),
                    },
                    "source_type": getattr(result, "source_type", "unknown"),
                    "score": getattr(result, "score", 0.0),
                    "content_snippet": result.text[:150] + "..." if len(result.text) > 150 else result.text,
                    "metadata": {
                        "file_path": getattr(result, "file_path", None),
                        "source_url": getattr(result, "source_url", None),
                        "breadcrumb": getattr(result, "breadcrumb_text", None),
                        "parent_document_title": getattr(result, "parent_document_title", None),
                    } if include_metadata else {},
                }
                for result in attachment_results
            ],
            "total_found": len(attachment_results),
            "attachment_summary": {
                "total_attachments": len(attachment_results),
                "file_types": list(organized_attachments.keys()),
                "groups_created": len(organized_attachments),
            },
            # Keep additional fields for backward compatibility
            "attachment_groups": attachment_data,
            "total_groups": len(organized_attachments),
            "total_attachments": len(attachment_results),
            "filter_criteria": attachment_filter,
            "metadata": {
                "all_file_types": list(organized_attachments.keys()),
                "largest_group_size": max((len(results) for results in organized_attachments.values()), default=0),
            } if include_metadata else {},
        }
