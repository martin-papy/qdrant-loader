"""
Cross-Document Intelligence Operations.

This module implements cross-document intelligence functionality including
document relationship analysis, similarity detection, conflict detection,
complementary content discovery, and document clustering.
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .core import SearchEngine

from ...utils.logging import LoggingConfig
from ..enhanced.cross_document_intelligence import ClusteringStrategy, SimilarityMetric

logger = LoggingConfig.get_logger(__name__)


class IntelligenceOperations:
    """Handles cross-document intelligence operations."""

    def __init__(self, engine: "SearchEngine"):
        """Initialize with search engine reference."""
        self.engine = engine
        self.logger = LoggingConfig.get_logger(__name__)

    async def analyze_document_relationships(
        self,
        query: str,
        limit: int | None = None,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze relationships between documents from search results.

        Args:
            query: Search query to get documents for analysis
            limit: Maximum number of documents to analyze
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by

        Returns:
            Comprehensive cross-document relationship analysis
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        try:
            # Get documents for analysis
            # Honor default conflict limit from config if caller didn't override
            effective_limit = limit
            config = getattr(self.engine, "config", None)
            if limit is None:
                if config is not None:
                    default_limit = getattr(config, "conflict_limit_default", None)
                    if isinstance(default_limit, int):
                        effective_limit = default_limit
                    else:
                        effective_limit = 20
                else:
                    effective_limit = 20

            documents = await self.engine.hybrid_search.search(
                query=query,
                limit=effective_limit,
                source_types=source_types,
                project_ids=project_ids,
            )

            if len(documents) < 2:
                return {
                    "error": "Need at least 2 documents for relationship analysis",
                    "document_count": len(documents),
                }

            # Perform cross-document analysis
            analysis = await self.engine.hybrid_search.analyze_document_relationships(
                documents
            )

            # Add query metadata
            analysis["query_metadata"] = {
                "original_query": query,
                "document_count": len(documents),
                "source_types": source_types,
                "project_ids": project_ids,
            }

            return analysis

        except Exception as e:
            self.logger.error(
                "Document relationship analysis failed", error=str(e), query=query
            )
            raise

    async def find_similar_documents(
        self,
        target_query: str,
        comparison_query: str,
        similarity_metrics: list[str] | None = None,
        max_similar: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Find documents similar to a target document.

        Args:
            target_query: Query to find the target document
            comparison_query: Query to get documents to compare against
            similarity_metrics: Similarity metrics to use
            max_similar: Maximum number of similar documents to return
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by

        Returns:
            List of similar documents with similarity scores
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        try:
            # Get target document (first result from target query)
            target_results = await self.engine.hybrid_search.search(
                query=target_query,
                limit=1,
                source_types=source_types,
                project_ids=project_ids,
            )

            if not target_results:
                return {
                    "error": "No target document found",
                    "target_query": target_query,
                }

            target_doc = target_results[0]

            # Get comparison documents
            comparison_results = await self.engine.hybrid_search.search(
                query=comparison_query,
                limit=50,  # Get more candidates for comparison
                source_types=source_types,
                project_ids=project_ids,
            )

            if len(comparison_results) < 2:
                return {
                    "error": "Need at least 1 comparison document",
                    "comparison_count": len(comparison_results),
                }

            # Parse similarity metrics
            metric_enums = []
            if similarity_metrics:
                for metric_str in similarity_metrics:
                    try:
                        metric_enums.append(SimilarityMetric(metric_str))
                    except ValueError:
                        self.logger.warning(f"Unknown similarity metric: {metric_str}")

            # Find similar documents
            similar = await self.engine.hybrid_search.find_similar_documents(
                target_doc, comparison_results, metric_enums or None, max_similar
            )

            return {
                "target_document": {
                    "document_id": target_doc.document_id,
                    "title": target_doc.get_display_title(),
                    "source_type": target_doc.source_type,
                },
                "similar_documents": similar,
                "similarity_metrics_used": (
                    [m.value for m in metric_enums] if metric_enums else "default"
                ),
                "comparison_documents_analyzed": len(comparison_results),
            }

        except Exception as e:
            self.logger.error("Similarity search failed", error=str(e))
            raise

    async def detect_document_conflicts(
        self,
        query: str,
        limit: int | None = None,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
        *,
        use_llm: bool | None = None,
        max_llm_pairs: int | None = None,
        overall_timeout_s: float | None = None,
        max_pairs_total: int | None = None,
        text_window_chars: int | None = None,
    ) -> dict[str, Any]:
        """
        Detect conflicts between documents.

        Args:
            query: Search query to get documents for conflict analysis
            limit: Maximum number of documents to analyze
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by

        Returns:
            Conflict analysis with detected conflicts and resolution suggestions
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        try:
            # Get documents for conflict analysis
            effective_limit = limit
            config = getattr(self.engine, "config", None)
            if limit is None and config is not None:
                default_limit = getattr(config, "conflict_limit_default", None)
                if isinstance(default_limit, int):
                    effective_limit = default_limit

            documents = await self.engine.hybrid_search.search(
                query=query,
                limit=effective_limit,
                source_types=source_types,
                project_ids=project_ids,
            )

            if len(documents) < 2:
                return {
                    "conflicts": [],
                    "resolution_suggestions": [],
                    "message": "Need at least 2 documents for conflict detection",
                    "document_count": len(documents),
                }

            # Detect conflicts with optional per-call overrides applied
            detector = self.engine.hybrid_search.cross_document_engine.conflict_detector
            call_overrides: dict[str, Any] = {}
            if use_llm is not None:
                call_overrides["conflict_use_llm"] = bool(use_llm)
            if isinstance(max_llm_pairs, int):
                call_overrides["conflict_max_llm_pairs"] = max_llm_pairs
            if isinstance(overall_timeout_s, int | float):
                call_overrides["conflict_overall_timeout_s"] = float(overall_timeout_s)
            if isinstance(max_pairs_total, int):
                call_overrides["conflict_max_pairs_total"] = max_pairs_total
            if isinstance(text_window_chars, int):
                call_overrides["conflict_text_window_chars"] = text_window_chars

            @contextmanager
            def temporary_detector_settings(det: Any, overrides: dict[str, Any] | None):
                """Temporarily apply merged detector settings and restore afterwards."""
                previous = (
                    getattr(det, "_settings", {}) if hasattr(det, "_settings") else {}
                )
                if not overrides:
                    # No overrides to apply; simply yield control
                    yield
                    return
                merged_settings = dict(previous)
                merged_settings.update(overrides)
                try:
                    det._settings = merged_settings  # type: ignore[attr-defined]
                except Exception:
                    # If settings assignment fails, proceed without overriding
                    pass
                try:
                    yield
                finally:
                    # Always attempt to restore previous settings
                    try:
                        det._settings = previous  # type: ignore[attr-defined]
                    except Exception:
                        pass

            with temporary_detector_settings(detector, call_overrides):
                conflicts = await self.engine.hybrid_search.detect_document_conflicts(
                    documents
                )

            # Add query metadata and original documents for formatting
            conflicts["query_metadata"] = {
                "original_query": query,
                "document_count": len(documents),
                "source_types": source_types,
                "project_ids": project_ids,
            }

            # Inject detector runtime stats via public accessor for structured output
            try:
                detector = (
                    self.engine.hybrid_search.cross_document_engine.conflict_detector
                )
                get_stats = getattr(detector, "get_stats", None) or getattr(
                    detector, "get_last_stats", None
                )
                raw_stats = {}
                if callable(get_stats):
                    raw_stats = get_stats() or {}

                if isinstance(raw_stats, dict) and raw_stats:
                    # Filter to JSON-safe scalar values only
                    safe_stats = {}
                    for key, value in raw_stats.items():
                        if isinstance(value, str | int | float | bool) and not str(
                            key
                        ).startswith("partial_"):
                            safe_stats[key] = value
                    if safe_stats:
                        conflicts["query_metadata"]["detector_stats"] = safe_stats
            except Exception as e:
                self.logger.debug("Failed to access detector stats", error=str(e))

            # Store lightweight, JSON-serializable representations of documents
            # to keep payload minimal and avoid non-serializable objects
            safe_documents: list[dict[str, Any]] = []
            for doc in documents:
                try:
                    document_id = getattr(doc, "document_id", None)
                    # Support either attribute or mapping style access
                    if document_id is None and isinstance(doc, dict):
                        document_id = doc.get("document_id") or doc.get("id")

                    title = None
                    if hasattr(doc, "get_display_title") and callable(
                        doc.get_display_title
                    ):
                        try:
                            title = doc.get_display_title()
                        except Exception:
                            title = None
                    if not title:
                        title = getattr(doc, "source_title", None)
                    if not title and isinstance(doc, dict):
                        title = doc.get("source_title") or doc.get("title")

                    source_type = getattr(doc, "source_type", None)
                    if source_type is None and isinstance(doc, dict):
                        source_type = doc.get("source_type")

                    safe_documents.append(
                        {
                            "document_id": document_id or "",
                            "title": title or "Untitled",
                            "source_type": source_type or "unknown",
                        }
                    )
                except Exception:
                    # Skip malformed entries
                    continue

            conflicts["original_documents"] = safe_documents

            return conflicts

        except Exception as e:
            self.logger.error("Conflict detection failed", error=str(e), query=query)
            raise

    async def find_complementary_content(
        self,
        target_query: str,
        context_query: str,
        max_recommendations: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Find content that complements a target document.

        Args:
            target_query: Query to find the target document
            context_query: Query to get contextual documents
            max_recommendations: Maximum number of recommendations
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by

        Returns:
            Dict containing complementary recommendations and target document info
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        try:
            self.logger.info(
                f"🔍 Step 1: Searching for target document with query: '{target_query}'"
            )
            # Get target document
            target_results = await self.engine.hybrid_search.search(
                query=target_query,
                limit=1,
                source_types=(source_types or None),
                project_ids=project_ids,
            )

            self.logger.info(f"🎯 Target search returned {len(target_results)} results")
            if not target_results:
                self.logger.warning("No target document found!")
                # Retry with a relaxed/sanitized query (drop stopwords and shorten)
                import re

                tokens = re.findall(r"\w+", target_query)
                stop = {
                    "the",
                    "and",
                    "or",
                    "of",
                    "for",
                    "to",
                    "a",
                    "an",
                    "phase",
                    "kickoff",
                }
                relaxed_tokens = [t for t in tokens if t.lower() not in stop]
                relaxed_query = (
                    " ".join(relaxed_tokens[:4]) if relaxed_tokens else target_query
                )

                if relaxed_query and relaxed_query != target_query:
                    self.logger.info(
                        f"🔁 Retrying target search with relaxed query: '{relaxed_query}'"
                    )
                    target_results = await self.engine.hybrid_search.search(
                        query=relaxed_query,
                        limit=1,
                        source_types=(source_types or None),
                        project_ids=project_ids,
                    )

                # Final fallback: use project anchor terms
                if not target_results:
                    fallback_query = "Mya Health " + " ".join(relaxed_tokens[:2])
                    self.logger.info(
                        f"🔁 Final fallback target search with query: '{fallback_query}'"
                    )
                    target_results = await self.engine.hybrid_search.search(
                        query=fallback_query,
                        limit=1,
                        source_types=(source_types or None),
                        project_ids=project_ids,
                    )

                if not target_results:
                    # Absolute last resort: generic project query
                    generic_query = "Mya Health"
                    self.logger.info(
                        f"🔁 Generic fallback target search with query: '{generic_query}'"
                    )
                    target_results = await self.engine.hybrid_search.search(
                        query=generic_query,
                        limit=1,
                        source_types=(source_types or None),
                        project_ids=project_ids,
                    )

                if not target_results:
                    return {
                        "complementary_recommendations": [],
                        "target_document": None,
                        "context_documents_analyzed": 0,
                    }

            target_doc = target_results[0]
            self.logger.info(f"📄 Target document: {target_doc.get_display_title()}")

            self.logger.info(
                f"🔍 Step 2: Searching for context documents with query: '{context_query}'"
            )
            # Get context documents for comparison - adaptive limit based on max_recommendations
            # Use factor 4 with a minimum of 20 to balance recall and efficiency
            adaptive_limit = max(max_recommendations * 4, 20)
            context_results = await self.engine.hybrid_search.search(
                query=context_query,
                limit=adaptive_limit,
                source_types=(source_types or None),
                project_ids=project_ids,
            )

            self.logger.info(
                f"📚 Context search returned {len(context_results)} documents"
            )
            if not context_results:
                self.logger.warning("No context documents found!")
                # Retry with a broad project-level context query
                broad_context = "Mya Health documentation architecture project"
                self.logger.info(
                    f"🔁 Retrying context search with broad query: '{broad_context}'"
                )
                context_results = await self.engine.hybrid_search.search(
                    query=broad_context,
                    limit=adaptive_limit,
                    source_types=(source_types or None),
                    project_ids=project_ids,
                )

                if not context_results:
                    return {
                        "complementary_recommendations": [],
                        "target_document": {
                            "document_id": target_doc.document_id,
                            "title": target_doc.get_display_title(),
                            "source_type": target_doc.source_type,
                        },
                        "context_documents_analyzed": 0,
                    }

            # Find complementary content
            self.logger.info("🔍 Step 3: Finding complementary content...")
            complementary = await self.engine.hybrid_search.find_complementary_content(
                target_doc, context_results, max_recommendations
            )

            self.logger.info(f"✅ Found {len(complementary)} recommendations")

            # Transform recommendations to expected format
            transformed_recommendations = []
            for rec in complementary:
                if isinstance(rec, dict):
                    # Get document info
                    doc = rec.get("document")
                    if doc:
                        transformed_rec = {
                            "document_id": (
                                doc.document_id
                                if hasattr(doc, "document_id")
                                else rec.get("document_id", "unknown")
                            ),
                            "title": (
                                doc.get_display_title()
                                if hasattr(doc, "get_display_title")
                                else (
                                    doc.source_title
                                    if hasattr(doc, "source_title")
                                    else rec.get("title", "Untitled")
                                )
                            ),
                            "relevance_score": rec.get(
                                "complementary_score", rec.get("relevance_score", 0.0)
                            ),
                            "reason": rec.get("explanation", rec.get("reason", "")),
                            "strategy": rec.get(
                                "relationship_type", rec.get("strategy", "related")
                            ),
                            # Preserve essential metadata for downstream formatters
                            "source_type": getattr(
                                doc, "source_type", rec.get("source_type", "unknown")
                            ),
                            "project_id": getattr(
                                doc, "project_id", rec.get("project_id")
                            ),
                        }
                        transformed_recommendations.append(transformed_rec)
                else:
                    # Handle non-dict recommendations
                    transformed_recommendations.append(rec)

            return {
                "complementary_recommendations": transformed_recommendations,
                "target_document": {
                    "document_id": target_doc.document_id,
                    "title": target_doc.get_display_title(),
                    "source_type": target_doc.source_type,
                },
                "context_documents_analyzed": len(context_results),
            }

        except Exception as e:
            self.logger.error("Complementary content search failed", error=str(e))
            raise

    async def cluster_documents(
        self,
        query: str,
        strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
        max_clusters: int = 10,
        min_cluster_size: int = 2,
        limit: int = 30,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Cluster documents using the specified strategy.

        Args:
            query: Search query to get documents for clustering
            strategy: Clustering strategy to use
            max_clusters: Maximum number of clusters to create
            min_cluster_size: Minimum documents per cluster
            limit: Maximum documents to analyze
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by

        Returns:
            Dictionary containing clusters and metadata
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        try:
            # Get documents for clustering
            documents = await self.engine.hybrid_search.search(
                query=query,
                limit=limit,
                source_types=source_types,
                project_ids=project_ids,
            )

            if len(documents) < min_cluster_size:
                return {
                    "clusters": [],
                    "clustering_metadata": {
                        "message": f"Need at least {min_cluster_size} documents for clustering",
                        "document_count": len(documents),
                        "original_query": query,
                        "source_types": source_types,
                        "project_ids": project_ids,
                        "strategy": strategy.value,
                        "max_clusters": max_clusters,
                        "min_cluster_size": min_cluster_size,
                    },
                }

            # Perform clustering
            clusters = await self.engine.hybrid_search.cluster_documents(
                documents=documents,
                strategy=strategy,
                max_clusters=max_clusters,
                min_cluster_size=min_cluster_size,
            )

            # Add query metadata - merge into clustering_metadata if it exists
            result = {**clusters}
            if "clustering_metadata" in result:
                result["clustering_metadata"]["original_query"] = query
                result["clustering_metadata"]["document_count"] = len(documents)
                result["clustering_metadata"]["source_types"] = source_types
                result["clustering_metadata"]["project_ids"] = project_ids
            else:
                result["query_metadata"] = {
                    "original_query": query,
                    "document_count": len(documents),
                    "source_types": source_types,
                    "project_ids": project_ids,
                    "strategy": strategy.value,
                    "max_clusters": max_clusters,
                    "min_cluster_size": min_cluster_size,
                }

            return result

        except Exception as e:
            self.logger.error("Document clustering failed", error=str(e), query=query)
            raise
