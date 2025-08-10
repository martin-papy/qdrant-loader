"""Cross-document intelligence operations handler for MCP server."""

import hashlib
import json
from typing import Any
import math

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

    def _get_or_create_document_id(self, doc: Any) -> str:
        """Return a stable, collision-resistant document id.

        Supports both dict-like and object-like inputs (e.g., HybridSearchResult).

        Preference order:
        1) Existing `document_id`
        2) Fallback composed of sanitized `source_type` + sanitized `source_title` + short content hash

        The hash is computed deterministically from a subset of stable attributes.
        """
        # Helper to access fields on dict or object safely
        def get_field(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Prefer explicit id if present and non-empty
        explicit_id = get_field(doc, "document_id", None)
        if explicit_id:
            return explicit_id

        # Extract core fields with sensible defaults
        raw_source_type = get_field(doc, "source_type", "unknown")
        raw_source_title = get_field(doc, "source_title", "unknown")

        # Sanitize to avoid ambiguity with colon-separated ID format
        source_type = str(raw_source_type or "unknown").replace(":", "-")
        source_title = str(raw_source_title or "unknown").replace(":", "-")

        # Collect commonly available distinguishing attributes
        candidate_fields = {
            "title": get_field(doc, "title", None),
            "source_type": source_type,
            "source_title": source_title,
            "source_url": get_field(doc, "source_url", None),
            "file_path": get_field(doc, "file_path", None),
            "repo_name": get_field(doc, "repo_name", None),
            "parent_id": get_field(doc, "parent_id", None),
            "original_filename": get_field(doc, "original_filename", None),
            "id": get_field(doc, "id", None),
        }

        # Deterministic JSON for hashing
        payload = json.dumps(
            {k: v for k, v in candidate_fields.items() if v is not None},
            sort_keys=True,
            ensure_ascii=False,
        )
        short_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]

        return f"{source_type}:{source_title}:{short_hash}"

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
            relationships = []
            summary_parts = []
            total_analyzed = analysis_results.get("query_metadata", {}).get(
                "document_count", 0
            )

            # Extract relationships from document clusters
            if "document_clusters" in analysis_results:
                clusters = analysis_results["document_clusters"]
                summary_parts.append(f"{len(clusters)} document clusters found")

                for cluster in clusters:
                    cluster_docs = cluster.get("documents", [])

                    # Limit emitted similarity pairs per cluster to reduce O(N^2) growth
                    # Determine max pairs (default 50) and compute number of docs to consider (M)
                    max_pairs: int = params.get("max_similarity_pairs_per_cluster", 50)

                    def _doc_score(d: Any) -> float:
                        try:
                            if isinstance(d, dict):
                                return float(
                                    d.get("score")
                                    or d.get("similarity")
                                    or d.get("relevance")
                                    or 0.0
                                )
                            # Object-like (e.g., HybridSearchResult)
                            return float(
                                getattr(d, "score", None)
                                or getattr(d, "similarity", None)
                                or getattr(d, "relevance", None)
                                or 0.0
                            )
                        except Exception:
                            return 0.0

                    # Sort docs by an available score descending to approximate top-K relevance
                    try:
                        sorted_docs = sorted(cluster_docs, key=_doc_score, reverse=True)
                    except Exception:
                        sorted_docs = list(cluster_docs)

                    # Compute M so that M*(M-1)/2 <= max_pairs
                    if max_pairs is None or max_pairs <= 0:
                        max_pairs = 0
                    if max_pairs == 0:
                        # Skip emitting similarity pairs for this cluster
                        continue

                    max_docs = int((1 + math.isqrt(1 + 8 * max_pairs)) // 2)
                    max_docs = max(2, max_docs)  # need at least one pair if any
                    docs_for_pairs = sorted_docs[:max_docs]

                    emitted_pairs = 0
                    for i, doc1 in enumerate(docs_for_pairs):
                        for doc2 in docs_for_pairs[i + 1 :]:
                            if emitted_pairs >= max_pairs:
                                break

                            # Extract stable document IDs using unified helper for any input type
                            doc1_id = self._get_or_create_document_id(doc1)
                            doc2_id = self._get_or_create_document_id(doc2)

                            # Extract titles for preview (truncated)
                            if isinstance(doc1, dict):
                                doc1_title = (
                                    doc1.get("title")
                                    or doc1.get("source_title")
                                    or "Unknown"
                                )[:100]
                            else:
                                doc1_title = str(getattr(doc1, "source_title", doc1))[:100]

                            if isinstance(doc2, dict):
                                doc2_title = (
                                    doc2.get("title")
                                    or doc2.get("source_title")
                                    or "Unknown"
                                )[:100]
                            else:
                                doc2_title = str(getattr(doc2, "source_title", doc2))[:100]

                            relationships.append(
                                {
                                    "document_1_id": doc1_id,
                                    "document_2_id": doc2_id,
                                    "document_1_title": doc1_title,
                                    "document_2_title": doc2_title,
                                    "relationship_type": "similarity",
                                    "confidence_score": cluster.get(
                                        "cohesion_score", 0.8
                                    ),
                                    "relationship_summary": f"Both documents belong to cluster: {cluster.get('theme', 'unnamed cluster')}",
                                }
                            )
                            emitted_pairs += 1

            # Extract conflict relationships
            if "conflict_analysis" in analysis_results:
                conflicts = analysis_results["conflict_analysis"].get(
                    "conflicting_pairs", []
                )
                if conflicts:
                    summary_parts.append(f"{len(conflicts)} conflicts detected")
                    for conflict in conflicts:
                        if isinstance(conflict, (list, tuple)) and len(conflict) >= 2:
                            doc1, doc2 = conflict[0], conflict[1]
                            conflict_info = conflict[2] if len(conflict) > 2 else {}

                            # Extract stable document IDs using unified helper for any input type
                            doc1_id = self._get_or_create_document_id(doc1)
                            doc2_id = self._get_or_create_document_id(doc2)
                            # Extract titles for preview (prefer title/source_title attributes)
                            def _display_title(d: Any) -> str:
                                if isinstance(d, dict):
                                    return (d.get("title") or d.get("source_title") or str(d))[:100]
                                return (getattr(d, "source_title", None) or getattr(d, "title", None) or str(d))[:100]

                            doc1_title = _display_title(doc1)
                            doc2_title = _display_title(doc2)

                            relationships.append(
                                {
                                    "document_1_id": doc1_id,
                                    "document_2_id": doc2_id,
                                    "document_1_title": doc1_title,
                                    "document_2_title": doc2_title,
                                    "relationship_type": "conflict",
                                    "confidence_score": conflict_info.get(
                                        "severity", 0.5
                                    ),
                                    "relationship_summary": f"Conflict detected: {conflict_info.get('type', 'unknown conflict')}",
                                }
                            )

            # Extract complementary relationships
            if "complementary_content" in analysis_results:
                complementary = analysis_results["complementary_content"]
                comp_count = 0
                for doc_id, complementary_content in complementary.items():
                    # Handle ComplementaryContent object properly - no limit on recommendations
                    if hasattr(complementary_content, "get_top_recommendations"):
                        recommendations = (
                            complementary_content.get_top_recommendations()
                        )  # Return all recommendations
                    else:
                        recommendations = (
                            complementary_content
                            if isinstance(complementary_content, list)
                            else []
                        )

                    for rec in recommendations:
                        if isinstance(rec, dict):
                            # Use proper field names from ComplementaryContent.get_top_recommendations()
                            target_doc_id = rec.get("document_id", "Unknown")
                            score = rec.get("relevance_score", 0.5)
                            reason = rec.get(
                                "recommendation_reason", "complementary content"
                            )

                            # Extract titles for preview
                            doc1_title = str(doc_id)[:100]
                            doc2_title = rec.get("title", str(target_doc_id))[:100]

                            relationships.append(
                                {
                                    "document_1_id": doc_id,
                                    "document_2_id": target_doc_id,
                                    "document_1_title": doc1_title,
                                    "document_2_title": doc2_title,
                                    "relationship_type": "complementary",
                                    "confidence_score": score,
                                    "relationship_summary": f"Complementary content: {reason}",
                                }
                            )
                            comp_count += 1
                if comp_count > 0:
                    summary_parts.append(f"{comp_count} complementary relationships")

            # Extract citation relationships
            if "citation_network" in analysis_results:
                citation_net = analysis_results["citation_network"]
                if citation_net.get("edges", 0) > 0:
                    summary_parts.append(
                        f"{citation_net['edges']} citation relationships"
                    )

            if "similarity_insights" in analysis_results:
                insights = analysis_results["similarity_insights"]
                if insights:
                    summary_parts.append("similarity patterns identified")

            # Create a simple summary string
            if summary_parts:
                summary_text = (
                    f"Analyzed {total_analyzed} documents: {', '.join(summary_parts)}"
                )
            else:
                summary_text = f"Analyzed {total_analyzed} documents with no significant relationships found"

            # Format according to MCP schema
            mcp_result = {
                "relationships": relationships,
                "total_analyzed": total_analyzed,
                "summary": summary_text,
            }

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
            conflict_results = await self.search_engine.detect_document_conflicts(
                query=params["query"],
                limit=params.get("limit", 15),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            logger.info("Conflict detection completed successfully")

            # Create lightweight structured content for MCP compliance
            original_documents = conflict_results.get("original_documents", [])
            structured_content = self.formatters.create_lightweight_conflict_results(
                conflict_results, params["query"], original_documents
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
