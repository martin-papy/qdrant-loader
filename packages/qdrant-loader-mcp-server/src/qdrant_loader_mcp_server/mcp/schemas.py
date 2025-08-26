"""MCP Tool Schema Definitions - refactored into modular files."""

from typing import Any

# Note: This module defines the MCP tool schemas directly. Duplicate
# import-based aliases have been removed to avoid redefinitions.


class MCPSchemas:
    """Backward-compatible wrapper exposing static methods."""

    # Static methods implemented below

    @staticmethod
    def get_hierarchy_search_tool_schema() -> dict[str, Any]:
        """Get the hierarchy search tool schema."""
        return {
            "name": "hierarchy_search",
            "description": "Search Confluence documents with hierarchy-aware filtering and organization",
            "annotations": {"read-only": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language",
                    },
                    "hierarchy_filter": {
                        "type": "object",
                        "properties": {
                            "depth": {
                                "type": "integer",
                                "description": "Filter by specific hierarchy depth (0 = root pages)",
                            },
                            "parent_title": {
                                "type": "string",
                                "description": "Filter by parent page title",
                            },
                            "root_only": {
                                "type": "boolean",
                                "description": "Show only root pages (no parent)",
                            },
                            "has_children": {
                                "type": "boolean",
                                "description": "Filter by whether pages have children",
                            },
                        },
                    },
                    "organize_by_hierarchy": {
                        "type": "boolean",
                        "description": "Group results by hierarchy structure",
                        "default": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "number"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "hierarchy_path": {"type": "string"},
                                "parent_title": {"type": "string"},
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "space_key": {"type": "string"},
                                        "project_id": {"type": "string"},
                                        "page_id": {"type": "string"},
                                        "hierarchy_level": {"type": "integer"},
                                    },
                                },
                            },
                        },
                    },
                    "total_found": {"type": "integer"},
                    "hierarchy_organization": {
                        "type": "object",
                        "properties": {
                            "organized_by_hierarchy": {"type": "boolean"},
                            "hierarchy_groups": {
                                "type": "array",
                                "items": {"type": "object"},
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def get_attachment_search_tool_schema() -> dict[str, Any]:
        """Get the attachment search tool schema."""
        return {
            "name": "attachment_search",
            "description": "Search for file attachments and their parent documents across Confluence, Jira, and other sources",
            "annotations": {"read-only": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language",
                    },
                    "attachment_filter": {
                        "type": "object",
                        "properties": {
                            "attachments_only": {
                                "type": "boolean",
                                "description": "Show only file attachments",
                            },
                            "parent_document_title": {
                                "type": "string",
                                "description": "Filter by parent document title",
                            },
                            "file_type": {
                                "type": "string",
                                "description": "Filter by file type (e.g., 'pdf', 'xlsx', 'png')",
                            },
                            "file_size_min": {
                                "type": "integer",
                                "description": "Minimum file size in bytes",
                            },
                            "file_size_max": {
                                "type": "integer",
                                "description": "Maximum file size in bytes",
                            },
                            "author": {
                                "type": "string",
                                "description": "Filter by attachment author",
                            },
                        },
                    },
                    "include_parent_context": {
                        "type": "boolean",
                        "description": "Include parent document information in results",
                        "default": True,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "number"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "attachment_info": {
                                    "type": "object",
                                    "properties": {
                                        "filename": {"type": "string"},
                                        "file_type": {"type": "string"},
                                        "file_size": {"type": "integer"},
                                        "parent_document": {"type": "string"},
                                    },
                                },
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {"type": "string"},
                                        "project_id": {"type": "string"},
                                        "upload_date": {"type": "string"},
                                        "author": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "total_found": {"type": "integer"},
                    "attachment_summary": {
                        "type": "object",
                        "properties": {
                            "total_attachments": {"type": "integer"},
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "attachments_only": {"type": "boolean"},
                        },
                    },
                },
            },
        }

    @staticmethod
    def get_analyze_relationships_tool_schema() -> dict[str, Any]:
        """Get the analyze document relationships tool schema."""
        return {
            "name": "analyze_relationships",
            "description": "Analyze relationships between documents",
            "annotations": {"read-only": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to get documents for analysis",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to analyze",
                        "default": 20,
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of source types to filter by",
                    },
                    "project_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of project IDs to filter by",
                    },
                    "use_llm": {
                        "type": "boolean",
                        "description": "Enable LLM validation for top pairs (budgeted)",
                    },
                    "max_llm_pairs": {
                        "type": "integer",
                        "description": "Maximum number of pairs to analyze with LLM",
                    },
                    "overall_timeout_s": {
                        "type": "number",
                        "description": "Overall analysis budget in seconds",
                    },
                    "max_pairs_total": {
                        "type": "integer",
                        "description": "Maximum candidate pairs to analyze after tiering",
                    },
                    "text_window_chars": {
                        "type": "integer",
                        "description": "Per-document text window size for lexical analysis",
                    },
                },
                "required": ["query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_1": {"type": "string"},
                                "document_2": {"type": "string"},
                                "relationship_type": {"type": "string"},
                                "score": {"type": "number"},
                                "description": {"type": "string"},
                            },
                        },
                    },
                    "total_analyzed": {"type": "integer"},
                    "summary": {"type": "string"},
                },
            },
        }

    @staticmethod
    def get_find_similar_tool_schema() -> dict[str, Any]:
        """Get the find similar documents tool schema."""
        return {
            "name": "find_similar_documents",
            "description": "Find documents similar to a target document using multiple similarity metrics",
            "annotations": {"read-only": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_query": {
                        "type": "string",
                        "description": "Query to find the target document",
                    },
                    "comparison_query": {
                        "type": "string",
                        "description": "Query to get documents to compare against",
                    },
                    "similarity_metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "entity_overlap",
                                "topic_overlap",
                                "semantic_similarity",
                                "metadata_similarity",
                                "hierarchical_distance",
                                "content_features",
                            ],
                        },
                        "description": "Similarity metrics to use",
                    },
                    "max_similar": {
                        "type": "integer",
                        "description": "Maximum number of similar documents to return",
                        "default": 5,
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of source types to filter by",
                    },
                    "project_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of project IDs to filter by",
                    },
                },
                "required": ["target_query", "comparison_query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "similar_documents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "title": {"type": "string"},
                                "similarity_score": {"type": "number"},
                                "similarity_metrics": {
                                    "type": "object",
                                    "properties": {
                                        "entity_overlap": {"type": "number"},
                                        "topic_overlap": {"type": "number"},
                                        "semantic_similarity": {"type": "number"},
                                        "metadata_similarity": {"type": "number"},
                                    },
                                },
                                "similarity_reason": {"type": "string"},
                                "content_preview": {"type": "string"},
                            },
                        },
                    },
                    "target_document": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content_preview": {"type": "string"},
                            "source_type": {"type": "string"},
                        },
                    },
                    "similarity_summary": {
                        "type": "object",
                        "properties": {
                            "total_compared": {"type": "integer"},
                            "similar_found": {"type": "integer"},
                            "highest_similarity": {"type": "number"},
                            "metrics_used": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def get_detect_conflicts_tool_schema() -> dict[str, Any]:
        """Get the detect conflicts tool schema."""
        return {
            "name": "detect_document_conflicts",
            "description": "Detect conflicts and contradictions between documents",
            "annotations": {"read-only": True, "compute-intensive": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to get documents for conflict analysis",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to analyze",
                        "default": 10,
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of source types to filter by",
                    },
                    "project_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of project IDs to filter by",
                    },
                },
                "required": ["query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "conflicts_detected": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "conflict_id": {"type": "string"},
                                "document_1": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "content_preview": {"type": "string"},
                                        "source_type": {"type": "string"},
                                    },
                                },
                                "document_2": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "content_preview": {"type": "string"},
                                        "source_type": {"type": "string"},
                                    },
                                },
                                "conflict_type": {"type": "string"},
                                "conflict_score": {"type": "number"},
                                "conflict_description": {"type": "string"},
                                "conflicting_statements": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "from_doc1": {"type": "string"},
                                            "from_doc2": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "conflict_summary": {
                        "type": "object",
                        "properties": {
                            "total_documents_analyzed": {"type": "integer"},
                            "conflicts_found": {"type": "integer"},
                            "conflict_types": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "highest_conflict_score": {"type": "number"},
                        },
                    },
                    "analysis_metadata": {
                        "type": "object",
                        "properties": {
                            "query_used": {"type": "string"},
                            "analysis_date": {"type": "string"},
                            "processing_time_ms": {"type": "number"},
                        },
                    },
                },
            },
        }

    @staticmethod
    def get_find_complementary_tool_schema() -> dict[str, Any]:
        """Get the find complementary content tool schema."""
        return {
            "name": "find_complementary_content",
            "description": "Find content that complements a target document",
            "annotations": {"read-only": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_query": {
                        "type": "string",
                        "description": "Query to find the target document",
                    },
                    "context_query": {
                        "type": "string",
                        "description": "Query to get contextual documents",
                    },
                    "max_recommendations": {
                        "type": "integer",
                        "description": "Maximum number of recommendations",
                        "default": 5,
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of source types to filter by",
                    },
                    "project_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of project IDs to filter by",
                    },
                },
                "required": ["target_query", "context_query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "complementary_content": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "title": {"type": "string"},
                                "content_preview": {"type": "string"},
                                "complementary_score": {"type": "number"},
                                "complementary_reason": {"type": "string"},
                                "relationship_type": {"type": "string"},
                                "source_type": {"type": "string"},
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "project_id": {"type": "string"},
                                        "created_date": {"type": "string"},
                                        "author": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "target_document": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content_preview": {"type": "string"},
                            "source_type": {"type": "string"},
                        },
                    },
                    "complementary_summary": {
                        "type": "object",
                        "properties": {
                            "total_analyzed": {"type": "integer"},
                            "complementary_found": {"type": "integer"},
                            "highest_score": {"type": "number"},
                            "relationship_types": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def get_cluster_documents_tool_schema() -> dict[str, Any]:
        """Get the cluster documents tool schema."""
        return {
            "name": "cluster_documents",
            "description": "Cluster documents based on similarity and relationships",
            "annotations": {"read-only": True, "compute-intensive": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to get documents for clustering",
                    },
                    "strategy": {
                        "type": "string",
                        "enum": [
                            "mixed_features",
                            "entity_based",
                            "topic_based",
                            "project_based",
                            "hierarchical",
                            "adaptive",
                        ],
                        "description": "Clustering strategy to use (adaptive automatically selects the best strategy)",
                        "default": "mixed_features",
                    },
                    "max_clusters": {
                        "type": "integer",
                        "description": "Maximum number of clusters to create",
                        "default": 10,
                    },
                    "min_cluster_size": {
                        "type": "integer",
                        "description": "Minimum size for a cluster",
                        "default": 2,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to cluster",
                        "default": 25,
                    },
                    "source_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of source types to filter by",
                    },
                    "project_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of project IDs to filter by",
                    },
                },
                "required": ["query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "clusters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cluster_id": {"type": "string"},
                                "cluster_name": {"type": "string"},
                                "cluster_theme": {"type": "string"},
                                "document_count": {"type": "integer"},
                                "cohesion_score": {"type": "number"},
                                "documents": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "document_id": {"type": "string"},
                                            "title": {"type": "string"},
                                            "content_preview": {"type": "string"},
                                            "source_type": {"type": "string"},
                                            "cluster_relevance": {"type": "number"},
                                        },
                                    },
                                },
                                "cluster_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "cluster_summary": {"type": "string"},
                            },
                        },
                    },
                    "clustering_metadata": {
                        "type": "object",
                        "properties": {
                            "total_documents": {"type": "integer"},
                            "clusters_created": {"type": "integer"},
                            "strategy": {"type": "string"},
                            "unclustered_documents": {"type": "integer"},
                            "clustering_quality": {"type": "number"},
                            "processing_time_ms": {"type": "number"},
                        },
                    },
                    "cluster_relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cluster_1": {"type": "string"},
                                "cluster_2": {"type": "string"},
                                "relationship_type": {"type": "string"},
                                "relationship_strength": {"type": "number"},
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def get_expand_cluster_tool_schema() -> dict[str, Any]:
        """Get the expand cluster tool schema for lazy loading cluster documents."""
        return {
            "name": "expand_cluster",
            "description": "Retrieve all documents from a specific cluster for lazy loading",
            "annotations": {"read-only": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cluster_id": {
                        "type": "string",
                        "description": "The ID of the cluster to expand and retrieve all documents",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return from cluster (default: 20)",
                        "default": 20,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of documents to skip for pagination (default: 0)",
                        "default": 0,
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include detailed metadata for each document (default: true)",
                        "default": True,
                    },
                },
                "required": ["cluster_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "cluster_id": {
                        "type": "string",
                        "description": "The expanded cluster ID",
                    },
                    "cluster_info": {
                        "type": "object",
                        "description": "Detailed cluster information",
                    },
                    "documents": {
                        "type": "array",
                        "description": "Full list of documents in the cluster",
                    },
                    "pagination": {
                        "type": "object",
                        "description": "Pagination information",
                    },
                },
            },
        }

    @staticmethod
    def get_expand_document_tool_schema() -> dict[str, Any]:
        """Get the expand document tool schema for lazy loading - uses same format as search."""
        return {
            "name": "expand_document",
            "description": "Retrieve full document content by document ID for lazy loading",
            "annotations": {"read-only": True},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The ID of the document to expand and retrieve full content",
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include detailed metadata (default: true)",
                        "default": True,
                    },
                    "include_hierarchy": {
                        "type": "boolean",
                        "description": "Include hierarchy information for Confluence documents (default: true)",
                        "default": True,
                    },
                    "include_attachments": {
                        "type": "boolean",
                        "description": "Include attachment information if available (default: true)",
                        "default": True,
                    },
                },
                "required": ["document_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "number"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "source_type": {"type": "string"},
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {"type": "string"},
                                        "project_id": {"type": "string"},
                                        "created_at": {"type": "string"},
                                        "last_modified": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "total_found": {"type": "integer"},
                    "query_context": {
                        "type": "object",
                        "properties": {
                            "original_query": {"type": "string"},
                            "source_types_filtered": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "project_ids_filtered": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }

    @classmethod
    def get_all_tool_schemas(cls) -> list[dict[str, Any]]:
        """Get all tool schemas."""
        return [
            cls.get_search_tool_schema(),
            cls.get_hierarchy_search_tool_schema(),
            cls.get_attachment_search_tool_schema(),
            cls.get_analyze_relationships_tool_schema(),
            cls.get_find_similar_tool_schema(),
            cls.get_detect_conflicts_tool_schema(),
            cls.get_find_complementary_tool_schema(),
            cls.get_cluster_documents_tool_schema(),
            cls.get_expand_document_tool_schema(),  # ✅ Add expand_document tool
            cls.get_expand_cluster_tool_schema(),  # ✅ Add expand_cluster tool
        ]
