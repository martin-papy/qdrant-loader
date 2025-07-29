"""MCP Handler implementation."""

from typing import Any

from ..search.engine import SearchEngine
from ..search.models import SearchResult
from ..search.processor import QueryProcessor
from ..utils import LoggingConfig
from .protocol import MCPProtocol

# Get logger for this module
logger = LoggingConfig.get_logger("src.mcp.handler")


class MCPHandler:
    """MCP Handler for processing RAG requests."""

    def __init__(self, search_engine: SearchEngine, query_processor: QueryProcessor):
        """Initialize MCP Handler."""
        self.protocol = MCPProtocol()
        self.search_engine = search_engine
        self.query_processor = query_processor
        logger.info("MCP Handler initialized")

    async def handle_request(self, request: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Handle MCP request.

        Args:
            request: The request to handle
            headers: Optional HTTP headers for protocol validation

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling request", request=request)
        
        # Optional protocol version validation from headers
        if headers:
            protocol_version = headers.get("mcp-protocol-version")
            if protocol_version and protocol_version not in ["2025-06-18", "2025-03-26", "2024-11-05"]:
                logger.warning(f"Unsupported protocol version in headers: {protocol_version}")

        # Validate request format
        if not self.protocol.validate_request(request):
            logger.error("Request validation failed")
            # For invalid requests, we need to determine if we can extract an ID
            request_id = None
            if isinstance(request, dict):
                request_id = request.get("id")
                if request_id is not None and not isinstance(request_id, (str, int)):
                    request_id = None
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "The request is not a valid JSON-RPC 2.0 request",
                },
            }

        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.debug(
            "Processing request", method=method, params=params, request_id=request_id
        )

        # Handle notifications (requests without id)
        if request_id is None:
            logger.debug("Handling notification", method=method)
            return {}

        try:
            if method == "initialize":
                logger.info("Handling initialize request")
                response = await self._handle_initialize(request_id, params)
                self.protocol.mark_initialized()
                logger.info("Server initialized successfully")
                return response
            elif method in ["listOfferings", "tools/list"]:
                logger.info(f"Handling {method} request")
                logger.debug(
                    f"{method} request details",
                    method=method,
                    params=params,
                    request_id=request_id,
                )
                if not isinstance(method, str):
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32600,
                            "message": "Invalid Request",
                            "data": "Method must be a string",
                        },
                    )
                response = await self._handle_list_offerings(request_id, params, method)
                logger.debug(f"{method} response", response=response)
                return response
            elif method == "search":
                logger.info("Handling search request")
                return await self._handle_search(request_id, params)
            # Cross-Document Intelligence Methods
            elif method == "analyze_document_relationships":
                logger.info("Handling document relationship analysis request")
                return await self._handle_analyze_document_relationships(request_id, params)
            elif method == "find_similar_documents":
                logger.info("Handling find similar documents request")
                return await self._handle_find_similar_documents(request_id, params)
            elif method == "detect_document_conflicts":
                logger.info("Handling conflict detection request")
                return await self._handle_detect_document_conflicts(request_id, params)
            elif method == "find_complementary_content":
                logger.info("Handling complementary content request")
                return await self._handle_find_complementary_content(request_id, params)
            elif method == "cluster_documents":
                logger.info("Handling document clustering request")
                return await self._handle_cluster_documents(request_id, params)
            elif method == "tools/call":
                logger.info("Handling tools/call request")
                tool_name = params.get("name")
                if tool_name == "search":
                    return await self._handle_search(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "hierarchy_search":
                    return await self._handle_hierarchy_search(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "attachment_search":
                    return await self._handle_attachment_search(
                        request_id, params.get("arguments", {})
                    )
                # Cross-Document Intelligence Tools
                elif tool_name == "analyze_document_relationships":
                    return await self._handle_analyze_document_relationships(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "find_similar_documents":
                    return await self._handle_find_similar_documents(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "detect_document_conflicts":
                    return await self._handle_detect_document_conflicts(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "find_complementary_content":
                    return await self._handle_find_complementary_content(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "cluster_documents":
                    return await self._handle_cluster_documents(
                        request_id, params.get("arguments", {})
                    )
                else:
                    logger.warning("Unknown tool requested", tool_name=tool_name)
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32601,
                            "message": "Method not found",
                            "data": f"Tool '{tool_name}' not found",
                        },
                    )
            else:
                logger.warning("Unknown method requested", method=method)
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32601,
                        "message": "Method not found",
                        "data": f"Method '{method}' not found",
                    },
                )
        except Exception as e:
            logger.error("Error handling request", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_initialize(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle initialize request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Initializing with params", params=params)
        return self.protocol.create_response(
            request_id,
            result={
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "Qdrant Loader MCP Server", "version": "1.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        )

    async def _handle_list_offerings(
        self, request_id: str | int | None, params: dict[str, Any], method: str
    ) -> dict[str, Any]:
        """Handle list offerings request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request
            method: The method name from the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Listing offerings with params", params=params)

        # Define the search tool according to MCP specification
        search_tool = {
            "name": "search",
            "description": "Perform semantic search across multiple data sources",
            "annotations": ["read-only"],
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
                        "items": {
                            "type": "string",
                        },
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
                                        "last_modified": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "total_found": {"type": "integer"},
                    "query_context": {
                        "type": "object",
                        "properties": {
                            "original_query": {"type": "string"},
                            "source_types_filtered": {"type": "array", "items": {"type": "string"}},
                            "project_ids_filtered": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        }

        # Define the hierarchical search tool for Confluence
        hierarchy_search_tool = {
            "name": "hierarchy_search",
            "description": "Search Confluence documents with hierarchy-aware filtering and organization",
            "annotations": ["read-only"],
            "inputSchema": {
                "type": "object",
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
                                        "hierarchy_level": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    },
                    "total_found": {"type": "integer"},
                    "hierarchy_organization": {
                        "type": "object",
                        "properties": {
                            "organized_by_hierarchy": {"type": "boolean"},
                            "hierarchy_groups": {"type": "array", "items": {"type": "object"}}
                        }
                    }
                }
            }
        }

        # Define the attachment search tool
        attachment_search_tool = {
            "name": "attachment_search",
            "description": "Search for file attachments and their parent documents across Confluence, Jira, and other sources",
            "annotations": ["read-only"],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language",
                    },
                    "attachment_filter": {
                        "type": "object",
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
                            },
                            "file_size_max": {
                                "type": "integer",
                                "description": "Maximum file size in bytes",
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
                                        "parent_document": {"type": "string"}
                                    }
                                },
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {"type": "string"},
                                        "project_id": {"type": "string"},
                                        "upload_date": {"type": "string"},
                                        "author": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "total_found": {"type": "integer"},
                    "attachment_summary": {
                        "type": "object",
                        "properties": {
                            "total_attachments": {"type": "integer"},
                            "file_types": {"type": "array", "items": {"type": "string"}},
                            "attachments_only": {"type": "boolean"}
                        }
                    }
                }
            }
        }

        # Cross-Document Intelligence Tools
        analyze_relationships_tool = {
            "name": "analyze_document_relationships",
            "description": "Analyze relationships between documents including clustering, similarities, and conflicts",
            "annotations": ["read-only", "compute-intensive"],
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
                },
                "required": ["query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "analysis_results": {
                        "type": "object",
                        "properties": {
                            "similarity_clusters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "cluster_id": {"type": "string"},
                                        "documents": {"type": "array", "items": {"type": "string"}},
                                        "similarity_score": {"type": "number"},
                                        "cluster_theme": {"type": "string"}
                                    }
                                }
                            },
                            "conflicts_detected": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "document_1": {"type": "string"},
                                        "document_2": {"type": "string"},
                                        "conflict_type": {"type": "string"},
                                        "conflict_score": {"type": "number"},
                                        "description": {"type": "string"}
                                    }
                                }
                            },
                            "complementary_pairs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "document_1": {"type": "string"},
                                        "document_2": {"type": "string"},
                                        "complementary_score": {"type": "number"},
                                        "relationship_type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "total_documents_analyzed": {"type": "integer"},
                    "analysis_metadata": {
                        "type": "object",
                        "properties": {
                            "processing_time_ms": {"type": "number"},
                            "analysis_date": {"type": "string"},
                            "query_used": {"type": "string"}
                        }
                    }
                }
            }
        }

        find_similar_tool = {
            "name": "find_similar_documents",
            "description": "Find documents similar to a target document using multiple similarity metrics",
            "annotations": ["read-only"],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_query": {
                        "type": "string",
                        "description": "Query to find the target document",
                    },
                    "comparison_query": {
                        "type": "string",
                        "description": "Query to get documents to compare against",
                    },
                    "similarity_metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["entity_overlap", "topic_overlap", "semantic_similarity", "metadata_similarity", "hierarchical_distance", "content_features"]
                        },
                        "description": "Similarity metrics to use",
                    },
                    "max_similar": {
                        "type": "integer",
                        "description": "Maximum number of similar documents to return",
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
                "required": ["target_query", "comparison_query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "similar_documents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "title": {"type": "string"},
                                "similarity_score": {"type": "number"},
                                "similarity_metrics": {
                                    "type": "object",
                                    "properties": {
                                        "entity_overlap": {"type": "number"},
                                        "topic_overlap": {"type": "number"},
                                        "semantic_similarity": {"type": "number"},
                                        "metadata_similarity": {"type": "number"}
                                    }
                                },
                                "similarity_reason": {"type": "string"},
                                "content_preview": {"type": "string"}
                            }
                        }
                    },
                    "target_document": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content_preview": {"type": "string"},
                            "source_type": {"type": "string"}
                        }
                    },
                    "similarity_summary": {
                        "type": "object",
                        "properties": {
                            "total_compared": {"type": "integer"},
                            "similar_found": {"type": "integer"},
                            "highest_similarity": {"type": "number"},
                            "metrics_used": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        }

        detect_conflicts_tool = {
            "name": "detect_document_conflicts",
            "description": "Detect conflicts and contradictions between documents",
            "annotations": ["read-only", "compute-intensive"],
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
                        "default": 15,
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
                                        "source_type": {"type": "string"}
                                    }
                                },
                                "document_2": {
                                    "type": "object", 
                                    "properties": {
                                        "title": {"type": "string"},
                                        "content_preview": {"type": "string"},
                                        "source_type": {"type": "string"}
                                    }
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
                                            "from_doc2": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "conflict_summary": {
                        "type": "object",
                        "properties": {
                            "total_documents_analyzed": {"type": "integer"},
                            "conflicts_found": {"type": "integer"},
                            "conflict_types": {"type": "array", "items": {"type": "string"}},
                            "highest_conflict_score": {"type": "number"}
                        }
                    },
                    "analysis_metadata": {
                        "type": "object",
                        "properties": {
                            "query_used": {"type": "string"},
                            "analysis_date": {"type": "string"},
                            "processing_time_ms": {"type": "number"}
                        }
                    }
                }
            }
        }

        find_complementary_tool = {
            "name": "find_complementary_content",
            "description": "Find content that complements a target document",
            "annotations": ["read-only"],
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
                                        "author": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "target_document": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content_preview": {"type": "string"},
                            "source_type": {"type": "string"}
                        }
                    },
                    "complementary_summary": {
                        "type": "object",
                        "properties": {
                            "total_analyzed": {"type": "integer"},
                            "complementary_found": {"type": "integer"},
                            "highest_score": {"type": "number"},
                            "relationship_types": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        }

        cluster_documents_tool = {
            "name": "cluster_documents",
            "description": "Cluster documents based on similarity and relationships",
            "annotations": ["read-only", "compute-intensive"],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to get documents for clustering",
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["mixed_features", "entity_based", "topic_based", "project_based"],
                        "description": "Clustering strategy to use",
                        "default": "mixed_features",
                    },
                    "max_clusters": {
                        "type": "integer",
                        "description": "Maximum number of clusters to create",
                        "default": 10,
                    },
                    "min_cluster_size": {
                        "type": "integer",
                        "description": "Minimum size for a cluster",
                        "default": 2,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to cluster",
                        "default": 25,
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
                    "clusters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cluster_id": {"type": "string"},
                                "cluster_name": {"type": "string"},
                                "cluster_theme": {"type": "string"},
                                "document_count": {"type": "integer"},
                                "cohesion_score": {"type": "number"},
                                "documents": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "document_id": {"type": "string"},
                                            "title": {"type": "string"},
                                            "content_preview": {"type": "string"},
                                            "source_type": {"type": "string"},
                                            "cluster_relevance": {"type": "number"}
                                        }
                                    }
                                },
                                "cluster_keywords": {"type": "array", "items": {"type": "string"}},
                                "cluster_summary": {"type": "string"}
                            }
                        }
                    },
                    "clustering_metadata": {
                        "type": "object",
                        "properties": {
                            "total_documents": {"type": "integer"},
                            "clusters_created": {"type": "integer"},
                            "strategy_used": {"type": "string"},
                            "unclustered_documents": {"type": "integer"},
                            "clustering_quality": {"type": "number"},
                            "processing_time_ms": {"type": "number"}
                        }
                    },
                    "cluster_relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cluster_1": {"type": "string"},
                                "cluster_2": {"type": "string"},
                                "relationship_type": {"type": "string"},
                                "relationship_strength": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }

        # If the method is tools/list, return the tools array with nextCursor
        if method == "tools/list":
            return self.protocol.create_response(
                request_id,
                result={
                    "tools": [
                        search_tool,
                        hierarchy_search_tool,
                        attachment_search_tool,
                        # Cross-Document Intelligence Tools
                        analyze_relationships_tool,
                        find_similar_tool,
                        detect_conflicts_tool,
                        find_complementary_tool,
                        cluster_documents_tool,
                    ]
                    # Omit nextCursor when there are no more results
                },
            )

        # Otherwise return the full offerings structure
        return self.protocol.create_response(
            request_id,
            result={
                "offerings": [
                    {
                        "id": "qdrant-loader",
                        "name": "Qdrant Loader",
                        "description": "Load data into Qdrant vector database",
                        "version": "1.0.0",
                        "tools": [
                            search_tool,
                            hierarchy_search_tool,
                            attachment_search_tool,
                            # Cross-Document Intelligence Tools
                            analyze_relationships_tool,
                            find_similar_tool,
                            detect_conflicts_tool,
                            find_complementary_tool,
                            cluster_documents_tool,
                        ],
                        "resources": [],
                        "resourceTemplates": [],
                    }
                ]
            },
        )

    async def _handle_search(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle search request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling search request with params", params=params)

        # Validate required parameters
        if "query" not in params:
            logger.error("Missing required parameter: query")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: query",
                },
            )

        # Extract parameters with defaults
        query = params["query"]
        source_types = params.get("source_types", [])
        project_ids = params.get("project_ids", [])
        limit = params.get("limit", 10)

        logger.info(
            "Processing search request",
            query=query,
            source_types=source_types,
            project_ids=project_ids,
            limit=limit,
        )

        try:
            # Process the query
            logger.debug("Processing query with OpenAI")
            processed_query = await self.query_processor.process_query(query)
            logger.debug(
                "Query processed successfully", processed_query=processed_query
            )

            # Perform the search
            logger.debug("Executing search in Qdrant")
            results = await self.search_engine.search(
                query=processed_query["query"],
                source_types=source_types,
                project_ids=project_ids,
                limit=limit,
            )
            logger.info(
                "Search completed successfully",
                result_count=len(results),
                first_result_score=results[0].score if results else None,
            )

            # Create structured results for MCP 2025-06-18 compliance
            structured_results = [
                {
                    "score": result.score,
                    "title": result.source_title or "Untitled",
                    "content": result.text,
                    "source_type": result.source_type,
                    "metadata": {
                        "file_path": getattr(result, 'file_path', ''),
                        "project_id": getattr(result, 'project_id', ''),
                        "created_at": getattr(result, 'created_at', ''),
                        "last_modified": getattr(result, 'last_modified', '')
                    }
                }
                for result in results
            ]
            
            # Keep existing text response for backward compatibility
            text_response = f"Found {len(results)} results:\n\n" + "\n\n".join(
                self._format_search_result(result) for result in results
            )
            
            # Format the response with both text and structured content
            response = self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": text_response,
                        }
                    ],
                    "structuredContent": {
                        "results": structured_results,
                        "total_found": len(results),
                        "query_context": {
                            "original_query": query,
                            "source_types_filtered": source_types,
                            "project_ids_filtered": project_ids
                        }
                    },
                    "isError": False,
                },
            )
            logger.debug("Search response formatted successfully")
            return response

        except Exception as e:
            logger.error("Error during search", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    def _format_search_result(self, result: SearchResult) -> str:
        """Format a search result for display."""
        formatted_result = f"Score: {result.score}\n"
        formatted_result += f"Text: {result.text}\n"
        formatted_result += f"Source: {result.source_type}"

        if result.source_title:
            formatted_result += f" - {result.source_title}"

        # Add project information if available
        project_info = result.get_project_info()
        if project_info:
            formatted_result += f"\n🏗️ {project_info}"

        # Add attachment information if this is a file attachment
        if result.is_attachment:
            formatted_result += "\n📎 Attachment"
            if result.original_filename:
                formatted_result += f": {result.original_filename}"
            if result.attachment_context:
                formatted_result += f"\n📋 {result.attachment_context}"
            if result.parent_document_title:
                formatted_result += f"\n📄 Attached to: {result.parent_document_title}"

        # Add hierarchy context for Confluence documents
        if result.source_type == "confluence" and result.breadcrumb_text:
            formatted_result += f"\n📍 Path: {result.breadcrumb_text}"

        if result.source_url:
            formatted_result += f" ({result.source_url})"

        if result.file_path:
            formatted_result += f"\nFile: {result.file_path}"

        if result.repo_name:
            formatted_result += f"\nRepo: {result.repo_name}"

        # Add hierarchy information for Confluence documents
        if result.source_type == "confluence" and result.hierarchy_context:
            formatted_result += f"\n🏗️ {result.hierarchy_context}"

        # Add parent information if available (for hierarchy, not attachments)
        if result.parent_title and not result.is_attachment:
            formatted_result += f"\n⬆️ Parent: {result.parent_title}"

        # Add children count if available
        if result.has_children():
            formatted_result += f"\n⬇️ Children: {result.children_count}"

        return formatted_result

    async def _handle_hierarchy_search(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle hierarchical search request for Confluence documents.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling hierarchy search request with params", params=params)

        # Validate required parameters
        if "query" not in params:
            logger.error("Missing required parameter: query")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: query",
                },
            )

        # Extract parameters with defaults
        query = params["query"]
        hierarchy_filter = params.get("hierarchy_filter", {})
        organize_by_hierarchy = params.get("organize_by_hierarchy", False)
        limit = params.get("limit", 10)

        logger.info(
            "Processing hierarchy search request",
            query=query,
            hierarchy_filter=hierarchy_filter,
            organize_by_hierarchy=organize_by_hierarchy,
            limit=limit,
        )

        try:
            # Process the query
            logger.debug("Processing query with OpenAI")
            processed_query = await self.query_processor.process_query(query)
            logger.debug(
                "Query processed successfully", processed_query=processed_query
            )

            # Perform the search (Confluence only for hierarchy)
            logger.debug("Executing hierarchy search in Qdrant")
            results = await self.search_engine.search(
                query=processed_query["query"],
                source_types=["confluence"],  # Only search Confluence for hierarchy
                limit=limit * 2,  # Get more results to filter
            )

            # Apply hierarchy filters
            filtered_results = self._apply_hierarchy_filters(results, hierarchy_filter)

            # Limit results after filtering
            filtered_results = filtered_results[:limit]

            # Organize results if requested
            if organize_by_hierarchy:
                organized_results = self._organize_by_hierarchy(filtered_results)
                response_text = self._format_hierarchical_results(organized_results)
            else:
                response_text = (
                    f"Found {len(filtered_results)} results:\n\n"
                    + "\n\n".join(
                        self._format_search_result(result)
                        for result in filtered_results
                    )
                )

            logger.info(
                "Hierarchy search completed successfully",
                result_count=len(filtered_results),
                first_result_score=(
                    filtered_results[0].score if filtered_results else None
                ),
            )

            # Format the response
            response = self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": response_text,
                        }
                    ],
                    "isError": False,
                },
            )
            logger.debug("Hierarchy search response formatted successfully")
            return response

        except Exception as e:
            logger.error("Error during hierarchy search", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    def _apply_hierarchy_filters(
        self, results: list[SearchResult], hierarchy_filter: dict[str, Any]
    ) -> list[SearchResult]:
        """Apply hierarchy-based filters to search results."""
        filtered_results = []

        for result in results:
            # Skip non-Confluence results
            if result.source_type != "confluence":
                continue

            # Apply depth filter
            if "depth" in hierarchy_filter:
                if result.depth != hierarchy_filter["depth"]:
                    continue

            # Apply parent title filter
            if "parent_title" in hierarchy_filter:
                if result.parent_title != hierarchy_filter["parent_title"]:
                    continue

            # Apply root only filter
            if hierarchy_filter.get("root_only", False):
                if not result.is_root_document():
                    continue

            # Apply has children filter
            if "has_children" in hierarchy_filter:
                if result.has_children() != hierarchy_filter["has_children"]:
                    continue

            filtered_results.append(result)

        return filtered_results

    def _organize_by_hierarchy(
        self, results: list[SearchResult]
    ) -> dict[str, list[SearchResult]]:
        """Organize search results by hierarchy structure."""
        hierarchy_groups = {}

        for result in results:
            # Group by root ancestor or use the document title if it's a root
            if result.breadcrumb_text:
                # Extract the root from breadcrumb
                breadcrumb_parts = result.breadcrumb_text.split(" > ")
                root_title = (
                    breadcrumb_parts[0] if breadcrumb_parts else result.source_title
                )
            else:
                root_title = result.source_title

            if root_title not in hierarchy_groups:
                hierarchy_groups[root_title] = []
            hierarchy_groups[root_title].append(result)

        # Sort within each group by depth and title
        for group in hierarchy_groups.values():
            group.sort(key=lambda x: (x.depth or 0, x.source_title))

        return hierarchy_groups

    def _format_hierarchical_results(
        self, organized_results: dict[str, list[SearchResult]]
    ) -> str:
        """Format hierarchically organized results for display."""
        formatted_sections = []

        for root_title, results in organized_results.items():
            section = f"📁 **{root_title}** ({len(results)} results)\n"

            for result in results:
                indent = "  " * (result.depth or 0)
                section += f"{indent}📄 {result.source_title}"
                if result.hierarchy_context:
                    section += f" | {result.hierarchy_context}"
                section += f" (Score: {result.score:.3f})\n"

                # Add a snippet of the content
                content_snippet = (
                    result.text[:150] + "..." if len(result.text) > 150 else result.text
                )
                section += f"{indent}   {content_snippet}\n"

                if result.source_url:
                    section += f"{indent}   🔗 {result.source_url}\n"
                section += "\n"

            formatted_sections.append(section)

        return (
            f"Found {sum(len(results) for results in organized_results.values())} results organized by hierarchy:\n\n"
            + "\n".join(formatted_sections)
        )

    async def _handle_attachment_search(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle attachment search request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling attachment search request with params", params=params)

        # Validate required parameters
        if "query" not in params:
            logger.error("Missing required parameter: query")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: query",
                },
            )

        # Extract parameters with defaults
        query = params["query"]
        attachment_filter = params.get("attachment_filter", {})
        include_parent_context = params.get("include_parent_context", True)
        limit = params.get("limit", 10)

        logger.info(
            "Processing attachment search request",
            query=query,
            attachment_filter=attachment_filter,
            include_parent_context=include_parent_context,
            limit=limit,
        )

        try:
            # Process the query
            logger.debug("Processing query with OpenAI")
            processed_query = await self.query_processor.process_query(query)
            logger.debug(
                "Query processed successfully", processed_query=processed_query
            )

            # Perform the search
            logger.debug("Executing attachment search in Qdrant")
            results = await self.search_engine.search(
                query=processed_query["query"],
                source_types=None,  # Search all sources for attachments
                limit=limit * 2,  # Get more results to filter
            )

            # Apply attachment filters
            filtered_results = self._apply_attachment_filters(
                results, attachment_filter
            )

            # Limit results after filtering
            filtered_results = filtered_results[:limit]

            logger.info(
                "Attachment search completed successfully",
                result_count=len(filtered_results),
                first_result_score=(
                    filtered_results[0].score if filtered_results else None
                ),
            )

            # Format the response
            response_text = f"Found {len(filtered_results)} results:\n\n" + "\n\n".join(
                self._format_attachment_search_result(result)
                for result in filtered_results
            )

            response = self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": response_text,
                        }
                    ],
                    "isError": False,
                },
            )
            logger.debug("Attachment search response formatted successfully")
            return response

        except Exception as e:
            logger.error("Error during attachment search", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    def _apply_attachment_filters(
        self, results: list[SearchResult], attachment_filter: dict[str, Any]
    ) -> list[SearchResult]:
        """Apply attachment-based filters to search results."""
        filtered_results = []

        for result in results:
            # Skip non-Confluence results
            if result.source_type != "confluence":
                continue

            # Apply attachments only filter
            if "attachments_only" in attachment_filter and not result.is_attachment:
                continue

            # Apply parent document title filter
            if "parent_document_title" in attachment_filter:
                if (
                    result.parent_document_title
                    != attachment_filter["parent_document_title"]
                ):
                    continue

            # Apply file type filter
            if "file_type" in attachment_filter:
                result_file_type = result.get_file_type()
                if result_file_type != attachment_filter["file_type"]:
                    continue

            # Apply file size filter
            if (
                "file_size_min" in attachment_filter
                and result.file_size
                and result.file_size < attachment_filter["file_size_min"]
            ):
                continue
            if (
                "file_size_max" in attachment_filter
                and result.file_size
                and result.file_size > attachment_filter["file_size_max"]
            ):
                continue

            # Apply author filter
            if "author" in attachment_filter:
                if result.attachment_author != attachment_filter["author"]:
                    continue

            filtered_results.append(result)

        return filtered_results

    def _format_attachment_search_result(self, result: SearchResult) -> str:
        """Format an attachment search result for display."""
        formatted_result = f"Score: {result.score}\n"
        formatted_result += f"Text: {result.text}\n"
        formatted_result += f"Source: {result.source_type}"

        if result.source_title:
            formatted_result += f" - {result.source_title}"

        # Add attachment information
        formatted_result += "\n📎 Attachment"
        if result.original_filename:
            formatted_result += f": {result.original_filename}"
        if result.attachment_context:
            formatted_result += f"\n📋 {result.attachment_context}"
        if result.parent_document_title:
            formatted_result += f"\n📄 Attached to: {result.parent_document_title}"

        # Add hierarchy context for Confluence documents
        if result.source_type == "confluence" and result.breadcrumb_text:
            formatted_result += f"\n📍 Path: {result.breadcrumb_text}"

        if result.source_url:
            formatted_result += f" ({result.source_url})"

        if result.file_path:
            formatted_result += f"\nFile: {result.file_path}"

        if result.repo_name:
            formatted_result += f"\nRepo: {result.repo_name}"

        # Add hierarchy information for Confluence documents
        if result.source_type == "confluence" and result.hierarchy_context:
            formatted_result += f"\n🏗️ {result.hierarchy_context}"

        # Add parent information if available (for hierarchy, not attachments)
        if result.parent_title and not result.is_attachment:
            formatted_result += f"\n⬆️ Parent: {result.parent_title}"

        # Add children count if available
        if result.has_children():
            formatted_result += f"\n⬇️ Children: {result.children_count}"

        return formatted_result

    # Cross-Document Intelligence Handler Methods

    async def _handle_analyze_document_relationships(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle document relationship analysis request."""
        logger.debug("Handling document relationship analysis with params", params=params)

        if "query" not in params:
            logger.error("Missing required parameter: query")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: query",
                },
            )

        try:
            analysis = await self.search_engine.analyze_document_relationships(
                query=params["query"],
                limit=params.get("limit", 20),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self._format_relationship_analysis(analysis),
                        }
                    ],
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error during document relationship analysis", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_find_similar_documents(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle find similar documents request."""
        logger.debug("Handling find similar documents with params", params=params)

        required_params = ["target_query", "comparison_query"]
        for param in required_params:
            if param not in params:
                logger.error(f"Missing required parameter: {param}")
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": f"Missing required parameter: {param}",
                    },
                )

        try:
            similar_docs = await self.search_engine.find_similar_documents(
                target_query=params["target_query"],
                comparison_query=params["comparison_query"],
                similarity_metrics=params.get("similarity_metrics"),
                max_similar=params.get("max_similar", 5),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self._format_similar_documents(similar_docs),
                        }
                    ],
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error finding similar documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_detect_document_conflicts(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle conflict detection request."""
        logger.debug("Handling conflict detection with params", params=params)

        if "query" not in params:
            logger.error("Missing required parameter: query")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: query",
                },
            )

        try:
            conflicts = await self.search_engine.detect_document_conflicts(
                query=params["query"],
                limit=params.get("limit", 15),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self._format_conflict_analysis(conflicts),
                        }
                    ],
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error detecting conflicts", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_find_complementary_content(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle complementary content request."""
        logger.debug("Handling complementary content with params", params=params)

        required_params = ["target_query", "context_query"]
        for param in required_params:
            if param not in params:
                logger.error(f"Missing required parameter: {param}")
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": f"Missing required parameter: {param}",
                    },
                )

        try:
            logger.info(f"🔍 About to call search_engine.find_complementary_content")
            logger.info(f"🔍 search_engine type: {type(self.search_engine)}")
            logger.info(f"🔍 search_engine is None: {self.search_engine is None}")
            
            complementary = await self.search_engine.find_complementary_content(
                target_query=params["target_query"],
                context_query=params["context_query"],
                max_recommendations=params.get("max_recommendations", 5),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )
            
            logger.info(f"✅ search_engine.find_complementary_content completed, got {len(complementary)} results")

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self._format_complementary_content(complementary),
                        }
                    ],
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error finding complementary content", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_cluster_documents(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle document clustering request."""
        logger.debug("Handling document clustering with params", params=params)

        if "query" not in params:
            logger.error("Missing required parameter: query")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: query",
                },
            )

        try:
            clusters = await self.search_engine.cluster_documents(
                query=params["query"],
                strategy=params.get("strategy", "mixed_features"),
                max_clusters=params.get("max_clusters", 10),
                min_cluster_size=params.get("min_cluster_size", 2),
                limit=params.get("limit", 25),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self._format_document_clusters(clusters),
                        }
                    ],
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error clustering documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    # Formatting Methods for Cross-Document Intelligence Results

    def _format_relationship_analysis(self, analysis: dict[str, Any]) -> str:
        """Format document relationship analysis for display."""
        if "error" in analysis:
            return f"❌ Error: {analysis['error']}"

        summary = analysis.get("summary", {})
        formatted = f"""🔍 **Document Relationship Analysis**

📊 **Summary:**
• Total Documents: {summary.get('total_documents', 0)}
• Clusters Found: {summary.get('clusters_found', 0)}
• Citation Relationships: {summary.get('citation_relationships', 0)}
• Conflicts Detected: {summary.get('conflicts_detected', 0)}

🏷️ **Query Information:**
• Original Query: {analysis.get('query_metadata', {}).get('original_query', 'N/A')}
• Documents Analyzed: {analysis.get('query_metadata', {}).get('document_count', 0)}
"""

        clusters = analysis.get("document_clusters", [])
        if clusters:
            formatted += "\n🗂️ **Document Clusters:**\n"
            for i, cluster in enumerate(clusters[:3], 1):  # Show first 3 clusters
                formatted += f"• Cluster {i}: {len(cluster.get('documents', []))} documents\n"

        conflicts = analysis.get("conflict_analysis", {}).get("conflicting_pairs", [])
        if conflicts:
            formatted += f"\n⚠️ **Conflicts Detected:** {len(conflicts)} conflicting document pairs\n"

        return formatted

    def _format_similar_documents(self, similar_docs: list[dict[str, Any]]) -> str:
        """Format similar documents results for display."""
        if not similar_docs:
            return "🔍 **Similar Documents**\n\nNo similar documents found."

        formatted = f"🔍 **Similar Documents** ({len(similar_docs)} found)\n\n"
        
        for i, doc_info in enumerate(similar_docs[:5], 1):  # Show top 5
            score = doc_info.get("similarity_score", 0)
            document = doc_info.get("document", {})
            reasons = doc_info.get("similarity_reasons", [])
            
            formatted += f"**{i}. Similarity Score: {score:.3f}**\n"
            if hasattr(document, 'source_title'):
                formatted += f"• Title: {document.source_title}\n"
            if reasons:
                formatted += f"• Reasons: {', '.join(reasons)}\n"
            formatted += "\n"

        return formatted

    def _format_conflict_analysis(self, conflicts: dict[str, Any]) -> str:
        """Format conflict analysis results for display."""
        conflicting_pairs = conflicts.get("conflicting_pairs", [])
        
        if not conflicting_pairs:
            return "✅ **Conflict Analysis**\n\nNo conflicts detected between documents."

        formatted = f"⚠️ **Conflict Analysis** ({len(conflicting_pairs)} conflicts found)\n\n"
        
        for i, (doc1, doc2, conflict_info) in enumerate(conflicting_pairs[:5], 1):
            conflict_type = conflict_info.get("type", "unknown")
            formatted += f"**{i}. Conflict Type: {conflict_type}**\n"
            formatted += f"• Document 1: {doc1}\n"
            formatted += f"• Document 2: {doc2}\n\n"

        suggestions = conflicts.get("resolution_suggestions", {})
        if suggestions:
            formatted += "💡 **Resolution Suggestions:**\n"
            # Convert dict values to list and take first 3
            suggestion_list = list(suggestions.values())[:3]
            for suggestion in suggestion_list:
                formatted += f"• {suggestion}\n"

        return formatted

    def _format_complementary_content(self, complementary: list[dict[str, Any]]) -> str:
        """Format complementary content results for display."""
        if not complementary:
            return "🔍 **Complementary Content**\n\nNo complementary content found."

        formatted = f"🔗 **Complementary Content** ({len(complementary)} recommendations)\n\n"
        
        for i, item in enumerate(complementary[:5], 1):  # Show top 5
            document = item.get("document", {})
            score = item.get("relevance_score", 0)  # Fixed: use correct key
            reason = item.get("recommendation_reason", "")  # Fixed: singular form
            
            formatted += f"**{i}. Complementary Score: {score:.3f}**\n"
            if hasattr(document, 'source_title'):
                formatted += f"• Title: {document.source_title}\n"
            if reason:
                formatted += f"• Why Complementary: {reason}\n"
            formatted += "\n"

        return formatted

    def _format_document_clusters(self, clusters: dict[str, Any]) -> str:
        """Format document clustering results for display."""
        cluster_list = clusters.get("clusters", [])
        metadata = clusters.get("clustering_metadata", {})
        
        if not cluster_list:
            message = metadata.get("message", "No clusters could be formed.")
            return f"🗂️ **Document Clustering**\n\n{message}"

        formatted = f"""🗂️ **Document Clustering Results**

📊 **Clustering Summary:**
• Strategy: {metadata.get('strategy', 'unknown')}
• Total Clusters: {metadata.get('total_clusters', 0)}
• Total Documents: {metadata.get('total_documents', 0)}
• Original Query: {metadata.get('original_query', 'N/A')}

"""

        for i, cluster in enumerate(cluster_list[:5], 1):  # Show first 5 clusters
            formatted += f"**Cluster {i} (ID: {cluster.get('id', 'unknown')})**\n"
            formatted += f"• Documents: {len(cluster.get('documents', []))}\n"
            formatted += f"• Coherence Score: {cluster.get('coherence_score', 0):.3f}\n"
            
            topics = cluster.get('centroid_topics', [])
            if topics:
                formatted += f"• Key Topics: {', '.join(topics[:3])}\n"
            
            entities = cluster.get('shared_entities', [])
            if entities:
                formatted += f"• Shared Entities: {', '.join(entities[:3])}\n"
            
            summary = cluster.get('cluster_summary', '')
            if summary:
                formatted += f"• Summary: {summary}\n"
            
            formatted += "\n"

        return formatted
