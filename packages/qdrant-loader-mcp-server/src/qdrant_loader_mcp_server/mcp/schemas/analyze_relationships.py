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
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to analyze",
                    "default": 20,
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
                },
                "max_llm_pairs": {
                    "type": "integer",
                    "description": "Maximum number of pairs to analyze with LLM",
                },
                "overall_timeout_s": {
                    "type": "number",
                    "description": "Overall analysis budget in seconds",
                },
                "max_pairs_total": {
                    "type": "integer",
                    "description": "Maximum candidate pairs to analyze after tiering",
                },
                "text_window_chars": {
                    "type": "integer",
                    "description": "Per-document text window size for lexical analysis",
                },
            },
            "required": ["query"],
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
                            "score": {"type": "number"},
                            "description": {"type": "string"},
                        },
                    },
                },
                "total_analyzed": {"type": "integer"},
                "summary": {"type": "string"},
            },
        },
    }


