from typing import Any


def get_search_tool_schema() -> dict[str, Any]:
    return {
        "name": "search",
        "description": "Perform semantic search across multiple data sources",
        "annotations": {"read-only": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query in natural language",
                },
                "source_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "git",
                            "confluence",
                            "jira",
                            "documentation",
                            "localfile",
                        ],
                    },
                    "description": "Optional list of source types to filter results",
                },
                "project_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of project IDs to filter results",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5,
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


