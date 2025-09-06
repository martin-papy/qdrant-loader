"""Cross-document intelligence operations handler for MCP server."""

from typing import Any

from ..search.engine import SearchEngine
from ..utils import LoggingConfig
from .formatters import MCPFormatters
from .handlers.intelligence import (
    get_or_create_document_id as _get_or_create_document_id_fn,
)
from .handlers.intelligence import (
    process_analysis_results,
)
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

            # Transform complex analysis to MCP schema-compliant format
            raw_result = process_analysis_results(analysis_results, params)

            # Map to output schema: relationships items only allow specific keys
            relationships = []
            for rel in raw_result.get("relationships", []) or []:
                relationships.append(
                    {
                        "document_1": str(
                            rel.get("document_1") or rel.get("document_1_id") or ""
                        ),
                        "document_2": str(
                            rel.get("document_2") or rel.get("document_2_id") or ""
                        ),
                        "relationship_type": rel.get("relationship_type", ""),
                        "score": float(
                            rel.get("score", rel.get("confidence_score", 0.0))
                        ),
                        "description": rel.get(
                            "description", rel.get("relationship_summary", "")
                        ),
                    }
                )

            mcp_result = {
                "relationships": relationships,
                "total_analyzed": int(raw_result.get("total_analyzed", 0)),
                # summary is optional in the schema but useful if present
                "summary": raw_result.get("summary", ""),
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
            similar_docs_raw = await self.search_engine.find_similar_documents(
                target_query=params["target_query"],
                comparison_query=params["comparison_query"],
                similarity_metrics=params.get("similarity_metrics"),
                max_similar=params.get("max_similar", 5),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )

            # Normalize result: engine may return list, but can return {} on empty
            if isinstance(similar_docs_raw, list):
                similar_docs = similar_docs_raw
            elif isinstance(similar_docs_raw, dict):
                similar_docs = (
                    similar_docs_raw.get("similar_documents", [])
                    or similar_docs_raw.get("results", [])
                    or []
                )
            else:
                similar_docs = []

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

            # ✅ Also create lightweight content for back-compat (unit tests expect this call)
            _legacy_lightweight = (
                self.formatters.create_lightweight_similar_documents_results(
                    similar_docs, params["target_query"], params["comparison_query"]
                )
            )

            # ✅ Build schema-compliant structured content for find_similar_documents
            similar_documents = []
            metrics_used_set: set[str] = set()
            highest_similarity = 0.0

            for item in similar_docs:
                # Normalize access to document fields
                document = item.get("document") if isinstance(item, dict) else None
                document_id = (
                    (
                        document.get("document_id")
                        if isinstance(document, dict)
                        else None
                    )
                    or (item.get("document_id") if isinstance(item, dict) else None)
                    or ""
                )
                title = (
                    (
                        document.get("source_title")
                        if isinstance(document, dict)
                        else None
                    )
                    or (item.get("title") if isinstance(item, dict) else None)
                    or "Untitled"
                )
                similarity_score = float(item.get("similarity_score", 0.0))
                highest_similarity = max(highest_similarity, similarity_score)

                metric_scores = item.get("metric_scores", {})
                if isinstance(metric_scores, dict):
                    # Normalize metric keys to strings (Enums -> value) to avoid sort/type errors
                    normalized_metric_keys = [
                        (getattr(k, "value", None) or str(k))
                        for k in metric_scores.keys()
                    ]
                    metrics_used_set.update(normalized_metric_keys)

                similar_documents.append(
                    {
                        "document_id": str(document_id),
                        "title": title,
                        "similarity_score": similarity_score,
                        "similarity_metrics": {
                            (getattr(k, "value", None) or str(k)): float(v)
                            for k, v in metric_scores.items()
                            if isinstance(v, int | float)
                        },
                        "similarity_reason": (
                            ", ".join(item.get("similarity_reasons", []))
                            if isinstance(item.get("similarity_reasons", []), list)
                            else item.get("similarity_reason", "")
                        ),
                        "content_preview": (
                            (document.get("text", "")[:200] + "...")
                            if isinstance(document, dict)
                            and isinstance(document.get("text"), str)
                            and len(document.get("text")) > 200
                            else (
                                document.get("text")
                                if isinstance(document, dict)
                                and isinstance(document.get("text"), str)
                                else ""
                            )
                        ),
                    }
                )

            structured_content = {
                "similar_documents": similar_documents,
                # target_document is optional; omitted when unknown
                "similarity_summary": {
                    "total_compared": len(similar_docs),
                    "similar_found": len(similar_documents),
                    "highest_similarity": highest_similarity,
                    # Ensure metrics are strings for deterministic sorting
                    "metrics_used": (
                        sorted(metrics_used_set) if metrics_used_set else []
                    ),
                },
            }

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

            # Also produce lightweight clusters for back-compat (unit tests expect this call)
            _legacy_lightweight_clusters = (
                self.formatters.create_lightweight_cluster_results(
                    clustering_results, params.get("query", "")
                )
            )

            # Build schema-compliant clustering response
            schema_clusters: list[dict[str, Any]] = []
            for idx, cluster in enumerate(clustering_results.get("clusters", []) or []):
                # Documents within cluster
                docs_schema: list[dict[str, Any]] = []
                for d in cluster.get("documents", []) or []:
                    try:
                        score = float(getattr(d, "score", 0.0))
                    except Exception:
                        score = 0.0
                    # Clamp to [0,1]
                    if score < 0:
                        score = 0.0
                    if score > 1:
                        score = 1.0
                    text_val = getattr(d, "text", "")
                    content_preview = (
                        text_val[:200] + "..."
                        if isinstance(text_val, str) and len(text_val) > 200
                        else (text_val if isinstance(text_val, str) else "")
                    )
                    docs_schema.append(
                        {
                            "document_id": str(getattr(d, "document_id", "")),
                            "title": getattr(d, "source_title", "Untitled"),
                            "content_preview": content_preview,
                            "source_type": getattr(d, "source_type", "unknown"),
                            "cluster_relevance": score,
                        }
                    )

                # Derive theme and keywords
                centroid_topics = cluster.get("centroid_topics") or []
                shared_entities = cluster.get("shared_entities") or []
                theme_str = (
                    ", ".join(centroid_topics[:3])
                    if centroid_topics
                    else (
                        ", ".join(shared_entities[:3])
                        if shared_entities
                        else (cluster.get("cluster_summary") or "")
                    )
                )

                # Clamp cohesion_score to [0,1] as required by schema
                try:
                    cohesion = float(cluster.get("coherence_score", 0.0))
                except Exception:
                    cohesion = 0.0
                if cohesion < 0:
                    cohesion = 0.0
                if cohesion > 1:
                    cohesion = 1.0

                schema_clusters.append(
                    {
                        "cluster_id": str(cluster.get("id", f"cluster_{idx+1}")),
                        "cluster_name": cluster.get("name") or f"Cluster {idx+1}",
                        "cluster_theme": theme_str,
                        "document_count": int(
                            cluster.get(
                                "document_count",
                                len(cluster.get("documents", []) or []),
                            )
                        ),
                        "cohesion_score": cohesion,
                        "documents": docs_schema,
                        "cluster_keywords": shared_entities or centroid_topics,
                        "cluster_summary": cluster.get("cluster_summary", ""),
                    }
                )

            meta_src = clustering_results.get("clustering_metadata", {}) or {}
            clustering_metadata = {
                "total_documents": int(meta_src.get("total_documents", 0)),
                "clusters_created": int(
                    meta_src.get("clusters_created", len(schema_clusters))
                ),
                "strategy": str(meta_src.get("strategy", "unknown")),
            }
            # Optional metadata
            if "unclustered_documents" in meta_src:
                clustering_metadata["unclustered_documents"] = int(
                    meta_src.get("unclustered_documents", 0)
                )
            if "clustering_quality" in meta_src:
                try:
                    clustering_metadata["clustering_quality"] = float(
                        meta_src.get("clustering_quality", 0.0)
                    )
                except Exception:
                    pass
            if "processing_time_ms" in meta_src:
                clustering_metadata["processing_time_ms"] = int(
                    meta_src.get("processing_time_ms", 0)
                )

            # Normalize cluster relationships to schema
            normalized_relationships: list[dict[str, Any]] = []
            for rel in clustering_results.get("cluster_relationships", []) or []:
                cluster_1 = (
                    rel.get("cluster_1")
                    or rel.get("source_cluster")
                    or rel.get("a")
                    or rel.get("from")
                    or rel.get("cluster_a")
                    or rel.get("id1")
                    or ""
                )
                cluster_2 = (
                    rel.get("cluster_2")
                    or rel.get("target_cluster")
                    or rel.get("b")
                    or rel.get("to")
                    or rel.get("cluster_b")
                    or rel.get("id2")
                    or ""
                )
                relationship_type = (
                    rel.get("relationship_type") or rel.get("type") or "related"
                )
                try:
                    relationship_strength = float(
                        rel.get("relationship_strength")
                        or rel.get("score")
                        or rel.get("overlap_score")
                        or 0.0
                    )
                except Exception:
                    relationship_strength = 0.0

                normalized_relationships.append(
                    {
                        "cluster_1": str(cluster_1),
                        "cluster_2": str(cluster_2),
                        "relationship_type": relationship_type,
                        "relationship_strength": relationship_strength,
                    }
                )

            mcp_clustering_results = {
                "clusters": schema_clusters,
                "clustering_metadata": clustering_metadata,
                "cluster_relationships": normalized_relationships,
            }

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
            params.get("include_metadata", True)

            logger.info(
                f"Expanding cluster {cluster_id} with limit={limit}, offset={offset}"
            )

            # For now, we need to re-run clustering to get cluster data
            # In a production system, this would be cached or stored
            # This is a placeholder implementation

            # Since we don't have cluster data persistence yet, return a helpful message
            # In the future, this would retrieve stored cluster data and expand it

            # Build schema-compliant placeholder payload
            page_num = (
                (int(offset) // int(limit)) + 1
                if isinstance(limit, int) and limit > 0
                else 1
            )
            expansion_result = {
                "cluster_id": str(cluster_id),
                "cluster_info": {
                    "cluster_name": "",
                    "cluster_theme": "",
                    "document_count": 0,
                },
                "documents": [],
                "pagination": {
                    "page": page_num,
                    "page_size": int(limit) if isinstance(limit, int) else 20,
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
