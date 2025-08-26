"""Search operations handler for MCP server."""

import inspect
from typing import Any

from ..search.engine import SearchEngine
from ..search.processor import QueryProcessor
from ..utils import LoggingConfig
from .formatters import MCPFormatters
from .handlers.search import (
    apply_attachment_filters,
    apply_hierarchy_filters,
    apply_lightweight_attachment_filters,
    format_lightweight_attachment_text,
    format_lightweight_hierarchy_text,
    organize_by_hierarchy,
)
from .protocol import MCPProtocol

# Get logger for this module
logger = LoggingConfig.get_logger("src.mcp.search_handler")


class SearchHandler:
    """Handler for search-related operations."""

    def __init__(
        self,
        search_engine: SearchEngine,
        query_processor: QueryProcessor,
        protocol: MCPProtocol,
    ):
        """Initialize search handler."""
        self.search_engine = search_engine
        self.query_processor = query_processor
        self.protocol = protocol
        self.formatters = MCPFormatters()

    async def handle_search(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle basic search request."""
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
            structured_results = self.formatters.create_structured_search_results(
                results
            )

            # Keep existing text response for backward compatibility
            text_response = f"Found {len(results)} results:\n\n" + "\n\n".join(
                self.formatters.format_search_result(result) for result in results
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
                            "project_ids_filtered": project_ids,
                        },
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

    async def handle_hierarchy_search(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle hierarchical search request for Confluence documents."""
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
        organize_flag = params.get("organize_by_hierarchy", False)
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

            # Perform the search (All source types for hierarchy - localfiles have folder structure)
            logger.debug("Executing hierarchy search in Qdrant")
            results = await self.search_engine.search(
                query=processed_query["query"],
                source_types=[
                    "confluence",
                    "localfile",
                ],  # Include localfiles with folder structure
                limit=max(
                    limit * 2, 40
                ),  # Get enough results to filter for hierarchy navigation
            )

            # Apply hierarchy filters (support sync or async patched functions in tests)
            maybe_filtered = self._apply_hierarchy_filters(results, hierarchy_filter)
            filtered_results = (
                await maybe_filtered
                if inspect.isawaitable(maybe_filtered)
                else maybe_filtered
            )

            # For hierarchy search, prioritize returning more documents for better hierarchy navigation
            # Limit to maximum of 20 documents for hierarchy index (not just the user's limit)
            hierarchy_limit = max(limit, 20)
            filtered_results = filtered_results[:hierarchy_limit]

            # Organize results if requested
            organized_results = None
            if organize_flag:
                organized_results = self._organize_by_hierarchy(filtered_results)
                response_text = format_lightweight_hierarchy_text(
                    organized_results, len(filtered_results)
                )
            else:
                response_text = format_lightweight_hierarchy_text(
                    {}, len(filtered_results)
                )

            logger.info(
                "Hierarchy search completed successfully",
                result_count=len(filtered_results),
                first_result_score=(
                    filtered_results[0].score if filtered_results else None
                ),
            )

            # Create structured content for MCP compliance
            structured_content = self.formatters.create_lightweight_hierarchy_results(
                filtered_results, organized_results or {}, query
            )

            # Format the response with both text and structured content
            response = self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": response_text,
                        }
                    ],
                    "structuredContent": structured_content,
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

    async def handle_attachment_search(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle attachment search request."""
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

            # Apply lightweight attachment filters (NEW - supports multi-source)
            filtered_results = self._apply_lightweight_attachment_filters(
                results, attachment_filter
            )

            # Limit to reasonable number for performance (ensure good navigation)
            attachment_limit = max(limit, 15)  # At least 15 for good navigation
            filtered_results = filtered_results[:attachment_limit]

            logger.info(
                "Attachment search completed successfully",
                result_count=len(filtered_results),
                first_result_score=(
                    filtered_results[0].score if filtered_results else None
                ),
            )

            # Create attachment groups for organized display
            organized_results = {}
            attachment_groups = []
            if filtered_results:
                # Group attachments by type for better organization
                attachment_groups = self.formatters._organize_attachments_by_type(
                    filtered_results
                )
                for group in attachment_groups:
                    group_results = group.get("results", [])
                    organized_results[group["group_name"]] = group_results

            # Create lightweight text response
            response_text = format_lightweight_attachment_text(
                organized_results, len(filtered_results)
            )

            # Create lightweight structured content for MCP compliance
            structured_content = self.formatters.create_lightweight_attachment_results(
                attachment_groups, query
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
                    "structuredContent": structured_content,
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

    # Back-compat thin wrappers for tests that patch private methods
    def _apply_hierarchy_filters(self, results, hierarchy_filter):
        return apply_hierarchy_filters(results, hierarchy_filter)

    def _organize_by_hierarchy(self, results):
        return organize_by_hierarchy(results)

    def _apply_attachment_filters(self, results, attachment_filter):
        return apply_attachment_filters(results, attachment_filter)

    def _apply_lightweight_attachment_filters(self, results, attachment_filter):
        return apply_lightweight_attachment_filters(
            results,
            attachment_filter,
            file_type_extractor=self.formatters._extract_file_type_minimal,
        )

    def _format_lightweight_attachment_text(self, organized_results, total_found):
        return format_lightweight_attachment_text(organized_results, total_found)

    def _format_lightweight_hierarchy_text(self, organized_results, total_found):
        return format_lightweight_hierarchy_text(organized_results, total_found)

    async def handle_expand_document(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle expand document request for lazy loading using standard search format."""
        logger.debug("Handling expand document with params", params=params)

        # Validate required parameter
        if (
            "document_id" not in params
            or params["document_id"] is None
            or params["document_id"] == ""
        ):
            logger.error("Missing required parameter: document_id")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: document_id",
                },
            )

        document_id = params["document_id"]

        try:
            logger.info(f"Expanding document with ID: {document_id}")

            # Search for the document - field search doesn't guarantee exact matches
            # Try document_id field search first, but get more results to filter
            results = await self.search_engine.search(
                query=f"document_id:{document_id}",
                limit=10,  # Get more results to ensure we find the exact match
            )

            # Filter for exact document_id matches
            exact_matches = [r for r in results if r.document_id == document_id]
            if exact_matches:
                results = exact_matches[:1]  # Take only the first exact match
            else:
                # Fallback to general search if no exact match in field search
                results = await self.search_engine.search(query=document_id, limit=10)
                # Filter again for exact document_id matches
                exact_matches = [r for r in results if r.document_id == document_id]
                if exact_matches:
                    results = exact_matches[:1]
                else:
                    results = []

            if not results:
                logger.warning(f"Document not found with ID: {document_id}")
                return self.protocol.create_response(
                    request_id,
                    error={
                        "code": -32604,
                        "message": "Document not found",
                        "data": f"No document found with ID: {document_id}",
                    },
                )

            logger.info(f"Successfully found document: {results[0].source_title}")

            # Use the existing search result formatting - exactly the same as standard search
            formatted_results = (
                "Found 1 document:\n\n"
                + self.formatters.format_search_result(results[0])
            )
            structured_results_list = self.formatters.create_structured_search_results(
                results
            )

            # Create the same structure as standard search
            structured_results = {
                "results": structured_results_list,
                "total_found": len(results),
                "query_context": {
                    "original_query": f"expand_document:{document_id}",
                    "source_types_filtered": [],
                    "project_ids_filtered": [],
                    "is_document_expansion": True,
                },
            }

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": formatted_results,
                        }
                    ],
                    "structuredContent": structured_results,
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error expanding document", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            )
