"""Cross-document intelligence operations handler for MCP server."""

from typing import Any

from ..search.engine import SearchEngine
from ..utils import LoggingConfig
from .formatters import MCPFormatters
from .protocol import MCPProtocol

# Get logger for this module
logger = LoggingConfig.get_logger("src.mcp.intelligence_handler")


class IntelligenceHandler:
    """Handler for cross-document intelligence operations."""

    def __init__(self, search_engine: SearchEngine, protocol: MCPProtocol):
        """Initialize intelligence handler."""
        self.search_engine = search_engine
        self.protocol = protocol
        self.formatters = MCPFormatters()

    async def handle_analyze_document_relationships(
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
                            "text": self.formatters.format_relationship_analysis(analysis),
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

    async def handle_find_similar_documents(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle find similar documents request."""
        logger.debug("Handling find similar documents with params", params=params)

        # Validate required parameters
        if "target_query" not in params or "comparison_query" not in params:
            logger.error("Missing required parameters: target_query and comparison_query")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameters: target_query and comparison_query",
                },
            )

        try:
            logger.info("Calling search_engine.find_similar_documents with params", 
                       target_query=params["target_query"], 
                       comparison_query=params["comparison_query"])
            
            # Call the actual search engine method
            similar_docs = await self.search_engine.find_similar_documents(
                target_query=params["target_query"],
                comparison_query=params["comparison_query"],
                similarity_metrics=params.get("similarity_metrics"),
                max_similar=params.get("max_similar", 5),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )
            
            logger.info(f"Got {len(similar_docs)} similar documents from search engine")

            # Handle empty results
            if not similar_docs:
                structured_content = {
                    "similar_documents": [],
                    "target_document": {
                        "title": params["target_query"],
                        "content_preview": "",
                        "source_type": ""
                    },
                    "similarity_summary": {
                        "total_compared": 0,
                        "similar_found": 0,
                        "highest_similarity": 0,
                        "metrics_used": params.get("similarity_metrics", [])
                    }
                }
                text_response = "No similar documents found."
            else:
                # Create text response
                text_response = f"Found {len(similar_docs)} similar documents:\n\n"
                for i, doc_info in enumerate(similar_docs, 1):
                    doc = doc_info["document"]
                    similarity_score = doc_info.get("similarity_score", 0)
                    text_response += f"{i}. {getattr(doc, 'source_title', 'Untitled')} (Score: {similarity_score:.3f})\n"
                    content_preview = getattr(doc, 'text', '')[:150]
                    if len(content_preview) < len(getattr(doc, 'text', '')):
                        content_preview += "..."
                    text_response += f"   {content_preview}\n\n"

                # Create structured content for MCP compliance
                structured_content = {
                    "similar_documents": [
                        {
                            "document_id": getattr(doc_info["document"], 'id', f"doc_{i}"),
                            "title": getattr(doc_info["document"], 'source_title', 'Untitled'),
                            "similarity_score": doc_info.get("similarity_score", 0),
                            "similarity_metrics": doc_info.get("metric_scores", {}),
                            "similarity_reason": "; ".join(doc_info.get("similarity_reasons", [])),
                            "content_preview": getattr(doc_info["document"], 'text', '')[:200] + "..." if len(getattr(doc_info["document"], 'text', '')) > 200 else getattr(doc_info["document"], 'text', '')
                        }
                        for i, doc_info in enumerate(similar_docs)
                    ],
                    "target_document": {
                        "title": params["target_query"],
                        "content_preview": "",
                        "source_type": ""
                    },
                    "similarity_summary": {
                        "total_compared": len(similar_docs),
                        "similar_found": len(similar_docs),
                        "highest_similarity": max([doc.get("similarity_score", 0) for doc in similar_docs]) if similar_docs else 0,
                        "metrics_used": params.get("similarity_metrics", [])
                    }
                }

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": text_response,
                        }
                    ],
                    "structuredContent": structured_content,
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error finding similar documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e),
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
                            "text": self.formatters.format_conflict_analysis(conflicts),
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
                            "text": self.formatters.format_complementary_content(complementary),
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
                            "text": self.formatters.format_document_clusters(clusters),
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