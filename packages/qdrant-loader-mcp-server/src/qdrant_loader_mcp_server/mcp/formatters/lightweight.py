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
            "similarity_index": [
                {
                    # Support dict or object for document field
                    **(
                        lambda document: {
                            "document_id": (
                                document.get("document_id", "")
                                if isinstance(document, dict)
                                else getattr(document, "document_id", "")
                            ),
                            "title": (
                                document.get("source_title", "Untitled")
                                if isinstance(document, dict)
                                else getattr(document, "source_title", "Untitled")
                            ),
                            "navigation_hints": {
                                "can_expand": True,
                                "has_children": (
                                    document.get("has_children", False)
                                    if isinstance(document, dict)
                                    else getattr(document, "has_children", False)
                                ),
                            },
                        }
                    )(doc_info.get("document", {})),
                    "similarity_score": doc_info.get("similarity_score", 0),
                    "similarity_info": {
                        "metric_scores": doc_info.get("metric_scores", {}),
                        "reasons": doc_info.get("similarity_reasons", []),
                    },
                }
                for doc_info in similar_docs[:10]  # Limit to top 10
            ],
            "query_info": {
                "target_query": target_query,
                "comparison_query": comparison_query,
                "total_found": len(similar_docs),
            },
            "navigation": {
                "total_found": len(similar_docs),
                "showing": min(len(similar_docs), 10),
            },
            # Keep legacy fields for backward compatibility
            "target_query": target_query,
            "comparison_query": comparison_query,
            "similar_documents": [
                {
                    "document": FormatterUtils.extract_minimal_doc_fields(
                        doc_info.get("document")
                    ),
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
        documents: list = None,
    ) -> dict[str, Any]:
        """Create lightweight conflict analysis results."""
        # Handle both new format ("conflicts") and old format ("conflicting_pairs")
        conflict_list = conflicts.get("conflicts", [])
        conflicting_pairs = conflicts.get("conflicting_pairs", [])

        processed_conflicts = []

        # Process conflicting_pairs format (tuples)
        for pair in conflicting_pairs:
            if len(pair) >= 3:
                doc1_id, doc2_id, conflict_info = pair[0], pair[1], pair[2]
                processed_conflicts.append(
                    {
                        "conflict_type": conflict_info.get("type", "unknown"),
                        "conflict_score": conflict_info.get("confidence", 0.0),
                        "conflict_description": conflict_info.get("description", ""),
                        "conflicting_statements": conflict_info.get(
                            "structured_indicators", []
                        ),
                        "document_1_id": doc1_id,
                        "document_2_id": doc2_id,
                    }
                )

        # Process conflicts format (dicts)
        for conflict in conflict_list:
            processed_conflicts.append(
                {
                    "conflict_type": conflict.get("conflict_type", "unknown"),
                    "conflict_score": conflict.get(
                        "confidence", conflict.get("severity_score", 0.0)
                    ),
                    "conflict_description": conflict.get("description", ""),
                    "conflicting_statements": FormatterUtils.extract_conflicting_statements(
                        conflict
                    ),
                }
            )

        return {
            "conflicts_detected": processed_conflicts[:5],  # Limit to top 5
            "conflict_summary": {
                "total_conflicts": len(processed_conflicts),
                "avg_confidence": (
                    sum(c.get("conflict_score", 0) for c in processed_conflicts)
                    / len(processed_conflicts)
                    if processed_conflicts
                    else 0
                ),
                "conflict_types": list(
                    {c.get("conflict_type", "unknown") for c in processed_conflicts}
                ),
            },
            "analysis_metadata": {
                "query": query,
                "document_count": conflicts.get("query_metadata", {}).get(
                    "document_count", len(documents) if documents else 0
                ),
                "analysis_depth": "lightweight",
            },
            "navigation": {
                "total_found": len(processed_conflicts),
                "showing": min(len(processed_conflicts), 5),
                "has_more": len(processed_conflicts) > 5,
            },
            # Keep legacy fields for backward compatibility
            "query": query,
            "conflicts": processed_conflicts[:5],
            "resolution_suggestions": conflicts.get("resolution_suggestions", []),
            "total_conflicts": len(processed_conflicts),
        }

    @staticmethod
    def create_lightweight_cluster_results(
        clusters: dict[str, Any],
        query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight document clustering results."""
        cluster_list = clusters.get("clusters", [])
        clustering_metadata = clusters.get("clustering_metadata", {})

        formatted_clusters = []
        for cluster in cluster_list[:8]:  # Limit to 8 clusters
            formatted_clusters.append(
                {
                    "cluster_id": cluster.get(
                        "id", f"cluster_{len(formatted_clusters)+1}"
                    ),
                    "cluster_name": cluster.get(
                        "name", f"Cluster {len(formatted_clusters)+1}"
                    ),
                    "coherence_score": cluster.get("coherence_score", 0),
                    "document_count": len(cluster.get("documents", [])),
                    "documents": [
                        FormatterUtils.extract_minimal_doc_fields(doc)
                        for doc in cluster.get("documents", [])[
                            :5
                        ]  # Limit docs per cluster
                    ],
                    "cluster_themes": cluster.get(
                        "shared_entities", cluster.get("cluster_themes", [])
                    ),
                    "centroid_topics": cluster.get("centroid_topics", []),
                }
            )

        return {
            "cluster_index": formatted_clusters,
            "clustering_metadata": {
                "strategy": clustering_metadata.get("strategy", "unknown"),
                "total_documents": clustering_metadata.get(
                    "total_documents",
                    sum(len(cluster.get("documents", [])) for cluster in cluster_list),
                ),
                "clusters_created": clustering_metadata.get(
                    "clusters_created", len(cluster_list)
                ),
                "query": query,
                "analysis_depth": "lightweight",
            },
            "expansion_info": {
                "total_clusters": len(cluster_list),
                "showing": len(formatted_clusters),
                "can_expand": len(cluster_list) > len(formatted_clusters),
                "documents_per_cluster": 5,  # Max docs shown per cluster
            },
            # Keep legacy fields for backward compatibility
            "query": query,
            "clusters": [
                {
                    "cluster_id": cluster.get("id", f"cluster_{i+1}"),
                    "documents": [
                        FormatterUtils.extract_minimal_doc_fields(doc)
                        for doc in cluster.get("documents", [])[
                            :5
                        ]  # Limit docs per cluster
                    ],
                    "cluster_themes": cluster.get(
                        "shared_entities", cluster.get("cluster_themes", [])
                    ),
                    "coherence_score": cluster.get("coherence_score", 0),
                    "document_count": len(cluster.get("documents", [])),
                }
                for i, cluster in enumerate(cluster_list[:8])  # Limit to 8 clusters
            ],
            "total_clusters": len(cluster_list),
            "total_documents": sum(
                len(cluster.get("documents", [])) for cluster in cluster_list
            ),
        }

    @staticmethod
    def create_lightweight_hierarchy_results(
        filtered_results: list[HybridSearchResult],
        organized_results: dict[str, list[HybridSearchResult]],
        query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight hierarchical results."""
        hierarchy_groups_data = []
        hierarchy_index_data = []

        for group_name, results in organized_results.items():
            clean_group_name = FormatterUtils.generate_clean_group_name(
                group_name, results
            )
            documents_data = [
                {
                    **FormatterUtils.extract_minimal_doc_fields(result),
                    "depth": FormatterUtils.extract_synthetic_depth(result),
                    "has_children": FormatterUtils.extract_has_children(result),
                    "parent_title": FormatterUtils.extract_synthetic_parent_title(
                        result
                    ),
                }
                for result in results[:10]  # Limit per group
            ]
            # Calculate depth range for the group
            depths = [
                FormatterUtils.extract_synthetic_depth(result) for result in results
            ]
            depth_range = [min(depths), max(depths)] if depths else [0, 0]

            group_data = {
                "group_key": group_name,  # Original key
                "group_name": clean_group_name,  # Clean display name
                "documents": documents_data,
                "document_ids": [doc["document_id"] for doc in documents_data],
                "depth_range": depth_range,
                "total_documents": len(results),
            }
            hierarchy_groups_data.append(group_data)

            # Create index entries as individual documents for compatibility
            for result in results:
                hierarchy_index_data.append(
                    {
                        "document_id": getattr(
                            result, "document_id", f"doc_{id(result)}"
                        ),
                        "title": getattr(result, "title", "Untitled"),
                        "score": getattr(result, "score", 0.0),
                        "hierarchy_info": {
                            "depth": FormatterUtils.extract_synthetic_depth(result),
                            "has_children": FormatterUtils.extract_has_children(result),
                            "parent_title": FormatterUtils.extract_synthetic_parent_title(
                                result
                            ),
                            "group_name": clean_group_name,
                            "source_type": getattr(result, "source_type", "unknown"),
                        },
                        "navigation_hints": {
                            "breadcrumb": FormatterUtils.extract_synthetic_parent_title(
                                result
                            ),
                            "level": FormatterUtils.extract_synthetic_depth(result),
                            "group": clean_group_name,
                            "siblings_count": len(results)
                            - 1,  # Other docs in same group
                            "children_count": 0,  # Default, could be enhanced with actual child detection
                        },
                    }
                )

        return {
            "hierarchy_index": hierarchy_index_data,
            "hierarchy_groups": hierarchy_groups_data,
            "total_found": len(filtered_results),
            "query_metadata": {
                "query": query,
                "search_query": query,  # Alias for compatibility
                "total_documents": len(filtered_results),
                "total_groups": len(organized_results),
                "analysis_type": "hierarchy",
                "source_types_found": list(
                    {
                        getattr(result, "source_type", "unknown")
                        for result in filtered_results
                    }
                ),
            },
            # Keep legacy fields for backward compatibility
            "query": query,
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
        result: dict[str, Any] = {
            "target_query": target_query,
            "complementary_index": [
                {
                    "document_id": getattr(
                        rec.get("document"), "document_id", rec.get("document_id")
                    ),
                    "title": getattr(
                        rec.get("document"),
                        "source_title",
                        rec.get("title", "Untitled"),
                    ),
                    "complementary_score": rec.get("relevance_score", 0),
                    "complementary_reason": rec.get(
                        "recommendation_reason", rec.get("reason", "")
                    ),
                    "relationship_type": rec.get("strategy", ""),
                    "basic_metadata": (
                        lambda doc_obj, rec_dict: {
                            "source_type": (
                                getattr(doc_obj, "source_type", None)
                                if doc_obj is not None
                                else None
                            )
                            or rec_dict.get("source_type")
                            or (
                                doc_obj.get("source_type")
                                if isinstance(doc_obj, dict)
                                else None
                            )
                            or "unknown",
                            "project_id": (
                                getattr(doc_obj, "project_id", None)
                                if doc_obj is not None
                                else None
                            )
                            or rec_dict.get("project_id")
                            or (
                                doc_obj.get("project_id")
                                if isinstance(doc_obj, dict)
                                else None
                            ),
                        }
                    )(rec.get("document"), rec),
                }
                for rec in complementary_recommendations
            ],
            "complementary_recommendations": [
                {
                    "document": {
                        "document_id": rec.get("document_id"),
                        "title": rec.get("title"),
                        "source_type": rec.get("source_type", "unknown"),
                        "score": rec.get("relevance_score", 0),
                    },
                    "relationship_type": "related",
                    "relevance_score": rec.get("relevance_score", 0),
                    "reasons": [rec.get("reason", "")] if rec.get("reason") else [],
                }
                for rec in complementary_recommendations[:8]  # Limit to 8
            ],
            "context_documents_analyzed": context_documents_analyzed,
            "total_recommendations": len(complementary_recommendations),
            "complementary_summary": {
                "total_found": len(complementary_recommendations),
                "complementary_found": len(complementary_recommendations),
                "total_analyzed": context_documents_analyzed,
                "average_score": (
                    sum(
                        rec.get("relevance_score", 0)
                        for rec in complementary_recommendations
                    )
                    / len(complementary_recommendations)
                    if complementary_recommendations
                    else 0
                ),
                "strategies_used": list(
                    {
                        rec.get("strategy", "unknown")
                        for rec in complementary_recommendations
                    }
                ),
            },
            "lazy_loading_enabled": False,
            "expand_document_hint": "Use tools/call with 'search' to get full document details",
        }

        # Only include target_document if available; shape must match schema
        if target_document is not None:
            if isinstance(target_document, dict):
                result["target_document"] = {
                    "document_id": target_document.get(
                        "document_id", target_document.get("id", "")
                    ),
                    "title": target_document.get("title", "Untitled"),
                    "content_preview": target_document.get("content_preview", ""),
                    "source_type": target_document.get("source_type", "unknown"),
                }
            else:
                # Assume HybridSearchResult-like object
                title_val = (
                    target_document.get_display_title()
                    if hasattr(target_document, "get_display_title")
                    else getattr(target_document, "source_title", "Untitled")
                )
                text_val = getattr(target_document, "text", "") or ""
                result["target_document"] = {
                    "document_id": getattr(
                        target_document,
                        "document_id",
                        getattr(target_document, "id", ""),
                    ),
                    "title": title_val,
                    "content_preview": (
                        text_val[:200] + "..."
                        if isinstance(text_val, str) and len(text_val) > 200
                        else text_val
                    ),
                    "source_type": getattr(target_document, "source_type", "unknown"),
                }

        return result

    @staticmethod
    def create_lightweight_attachment_results(
        filtered_results: list[HybridSearchResult],
        attachment_filter: dict[str, Any],
        query: str = "",
    ) -> dict[str, Any]:
        """Create lightweight attachment results."""
        # Filter only attachment results
        attachment_results = [
            result
            for result in filtered_results
            if getattr(result, "is_attachment", False)
        ]

        # Group by file type for organized display
        organized_attachments = {}
        for result in attachment_results:
            file_type = FormatterUtils.extract_file_type_minimal(result)
            if file_type not in organized_attachments:
                organized_attachments[file_type] = []
            organized_attachments[file_type].append(result)

        # Create attachment index
        attachment_index = [
            {
                "document_id": getattr(result, "document_id", ""),
                "title": getattr(result, "source_title", "Untitled"),
                "attachment_info": {
                    "filename": FormatterUtils.extract_safe_filename(result),
                    "file_type": FormatterUtils.extract_file_type_minimal(result),
                    "file_size": getattr(result, "file_size", None),
                },
                "score": getattr(result, "score", 0.0),
                "source_url": getattr(result, "source_url", None),
            }
            for result in attachment_results[:20]  # Limit to top 20
        ]

        # Create attachment groups
        attachment_groups = [
            {
                "file_type": file_type,
                "attachments": [
                    {
                        **FormatterUtils.extract_minimal_doc_fields(result),
                        "filename": FormatterUtils.extract_safe_filename(result),
                        "file_type": FormatterUtils.extract_file_type_minimal(result),
                    }
                    for result in results[:15]  # Limit per group
                ],
                "total_attachments": len(results),
            }
            for file_type, results in organized_attachments.items()
        ]

        return {
            "attachment_index": attachment_index,
            "attachment_groups": attachment_groups,
            "total_found": len(attachment_results),
            "query_metadata": {
                "query": query,
                "filter": attachment_filter,
                "total_attachments": len(attachment_results),
                "file_types": list(organized_attachments.keys()),
            },
            # Keep legacy fields for backward compatibility
            "query": query,
            "total_groups": len(organized_attachments),
        }
