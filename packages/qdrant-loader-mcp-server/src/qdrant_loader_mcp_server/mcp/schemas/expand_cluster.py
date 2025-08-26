from typing import Any


def get_expand_cluster_tool_schema() -> dict[str, Any]:
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
                    "minimum": 1,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of documents to skip for pagination (default: 0)",
                    "default": 0,
                    "minimum": 0,
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Include detailed metadata for each document (default: true)",
                    "default": True,
                },
            },
            "required": ["cluster_id"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "cluster_id": {
                    "type": "string",
                    "description": "The expanded cluster ID",
                },
                "cluster_info": {
                    "type": "object",
                    "description": "Detailed cluster information",
                    "additionalProperties": False,
                    "properties": {
                        "cluster_name": {"type": "string"},
                        "cluster_theme": {"type": "string"},
                        "document_count": {"type": "integer"},
                    },
                },
                "documents": {
                    "type": "array",
                    "description": "Full list of documents in the cluster",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"},
                            "metadata": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["id", "text"],
                    },
                },
                "pagination": {
                    "type": "object",
                    "description": "Pagination information",
                    "additionalProperties": False,
                    "properties": {
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                        "total": {"type": "integer"},
                        "has_more": {"type": "boolean"},
                    },
                    "required": ["page", "page_size", "total", "has_more"],
                },
            },
            "required": ["cluster_id", "documents", "pagination"],
        },
    }
