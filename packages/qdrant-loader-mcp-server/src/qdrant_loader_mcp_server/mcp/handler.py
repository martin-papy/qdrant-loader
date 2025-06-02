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
                elif tool_name == "hierarchy_search":
                    return await self._handle_hierarchy_search(
                        request_id, params.get("arguments", {})
                    )
                elif tool_name == "attachment_search":
                    return await self._handle_attachment_search(
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
        }

        # Define the hierarchical search tool for Confluence
        hierarchy_search_tool = {
            "name": "hierarchy_search",
            "description": "Search Confluence documents with hierarchy-aware filtering and organization",
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
        }

        # Define the attachment search tool
        attachment_search_tool = {
            "name": "attachment_search",
            "description": "Search for file attachments and their parent documents across Confluence, Jira, and other sources",
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
            formatted_result += f"\n📎 Attachment"
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
        formatted_result += f"\n📎 Attachment"
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
