from typing import Any


def get_find_complementary_tool_schema() -> dict[str, Any]:
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
