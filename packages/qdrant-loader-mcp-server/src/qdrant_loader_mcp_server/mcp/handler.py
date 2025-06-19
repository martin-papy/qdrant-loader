"""MCP Handler implementation."""

from typing import Any

from ..graphiti import (
    get_graphiti_capabilities,
    is_graphiti_available,
    perform_graphiti_search,
)
from ..search.engine import SearchEngine
from ..search.exceptions import (
    FusionStrategyError,
    GraphitiError,
    HybridSearchError,
    Neo4jConnectionError,
    Neo4jQueryError,
    OpenAIEmbeddingError,
    QdrantConnectionError,
    QdrantQueryError,
    SearchConfigurationError,
    SearchEngineError,
)
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

    def _validate_fusion_strategy(
        self, fusion_strategy: str, request_id: str | int | None
    ) -> dict[str, Any] | None:
        """Validate fusion strategy parameter.

        Args:
            fusion_strategy: The fusion strategy to validate
            request_id: The request ID for error responses

        Returns:
            Error response dict if invalid, None if valid
        """
        if fusion_strategy is not None:
            from ..search.enhanced_hybrid_search import FusionStrategy

            try:
                FusionStrategy(fusion_strategy)
            except ValueError:
                logger.error("Invalid fusion strategy", fusion_strategy=fusion_strategy)
                valid_strategies = [strategy.value for strategy in FusionStrategy]
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": f"Invalid fusion strategy: {fusion_strategy}. Valid strategies: {', '.join(valid_strategies)}",
                    },
                )
        return None

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP request.

        Args:
            request: The request to handle

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling request", request=request)

        # Handle non-dict requests
        if not isinstance(request, dict):
            logger.error("Request is not a dictionary")
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "The request is not a valid JSON-RPC 2.0 request",
                },
            }

        # Validate request format
        if not self.protocol.validate_request(request):
            logger.error("Request validation failed")
            # For invalid requests, we need to determine if we can extract an ID
            request_id = request.get("id")
            if request_id is None or not isinstance(request_id, str | int):
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
                logger.info("Handling {method} request")
                logger.debug(
                    "{method} request details",
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
                logger.debug("{method} response", response=response)
                return response
            elif method == "search":
                logger.info("Handling search request")
                return await self._handle_search(request_id, params)
            elif method == "tools/call":
                logger.info("Handling tools/call request")
                tool_name = params.get("name")
                if tool_name == "search":
                    return await self._handle_search(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "enhanced_search":
                    return await self._handle_enhanced_search(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "enrich_with_relationships":
                    return await self._handle_enrich_with_relationships(
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
                elif tool_name == "find_relationships":
                    return await self._handle_find_relationships(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "trace_dependencies":
                    return await self._handle_trace_dependencies(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "analyze_impact":
                    return await self._handle_analyze_impact(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "get_temporal_context":
                    return await self._handle_get_temporal_context(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "get_capabilities":
                    return await self._handle_get_capabilities(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "fusion_benchmark":
                    return await self._handle_fusion_benchmark(
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
        except SearchEngineError as e:
            logger.error(
                "Search engine error handling request",
                error_code=e.error_code,
                message=e.message,
                details=e.details,
                recoverable=e.recoverable,
            )
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": f"Search engine error: {e.message}",
                    "data": e.to_dict(),
                },
            )
        except Exception as e:
            logger.error("Unexpected error handling request", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Internal error",
                    "data": {
                        "error_type": type(e).__name__,
                        "message": str(e),
                        "recoverable": True,
                    },
                },
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
                "protocolVersion": "2024-11-05",
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
            "description": "Perform semantic search across multiple data sources with optional hybrid search capabilities",
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
                    "mode": {
                        "type": "string",
                        "enum": ["vector_only", "graph_only", "hybrid", "auto"],
                        "description": "Optional search mode for hybrid capabilities (defaults to legacy behavior)",
                    },
                    "vector_weight": {
                        "type": "number",
                        "description": "Optional weight for vector search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "keyword_weight": {
                        "type": "number",
                        "description": "Optional weight for keyword search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "graph_weight": {
                        "type": "number",
                        "description": "Optional weight for graph search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "fusion_strategy": {
                        "type": "string",
                        "enum": [
                            "weighted_sum",
                            "reciprocal_rank_fusion",
                            "maximal_marginal_relevance",
                            "graph_enhanced_weighted",
                            "confidence_adaptive",
                            "multi_stage",
                            "context_aware",
                        ],
                        "description": "Optional fusion strategy for combining search results",
                    },
                },
                "required": ["query"],
            },
        }

        # Define the hierarchical search tool for Confluence
        hierarchy_search_tool = {
            "name": "hierarchy_search",
            "description": "Search Confluence documents with hierarchy-aware filtering, organization, and optional hybrid search capabilities",
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
                    "mode": {
                        "type": "string",
                        "enum": ["vector_only", "graph_only", "hybrid", "auto"],
                        "description": "Optional search mode for hybrid capabilities",
                    },
                    "vector_weight": {
                        "type": "number",
                        "description": "Optional weight for vector search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "keyword_weight": {
                        "type": "number",
                        "description": "Optional weight for keyword search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "graph_weight": {
                        "type": "number",
                        "description": "Optional weight for graph search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "fusion_strategy": {
                        "type": "string",
                        "enum": [
                            "weighted_sum",
                            "reciprocal_rank_fusion",
                            "maximal_marginal_relevance",
                            "graph_enhanced_weighted",
                            "confidence_adaptive",
                            "multi_stage",
                            "context_aware",
                        ],
                        "description": "Optional fusion strategy for combining search results",
                    },
                },
                "required": ["query"],
            },
        }

        # Define the attachment search tool
        attachment_search_tool = {
            "name": "attachment_search",
            "description": "Search for file attachments and their parent documents across Confluence, Jira, and other sources with optional hybrid search capabilities",
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
                    "mode": {
                        "type": "string",
                        "enum": ["vector_only", "graph_only", "hybrid", "auto"],
                        "description": "Optional search mode for hybrid capabilities",
                    },
                    "vector_weight": {
                        "type": "number",
                        "description": "Optional weight for vector search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "keyword_weight": {
                        "type": "number",
                        "description": "Optional weight for keyword search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "graph_weight": {
                        "type": "number",
                        "description": "Optional weight for graph search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "fusion_strategy": {
                        "type": "string",
                        "enum": [
                            "weighted_sum",
                            "reciprocal_rank_fusion",
                            "maximal_marginal_relevance",
                            "graph_enhanced_weighted",
                            "confidence_adaptive",
                            "multi_stage",
                            "context_aware",
                        ],
                        "description": "Optional fusion strategy for combining search results",
                    },
                },
                "required": ["query"],
            },
        }

        # Define the graph operation tools
        find_relationships_tool = {
            "name": "find_relationships",
            "description": "Discover relationships between entities in the knowledge graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID of the entity to find relationships for",
                    },
                    "relationship_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional filter for specific relationship types (e.g., 'overlaps_with', 'extends', 'preferred_for_task')",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth for relationship traversal (default: 2)",
                        "default": 2,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of relationships to return",
                        "default": 20,
                    },
                },
                "required": ["entity_id"],
            },
        }

        trace_dependencies_tool = {
            "name": "trace_dependencies",
            "description": "Trace dependency chains between entities in the knowledge graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID of the entity to trace dependencies for",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["upstream", "downstream", "both"],
                        "description": "Direction to trace dependencies",
                        "default": "downstream",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth for dependency traversal (default: 3)",
                        "default": 3,
                    },
                    "include_transitive": {
                        "type": "boolean",
                        "description": "Include transitive dependencies",
                        "default": True,
                    },
                },
                "required": ["entity_id"],
            },
        }

        analyze_impact_tool = {
            "name": "analyze_impact",
            "description": "Analyze the downstream impact of changes to an entity",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID of the entity to analyze impact for",
                    },
                    "change_type": {
                        "type": "string",
                        "enum": ["modify", "remove", "update"],
                        "description": "Type of change to analyze impact for",
                        "default": "modify",
                    },
                    "include_indirect": {
                        "type": "boolean",
                        "description": "Include indirect impact analysis",
                        "default": True,
                    },
                    "severity_threshold": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Minimum severity level to include in results",
                        "default": "medium",
                    },
                },
                "required": ["entity_id"],
            },
        }

        get_temporal_context_tool = {
            "name": "get_temporal_context",
            "description": "Retrieve temporal metadata and historical context for entities",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID of the entity to get temporal context for",
                    },
                    "include_history": {
                        "type": "boolean",
                        "description": "Include historical changes and versions",
                        "default": True,
                    },
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "format": "date-time",
                                "description": "Start date for temporal range (ISO format)",
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date-time",
                                "description": "End date for temporal range (ISO format)",
                            },
                        },
                        "description": "Optional time range filter",
                    },
                },
                "required": ["entity_id"],
            },
        }

        # Define the enhanced hybrid search tool
        enhanced_search_tool = {
            "name": "enhanced_search",
            "description": "Perform enhanced hybrid search with configurable parameters and advanced fusion strategies",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "mode": {
                        "type": "string",
                        "enum": ["vector_only", "graph_only", "hybrid", "auto"],
                        "description": "Search mode to use",
                        "default": "auto",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10,
                    },
                    "vector_weight": {
                        "type": "number",
                        "description": "Weight for vector search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "keyword_weight": {
                        "type": "number",
                        "description": "Weight for keyword search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "graph_weight": {
                        "type": "number",
                        "description": "Weight for graph search results (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "project_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of project IDs to filter results",
                    },
                },
                "required": ["query"],
            },
        }

        # Define the fusion benchmark tool
        fusion_benchmark_tool = {
            "name": "fusion_benchmark",
            "description": "Benchmark and compare different fusion strategies for hybrid search results",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text for benchmarking",
                    },
                    "strategies": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "weighted_sum",
                                "reciprocal_rank_fusion",
                                "maximal_marginal_relevance",
                                "graph_enhanced_weighted",
                                "confidence_adaptive",
                                "multi_stage",
                                "context_aware",
                            ],
                        },
                        "description": "List of fusion strategies to benchmark",
                        "default": [
                            "weighted_sum",
                            "graph_enhanced_weighted",
                            "confidence_adaptive",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results per strategy",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                    "include_debug": {
                        "type": "boolean",
                        "description": "Include detailed debug information in results",
                        "default": False,
                    },
                    "project_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of project IDs to filter results",
                    },
                },
                "required": ["query"],
            },
        }

        # Define the relationship enrichment tool
        relationship_enrichment_tool = {
            "name": "enrich_with_relationships",
            "description": "Enrich QDrant vector search candidates with Neo4j relationship context and graph-based scoring",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entity IDs to enrich with relationship context",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum graph traversal depth for relationship discovery",
                        "default": 2,
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "include_centrality": {
                        "type": "boolean",
                        "description": "Include centrality scoring in the results",
                        "default": True,
                    },
                    "include_temporal": {
                        "type": "boolean",
                        "description": "Include temporal relevance scoring",
                        "default": True,
                    },
                    "relationship_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional filter for specific relationship types",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of related entities to return per input entity",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["entity_ids"],
            },
        }

        # Define the capabilities tool
        get_capabilities_tool = {
            "name": "get_capabilities",
            "description": "Get current search and graph capabilities, including Graphiti availability status",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

        # If the method is tools/list, return the tools array with nextCursor
        if method == "tools/list":
            return self.protocol.create_response(
                request_id,
                result={
                    "tools": [
                        search_tool,
                        enhanced_search_tool,
                        fusion_benchmark_tool,
                        relationship_enrichment_tool,
                        hierarchy_search_tool,
                        attachment_search_tool,
                        find_relationships_tool,
                        trace_dependencies_tool,
                        analyze_impact_tool,
                        get_temporal_context_tool,
                        get_capabilities_tool,
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

        # Extract optional hybrid search parameters
        mode = params.get("mode")
        vector_weight = params.get("vector_weight")
        keyword_weight = params.get("keyword_weight")
        graph_weight = params.get("graph_weight")
        fusion_strategy = params.get("fusion_strategy")

        logger.info(
            "Processing search request",
            query=query,
            source_types=source_types,
            project_ids=project_ids,
            limit=limit,
            mode=mode,
            hybrid_params_provided=any(
                [mode, vector_weight, keyword_weight, graph_weight, fusion_strategy]
            ),
        )

        try:
            # Validate hybrid parameters if provided
            if mode is not None:
                from ..search.enhanced_hybrid_search import SearchMode

                try:
                    SearchMode(mode)
                except ValueError:
                    logger.error("Invalid search mode", mode=mode)
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid search mode: {mode}. Must be one of: vector_only, graph_only, hybrid, auto",
                        },
                    )

            # Validate weight parameters
            for weight_name, weight_value in [
                ("vector_weight", vector_weight),
                ("keyword_weight", keyword_weight),
                ("graph_weight", graph_weight),
            ]:
                if weight_value is not None and not (0.0 <= weight_value <= 1.0):
                    logger.error(
                        "Invalid weight parameter",
                        weight_name=weight_name,
                        weight_value=weight_value,
                    )
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid {weight_name}: {weight_value}. Must be between 0.0 and 1.0",
                        },
                    )

            # Validate fusion strategy if provided
            if fusion_strategy is not None:
                from ..search.enhanced_hybrid_search import FusionStrategy

                try:
                    FusionStrategy(fusion_strategy)
                except ValueError:
                    logger.error(
                        "Invalid fusion strategy", fusion_strategy=fusion_strategy
                    )
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid fusion strategy: {fusion_strategy}",
                        },
                    )

            # Process the query
            logger.debug("Processing query with OpenAI")
            processed_query = await self.query_processor.process_query(query)
            logger.debug(
                "Query processed successfully", processed_query=processed_query
            )

            # Determine if we should use enhanced search or legacy search
            use_enhanced_search = any(
                [mode, vector_weight, keyword_weight, graph_weight, fusion_strategy]
            )

            if use_enhanced_search:
                logger.debug("Using enhanced hybrid search due to hybrid parameters")
                # Use enhanced search capabilities
                results = await self.search_engine.search(
                    query=processed_query["query"],
                    source_types=source_types,
                    project_ids=project_ids,
                    limit=limit,
                    mode=mode,
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
                    graph_weight=graph_weight,
                    fusion_strategy=fusion_strategy,
                )
            else:
                logger.debug("Using legacy search behavior")
                # Perform the legacy search
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

            # Format the response
            response = self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(results)} results:\n\n"
                            + "\n\n".join(
                                self._format_search_result(result) for result in results
                            ),
                        }
                    ],
                    "isError": False,
                },
            )
            logger.debug("Search response formatted successfully")
            return response

        except QdrantConnectionError as e:
            logger.error("Qdrant connection failed during search", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Vector database connection failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Please check if Qdrant server is running and accessible",
                    },
                },
            )
        except QdrantQueryError as e:
            logger.error("Qdrant query failed during search", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Vector search query failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Please check your query parameters and try again",
                    },
                },
            )
        except Neo4jConnectionError as e:
            logger.error("Neo4j connection failed during search", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Graph database connection failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Graph search features may be limited. Vector search will continue to work.",
                    },
                },
            )
        except Neo4jQueryError as e:
            logger.error("Neo4j query failed during search", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Graph search query failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Falling back to vector-only search",
                    },
                },
            )
        except GraphitiError as e:
            logger.error("Graphiti operation failed during search", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Knowledge graph search failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Falling back to basic hybrid search",
                    },
                },
            )
        except OpenAIEmbeddingError as e:
            logger.error("OpenAI embedding failed during search", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Text embedding generation failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Please check your OpenAI API key and try again",
                    },
                },
            )
        except SearchConfigurationError as e:
            logger.error("Search configuration error", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid search configuration",
                    "data": e.to_dict(),
                },
            )
        except FusionStrategyError as e:
            logger.error("Fusion strategy error during search", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Result fusion failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Falling back to default fusion strategy",
                    },
                },
            )
        except HybridSearchError as e:
            logger.error("Hybrid search error", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Hybrid search operation failed",
                    "data": {
                        **e.to_dict(),
                        "suggestion": "Some search components may have failed. Partial results may be available.",
                    },
                },
            )
        except SearchEngineError as e:
            logger.error("Search engine error", error=e.to_dict())
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": f"Search error: {e.message}",
                    "data": e.to_dict(),
                },
            )
        except Exception as e:
            logger.error("Unexpected error during search", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Unexpected search error",
                    "data": {
                        "error_type": type(e).__name__,
                        "message": str(e),
                        "recoverable": True,
                        "suggestion": "Please try again or contact support if the issue persists",
                    },
                },
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

    async def _handle_enhanced_search(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle enhanced hybrid search request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling enhanced search request with params", params=params)

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
        mode = params.get("mode", "hybrid")
        vector_weight = params.get("vector_weight")
        keyword_weight = params.get("keyword_weight")
        graph_weight = params.get("graph_weight")
        source_types = params.get("source_types", [])
        project_ids = params.get("project_ids", [])
        limit = params.get("limit", 10)

        # Import SearchMode enum for validation
        from ..search.enhanced_hybrid_search import SearchMode

        # Validate mode parameter
        try:
            search_mode = SearchMode(mode) if mode else None
        except ValueError:
            logger.error("Invalid search mode", mode=mode)
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": f"Invalid search mode: {mode}. Must be one of: vector_only, graph_only, hybrid, auto",
                },
            )

        # Validate weight parameters
        for weight_name, weight_value in [
            ("vector_weight", vector_weight),
            ("keyword_weight", keyword_weight),
            ("graph_weight", graph_weight),
        ]:
            if weight_value is not None and not (0.0 <= weight_value <= 1.0):
                logger.error(
                    "Invalid weight parameter", name=weight_name, value=weight_value
                )
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": f"Invalid {weight_name}: {weight_value}. Must be between 0.0 and 1.0",
                    },
                )

        logger.info(
            "Processing enhanced search request",
            query=query,
            mode=mode,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            graph_weight=graph_weight,
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

            # Perform the enhanced search
            logger.debug("Executing enhanced hybrid search")
            results = await self.search_engine.search(
                query=processed_query["query"],
                source_types=source_types,
                project_ids=project_ids,
                limit=limit,
                mode=search_mode,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
                graph_weight=graph_weight,
            )

            # Check if enhanced search was actually used
            capabilities = self.search_engine.get_search_capabilities()
            search_type = (
                "enhanced" if capabilities.get("enhanced_hybrid_search") else "basic"
            )

            logger.info(
                "Enhanced search completed successfully",
                result_count=len(results),
                search_type=search_type,
                first_result_score=results[0].score if results else None,
            )

            # Format the response with enhanced information
            response_text = f"Enhanced Hybrid Search Results ({search_type} engine):\n"
            response_text += f"Query: {query}\n"
            response_text += f"Mode: {mode}\n"

            if (
                vector_weight is not None
                or keyword_weight is not None
                or graph_weight is not None
            ):
                response_text += f"Weights: vector={vector_weight}, keyword={keyword_weight}, graph={graph_weight}\n"

            response_text += f"Found {len(results)} results:\n\n"
            response_text += "\n\n".join(
                self._format_search_result(result) for result in results
            )

            # Add capabilities information if no results or enhanced search wasn't used
            if not results or search_type == "basic":
                response_text += "\n\n📊 Search Engine Status:\n"
                response_text += f"- Enhanced Search Available: {capabilities.get('enhanced_hybrid_search', False)}\n"
                response_text += f"- Graph Search Available: {capabilities.get('graph_search', False)}\n"
                response_text += f"- Graphiti Available: {capabilities.get('graphiti_available', False)}\n"

                if search_type == "basic":
                    response_text += "\n💡 Note: Enhanced search parameters were provided but basic search was used. This may be due to Graphiti not being available or configured."

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
            logger.debug("Enhanced search response formatted successfully")
            return response

        except Exception as e:
            logger.error("Error during enhanced search", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_enrich_with_relationships(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle relationship enrichment request for QDrant vector search candidates.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug(
            "Handling relationship enrichment request with params", params=params
        )

        # Validate required parameters
        if "entity_ids" not in params:
            logger.error("Missing required parameter: entity_ids")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: entity_ids",
                },
            )

        # Extract parameters with defaults
        entity_ids = params["entity_ids"]
        max_depth = params.get("max_depth", 2)
        include_centrality = params.get("include_centrality", True)
        include_temporal = params.get("include_temporal", True)
        relationship_types = params.get("relationship_types", [])
        limit = params.get("limit", 20)

        if not entity_ids:
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "entity_ids cannot be empty",
                },
            )

        logger.info(
            "Processing relationship enrichment request",
            entity_ids=entity_ids,
            max_depth=max_depth,
            include_centrality=include_centrality,
            include_temporal=include_temporal,
            relationship_types=relationship_types,
            limit=limit,
        )

        try:
            # Check if enhanced search engine is available
            if (
                hasattr(self.search_engine, "enhanced_hybrid_search")
                and self.search_engine.enhanced_hybrid_search
            ):
                enhanced_engine = self.search_engine.enhanced_hybrid_search

                # Check if graph search module is available
                if (
                    hasattr(enhanced_engine, "graph_module")
                    and enhanced_engine.graph_module
                ):
                    graph_module = enhanced_engine.graph_module

                    # Perform relationship enrichment for each entity
                    enriched_entities = []

                    for entity_id in entity_ids:
                        try:
                            # Build enrichment query for this entity
                            enrichment_query = f"entity:{entity_id}"

                            # Get relationship context using graph search
                            graph_results = await graph_module.search(
                                query=enrichment_query,
                                limit=limit,
                                max_depth=max_depth,
                                include_relationships=True,
                                include_temporal=include_temporal,
                            )

                            # Filter by relationship types if specified
                            if relationship_types:
                                filtered_results = []
                                for result in graph_results:
                                    if any(
                                        rel_type in result.relationship_types
                                        for rel_type in relationship_types
                                    ):
                                        filtered_results.append(result)
                                graph_results = filtered_results

                            # Create enriched entity data
                            enriched_entity = {
                                "entity_id": entity_id,
                                "relationship_count": len(graph_results),
                                "relationships": [],
                                "centrality_score": 0.0,
                                "temporal_relevance": 1.0,
                                "connected_entities": [],
                            }

                            # Process graph results
                            total_centrality = 0.0
                            total_temporal = 0.0

                            for result in graph_results:
                                relationship_data = {
                                    "related_entity_id": result.id,
                                    "content": result.content,
                                    "title": result.title,
                                    "relationship_types": result.relationship_types,
                                    "graph_distance": result.graph_distance,
                                    "centrality_score": result.centrality_score,
                                    "temporal_relevance": result.temporal_relevance,
                                    "combined_score": result.combined_score,
                                }

                                enriched_entity["relationships"].append(
                                    relationship_data
                                )
                                enriched_entity["connected_entities"].extend(
                                    result.entity_ids
                                )

                                if include_centrality:
                                    total_centrality += result.centrality_score
                                if include_temporal:
                                    total_temporal += result.temporal_relevance

                            # Calculate aggregate scores
                            if graph_results:
                                enriched_entity["centrality_score"] = (
                                    total_centrality / len(graph_results)
                                )
                                enriched_entity["temporal_relevance"] = (
                                    total_temporal / len(graph_results)
                                )

                            # Remove duplicates from connected entities
                            enriched_entity["connected_entities"] = list(
                                set(enriched_entity["connected_entities"])
                            )

                            enriched_entities.append(enriched_entity)

                        except Exception as e:
                            logger.error(f"Error enriching entity {entity_id}: {e}")
                            # Add error entry for this entity
                            enriched_entities.append(
                                {
                                    "entity_id": entity_id,
                                    "error": str(e),
                                    "relationship_count": 0,
                                    "relationships": [],
                                    "centrality_score": 0.0,
                                    "temporal_relevance": 0.0,
                                    "connected_entities": [],
                                }
                            )

                    # Format response
                    response_text = "🔗 **Relationship Enrichment Results**\n\n"
                    response_text += f"Enriched {len(enriched_entities)} entities with relationship context.\n\n"

                    for enriched in enriched_entities:
                        if "error" in enriched:
                            response_text += f"❌ **Entity {enriched['entity_id']}**: Error - {enriched['error']}\n\n"
                        else:
                            response_text += f"🎯 **Entity {enriched['entity_id']}**\n"
                            response_text += f"   • Relationships: {enriched['relationship_count']}\n"
                            response_text += f"   • Connected Entities: {len(enriched['connected_entities'])}\n"

                            if include_centrality:
                                response_text += f"   • Centrality Score: {enriched['centrality_score']:.3f}\n"
                            if include_temporal:
                                response_text += f"   • Temporal Relevance: {enriched['temporal_relevance']:.3f}\n"

                            # Show top relationships
                            top_relationships = sorted(
                                enriched["relationships"],
                                key=lambda x: x["combined_score"],
                                reverse=True,
                            )[:5]

                            if top_relationships:
                                response_text += "   • **Top Relationships:**\n"
                                for rel in top_relationships:
                                    response_text += f"     - {rel['title']} (score: {rel['combined_score']:.3f})\n"
                                    response_text += f"       Types: {', '.join(rel['relationship_types'])}\n"

                            response_text += "\n"

                    return self.protocol.create_response(
                        request_id,
                        result={
                            "content": [
                                {
                                    "type": "text",
                                    "text": response_text,
                                }
                            ],
                            "isError": False,
                            "enriched_entities": enriched_entities,
                        },
                    )
                else:
                    # Graph module not available - use content-based fallback
                    response_text = (
                        "⚠️ **Graph Search Unavailable - Using Content Fallback**\n\n"
                    )
                    response_text += "Neo4j graph search is not available. Performing content-based relationship discovery.\n\n"

                    # TODO: Implement content-based relationship discovery as fallback
                    # For now, return basic information
                    enriched_entities = []
                    for entity_id in entity_ids:
                        enriched_entities.append(
                            {
                                "entity_id": entity_id,
                                "relationship_count": 0,
                                "relationships": [],
                                "centrality_score": 0.0,
                                "temporal_relevance": 1.0,
                                "connected_entities": [],
                                "fallback_mode": True,
                            }
                        )

                    response_text += "📋 **Configuration Status:**\n"
                    from ..graphiti import is_graphiti_available

                    graphiti_available = await is_graphiti_available()

                    response_text += f"• Graphiti Available: {'✅ Yes' if graphiti_available else '❌ No'}\n"
                    response_text += f"• Enhanced Search Engine: {'✅ Available' if hasattr(self.search_engine, 'enhanced_hybrid_search') else '❌ Not Available'}\n"

                    return self.protocol.create_response(
                        request_id,
                        result={
                            "content": [
                                {
                                    "type": "text",
                                    "text": response_text,
                                }
                            ],
                            "isError": False,
                            "enriched_entities": enriched_entities,
                        },
                    )
            else:
                # Enhanced search engine not available
                response_text = "⚠️ **Enhanced Search Engine Unavailable**\n\n"
                response_text += "Enhanced hybrid search engine is not available. Cannot enrich entities with relationship context.\n"
                response_text += "Using basic search engine which does not support graph operations.\n\n"

                return self.protocol.create_response(
                    request_id,
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": response_text,
                            }
                        ],
                        "isError": False,
                        "enriched_entities": [],
                    },
                )

        except Exception as e:
            logger.error("Error in relationship enrichment", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Internal error during relationship enrichment",
                    "data": str(e),
                },
            )

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

        # Extract optional hybrid search parameters
        mode = params.get("mode")
        vector_weight = params.get("vector_weight")
        keyword_weight = params.get("keyword_weight")
        graph_weight = params.get("graph_weight")
        fusion_strategy = params.get("fusion_strategy")

        logger.info(
            "Processing hierarchy search request",
            query=query,
            hierarchy_filter=hierarchy_filter,
            organize_by_hierarchy=organize_by_hierarchy,
            limit=limit,
            mode=mode,
            hybrid_params_provided=any(
                [mode, vector_weight, keyword_weight, graph_weight, fusion_strategy]
            ),
        )

        try:
            # Validate hybrid parameters if provided (reuse validation from basic search)
            if mode is not None:
                from ..search.enhanced_hybrid_search import SearchMode

                try:
                    SearchMode(mode)
                except ValueError:
                    logger.error("Invalid search mode", mode=mode)
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid search mode: {mode}. Must be one of: vector_only, graph_only, hybrid, auto",
                        },
                    )

            # Validate weight parameters
            for weight_name, weight_value in [
                ("vector_weight", vector_weight),
                ("keyword_weight", keyword_weight),
                ("graph_weight", graph_weight),
            ]:
                if weight_value is not None and not (0.0 <= weight_value <= 1.0):
                    logger.error(
                        "Invalid weight parameter",
                        weight_name=weight_name,
                        weight_value=weight_value,
                    )
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid {weight_name}: {weight_value}. Must be between 0.0 and 1.0",
                        },
                    )

            # Validate fusion strategy if provided
            if fusion_strategy is not None:
                from ..search.enhanced_hybrid_search import FusionStrategy

                try:
                    FusionStrategy(fusion_strategy)
                except ValueError:
                    logger.error(
                        "Invalid fusion strategy", fusion_strategy=fusion_strategy
                    )
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid fusion strategy: {fusion_strategy}",
                        },
                    )

            # Process the query
            logger.debug("Processing query with OpenAI")
            processed_query = await self.query_processor.process_query(query)
            logger.debug(
                "Query processed successfully", processed_query=processed_query
            )

            # Determine if we should use enhanced search or legacy search
            use_enhanced_search = any(
                [mode, vector_weight, keyword_weight, graph_weight, fusion_strategy]
            )

            # Perform the search (Confluence only for hierarchy)
            logger.debug("Executing hierarchy search in Qdrant")
            if use_enhanced_search:
                logger.debug("Using enhanced hybrid search for hierarchy search")
                results = await self.search_engine.search(
                    query=processed_query["query"],
                    source_types=["confluence"],  # Only search Confluence for hierarchy
                    limit=limit * 2,  # Get more results to filter
                    mode=mode,
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
                    graph_weight=graph_weight,
                    fusion_strategy=fusion_strategy,
                )
            else:
                logger.debug("Using legacy search for hierarchy search")
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

        # Extract optional hybrid search parameters
        mode = params.get("mode")
        vector_weight = params.get("vector_weight")
        keyword_weight = params.get("keyword_weight")
        graph_weight = params.get("graph_weight")
        fusion_strategy = params.get("fusion_strategy")

        logger.info(
            "Processing attachment search request",
            query=query,
            attachment_filter=attachment_filter,
            include_parent_context=include_parent_context,
            limit=limit,
            mode=mode,
            hybrid_params_provided=any(
                [mode, vector_weight, keyword_weight, graph_weight, fusion_strategy]
            ),
        )

        try:
            # Validate hybrid parameters if provided (reuse validation from basic search)
            if mode is not None:
                from ..search.enhanced_hybrid_search import SearchMode

                try:
                    SearchMode(mode)
                except ValueError:
                    logger.error("Invalid search mode", mode=mode)
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid search mode: {mode}. Must be one of: vector_only, graph_only, hybrid, auto",
                        },
                    )

            # Validate weight parameters
            for weight_name, weight_value in [
                ("vector_weight", vector_weight),
                ("keyword_weight", keyword_weight),
                ("graph_weight", graph_weight),
            ]:
                if weight_value is not None and not (0.0 <= weight_value <= 1.0):
                    logger.error(
                        "Invalid weight parameter",
                        weight_name=weight_name,
                        weight_value=weight_value,
                    )
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid {weight_name}: {weight_value}. Must be between 0.0 and 1.0",
                        },
                    )

            # Validate fusion strategy if provided
            if fusion_strategy is not None:
                from ..search.enhanced_hybrid_search import FusionStrategy

                try:
                    FusionStrategy(fusion_strategy)
                except ValueError:
                    logger.error(
                        "Invalid fusion strategy", fusion_strategy=fusion_strategy
                    )
                    return self.protocol.create_response(
                        request_id,
                        error={
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Invalid fusion strategy: {fusion_strategy}",
                        },
                    )

            # Process the query
            logger.debug("Processing query with OpenAI")
            processed_query = await self.query_processor.process_query(query)
            logger.debug(
                "Query processed successfully", processed_query=processed_query
            )

            # Determine if we should use enhanced search or legacy search
            use_enhanced_search = any(
                [mode, vector_weight, keyword_weight, graph_weight, fusion_strategy]
            )

            # Perform the search
            logger.debug("Executing attachment search in Qdrant")
            if use_enhanced_search:
                logger.debug("Using enhanced hybrid search for attachment search")
                results = await self.search_engine.search(
                    query=processed_query["query"],
                    source_types=None,  # Search all sources for attachments
                    limit=limit * 2,  # Get more results to filter
                    mode=mode,
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
                    graph_weight=graph_weight,
                    fusion_strategy=fusion_strategy,
                )
            else:
                logger.debug("Using legacy search for attachment search")
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

    async def _handle_find_relationships(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle find_relationships request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling find_relationships request", params=params)

        try:
            # Extract parameters
            entity_id = params.get("entity_id")
            if not entity_id:
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": "entity_id is required",
                    },
                )

            # TODO: Use relationship_types, max_depth when graph functionality is available
            limit = params.get("limit", 20)

            # Check if Graphiti is available for graph operations
            if await is_graphiti_available():
                # Use Graphiti for real graph relationship discovery
                logger.info(
                    "Using Graphiti for relationship discovery", entity_id=entity_id
                )
                graph_results = await perform_graphiti_search(
                    query=f"relationships for entity {entity_id}", limit=limit
                )

                if graph_results:
                    response_text = f"Graph relationships for entity '{entity_id}':\n\n"
                    for i, result in enumerate(graph_results, 1):
                        # Format Graphiti edge results
                        response_text += (
                            f"{i}. {getattr(result, 'fact', str(result))}\n"
                        )
                        if hasattr(result, "source_node_uuid") and hasattr(
                            result, "target_node_uuid"
                        ):
                            response_text += f"   Source: {result.source_node_uuid}\n"
                            response_text += f"   Target: {result.target_node_uuid}\n"
                        response_text += "\n"
                else:
                    response_text = (
                        f"No graph relationships found for entity '{entity_id}'"
                    )
            else:
                # Fall back to content-based search
                logger.info(
                    "Graphiti not available, using content-based search fallback"
                )
                search_results = await self.search_engine.search(
                    query=f"relationships related to {entity_id}",
                    limit=limit,
                )

                response_text = f"Relationship-related content for entity '{entity_id}' (content-based search):\n\n"
                for i, result in enumerate(search_results, 1):
                    response_text += f"{i}. {result.source_title}\n"
                    response_text += f"   Content: {result.text[:100]}...\n"
                    response_text += f"   Score: {result.score:.3f}\n\n"

                if not search_results:
                    response_text += "No relationship-related content found."

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [{"type": "text", "text": response_text}],
                    "total_found": len(search_results),
                    "note": "Graph functionality not yet available. Results based on content search.",
                },
            )

        except Exception as e:
            logger.error("Error in find_relationships", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_trace_dependencies(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle trace_dependencies request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling trace_dependencies request", params=params)

        try:
            # Extract parameters
            entity_id = params.get("entity_id")
            if not entity_id:
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": "entity_id is required",
                    },
                )

            direction = params.get("direction", "downstream")
            # TODO: Use max_depth, include_transitive when graph functionality is available

            # Build query based on direction
            if direction == "upstream":
                query = f"dependencies of {entity_id} upstream"
            elif direction == "downstream":
                query = f"what depends on {entity_id} downstream"
            else:  # both
                query = f"all dependencies for {entity_id}"

            # Graph functionality not yet available - use content-based search
            # TODO: Integrate EnhancedHybridSearchEngine with graph capabilities
            search_results = await self.search_engine.search(
                query=query,
                limit=20,
            )

            response_text = f"Dependency-related content for entity '{entity_id}' ({direction}):\n\n"
            for i, result in enumerate(search_results, 1):
                response_text += f"{i}. {result.source_title}\n"
                response_text += f"   Content: {result.text[:100]}...\n"
                response_text += f"   Score: {result.score:.3f}\n\n"

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [{"type": "text", "text": response_text}],
                    "total_found": len(search_results),
                    "note": "Graph functionality not yet available. Results based on content search.",
                },
            )

        except Exception as e:
            logger.error("Error in trace_dependencies", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_analyze_impact(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle analyze_impact request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling analyze_impact request", params=params)

        try:
            # Extract parameters
            entity_id = params.get("entity_id")
            if not entity_id:
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": "entity_id is required",
                    },
                )

            change_type = params.get("change_type", "modify")
            # TODO: Use include_indirect, severity_threshold when graph functionality is available

            # Build impact analysis query
            query = f"impact of {change_type} {entity_id} downstream effects"

            # Graph functionality not yet available - use content-based search
            # TODO: Integrate EnhancedHybridSearchEngine with graph capabilities
            search_results = await self.search_engine.search(
                query=query,
                limit=15,
            )

            response_text = f"Impact-related content for {change_type} operation on entity '{entity_id}':\n\n"
            for i, result in enumerate(search_results, 1):
                response_text += f"{i}. {result.source_title}\n"
                response_text += f"   Content: {result.text[:100]}...\n"
                response_text += f"   Score: {result.score:.3f}\n\n"

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [{"type": "text", "text": response_text}],
                    "total_found": len(search_results),
                    "note": "Graph functionality not yet available. Results based on content search.",
                },
            )

        except Exception as e:
            logger.error("Error in analyze_impact", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_get_temporal_context(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle get_temporal_context request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling get_temporal_context request", params=params)

        try:
            # Extract parameters
            entity_id = params.get("entity_id")
            if not entity_id:
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": "entity_id is required",
                    },
                )

            # TODO: Use include_history, time_range when graph functionality is available

            # Build temporal query
            query = f"temporal context history timeline {entity_id}"

            # Graph functionality not yet available - use content-based search
            # TODO: Integrate EnhancedHybridSearchEngine with graph capabilities
            search_results = await self.search_engine.search(
                query=query,
                limit=10,
            )

            response_text = f"Temporal-related content for entity '{entity_id}':\n\n"
            for i, result in enumerate(search_results, 1):
                response_text += f"{i}. {result.source_title}\n"
                response_text += f"   Content: {result.text[:100]}...\n"
                response_text += f"   Score: {result.score:.3f}\n\n"

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [{"type": "text", "text": response_text}],
                    "total_found": len(search_results),
                    "note": "Graph functionality not yet available. Results based on content search.",
                },
            )

        except Exception as e:
            logger.error("Error in get_temporal_context", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_get_capabilities(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle get capabilities request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling get capabilities request")

        try:
            # Get Graphiti capabilities
            capabilities = await get_graphiti_capabilities()

            # Add base search capabilities
            capabilities.update(
                {
                    "vector_search": True,
                    "semantic_search": True,
                    "hybrid_search_basic": True,
                    "hierarchy_search": True,
                    "attachment_search": True,
                    "source_filtering": True,
                    "project_filtering": True,
                }
            )

            # Format response
            capabilities_text = "🔍 **Search & Graph Capabilities**\n\n"

            # Graphiti status
            if capabilities["graphiti_available"]:
                capabilities_text += "✅ **Graphiti Graph Database**: Available\n"
                capabilities_text += "  • Hybrid semantic + graph search\n"
                capabilities_text += "  • Temporal queries and versioning\n"
                capabilities_text += "  • Node distance reranking\n"
                capabilities_text += "  • Relationship discovery\n"
                capabilities_text += "  • Dependency tracing\n"
                capabilities_text += "  • Impact analysis\n\n"
            else:
                capabilities_text += "⚠️ **Graphiti Graph Database**: Not Available\n"
                capabilities_text += (
                    "  • Graph operations will use content-based fallback\n"
                )
                capabilities_text += (
                    "  • Configure NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD to enable\n\n"
                )

            # Base capabilities
            capabilities_text += "✅ **Vector Search**: Available\n"
            capabilities_text += "✅ **Semantic Search**: Available\n"
            capabilities_text += "✅ **Hierarchy Search**: Available (Confluence)\n"
            capabilities_text += "✅ **Attachment Search**: Available\n"
            capabilities_text += "✅ **Source Filtering**: Available\n"
            capabilities_text += "✅ **Project Filtering**: Available\n\n"

            # Configuration details
            if capabilities.get("configuration"):
                config = capabilities["configuration"]
                capabilities_text += "⚙️ **Configuration**:\n"
                capabilities_text += (
                    f"  • Neo4j URI: {config.get('neo4j_uri', 'not configured')}\n"
                )
                capabilities_text += (
                    f"  • Neo4j User: {config.get('neo4j_user', 'not configured')}\n"
                )
                capabilities_text += f"  • Neo4j Password: {'✓ set' if config.get('neo4j_password_set') else '✗ not set'}\n"

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": capabilities_text,
                        }
                    ],
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error getting capabilities", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )

    async def _handle_fusion_benchmark(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle fusion_benchmark request.

        Args:
            request_id: The ID of the request
            params: The parameters of the request

        Returns:
            Dict[str, Any]: The response
        """
        logger.debug("Handling fusion_benchmark request", params=params)

        try:
            # Extract parameters
            query = params.get("query")
            if not query:
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32602,
                        "message": "Invalid params",
                        "data": "query is required",
                    },
                )

            strategies = params.get(
                "strategies",
                ["weighted_sum", "graph_enhanced_weighted", "confidence_adaptive"],
            )
            limit = params.get("limit", 10)
            include_debug = params.get("include_debug", False)
            project_ids = params.get("project_ids", [])

            logger.info(
                "Processing fusion_benchmark request",
                query=query,
                strategies=strategies,
                limit=limit,
                include_debug=include_debug,
                project_ids=project_ids,
            )

            # Perform fusion benchmark
            benchmark_results = await self.search_engine.fusion_benchmark(
                query=query,
                strategies=strategies,
                limit=limit,
                include_debug=include_debug,
                project_ids=project_ids,
            )

            response_text = f"Fusion Benchmark Results for query '{query}':\n\n"
            for strategy, results in benchmark_results.items():
                response_text += f"**Strategy: {strategy}**\n"
                response_text += f"Found {len(results)} results:\n\n"
                response_text += "\n\n".join(
                    self._format_search_result(result) for result in results
                )
                response_text += "\n\n"

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [{"type": "text", "text": response_text}],
                    "total_found": sum(
                        len(results) for results in benchmark_results.values()
                    ),
                    "note": "Graph functionality not yet available. Results based on content search.",
                },
            )

        except Exception as e:
            logger.error("Error in fusion_benchmark", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )
