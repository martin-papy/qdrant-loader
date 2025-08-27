from typing import Any


def get_expand_document_tool_schema() -> dict[str, Any]:
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
                    "description": "Include detailed metadata (optional, default: true)",
                    "default": True,
                },
                "include_hierarchy": {
                    "type": "boolean",
                    "description": "Include hierarchy information for Confluence documents (optional, default: true)",
                    "default": True,
                },
                "include_attachments": {
                    "type": "boolean",
                    "description": "Include attachment information if available (optional, default: true)",
                    "default": True,
                },
            },
            "required": ["document_id"],
            "additionalProperties": False,
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
