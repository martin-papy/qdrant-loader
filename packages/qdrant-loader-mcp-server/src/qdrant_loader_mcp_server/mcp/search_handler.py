"""Search operations handler for MCP server."""

import inspect
from typing import Any

from ..search.components.search_result_models import HybridSearchResult
from ..search.engine import SearchEngine
from ..search.processor import QueryProcessor
from ..utils import LoggingConfig
from .formatters import MCPFormatters
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
            if organize_by_hierarchy:
                organized_results = self._organize_by_hierarchy(filtered_results)
                response_text = self._format_lightweight_hierarchy_text(
                    organized_results, len(filtered_results)
                )
            else:
                response_text = self._format_lightweight_hierarchy_text(
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
                filtered_results, organized_results, query
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
            if filtered_results:
                # Group attachments by type for better organization
                attachment_groups = self.formatters._organize_attachments_by_type(
                    filtered_results
                )
                for group in attachment_groups:
                    group_results = [
                        r
                        for r in filtered_results
                        if r.document_id in group["document_ids"]
                    ]
                    organized_results[group["group_name"]] = group_results

            # Create lightweight text response
            response_text = self._format_lightweight_attachment_text(
                organized_results, len(filtered_results)
            )

            # Create lightweight structured content for MCP compliance
            structured_content = self.formatters.create_lightweight_attachment_results(
                filtered_results, attachment_filter, query
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
                file_path_val = getattr(result, "file_path", None)
                if result.source_type == "localfile" and file_path_val:
                    # Depth = number of folders before filename
                    path_parts = [p for p in file_path_val.split("/") if p]
                    # Depth definition: number of folders before filename minus 1
                    folder_depth = max(0, len(path_parts) - 2)
                    if folder_depth != hierarchy_filter["depth"]:
                        continue
                elif (
                    hasattr(result, "depth")
                    and result.depth != hierarchy_filter["depth"]
                ):
                    continue

            # Apply parent title filter - for localfiles use parent folder
            if "parent_title" in hierarchy_filter:
                file_path_val = getattr(result, "file_path", None)
                if result.source_type == "localfile" and file_path_val:
                    # Get parent folder name
                    path_parts = [p for p in file_path_val.split("/") if p]
                    parent_folder = path_parts[-2] if len(path_parts) > 1 else ""
                    if parent_folder != hierarchy_filter["parent_title"]:
                        continue
                else:
                    parent_title_val = getattr(result, "parent_title", None)
                    if parent_title_val is not None and parent_title_val != hierarchy_filter["parent_title"]:
                        continue

            # Apply root only filter
            if hierarchy_filter.get("root_only", False):
                # For localfiles, check if it's in the root folder
                file_path_val = getattr(result, "file_path", None)
                if result.source_type == "localfile" and file_path_val:
                    path_parts = [p for p in file_path_val.split("/") if p]
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
            file_path_val = getattr(result, "file_path", None)
            if result.source_type == "localfile" and file_path_val:
                # For localfiles, use top-level folder as root
                path_parts = [p for p in file_path_val.split("/") if p]
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
                x_file_path = getattr(x, "file_path", None)
                if x.source_type == "localfile" and x_file_path:
                    folder_depth = len([p for p in x_file_path.split("/") if p]) - 1
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
            _min_size = attachment_filter.get("file_size_min")
            if (
                _min_size is not None
                and result.file_size is not None
                and result.file_size < _min_size
            ):
                continue
            _max_size = attachment_filter.get("file_size_max")
            if (
                _max_size is not None
                and result.file_size is not None
                and result.file_size > _max_size
            ):
                continue

            # Apply author filter
            if "author" in attachment_filter:
                if result.attachment_author != attachment_filter["author"]:
                    continue

            filtered_results.append(result)

        return filtered_results

    def _apply_lightweight_attachment_filters(
        self, results: list[HybridSearchResult], attachment_filter: dict[str, Any]
    ) -> list[HybridSearchResult]:
        """Fast filtering optimized for attachment discovery across all sources."""
        filtered_results = []

        for result in results:
            # Quick attachment detection - avoid expensive checks
            _is_attachment_flag = bool(getattr(result, "is_attachment", False))
            _original_filename = getattr(result, "original_filename", None)
            _file_path = getattr(result, "file_path", None)
            _is_path_file = (
                isinstance(_file_path, str)
                and "." in _file_path
                and not _file_path.endswith("/")
            )
            is_attachment = (
                _is_attachment_flag or bool(_original_filename) or _is_path_file
            )

            if not is_attachment:
                continue

            # Apply filters with early exits for performance
            if attachment_filter.get("attachments_only") and not bool(
                getattr(result, "is_attachment", False)
            ):
                continue

            if attachment_filter.get("file_type"):
                file_type = self.formatters._extract_file_type_minimal(result)
                if file_type != attachment_filter["file_type"]:
                    continue

            # Size filters with null checks (include zero-byte files)
            _file_size = getattr(result, "file_size", None)
            if (
                attachment_filter.get("file_size_min") is not None
                and _file_size is not None
                and _file_size < attachment_filter["file_size_min"]
            ):
                    continue

            if (
                attachment_filter.get("file_size_max") is not None
                and _file_size is not None
                and _file_size > attachment_filter["file_size_max"]
            ):
                    continue

            # Parent document filter (works across source types)
            if attachment_filter.get("parent_document_title"):
                parent_title = getattr(
                    result, "parent_document_title", None
                ) or getattr(result, "parent_title", None)
                if parent_title != attachment_filter["parent_document_title"]:
                    continue

            # Author filter
            if attachment_filter.get("author"):
                author = getattr(result, "attachment_author", None) or getattr(
                    result, "author", None
                )
                if author != attachment_filter["author"]:
                    continue

            filtered_results.append(result)

        return filtered_results

    def _format_lightweight_attachment_text(
        self, organized_results: dict[str, list], total_found: int
    ) -> str:
        """Format attachment results as lightweight text summary."""
        if not organized_results:
            return f"📎 **Attachment Search Results**\n\nFound {total_found} attachments. Use the structured data below to navigate and retrieve specific files."

        formatted = f"📎 **Attachment Search Results** ({total_found} attachments)\n\n"

        for group_name, results in organized_results.items():
            formatted += f"📁 **{group_name}** ({len(results)} files)\n"

            # Show first few attachments as examples
            for result in results[:3]:
                filename = self.formatters._extract_safe_filename(result)
                file_type = self.formatters._extract_file_type_minimal(result)
                formatted += (
                    f"  📄 {filename} ({file_type}) - Score: {result.score:.3f}\n"
                )

            if len(results) > 3:
                formatted += f"  ... and {len(results) - 3} more files\n"
            formatted += "\n"

        formatted += "💡 **Usage:** Use the structured attachment data to:\n"
        formatted += "• Browse attachments by file type or source\n"
        formatted += "• Get document IDs for specific file content retrieval\n"
        formatted += "• Filter attachments by metadata (size, type, etc.)\n"

        return formatted

    def _format_lightweight_hierarchy_text(
        self, organized_results: dict[str, list], total_found: int
    ) -> str:
        """Format hierarchy results as lightweight text summary."""
        if not organized_results:
            return f"📋 **Hierarchy Search Results**\n\nFound {total_found} documents. Use the structured data below to navigate the hierarchy and retrieve specific documents."

        formatted = f"📋 **Hierarchy Search Results** ({total_found} documents)\n\n"

        for group_name, results in organized_results.items():
            clean_name = self.formatters._generate_clean_group_name(group_name, results)
            formatted += f"📁 **{clean_name}** ({len(results)} documents)\n"

            # Show first few documents as examples
            for result in results[:3]:
                formatted += f"  📄 {result.source_title} (Score: {result.score:.3f})\n"

            if len(results) > 3:
                formatted += f"  ... and {len(results) - 3} more documents\n"
            formatted += "\n"

        formatted += "💡 **Usage:** Use the structured hierarchy data to:\n"
        formatted += "• Browse document groups and navigate hierarchy levels\n"
        formatted += "• Get document IDs for specific content retrieval\n"
        formatted += "• Understand document relationships and organization\n"

        return formatted

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
