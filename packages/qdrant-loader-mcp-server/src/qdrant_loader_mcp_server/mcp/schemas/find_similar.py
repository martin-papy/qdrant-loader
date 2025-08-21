from typing import Any


def get_find_similar_tool_schema() -> dict[str, Any]:
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
                                    "hierarchical_distance": {"type": "number"},
                                    "content_features": {"type": "number"},
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
                        "metrics_used": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    }


