from typing import Any


def get_hierarchy_search_tool_schema() -> dict[str, Any]:
    return {
        "name": "hierarchy_search",
        "description": "Search Confluence documents with hierarchy-aware filtering and organization",
        "annotations": {"read-only": True},
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
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
