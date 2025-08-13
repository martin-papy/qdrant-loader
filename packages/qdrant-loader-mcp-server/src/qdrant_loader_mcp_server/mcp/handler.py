"""MCP Handler implementation."""

from typing import Any

from ..search.engine import SearchEngine
from ..search.processor import QueryProcessor
from ..utils import LoggingConfig, get_version
from .intelligence_handler import IntelligenceHandler
from .protocol import MCPProtocol
from .schemas import MCPSchemas
from .search_handler import SearchHandler

# Get logger for this module
logger = LoggingConfig.get_logger("src.mcp.handler")


class MCPHandler:
    """MCP Handler for processing RAG requests."""

    def __init__(self, search_engine: SearchEngine, query_processor: QueryProcessor):
        """Initialize MCP Handler."""
        self.protocol = MCPProtocol()
        self.search_engine = search_engine
        self.query_processor = query_processor

        # Initialize specialized handlers
        self.search_handler = SearchHandler(
            search_engine, query_processor, self.protocol
        )
        self.intelligence_handler = IntelligenceHandler(search_engine, self.protocol)

        # Reduce noise on startup: use DEBUG level instead of INFO
        logger.debug("MCP Handler initialized")

    async def handle_request(
        self, request: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
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
            if protocol_version and protocol_version not in [
                "2025-06-18",
                "2025-03-26",
                "2024-11-05",
            ]:
                logger.warning(
                    f"Unsupported protocol version in headers: {protocol_version}"
                )

        # Validate request format
        if not self.protocol.validate_request(request):
            logger.error("Request validation failed")
            # For invalid requests, we need to determine if we can extract an ID
            request_id = None
            if isinstance(request, dict):
                request_id = request.get("id")
                if request_id is not None and not isinstance(request_id, str | int):
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
                return await self.search_handler.handle_search(request_id, params)
            # Cross-Document Intelligence Methods
            elif method == "analyze_document_relationships":
                logger.info("Handling document relationship analysis request")
                return await self.intelligence_handler.handle_analyze_document_relationships(
                    request_id, params
                )
            elif method == "find_similar_documents":
                logger.info("Handling find similar documents request")
                return await self.intelligence_handler.handle_find_similar_documents(
                    request_id, params
                )
            elif method == "detect_document_conflicts":
                logger.info("Handling conflict detection request")
                return await self.intelligence_handler.handle_detect_document_conflicts(
                    request_id, params
                )
            elif method == "find_complementary_content":
                logger.info("Handling complementary content request")
                return (
                    await self.intelligence_handler.handle_find_complementary_content(
                        request_id, params
                    )
                )
            elif method == "cluster_documents":
                logger.info("Handling document clustering request")
                return await self.intelligence_handler.handle_cluster_documents(
                    request_id, params
                )
            elif method == "tools/call":
                logger.info("Handling tools/call request")
                tool_name = params.get("name")
                if tool_name == "search":
                    return await self.search_handler.handle_search(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "hierarchy_search":
                    return await self.search_handler.handle_hierarchy_search(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "attachment_search":
                    return await self.search_handler.handle_attachment_search(
                        request_id, params.get("arguments", {})
                    )
                # Cross-Document Intelligence Tools
                elif tool_name == "analyze_relationships":
                    logger.info("🔍 DEBUG: analyze_relationships tool called!")
                    logger.info(
                        f"🔍 DEBUG: intelligence_handler exists: {self.intelligence_handler is not None}"
                    )
                    return await self.intelligence_handler.handle_analyze_document_relationships(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "find_similar_documents":
                    return (
                        await self.intelligence_handler.handle_find_similar_documents(
                            request_id, params.get("arguments", {})
                        )
                    )
                elif tool_name == "detect_document_conflicts":
                    return await self.intelligence_handler.handle_detect_document_conflicts(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "find_complementary_content":
                    return await self.intelligence_handler.handle_find_complementary_content(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "cluster_documents":
                    return await self.intelligence_handler.handle_cluster_documents(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "expand_document":
                    return await self.search_handler.handle_expand_document(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "expand_cluster":
                    return await self.intelligence_handler.handle_expand_cluster(
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
                "serverInfo": {
                    "name": "Qdrant Loader MCP Server",
                    "version": get_version(),
                },
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

        # Get all tool schemas from the schemas module
        all_tools = MCPSchemas.get_all_tool_schemas()

        # If the method is tools/list, return the tools array with nextCursor
        if method == "tools/list":
            return self.protocol.create_response(
                request_id,
                result={
                    "tools": all_tools
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
                        "tools": all_tools,
                        "resources": [],
                        "resourceTemplates": [],
                    }
                ]
            },
        )
