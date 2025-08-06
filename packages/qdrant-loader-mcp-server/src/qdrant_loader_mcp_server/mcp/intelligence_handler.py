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
                            # Extract document IDs for lazy loading
                            doc1_id = doc1.get("document_id") or f"{doc1.get('source_type', 'unknown')}:{doc1.get('source_title', 'unknown')}"
                            doc2_id = doc2.get("document_id") or f"{doc2.get('source_type', 'unknown')}:{doc2.get('source_title', 'unknown')}"
                            
                            # Extract titles for preview (truncated)
                            doc1_title = doc1.get("title", doc1.get("source_title", "Unknown"))[:100]
                            doc2_title = doc2.get("title", doc2.get("source_title", "Unknown"))[:100]
                            
                            relationships.append({
                                "document_1_id": doc1_id,
                                "document_2_id": doc2_id,
                                "document_1_title": doc1_title,
                                "document_2_title": doc2_title,
                                "relationship_type": "similarity",
                                "confidence_score": cluster.get("cohesion_score", 0.8),
                                "relationship_summary": f"Both documents belong to cluster: {cluster.get('theme', 'unnamed cluster')}"
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
                            
                            # Extract document IDs if available
                            doc1_id = doc1.get("document_id") if isinstance(doc1, dict) else str(doc1)
                            doc2_id = doc2.get("document_id") if isinstance(doc2, dict) else str(doc2)
                            doc1_title = doc1.get("title", str(doc1))[:100] if isinstance(doc1, dict) else str(doc1)[:100]
                            doc2_title = doc2.get("title", str(doc2))[:100] if isinstance(doc2, dict) else str(doc2)[:100]
                            
                            relationships.append({
                                "document_1_id": doc1_id,
                                "document_2_id": doc2_id,
                                "document_1_title": doc1_title,
                                "document_2_title": doc2_title,
                                "relationship_type": "conflict",
                                "confidence_score": conflict_info.get("severity", 0.5),
                                "relationship_summary": f"Conflict detected: {conflict_info.get('type', 'unknown conflict')}"
                            })
                            
            # Extract complementary relationships
            if "complementary_content" in analysis_results:
                complementary = analysis_results["complementary_content"]
                comp_count = 0
                for doc_id, complementary_content in complementary.items():
                    # Handle ComplementaryContent object properly - no limit on recommendations
                    if hasattr(complementary_content, 'get_top_recommendations'):
                        recommendations = complementary_content.get_top_recommendations()  # Return all recommendations
                    else:
                        recommendations = complementary_content if isinstance(complementary_content, list) else []
                    
                    for rec in recommendations:
                        if isinstance(rec, dict):
                            # Use proper field names from ComplementaryContent.get_top_recommendations()
                            target_doc_id = rec.get("document_id", "Unknown")
                            score = rec.get("relevance_score", 0.5)
                            reason = rec.get("recommendation_reason", "complementary content")
                            
                            # Extract titles for preview
                            doc1_title = str(doc_id)[:100]
                            doc2_title = rec.get("title", str(target_doc_id))[:100]
                            
                            relationships.append({
                                "document_1_id": doc_id,
                                "document_2_id": target_doc_id,
                                "document_1_title": doc1_title,
                                "document_2_title": doc2_title,
                                "relationship_type": "complementary",
                                "confidence_score": score,
                                "relationship_summary": f"Complementary content: {reason}"
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
                                # 🔥 Use actual document_id from HybridSearchResult
                                "document_id": comp_doc.get("document", {}).document_id or f"comp_{i}",
                                "title": comp_doc.get("document", {}).get_display_title() if hasattr(comp_doc.get("document", {}), "get_display_title") else getattr(comp_doc.get("document", {}), "source_title", ""),
                                "content_preview": getattr(comp_doc.get("document", {}), "text", "")[:200] or "",
                                "complementary_score": comp_doc.get("relevance_score", 0.0),
                                "complementary_reason": comp_doc.get("recommendation_reason", "Complementary content found"),
                                "relationship_type": comp_doc.get("strategy", "related"),
                                "source_type": getattr(comp_doc.get("document", {}), "source_type", "") or "",
                                # 🔥 Root level fields (matching our search structure)
                                "url": getattr(comp_doc.get("document", {}), "source_url", "") or "",
                                "created_at": getattr(comp_doc.get("document", {}), "created_at", "") or "",
                                "updated_at": getattr(comp_doc.get("document", {}), "last_modified", "") or "",
                                "metadata": {
                                    "project_id": getattr(comp_doc.get("document", {}), "project_id", "") or "",
                                    "project_name": getattr(comp_doc.get("document", {}), "project_name", "") or "",
                                    "file_path": getattr(comp_doc.get("document", {}), "file_path", "") or "",
                                    "file_type": getattr(comp_doc.get("document", {}), "file_type", "") or "",
                                    "file_size": getattr(comp_doc.get("document", {}), "file_size", None),
                                    "word_count": getattr(comp_doc.get("document", {}), "word_count", None),
                                    "chunk_info": getattr(comp_doc.get("document", {}), "chunk_info", "") or ""
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

            # Transform clustering results to match MCP schema
            mcp_clusters = []
            clusters = clustering_results.get("clusters", [])
            
            for i, cluster in enumerate(clusters):
                # Transform documents to match schema
                mcp_documents = []
                cluster_docs = cluster.get("documents", [])
                
                for j, doc in enumerate(cluster_docs):
                    if hasattr(doc, 'source_title'):
                        # Handle SearchResult objects - use proper fields
                        # Create a proper document ID from available data
                        doc_id = (
                            doc.parent_document_id or  # For attachments
                            f"{doc.source_type}:{doc.source_title}" or  # Fallback composite ID
                            f"doc_{j}"  # Last resort
                        )
                        
                        # Smart title extraction with multiple fallbacks
                        title = (
                            doc.source_title or 
                            doc.parent_document_title or 
                            doc.section_title or 
                            doc.parent_title or 
                            doc.original_filename or
                            (doc.text.split('\n')[0][:50] + "..." if doc.text and len(doc.text.split('\n')[0]) > 50 else doc.text.split('\n')[0] if doc.text else None) or
                            "Untitled"
                        )
                        
                        mcp_doc = {
                            "document_id": doc_id,
                            "title": title,
                            "content_preview": (doc.text[:200] + "...") if len(doc.text) > 200 else doc.text,
                            "source_type": doc.source_type,
                            "cluster_relevance": 1.0
                        }
                    elif isinstance(doc, dict):
                        # Handle dict objects with smart title extraction
                        title = (
                            doc.get("title") or 
                            doc.get("source_title") or 
                            doc.get("parent_document_title") or 
                            doc.get("section_title") or 
                            doc.get("parent_title") or 
                            doc.get("original_filename") or
                            (doc.get("text", "").split('\n')[0][:50] + "..." if doc.get("text") and len(doc.get("text", "").split('\n')[0]) > 50 else doc.get("text", "").split('\n')[0] if doc.get("text") else None) or
                            "Untitled"
                        )
                        
                        mcp_doc = {
                            "document_id": doc.get("document_id", f"doc_{j}"),
                            "title": title,
                            "content_preview": doc.get("content_preview", doc.get("text", "")[:200]),
                            "source_type": doc.get("source_type", "unknown"),
                            "cluster_relevance": doc.get("cluster_relevance", 1.0)
                        }
                    else:
                        # Fallback for unknown formats
                        mcp_doc = {
                            "document_id": f"doc_{j}",
                            "title": str(doc),
                            "content_preview": "",
                            "source_type": "unknown",
                            "cluster_relevance": 1.0
                        }
                    mcp_documents.append(mcp_doc)
                
                mcp_cluster = {
                    "cluster_id": f"cluster_{i}",
                    "cluster_name": cluster.get("name", f"Cluster {i+1}"),
                    "cluster_theme": cluster.get("theme", f"Theme {i+1}"),
                    "document_count": len(mcp_documents),
                    "cohesion_score": cluster.get("cohesion_score", 0.8),
                    "documents": mcp_documents,
                    "cluster_keywords": cluster.get("keywords", []),
                    "cluster_summary": cluster.get("summary", f"Cluster of {len(mcp_documents)} documents")
                }
                mcp_clusters.append(mcp_cluster)
            
            # Create metadata
            metadata = clustering_results.get("clustering_metadata", {})
            mcp_clustering_results = {
                "clusters": mcp_clusters,
                "clustering_metadata": {
                    "total_documents": metadata.get("total_documents", sum(len(c["documents"]) for c in mcp_clusters)),
                    "clusters_created": len(mcp_clusters),
                    "strategy_used": params.get("strategy", "mixed_features"),
                    "unclustered_documents": metadata.get("unclustered_documents", 0),
                    "clustering_quality": metadata.get("clustering_quality", 0.0),
                    "processing_time_ms": metadata.get("processing_time_ms", 0.0)
                },
                "cluster_relationships": clustering_results.get("cluster_relationships", [])[:3]
            }

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": self.formatters.format_document_clusters(clustering_results),
                        }
                    ],
                    "structuredContent": mcp_clustering_results,
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error clustering documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal server error"},
            ) 