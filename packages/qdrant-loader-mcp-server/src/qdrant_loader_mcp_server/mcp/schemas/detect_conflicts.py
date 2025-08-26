from typing import Any


def get_detect_conflicts_tool_schema() -> dict[str, Any]:
    return {
        "name": "detect_conflicts",
        "description": "Detect conflicts and contradictions between documents",
        "annotations": {"read-only": True, "compute-intensive": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to get documents for conflict analysis",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to analyze",
                    "default": 10,
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
            "required": ["query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "conflicts_detected": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "conflict_id": {"type": "string"},
                            "document_1": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content_preview": {"type": "string"},
                                    "source_type": {"type": "string"},
                                },
                            },
                            "document_2": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content_preview": {"type": "string"},
                                    "source_type": {"type": "string"},
                                },
                            },
                            "conflict_type": {"type": "string"},
                            "conflict_score": {"type": "number"},
                            "conflict_description": {"type": "string"},
                            "conflicting_statements": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from_doc1": {"type": "string"},
                                        "from_doc2": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
                "conflict_summary": {
                    "type": "object",
                    "properties": {
                        "total_documents_analyzed": {"type": "integer"},
                        "conflicts_found": {"type": "integer"},
                        "conflict_types": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "highest_conflict_score": {"type": "number"},
                    },
                },
                "analysis_metadata": {
                    "type": "object",
                    "properties": {
                        "query_used": {"type": "string"},
                        "analysis_date": {"type": "string"},
                        "processing_time_ms": {"type": "number"},
                    },
                },
            },
        },
    }
