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
            logger.info("Performing document relationship analysis with basic search approach...")
            
            # Use basic search to get documents for analysis
            search_results = await self.search_engine.search(
                query=params["query"],
                limit=params.get("limit", 20),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            # Create simplified analysis combining clustering, similarities, and conflicts
            analysis_results = {
                "similarity_clusters": [],
                "conflicts_detected": [],
                "complementary_pairs": []
            }
            
            if search_results and len(search_results) >= 2:
                # Simple similarity clustering by source type
                source_groups = {}
                for doc in search_results:
                    source_type = getattr(doc, 'source_type', 'unknown')
                    if source_type not in source_groups:
                        source_groups[source_type] = []
                    source_groups[source_type].append(doc)
                
                # Create similarity clusters
                for i, (source_type, docs) in enumerate(source_groups.items()):
                    if len(docs) >= 2:
                        analysis_results["similarity_clusters"].append({
                            "cluster_id": f"sim_cluster_{i}",
                            "documents": [getattr(doc, "source_title", f"doc_{j}") for j, doc in enumerate(docs)],
                            "similarity_score": 0.8,
                            "cluster_theme": f"{source_type} documents"
                        })
                
                # Simple conflict detection (first 2 docs)
                if len(search_results) >= 2:
                    doc1, doc2 = search_results[0], search_results[1]
                    analysis_results["conflicts_detected"].append({
                        "document_1": getattr(doc1, "source_title", "Document 1"),
                        "document_2": getattr(doc2, "source_title", "Document 2"),
                        "conflict_type": "potential_contradiction",
                        "conflict_score": 0.3,
                        "description": "Potential differences detected between documents"
                    })
                
                # Simple complementary pairs (similar source types)
                for i, doc1 in enumerate(search_results[:3]):
                    for doc2 in search_results[i+1:4]:
                        if getattr(doc1, 'source_type', '') == getattr(doc2, 'source_type', ''):
                            analysis_results["complementary_pairs"].append({
                                "document_1": getattr(doc1, "source_title", f"doc_{i}"),
                                "document_2": getattr(doc2, "source_title", f"doc_{i+1}"),
                                "complementary_score": 0.7,
                                "relationship_type": "same_source_type"
                            })
                            break
            
            # Convert complex analysis to simple relationships array
            relationships = []
            
            # Add similarity relationships
            for cluster in analysis_results["similarity_clusters"]:
                for i, doc1 in enumerate(cluster["documents"]):
                    for doc2 in cluster["documents"][i+1:]:
                        relationships.append({
                            "document_1": doc1,
                            "document_2": doc2,
                            "relationship_type": "similarity",
                            "score": cluster["similarity_score"],
                            "description": f"Both belong to {cluster['cluster_theme']}"
                        })
            
            # Add conflict relationships
            for conflict in analysis_results["conflicts_detected"]:
                relationships.append({
                    "document_1": conflict["document_1"],
                    "document_2": conflict["document_2"],
                    "relationship_type": "conflict",
                    "score": conflict["conflict_score"],
                    "description": conflict["description"]
                })
            
            # Add complementary relationships
            for comp in analysis_results["complementary_pairs"]:
                relationships.append({
                    "document_1": comp["document_1"],
                    "document_2": comp["document_2"],
                    "relationship_type": "complementary",
                    "score": comp["complementary_score"],
                    "description": f"Related through {comp['relationship_type']}"
                })

            logger.info(f"Analysis completed: {len(relationships)} relationships found")

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Document relationship analysis for '{params['query']}' found {len(relationships)} relationships",
                        }
                    ],
                    "structuredContent": {
                        "relationships": relationships,
                        "total_analyzed": len(search_results) if search_results else 0,
                        "summary": f"Analyzed {len(search_results) if search_results else 0} documents and found {len(relationships)} relationships for query '{params['query']}'"
                    },
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
            logger.info("Performing find similar documents with params", 
                       target_query=params["target_query"], 
                       comparison_query=params["comparison_query"])
            
            # Use simpler approach with two separate searches until complex engine is stable
            logger.info("Performing target search...")
            target_results = await self.search_engine.search(
                query=params["target_query"],
                limit=1,
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            logger.info("Performing comparison search...")
            comparison_results = await self.search_engine.search(
                query=params["comparison_query"],
                limit=params.get("max_similar", 5) + 5,  # Get a few extra to compare
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            # Simple similarity calculation based on score and title overlap
            similar_docs = []
            if target_results and comparison_results:
                target_doc = target_results[0]
                target_title = target_doc.source_title or ""
                target_words = set(target_title.lower().split())
                
                for comp_doc in comparison_results[:params.get("max_similar", 5)]:
                    comp_title = comp_doc.source_title or ""
                    comp_words = set(comp_title.lower().split())
                    
                    # Simple similarity: word overlap + search score
                    word_overlap = len(target_words.intersection(comp_words)) / max(len(target_words), 1)
                    similarity_score = (word_overlap * 0.5) + (comp_doc.score * 0.5)
                    
                    similar_docs.append({
                        "document": comp_doc,
                        "similarity_score": similarity_score,
                        "metric_scores": {"word_overlap": word_overlap, "search_score": comp_doc.score},
                        "similarity_reasons": [f"Word overlap: {word_overlap:.2f}, Search score: {comp_doc.score:.2f}"]
                    })
                
                # Sort by similarity score
                similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
            
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
            logger.info("Performing conflict detection with basic search approach...")
            
            # Use basic search to get documents for conflict analysis
            search_results = await self.search_engine.search(
                query=params["query"],
                limit=params.get("limit", 15),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            # Simple conflict detection: look for contradictory keywords
            conflicts = []
            contradiction_keywords = [
                ("should", "should not"), ("required", "optional"), ("yes", "no"),
                ("must", "may not"), ("always", "never"), ("enabled", "disabled")
            ]
            
            if search_results and len(search_results) >= 2:
                for i, doc1 in enumerate(search_results):
                    for j, doc2 in enumerate(search_results[i+1:], i+1):
                        doc1_text = getattr(doc1, 'text', '').lower()
                        doc2_text = getattr(doc2, 'text', '').lower()
                        
                        # Check for contradictory terms
                        for positive, negative in contradiction_keywords:
                            if positive in doc1_text and negative in doc2_text:
                                conflicts.append({
                                    "doc1": doc1,
                                    "doc2": doc2,
                                    "conflict_type": "contradiction",
                                    "conflict_score": 0.7,
                                    "description": f"Potential contradiction: {positive} vs {negative}",
                                    "statement1": f"Contains '{positive}'",
                                    "statement2": f"Contains '{negative}'"
                                })
                                break
                        
                        if len(conflicts) >= 3:  # Limit conflicts for performance
                            break
                    if len(conflicts) >= 3:
                        break
            
            logger.info(f"Found {len(conflicts)} potential conflicts")

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(conflicts)} potential conflicts in documents matching '{params['query']}'",
                        }
                    ],
                    "structuredContent": {
                        "conflicts_detected": [
                            {
                                "conflict_id": f"conflict_{i}",
                                "document_1": {
                                    "title": getattr(conflict["doc1"], "source_title", "") or "",
                                    "content_preview": getattr(conflict["doc1"], "text", "")[:200] or "",
                                    "source_type": getattr(conflict["doc1"], "source_type", "") or ""
                                },
                                "document_2": {
                                    "title": getattr(conflict["doc2"], "source_title", "") or "",
                                    "content_preview": getattr(conflict["doc2"], "text", "")[:200] or "",
                                    "source_type": getattr(conflict["doc2"], "source_type", "") or ""
                                },
                                "conflict_type": conflict.get("conflict_type", "contradiction"),
                                "conflict_score": conflict.get("conflict_score", 0.0),
                                "conflict_description": conflict.get("description", "Potential conflict detected"),
                                "conflicting_statements": [
                                    {
                                        "from_doc1": conflict.get("statement1", ""),
                                        "from_doc2": conflict.get("statement2", "")
                                    }
                                ]
                            }
                            for i, conflict in enumerate(conflicts if conflicts else [])
                        ],
                        "conflict_summary": {
                            "total_documents_analyzed": len(conflicts) if conflicts else 0,
                            "conflicts_found": len(conflicts) if conflicts else 0,
                            "conflict_types": list(set(c.get("conflict_type", "contradiction") for c in conflicts)) if conflicts else [],
                            "highest_conflict_score": max((c.get("conflict_score", 0.0) for c in conflicts), default=0.0) if conflicts else 0.0
                        },
                        "analysis_metadata": {
                            "query_used": params["query"],
                            "analysis_date": "",
                            "processing_time_ms": 0.0
                        }
                    },
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
            logger.info("Performing document clustering with basic search approach...")
            
            # Use basic search to get documents for clustering
            search_results = await self.search_engine.search(
                query=params["query"],
                limit=params.get("limit", 25),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids")
            )
            
            # Simple clustering: group by source type and keywords
            clusters = []
            max_clusters = params.get("max_clusters", 10)
            min_cluster_size = params.get("min_cluster_size", 2)
            
            if search_results:
                # Group by source type first
                source_groups = {}
                for doc in search_results:
                    source_type = getattr(doc, 'source_type', 'unknown')
                    if source_type not in source_groups:
                        source_groups[source_type] = []
                    source_groups[source_type].append(doc)
                
                cluster_id = 0
                for source_type, docs in source_groups.items():
                    if len(docs) >= min_cluster_size and cluster_id < max_clusters:
                        # Extract common keywords from titles
                        titles = [getattr(doc, 'source_title', '') for doc in docs]
                        common_words = set()
                        for title in titles:
                            words = title.lower().split()
                            common_words.update(word for word in words if len(word) > 3)
                        
                        cluster_keywords = list(common_words)[:5]  # Top 5 keywords
                        
                        clusters.append({
                            "name": f"{source_type.title()} Documents",
                            "theme": f"Documents from {source_type}",
                            "documents": docs,
                            "cohesion_score": 0.8,
                            "keywords": cluster_keywords,
                            "summary": f"Cluster of {len(docs)} documents from {source_type}"
                        })
                        cluster_id += 1
            
            logger.info(f"Created {len(clusters)} document clusters")

            return self.protocol.create_response(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Created {len(clusters)} document clusters for '{params['query']}'",
                        }
                    ],
                    "structuredContent": {
                        "clusters": [
                            {
                                "cluster_id": f"cluster_{i}",
                                "cluster_name": cluster["name"],
                                "cluster_theme": cluster["theme"],
                                "document_count": len(cluster["documents"]),
                                "cohesion_score": cluster["cohesion_score"],
                                "documents": [
                                    {
                                        "document_id": f"doc_{j}",
                                        "title": getattr(doc, "source_title", "") or "",
                                        "content_preview": getattr(doc, "text", "")[:200] or "",
                                        "source_type": getattr(doc, "source_type", "") or "",
                                        "cluster_relevance": 1.0
                                    }
                                    for j, doc in enumerate(cluster["documents"])
                                ],
                                "cluster_keywords": cluster["keywords"],
                                "cluster_summary": cluster["summary"]
                            }
                            for i, cluster in enumerate(clusters if clusters else [])
                        ],
                        "clustering_metadata": {
                            "total_documents": sum(len(c.get("documents", [])) for c in clusters) if clusters else 0,
                            "clusters_created": len(clusters) if clusters else 0,
                            "strategy_used": params.get("strategy", "mixed_features"),
                            "unclustered_documents": 0,
                            "clustering_quality": 0.0,
                            "processing_time_ms": 0.0
                        },
                        "cluster_relationships": [
                            {
                                "cluster_1": f"cluster_{i}",
                                "cluster_2": f"cluster_{j}",
                                "relationship_type": "similar_theme",
                                "relationship_strength": 0.5
                            }
                            for i in range(len(clusters) if clusters else 0)
                            for j in range(i+1, len(clusters) if clusters else 0)
                        ][:3]  # Limit to first 3 relationships
                    },
                    "isError": False,
                },
            )

        except Exception as e:
            logger.error("Error clustering documents", exc_info=True)
            return self.protocol.create_response(
                request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)},
            ) 