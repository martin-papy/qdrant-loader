from typing import Any


def get_expand_chunk_context_tool_schema() -> dict[str, Any]:
    """Get expand chunk context tool schema"""
    return {
        "name": "expand_chunk_context",
        "description": "Retrieve neighboring chunks within the same document based on a given chunk_index. This helps expand context around a specific chunk.",
        "annotations": {"read-only": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Unique identifier of the document.",
                },
                "chunk_index": {
                    "type": "integer",
                    "description": "Index of the target chunk within the document.",
                    "minimum": 0,
                },
                "window_size": {
                    "type": "integer",
                    "description": "Number of chunks to include before and after the target chunk.",
                    "default": 2,
                    "minimum": 0,
                },
            },
            "required": ["document_id", "chunk_index"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "structured_results": {
                    "type": "object",
                    "properties": {
                        "context_chunks": {
                            "type": "object",
                            "properties": {
                                "pre": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "Chunks before the target chunk.",
                                },
                                "target": {
                                    "type": ["object", "null"],
                                    "description": "The target chunk.",
                                },
                                "post": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "Chunks after the target chunk.",
                                },
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "chunk_index": {"type": "integer"},
                                "window_size": {"type": "integer"},
                                "context_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {"type": "integer"},
                                        "end": {"type": "integer"},
                                    },
                                },
                                "total_chunks": {"type": "integer"},
                            },
                        },
                    },
                }
            },
        },
    }
