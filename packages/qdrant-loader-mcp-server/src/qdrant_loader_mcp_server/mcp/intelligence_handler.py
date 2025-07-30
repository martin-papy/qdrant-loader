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
            logger.info("Performing document relationship analysis using SearchEngine...")
            
            # Use the sophisticated SearchEngine method
            analysis_results = await self.search_engine.analyze_document_relationships(
                query=params["query"],
                limit=params.get("limit", 20),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            logger.info(f"Analysis completed successfully")

            # Transform complex analysis to MCP schema format
            relationships = []
            summary_parts = []
            total_analyzed = analysis_results.get("query_metadata", {}).get("document_count", 0)
            
            # Extract relationships from document clusters
            if "document_clusters" in analysis_results:
                clusters = analysis_results["document_clusters"]
                summary_parts.append(f"{len(clusters)} document clusters found")
                
                for cluster in clusters:
                    cluster_docs = cluster.get("documents", [])
                    # Create similarity relationships between documents in the same cluster
                    for i, doc1 in enumerate(cluster_docs):
                        for doc2 in cluster_docs[i+1:]:
                            doc1_title = doc1.get("title", doc1.get("source_title", "Unknown"))
                            doc2_title = doc2.get("title", doc2.get("source_title", "Unknown"))
                            relationships.append({
                                "document_1": doc1_title,
                                "document_2": doc2_title,
                                "relationship_type": "similarity",
                                "score": cluster.get("cohesion_score", 0.8),
                                "description": f"Both documents belong to cluster: {cluster.get('theme', 'unnamed cluster')}"
                            })
                
            # Extract conflict relationships
            if "conflict_analysis" in analysis_results:
                conflicts = analysis_results["conflict_analysis"].get("conflicting_pairs", [])
                if conflicts:
                    summary_parts.append(f"{len(conflicts)} conflicts detected")
                    for conflict in conflicts:
                        if isinstance(conflict, (list, tuple)) and len(conflict) >= 2:
                            doc1, doc2 = conflict[0], conflict[1]
                            conflict_info = conflict[2] if len(conflict) > 2 else {}
                            relationships.append({
                                "document_1": str(doc1),
                                "document_2": str(doc2),
                                "relationship_type": "conflict",
                                "score": conflict_info.get("severity", 0.5),
                                "description": f"Conflict detected: {conflict_info.get('type', 'unknown conflict')}"
                            })
                            
            # Extract complementary relationships
            if "complementary_content" in analysis_results:
                complementary = analysis_results["complementary_content"]
                comp_count = 0
                for doc_id, recommendations in complementary.items():
                    for rec in recommendations[:2]:  # Limit to top 2 per document
                        if isinstance(rec, dict):
                            target_doc = rec.get("target_doc", "Unknown")
                            score = rec.get("score", 0.5)
                            reason = rec.get("reason", "complementary content")
                            relationships.append({
                                "document_1": doc_id,
                                "document_2": target_doc,
                                "relationship_type": "complementary",
                                "score": score,
                                "description": f"Complementary content: {reason}"
                            })
                            comp_count += 1
                if comp_count > 0:
                    summary_parts.append(f"{comp_count} complementary relationships")
                    
            # Extract citation relationships
            if "citation_network" in analysis_results:
                citation_net = analysis_results["citation_network"]
                if citation_net.get("edges", 0) > 0:
                    summary_parts.append(f"{citation_net['edges']} citation relationships")
                    
            if "similarity_insights" in analysis_results:
                insights = analysis_results["similarity_insights"]
                if insights:
                    summary_parts.append("similarity patterns identified")
            
            # Create a simple summary string
            if summary_parts:
                summary_text = f"Analyzed {total_analyzed} documents: {', '.join(summary_parts)}"
            else:
                summary_text = f"Analyzed {total_analyzed} documents with no significant relationships found"

            # Format according to MCP schema
            mcp_result = {
                "relationships": relationships,
                "total_analyzed": total_analyzed,
                "summary": summary_text
            }

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_relationship_analysis(analysis_results),
                        }
                    ],
                    "structuredContent": mcp_result,
                    "isError": False,
                },
            )

        except Exception as e:
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
            logger.info("Performing find similar documents using SearchEngine...", 
                       target_query=params["target_query"], 
                       comparison_query=params["comparison_query"])
            
            # Use the sophisticated SearchEngine method
            similar_docs = await self.search_engine.find_similar_documents(
                target_query=params["target_query"],
                comparison_query=params["comparison_query"],
                similarity_metrics=params.get("similarity_metrics"),
                max_similar=params.get("max_similar", 5),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            logger.info(f"Got {len(similar_docs)} similar documents from SearchEngine")

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_similar_documents(similar_docs),
                        }
                    ],
                    "structuredContent": {
                        "similar_documents": similar_docs,
                        "similarity_summary": {
                            "total_found": len(similar_docs),
                            "metrics_used": params.get("similarity_metrics", [])
                        }
                    },
                    "isError": False,
                },
            )

        except Exception as e:
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
            conflict_results = await self.search_engine.detect_document_conflicts(
                query=params["query"],
                limit=params.get("limit", 15),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            logger.info(f"Conflict detection completed successfully")

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_conflict_analysis(conflict_results),
                        }
                    ],
                    "structuredContent": conflict_results,
                    "isError": False,
                },
            )

        except Exception as e:
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
                    "structuredContent": {
                        "complementary_content": [
                            {
                                "document_id": f"comp_{i}",
                                "title": getattr(comp_doc.get("document", {}), "source_title", "") or "",
                                "content_preview": getattr(comp_doc.get("document", {}), "text", "")[:200] or "",
                                "complementary_score": comp_doc.get("complementary_score", 0.0),
                                "complementary_reason": comp_doc.get("reason", "Complementary content found"),
                                "relationship_type": comp_doc.get("relationship_type", "related"),
                                "source_type": getattr(comp_doc.get("document", {}), "source_type", "") or "",
                                "metadata": {
                                    "project_id": getattr(comp_doc.get("document", {}), "project_id", "") or "",
                                    "created_date": "",
                                    "author": ""
                                }
                            }
                            for i, comp_doc in enumerate(complementary if complementary else [])
                        ],
                        "target_document": {
                            "title": params["target_query"],
                            "content_preview": "",
                            "source_type": ""
                        },
                        "complementary_summary": {
                            "total_analyzed": len(complementary) if complementary else 0,
                            "complementary_found": len(complementary) if complementary else 0,
                            "highest_score": max((c.get("complementary_score", 0.0) for c in complementary), default=0.0) if complementary else 0.0,
                            "relationship_types": list(set(c.get("relationship_type", "related") for c in complementary)) if complementary else []
                        }
                    },
                    "isError": False,
                },
            )

        except Exception as e:
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
                project_ids=params.get("project_ids")
            )
            
            logger.info(f"Document clustering completed successfully")

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_document_clusters(clustering_results),
                        }
                    ],
                    "structuredContent": clustering_results,
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error clustering documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal server error"},
            ) 