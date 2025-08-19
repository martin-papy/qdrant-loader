from typing import Any


def get_cluster_documents_tool_schema() -> dict[str, Any]:
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
                            "cluster_keywords": {"type": "array", "items": {"type": "string"}},
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


