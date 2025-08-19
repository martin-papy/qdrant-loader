"""Cross-document intelligence operations handler for MCP server."""

import hashlib
import json
from typing import Any

from ..search.engine import SearchEngine
from ..utils import LoggingConfig
from .formatters import MCPFormatters
from .protocol import MCPProtocol
from .handlers.intelligence import (
    process_analysis_results,
    get_or_create_document_id as _get_or_create_document_id_fn,
)

# Get logger for this module
logger = LoggingConfig.get_logger("src.mcp.intelligence_handler")


class IntelligenceHandler:
    """Handler for cross-document intelligence operations."""

    def __init__(self, search_engine: SearchEngine, protocol: MCPProtocol):
        """Initialize intelligence handler."""
        self.search_engine = search_engine
        self.protocol = protocol
        self.formatters = MCPFormatters()

    def _get_or_create_document_id(self, doc: Any) -> str:
        return _get_or_create_document_id_fn(doc)

    async def handle_analyze_document_relationships(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle document relationship analysis request."""
        logger.debug(
            "Handling document relationship analysis with params", params=params
        )

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
            logger.info(
                "Performing document relationship analysis using SearchEngine..."
            )

            # Use the sophisticated SearchEngine method
            analysis_results = await self.search_engine.analyze_document_relationships(
                query=params["query"],
                limit=params.get("limit", 20),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            logger.info("Analysis completed successfully")

            # Transform complex analysis to MCP schema format
            mcp_result = process_analysis_results(analysis_results, params)

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_relationship_analysis(
                                analysis_results
                            ),
                        }
                    ],
                    "structuredContent": mcp_result,
                    "isError": False,
                },
            )

        except Exception:
            logger.error("Error during document relationship analysis", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal server error"},
            )

    async def handle_find_similar_documents(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle find similar documents request."""
        logger.debug("Handling find similar documents with params", params=params)

        # Validate required parameters
        if "target_query" not in params or "comparison_query" not in params:
            logger.error(
                "Missing required parameters: target_query and comparison_query"
            )
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameters: target_query and comparison_query",
                },
            )

        try:
            logger.info(
                "Performing find similar documents using SearchEngine...",
                target_query=params["target_query"],
                comparison_query=params["comparison_query"],
            )

            # Use the sophisticated SearchEngine method
            similar_docs = await self.search_engine.find_similar_documents(
                target_query=params["target_query"],
                comparison_query=params["comparison_query"],
                similarity_metrics=params.get("similarity_metrics"),
                max_similar=params.get("max_similar", 5),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            logger.info(f"Got {len(similar_docs)} similar documents from SearchEngine")

            # ✅ Add response validation
            expected_count = params.get("max_similar", 5)
            if len(similar_docs) < expected_count:
                logger.warning(
                    f"Expected up to {expected_count} similar documents, but only got {len(similar_docs)}. "
                    f"This may indicate similarity threshold issues or insufficient comparison documents."
                )

            # ✅ Log document IDs for debugging
            doc_ids = [doc.get("document_id") for doc in similar_docs]
            logger.debug(f"Similar document IDs: {doc_ids}")

            # ✅ Validate that document_id is present in responses
            missing_ids = [
                i for i, doc in enumerate(similar_docs) if not doc.get("document_id")
            ]
            if missing_ids:
                logger.error(
                    f"Missing document_id in similar documents at indices: {missing_ids}"
                )

            # ✅ Create structured content for MCP compliance using lightweight formatter
            structured_content = (
                self.formatters.create_lightweight_similar_documents_results(
                    similar_docs, params["target_query"], params["comparison_query"]
                )
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_similar_documents(
                                similar_docs
                            ),
                        }
                    ],
                    "structuredContent": structured_content,
                    "isError": False,
                },
            )

        except Exception:
            logger.error("Error finding similar documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Internal server error",
                },
            )

    async def handle_detect_document_conflicts(
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
            logger.info("Performing conflict detection using SearchEngine...")

            # Use the sophisticated SearchEngine method
            # Build kwargs, include overrides only if explicitly provided
            conflict_kwargs: dict[str, Any] = {
                "query": params["query"],
                "limit": params.get("limit"),
                "source_types": params.get("source_types"),
                "project_ids": params.get("project_ids"),
            }
            for opt in (
                "use_llm",
                "max_llm_pairs",
                "overall_timeout_s",
                "max_pairs_total",
                "text_window_chars",
            ):
                if opt in params and params[opt] is not None:
                    conflict_kwargs[opt] = params[opt]

            conflict_results = await self.search_engine.detect_document_conflicts(
                **conflict_kwargs
            )

            logger.info("Conflict detection completed successfully")

            # Create lightweight structured content for MCP compliance
            original_documents = conflict_results.get("original_documents", [])
            structured_content = self.formatters.create_lightweight_conflict_results(
                conflict_results, params["query"]
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_conflict_analysis(
                                conflict_results
                            ),
                        }
                    ],
                    "structuredContent": structured_content,
                    "isError": False,
                },
            )

        except Exception:
            logger.error("Error detecting conflicts", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal server error"},
            )

    async def handle_find_complementary_content(
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
            logger.info("🔍 About to call search_engine.find_complementary_content")
            logger.info(f"🔍 search_engine type: {type(self.search_engine)}")
            logger.info(f"🔍 search_engine is None: {self.search_engine is None}")

            result = await self.search_engine.find_complementary_content(
                target_query=params["target_query"],
                context_query=params["context_query"],
                max_recommendations=params.get("max_recommendations", 5),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            # Defensive check to ensure we received the expected result type
            if not isinstance(result, dict):
                logger.error(
                    "Unexpected complementary content result type",
                    got_type=str(type(result)),
                )
                return self.protocol.create_response(
                    request_id,
                    error={"code": -32603, "message": "Internal server error"},
                )

            complementary_recommendations = result.get(
                "complementary_recommendations", []
            )
            target_document = result.get("target_document")
            context_documents_analyzed = result.get("context_documents_analyzed", 0)

            logger.info(
                f"✅ search_engine.find_complementary_content completed, got {len(complementary_recommendations)} results"
            )

            # Create lightweight structured content using the new formatter
            structured_content = (
                self.formatters.create_lightweight_complementary_results(
                    complementary_recommendations=complementary_recommendations,
                    target_document=target_document,
                    context_documents_analyzed=context_documents_analyzed,
                    target_query=params["target_query"],
                )
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_complementary_content(
                                complementary_recommendations
                            ),
                        }
                    ],
                    "structuredContent": structured_content,
                    "isError": False,
                },
            )

        except Exception:
            logger.error("Error finding complementary content", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal server error"},
            )

    async def handle_cluster_documents(
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
            logger.info("Performing document clustering using SearchEngine...")

            # Use the sophisticated SearchEngine method
            clustering_results = await self.search_engine.cluster_documents(
                query=params["query"],
                limit=params.get("limit", 25),
                max_clusters=params.get("max_clusters", 10),
                min_cluster_size=params.get("min_cluster_size", 2),
                strategy=params.get("strategy", "mixed_features"),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            logger.info("Document clustering completed successfully")

            # Create lightweight clustering response following hierarchy_search pattern
            mcp_clustering_results = self.formatters.create_lightweight_cluster_results(
                clustering_results, params.get("query", "")
            )

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_document_clusters(
                                clustering_results
                            ),
                        }
                    ],
                    "structuredContent": mcp_clustering_results,
                    "isError": False,
                },
            )

        except Exception:
            logger.error("Error clustering documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal server error"},
            )

    async def handle_expand_cluster(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle cluster expansion request for lazy loading."""
        logger.debug("Handling expand cluster with params", params=params)

        if "cluster_id" not in params:
            logger.error("Missing required parameter: cluster_id")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: cluster_id",
                },
            )

        try:
            cluster_id = params["cluster_id"]
            limit = params.get("limit", 20)
            offset = params.get("offset", 0)
            include_metadata = params.get("include_metadata", True)

            logger.info(
                f"Expanding cluster {cluster_id} with limit={limit}, offset={offset}"
            )

            # For now, we need to re-run clustering to get cluster data
            # In a production system, this would be cached or stored
            # This is a placeholder implementation

            # Since we don't have cluster data persistence yet, return a helpful message
            # In the future, this would retrieve stored cluster data and expand it

            expansion_result = {
                "cluster_id": cluster_id,
                "message": "Cluster expansion functionality requires re-running clustering",
                "suggestion": "Please run cluster_documents again and use the lightweight response for navigation",
                "cluster_info": {
                    "expansion_requested": True,
                    "limit": limit,
                    "offset": offset,
                    "include_metadata": include_metadata,
                },
                "documents": [],
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": 0,
                    "has_more": False,
                },
            }

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"🔄 **Cluster Expansion Request**\n\nCluster ID: {cluster_id}\n\n"
                            + "Currently, cluster expansion requires re-running the clustering operation. "
                            + "The lightweight cluster response provides the first 5 documents per cluster. "
                            + "For complete cluster content, please run `cluster_documents` again.\n\n"
                            + "💡 **Future Enhancement**: Cluster data will be cached to enable true lazy loading.",
                        }
                    ],
                    "structuredContent": expansion_result,
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error expanding cluster", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Internal server error",
                    "data": str(e),
                },
            )
