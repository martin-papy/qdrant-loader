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
                    "minLength": 1,
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
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "project_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of project IDs to filter results",
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5,
                    "minimum": 1,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "results": {
                    "type": "array",
                    "minItems": 0,
                    "items": {
                        "type": "object",
                        # Allow extra fields for richer result payloads (e.g., document_id, content_snippet, source_url)
                        "additionalProperties": True,
                        "properties": {
                            "score": {"type": "number"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "source_type": {
                                "type": "string",
                                "enum": [
                                    "git",
                                    "confluence",
                                    "jira",
                                    "documentation",
                                    "localfile",
                                ],
                            },
                            "metadata": {
                                "type": "object",
                                # Allow flexible metadata keys; formatter may include breadcrumb, hierarchy, etc.
                                "additionalProperties": True,
                                "properties": {
                                    "file_path": {"type": "string"},
                                    "project_id": {"type": "string"},
                                    "created_at": {
                                        "type": "string",
                                        "format": "date-time",
                                    },
                                    "last_modified": {
                                        "type": "string",
                                        "format": "date-time",
                                    },
                                },
                            },
                        },
                        "required": [
                            "score",
                            "title",
                            "content",
                            "source_type",
                            "metadata",
                        ],
                    },
                },
                "total_found": {"type": "integer", "minimum": 0},
                "query_context": {
                    "type": "object",
                    "additionalProperties": False,
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
            "required": ["results", "total_found"],
        },
    }
