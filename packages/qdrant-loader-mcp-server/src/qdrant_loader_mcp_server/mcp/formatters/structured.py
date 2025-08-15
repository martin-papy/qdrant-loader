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
    ) -> dict[str, Any]:
        """Create structured search results with comprehensive metadata."""
        return {
            "query": query,
            "results": [
                {
                    "document_id": getattr(result, "document_id", ""),
                    "title": getattr(result, "source_title", "Untitled"),
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
                        "is_attachment": getattr(result, "is_attachment", False),
                        "depth": FormatterUtils.extract_synthetic_depth(result),
                        "has_children": FormatterUtils.extract_has_children(result),
                    },
                }
                for result in results[:max_results]
            ],
            "total_results": len(results),
            "metadata": {
                "source_types": list(set(getattr(r, "source_type", "unknown") for r in results)),
                "avg_score": sum(getattr(r, "score", 0) for r in results) / len(results) if results else 0,
            },
        }

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
        organized_attachments: list[dict],
        query: str = "",
    ) -> dict[str, Any]:
        """Create structured attachment results with detailed organization."""
        attachment_data = []
        
        for group in organized_attachments:
            attachments = []
            
            for result in group["results"]:
                attachment_info = {
                    "document_id": getattr(result, "document_id", ""),
                    "filename": FormatterUtils.extract_safe_filename(result),
                    "file_type": FormatterUtils.extract_file_type_minimal(result),
                    "source_type": getattr(result, "source_type", "unknown"),
                    "score": getattr(result, "score", 0.0),
                    "content_snippet": (
                        result.text[:150] + "..." if len(result.text) > 150 else result.text
                    ),
                    "metadata": {
                        "original_filename": getattr(result, "original_filename", None),
                        "attachment_context": getattr(result, "attachment_context", None),
                        "parent_document_title": getattr(result, "parent_document_title", None),
                        "file_path": getattr(result, "file_path", None),
                        "source_url": getattr(result, "source_url", None),
                        "breadcrumb": getattr(result, "breadcrumb_text", None),
                    },
                }
                attachments.append(attachment_info)
            
            attachment_data.append({
                "group_name": group["group_name"],
                "file_types": group["file_types"],
                "attachments": attachments,
                "total_attachments": group["count"],
                "metadata": {
                    "avg_score": sum(getattr(r, "score", 0) for r in group["results"]) / len(group["results"]) if group["results"] else 0,
                    "source_types": list(set(getattr(r, "source_type", "unknown") for r in group["results"])),
                },
            })
        
        return {
            "query": query,
            "attachment_groups": attachment_data,
            "total_groups": len(organized_attachments),
            "total_attachments": sum(group["count"] for group in organized_attachments),
            "metadata": {
                "all_file_types": list(set(ft for group in organized_attachments for ft in group["file_types"])),
                "largest_group_size": max((group["count"] for group in organized_attachments), default=0),
            },
        }
