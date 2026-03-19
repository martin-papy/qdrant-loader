"""Cross-document intelligence operations handler for MCP server."""

import time
import uuid
from typing import Any

from ..search.engine import SearchEngine
from ..utils import LoggingConfig
from .formatters import MCPFormatters
from .handlers.intelligence import (
    get_or_create_document_id as _get_or_create_document_id_fn,
)
from .handlers.intelligence import process_analysis_results
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
        self._cluster_store = {}
        self._ttl = 300
        self._max_sessions = 500

    def _get_or_create_document_id(self, doc: Any) -> str:
        return _get_or_create_document_id_fn(doc)

    def _expand_cluster_docs_to_schema(
        self, docs: list[Any], include_metadata: bool
    ) -> list[dict[str, Any]]:
        """Build documents array to match expand_cluster outputSchema (id, text, metadata)."""
        result = []
        for doc in docs:
            doc_id = getattr(doc, "document_id", None) or getattr(doc, "id", None) or ""
            item = {"id": str(doc_id), "text": getattr(doc, "text", "") or ""}
            if include_metadata:
                item["metadata"] = {
                    "title": getattr(doc, "source_title", ""),
                    "source_type": getattr(doc, "source_type", ""),
                    "source_url": getattr(doc, "source_url", None),
                    "file_path": getattr(doc, "file_path", None),
                }
            result.append(item)
        return result

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
        """
        Handle a "find similar documents" request and return MCP-formatted results.

        Parameters:
            request_id (str | int | None): The request identifier to include in the MCP response.
            params (dict[str, Any]): Request parameters. Required keys:
                - target_query: The primary query or document to compare against.
                - comparison_query: The query or document set to compare with the target.
              Optional keys:
                - similarity_metrics: Metrics or configuration used to compute similarity.
                - max_similar (int): Maximum number of similar documents to return (default 5).
                - source_types: Restrict search to specific source types.
                - project_ids: Restrict search to specific project identifiers.
                - similarity_threshold (float): Minimum similarity score to consider (default 0.7).

        Returns:
            dict[str, Any]: An MCP protocol response dictionary. On success the response's `result` contains:
                - content: a list with a single text block (human-readable summary).
                - structuredContent: a dict with
                    - similar_documents: list of similar document entries, each containing
                      `document_id`, `title`, `similarity_score`, `similarity_metrics`,
                      `similarity_reason`, and `content_preview`.
                    - similarity_summary: metadata including `total_compared`, `similar_found`,
                      `highest_similarity`, and `metrics_used`.
                - isError: False
            On invalid parameters the function returns an MCP error response with code -32602.
            On internal failures the function returns an MCP error response with code -32603.
        """
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
                similarity_threshold=params.get(
                    "similarity_threshold", 0.7
                ),  # Default 0.7
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

                # Extract document_id - try both dict and object attribute access
                document_id = (
                    item.get("document_id", "") if isinstance(item, dict) else ""
                )
                if not document_id and document:
                    document_id = (
                        document.get("document_id")
                        if isinstance(document, dict)
                        else getattr(document, "document_id", "")
                    )

                # Extract title - try both dict and object attribute access
                title = "Untitled"
                if document:
                    if isinstance(document, dict):
                        title = document.get("source_title", "Untitled")
                    else:
                        title = getattr(document, "source_title", "Untitled")
                if not title or title == "Untitled":
                    title = (
                        item.get("source_title", "Untitled")
                        if isinstance(item, dict)
                        else "Untitled"
                    )

                # Extract text content - try both dict and object attribute access
                content_text = ""
                if document:
                    if isinstance(document, dict):
                        content_text = document.get("text", "")
                    else:
                        content_text = getattr(document, "text", "")

                # Create content preview
                content_preview = ""
                if content_text and isinstance(content_text, str):
                    content_preview = (
                        content_text[:200] + "..."
                        if len(content_text) > 200
                        else content_text
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
                            ", ".join(reasons)
                            if isinstance(
                                reasons := item.get("similarity_reasons"), list
                            )
                            else (
                                item.get("similarity_reason", "") or str(reasons or "")
                            )
                        ),
                        "content_preview": content_preview,
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
            logger.debug(
                "Calling search_engine.find_complementary_content (%s)",
                type(self.search_engine).__name__,
            )

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

            logger.debug(
                "find_complementary_content completed, got %s results",
                len(complementary_recommendations),
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
            # cleanup before add new session
            self._cleanup_sessions()

            # Store for expand_cluster call (keep full document object)
            cluster_session_id = str(uuid.uuid4())
            self._cluster_store[cluster_session_id] = {
                "data": {
                    "clusters": clustering_results.get("clusters", []),
                    "clustering_metadata": clustering_results.get(
                        "clustering_metadata"
                    ),
                },
                "expires_at": time.time() + self._ttl,
            }

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
                        "cluster_id": str(cluster.get("id", f"cluster_{idx + 1}")),
                        "cluster_name": cluster.get("name") or f"Cluster {idx + 1}",
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
                    "structuredContent": {
                        **mcp_clustering_results,
                        "cluster_session_id": cluster_session_id,
                    },
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

        # 0. Cleanup global
        self._cleanup_sessions()

        # 1. Validate cluster_session_id
        cluster_session_id = params.get("cluster_session_id")
        if not cluster_session_id:
            logger.error("Missing required parameter: cluster_session_id")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: cluster_session_id",
                },
            )

        # 2. Validate cluster_id
        cluster_id = params.get("cluster_id")
        if not cluster_id:
            logger.error("Missing required parameter: cluster_id")
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32602,
                    "message": "Invalid params",
                    "data": "Missing required parameter: cluster_id",
                },
            )

        cluster_id = str(cluster_id).strip()

        # 3. Pagination params
        try:
            limit = max(1, min(100, int(params.get("limit", 20))))
        except Exception:
            limit = 20

        try:
            offset = max(0, int(params.get("offset", 0)))
        except Exception:
            offset = 0

        include_metadata = params.get("include_metadata", True)

        # 4. Get cache by cluster_session_id
        entry = self._cluster_store.get(cluster_session_id)

        if not entry:
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32604,
                    "message": "Cluster not found",
                    "data": "Invalid or expired cluster_session_id",
                },
            )

        # 5. Lazy TTL check
        now = time.time()
        if entry.get("expires_at", 0) < now:
            self._cluster_store.pop(cluster_session_id, None)

            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32604,
                    "message": "Cluster expired",
                    "data": "cluster_session_id has expired",
                },
            )

        cache = entry.get("data") or {}
        clusters = cache.get("clusters") or []

        # 6. Find cluster
        cluster = next(
            (
                c
                for idx, c in enumerate(clusters)
                if str(c.get("id", f"cluster_{idx + 1}")) == cluster_id
            ),
            None,
        )

        if not cluster:
            return self.protocol.create_response(
                request_id,
                error={
                    "code": -32604,
                    "message": "Cluster not found",
                    "data": f"No cluster with id '{cluster_id}' found",
                },
            )

        # 7. Pagination
        all_docs = cluster.get("documents") or []
        total = len(all_docs)

        slice_docs = all_docs[offset : offset + limit]
        has_more = offset + len(slice_docs) < total
        page = (offset // limit) + 1 if limit > 0 else 1
        # 8. Transform documents
        doc_schema_list = self._expand_cluster_docs_to_schema(
            slice_docs, include_metadata
        )

        # 9. Extract theme
        theme = (
            cluster.get("cluster_summary")
            or ", ".join(
                (
                    cluster.get("shared_entities")
                    or cluster.get("centroid_topics")
                    or []
                )[:3]
            )
            or "N/A"
        )

        # 10. Build result
        result = {
            "cluster_id": cluster_id,
            "cluster_info": {
                "cluster_name": cluster.get("name") or f"Cluster {cluster_id}",
                "cluster_theme": theme,
                "document_count": total,
            },
            "documents": doc_schema_list,
            "pagination": {
                "page": page,
                "page_size": limit,
                "total": total,
                "has_more": has_more,
            },
        }

        # 11. Return response
        return self.protocol.create_response(
            request_id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": self._format_text_block(result),
                    }
                ],
                "structuredContent": result,
                "isError": False,
            },
        )

    def _format_text_block(self, result: dict) -> str:
        info = result.get("cluster_info", {})
        docs = result.get("documents", [])
        total = info.get("document_count", 0)

        text = (
            f"**Cluster: {info.get('cluster_name', 'Unknown')}**\n"
            f"Theme: {info.get('cluster_theme', 'N/A')}\n"
            f"Documents: {total}\n\n"
        )

        for i, d in enumerate(docs[:5], 1):
            title = d.get("metadata", {}).get("title", d.get("id", "Unknown"))
            text += f"{i}. {title}\n"

        if total > 5:
            text += f"... and {total - 5} more.\n"

        return text

    def _cleanup_sessions(self):
        """Cleanup expired sessions + enforce max size."""
        now = time.time()

        # 1. Remove expired
        expired_keys = [
            k for k, v in self._cluster_store.items() if v.get("expires_at", 0) < now
        ]
        for k in expired_keys:
            self._cluster_store.pop(k, None)

        # 2. Enforce max size (optional but recommended)
        max_sessions = getattr(self, "_max_sessions", 500)

        if len(self._cluster_store) > max_sessions:
            # sort by expiry (oldest first)
            sorted_items = sorted(
                self._cluster_store.items(), key=lambda x: x[1].get("expires_at", 0)
            )

            overflow = len(self._cluster_store) - max_sessions

            for k, _ in sorted_items[:overflow]:
                self._cluster_store.pop(k, None)
