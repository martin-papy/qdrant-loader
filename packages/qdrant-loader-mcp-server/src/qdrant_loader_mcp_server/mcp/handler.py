"""MCP Handler implementation."""

from typing import Any

from ..search.engine import SearchEngine
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
            elif method == "tools/call":
                logger.info("Handling tools/call request")
                tool_name = params.get("name")
                if tool_name == "search":
                    return await self._handle_search(
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
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "Qdrant Loader MCP Server", "version": "1.0.0"},
                "capabilities": {
                    "tools": {"enabled": True, "supported": ["search"]},
                    "prompts": {"enabled": False},
                    "resources": {"enabled": True},
                    "logging": {"enabled": False},
                    "roots": {"listChanged": False},
                },
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
                            "enum": ["git", "confluence", "jira", "documentation"],
                        },
                        "description": "Optional list of source types to filter results",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        }

        # If the method is tools/list, return the tools array with nextCursor
        if method == "tools/list":
            return self.protocol.create_response(
                request_id,
                result={
                    "tools": [search_tool]
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
                        "tools": [search_tool],
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
        limit = params.get("limit", 10)

        logger.info(
            "Processing search request",
            query=query,
            source_types=source_types,
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
                                f"Score: {result.score}\n"
                                f"Text: {result.text}\n"
                                f"Source: {result.source_type}"
                                + (
                                    f" - {result.source_title}"
                                    if result.source_title
                                    else ""
                                )
                                + (
                                    f" ({result.source_url})"
                                    if result.source_url
                                    else ""
                                )
                                + (
                                    f"\nFile: {result.file_path}"
                                    if result.file_path
                                    else ""
                                )
                                + (
                                    f"\nRepo: {result.repo_name}"
                                    if result.repo_name
                                    else ""
                                )
                                for result in results
                            ),
                        }
                    ],
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
