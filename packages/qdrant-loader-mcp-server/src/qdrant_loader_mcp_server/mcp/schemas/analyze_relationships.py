from typing import Any


def get_analyze_relationships_tool_schema() -> dict[str, Any]:
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
                    "minLength": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to analyze",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 1000,
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
                    "default": False,
                },
                "max_llm_pairs": {
                    "type": "integer",
                    "description": "Maximum number of pairs to analyze with LLM",
                    "default": 5,
                    "minimum": 0,
                    "maximum": 100,
                },
                "overall_timeout_s": {
                    "type": "number",
                    "description": "Overall analysis budget in seconds",
                    "default": 60,
                    "minimum": 0,
                    "maximum": 3600,
                },
                "max_pairs_total": {
                    "type": "integer",
                    "description": "Maximum candidate pairs to analyze after tiering",
                    "default": 1000,
                    "minimum": 0,
                    "maximum": 100000,
                },
                "text_window_chars": {
                    "type": "integer",
                    "description": "Per-document text window size for lexical analysis",
                    "default": 1000,
                    "minimum": 0,
                    "maximum": 10000,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
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
                            "score": {"type": "number", "minimum": 0, "maximum": 1},
                            "description": {"type": "string"},
                        },
                        "required": [
                            "document_1",
                            "document_2",
                            "relationship_type",
                            "score",
                        ],
                        "additionalProperties": False,
                    },
                },
                "total_analyzed": {"type": "integer"},
                "summary": {"type": "string"},
            },
            "required": ["relationships", "total_analyzed"],
            "additionalProperties": False,
        },
    }
