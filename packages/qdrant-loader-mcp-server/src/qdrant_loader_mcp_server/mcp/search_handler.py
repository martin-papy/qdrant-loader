"""Search operations handler for MCP server."""

from typing import Any

from ..search.engine import SearchEngine
from ..search.components.search_result_models import HybridSearchResult
from ..search.processor import QueryProcessor
from ..utils import LoggingConfig
from .formatters import MCPFormatters
from .protocol import MCPProtocol

# Get logger for this module
logger = LoggingConfig.get_logger("src.mcp.search_handler")


class SearchHandler:
    """Handler for search-related operations."""

    def __init__(self, search_engine: SearchEngine, query_processor: QueryProcessor, protocol: MCPProtocol):
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
            structured_results = self.formatters.create_structured_search_results(results)
            
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

            # Perform the search (All source types for hierarchy - localfiles have folder structure)
            logger.debug("Executing hierarchy search in Qdrant")
            results = await self.search_engine.search(
                query=processed_query["query"],
                source_types=["confluence", "localfile"],  # Include localfiles with folder structure
                limit=limit * 2,  # Get more results to filter
            )

            # Apply hierarchy filters
            filtered_results = self._apply_hierarchy_filters(results, hierarchy_filter)

            # Limit results after filtering
            filtered_results = filtered_results[:limit]

            # Organize results if requested
            organized_results = None
            if organize_by_hierarchy:
                organized_results = self._organize_by_hierarchy(filtered_results)
                response_text = self.formatters.format_hierarchical_results(organized_results)
            else:
                response_text = (
                    f"Found {len(filtered_results)} results:\n\n"
                    + "\n\n".join(
                        self.formatters.format_search_result(result)
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

            # Create structured content for MCP compliance
            structured_content = self.formatters.create_structured_hierarchy_results(
                filtered_results, organize_by_hierarchy, organized_results
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
                self.formatters.format_attachment_search_result(result)
                for result in filtered_results
            )

            # Create structured content for MCP compliance
            structured_content = self.formatters.create_structured_attachment_results(
                filtered_results, attachment_filter, include_parent_context
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

    def _apply_hierarchy_filters(
        self, results: list[HybridSearchResult], hierarchy_filter: dict[str, Any]
    ) -> list[HybridSearchResult]:
        """Apply hierarchy-based filters to search results."""
        filtered_results = []

        for result in results:
            # Only process sources that have hierarchical structure (confluence, localfile)
            if result.source_type not in ["confluence", "localfile"]:
                continue

            # Apply depth filter - use folder depth for localfiles
            if "depth" in hierarchy_filter:
                # For localfiles, calculate depth from file_path folder structure
                if result.source_type == "localfile" and result.file_path:
                    folder_depth = len([p for p in result.file_path.split('/') if p]) - 1  # Exclude filename
                    if folder_depth != hierarchy_filter["depth"]:
                        continue
                elif hasattr(result, 'depth') and result.depth != hierarchy_filter["depth"]:
                    continue

            # Apply parent title filter - for localfiles use parent folder
            if "parent_title" in hierarchy_filter:
                if result.source_type == "localfile" and result.file_path:
                    # Get parent folder name
                    path_parts = [p for p in result.file_path.split('/') if p]
                    parent_folder = path_parts[-2] if len(path_parts) > 1 else ""
                    if parent_folder != hierarchy_filter["parent_title"]:
                        continue
                elif hasattr(result, 'parent_title') and result.parent_title != hierarchy_filter["parent_title"]:
                    continue

            # Apply root only filter
            if hierarchy_filter.get("root_only", False):
                # For localfiles, check if it's in the root folder
                if result.source_type == "localfile" and result.file_path:
                    path_parts = [p for p in result.file_path.split('/') if p]
                    is_root = len(path_parts) <= 2  # Root folder + filename
                    if not is_root:
                        continue
                elif not result.is_root_document():
                    continue

            # Apply has children filter - skip for localfiles as we don't track child relationships
            if "has_children" in hierarchy_filter and result.source_type != "localfile":
                if result.has_children() != hierarchy_filter["has_children"]:
                    continue

            filtered_results.append(result)

        return filtered_results

    def _organize_by_hierarchy(
        self, results: list[HybridSearchResult]
    ) -> dict[str, list[HybridSearchResult]]:
        """Organize search results by hierarchy structure."""
        hierarchy_groups = {}

        for result in results:
            # Group by root ancestor or use the document title if it's a root
            if result.source_type == "localfile" and result.file_path:
                # For localfiles, use top-level folder as root
                path_parts = [p for p in result.file_path.split('/') if p]
                root_title = path_parts[0] if path_parts else "Root"
            elif result.breadcrumb_text:
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
            def sort_key(x):
                # Calculate depth for localfiles from folder structure
                if x.source_type == "localfile" and x.file_path:
                    folder_depth = len([p for p in x.file_path.split('/') if p]) - 1
                    return (folder_depth, x.source_title)
                else:
                    return (x.depth or 0, x.source_title)
            group.sort(key=sort_key)

        return hierarchy_groups

    def _apply_attachment_filters(
        self, results: list[HybridSearchResult], attachment_filter: dict[str, Any]
    ) -> list[HybridSearchResult]:
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