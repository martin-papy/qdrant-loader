from typing import Any


def get_attachment_search_tool_schema() -> dict[str, Any]:
    return {
        "name": "attachment_search",
        "description": "Search for file attachments and their parent documents across Confluence, Jira, and other sources",
        "annotations": {"read-only": True},
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query in natural language",
                },
                "attachment_filter": {
                    "type": "object",
                    "additionalProperties": False,
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
                            "minimum": 0,
                        },
                        "file_size_max": {
                            "type": "integer",
                            "description": "Maximum file size in bytes",
                            "minimum": 0,
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
                        "file_types": {"type": "array", "items": {"type": "string"}},
                        "attachments_only": {"type": "boolean"},
                    },
                },
            },
        },
    }
