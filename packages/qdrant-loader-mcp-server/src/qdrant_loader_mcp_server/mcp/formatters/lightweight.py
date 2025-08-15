"""
Lightweight Result Formatters - Efficient Result Construction.

This module handles the creation of lightweight, efficient result structures
for MCP responses, optimizing for minimal data transfer and fast processing.
"""

from typing import Any
from ...search.components.search_result_models import HybridSearchResult
from .utils import FormatterUtils


class LightweightResultFormatters:
    """Handles lightweight result construction operations."""

    @staticmethod 
    def create_lightweight_similar_documents_results(
        similar_docs: list[dict[str, Any]],
        target_query: str = "",
        comparison_query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight similar documents results."""
        return {
            "target_query": target_query,
            "comparison_query": comparison_query,
            "similar_documents": [
                {
                    "document": FormatterUtils.extract_minimal_doc_fields(doc_info.get("document")),
                    "similarity_score": doc_info.get("similarity_score", 0),
                    "similarity_reasons": doc_info.get("similarity_reasons", []),
                }
                for doc_info in similar_docs[:10]  # Limit to top 10
            ],
            "total_found": len(similar_docs),
        }

    @staticmethod
    def create_lightweight_conflict_results(
        conflicts: dict[str, Any],
        query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight conflict analysis results."""
        conflict_list = conflicts.get("conflicts", [])
        
        return {
            "query": query,
            "conflicts": [
                {
                    "conflict_id": f"conflict_{i+1}",
                    "document_1": FormatterUtils.extract_minimal_doc_fields(conflict.get("document_1", {})),
                    "document_2": FormatterUtils.extract_minimal_doc_fields(conflict.get("document_2", {})),
                    "conflict_type": conflict.get("conflict_type", "unknown"),
                    "severity": conflict.get("severity", "unknown"),
                    "conflicting_statements": FormatterUtils.extract_conflicting_statements(conflict),
                }
                for i, conflict in enumerate(conflict_list[:5])  # Limit to top 5
            ],
            "resolution_suggestions": conflicts.get("resolution_suggestions", []),
            "total_conflicts": len(conflict_list),
        }

    @staticmethod
    def create_lightweight_cluster_results(
        clusters: dict[str, Any],
        query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight document clustering results."""
        cluster_list = clusters.get("clusters", [])
        
        return {
            "query": query, 
            "clusters": [
                {
                    "cluster_id": f"cluster_{i+1}",
                    "documents": [
                        FormatterUtils.extract_minimal_doc_fields(doc)
                        for doc in cluster.get("documents", [])[:5]  # Limit docs per cluster
                    ],
                    "cluster_themes": cluster.get("cluster_themes", []),
                    "coherence_score": cluster.get("coherence_score", 0),
                    "document_count": len(cluster.get("documents", [])),
                }
                for i, cluster in enumerate(cluster_list[:8])  # Limit to 8 clusters
            ],
            "total_clusters": len(cluster_list),
            "total_documents": sum(len(cluster.get("documents", [])) for cluster in cluster_list),
        }

    @staticmethod
    def create_lightweight_hierarchy_results(
        organized_results: dict[str, list[HybridSearchResult]],
        query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight hierarchical results."""
        return {
            "query": query,
            "hierarchy_groups": [
                {
                    "group_name": FormatterUtils.generate_clean_group_name(group_name, results),
                    "documents": [
                        {
                            **FormatterUtils.extract_minimal_doc_fields(result),
                            "depth": FormatterUtils.extract_synthetic_depth(result),
                            "has_children": FormatterUtils.extract_has_children(result),
                            "parent_title": FormatterUtils.extract_synthetic_parent_title(result),
                        }
                        for result in results[:10]  # Limit per group
                    ],
                    "total_documents": len(results),
                }
                for group_name, results in organized_results.items()
            ],
            "total_groups": len(organized_results),
        }

    @staticmethod
    def create_lightweight_complementary_results(
        complementary_recommendations: list[dict[str, Any]],
        target_document: "HybridSearchResult" = None,
        context_documents_analyzed: int = 0,
        target_query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight complementary content results."""
        return {
            "target_query": target_query,
            "target_document": (
                FormatterUtils.extract_minimal_doc_fields(target_document) 
                if target_document else None
            ),
            "complementary_recommendations": [
                {
                    "document": FormatterUtils.extract_minimal_doc_fields(rec.get("document")),
                    "relationship_type": rec.get("relationship_type", "related"),
                    "relevance_score": rec.get("relevance_score", 0),
                    "reasons": rec.get("reasons", []),
                }
                for rec in complementary_recommendations[:8]  # Limit to 8
            ],
            "context_documents_analyzed": context_documents_analyzed,
            "total_recommendations": len(complementary_recommendations),
        }

    @staticmethod
    def create_lightweight_attachment_results(
        organized_attachments: list[dict],
        query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight attachment results."""
        return {
            "query": query,
            "attachment_groups": [
                {
                    "group_name": group["group_name"],
                    "file_types": group["file_types"],
                    "attachments": [
                        {
                            **FormatterUtils.extract_minimal_doc_fields(result),
                            "filename": FormatterUtils.extract_safe_filename(result),
                            "file_type": FormatterUtils.extract_file_type_minimal(result),
                        }
                        for result in group["results"][:15]  # Limit per group
                    ],
                    "total_attachments": group["count"],
                }
                for group in organized_attachments[:10]  # Limit groups
            ],
            "total_groups": len(organized_attachments),
        }
