"""Vector search service for hybrid search."""

from __future__ import annotations

import asyncio
import hashlib
import time
from asyncio import Lock
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http import models as qdrant_models

from qdrant_client.http import models
from qdrant_loader_core.config import (
    CollectionVectorCapabilities,
    parse_collection_capabilities,
)
from qdrant_loader_core.sparse import get_sparse_encoder

from ...utils.logging import LoggingConfig
from ..sparse_config import load_sparse_runtime_config
from .field_query_parser import FieldQueryParser

# Task-local flag set by vector_search when Qdrant fusion is used for the
# current query. ContextVar isolates concurrent searches that share the same
# VectorSearchService instance.
_used_qdrant_hybrid_ctx: ContextVar[bool] = ContextVar(
    "vector_search_used_qdrant_hybrid", default=False
)


@dataclass
class FilterResult:
    score: float
    payload: dict


class VectorSearchService:
    """Handles vector search operations using Qdrant."""

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        collection_name: str,
        min_score: float = 0.3,
        cache_enabled: bool = True,
        cache_ttl: int = 300,
        cache_max_size: int = 500,
        hnsw_ef: int = 128,
        use_exact_search: bool = False,
        *,
        embeddings_provider: Any | None = None,
        openai_client: Any | None = None,
        embedding_model: str = "text-embedding-3-small",
    ):
        """Initialize the vector search service.

        Args:
            qdrant_client: Asynchronous Qdrant client instance (AsyncQdrantClient)
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            min_score: Minimum score threshold
            cache_enabled: Whether to enable search result caching
            cache_ttl: Cache time-to-live in seconds
            cache_max_size: Maximum number of cached results
        """
        self.qdrant_client = qdrant_client
        self.embeddings_provider = embeddings_provider
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.min_score = min_score

        # Search result caching configuration
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.cache_max_size = cache_max_size
        self._search_cache: dict[str, dict[str, Any]] = {}
        self._cache_lock: Lock = Lock()

        # Cache performance metrics
        self._cache_hits = 0
        self._cache_misses = 0

        # Field query parser for handling field:value syntax
        self.field_parser = FieldQueryParser()

        self.logger = LoggingConfig.get_logger(__name__)

        self.sparse_runtime = load_sparse_runtime_config()
        self._collection_capabilities: CollectionVectorCapabilities | None = None
        self._capabilities_lock: Lock = Lock()

        # Qdrant search parameters
        self.hnsw_ef = hnsw_ef
        self.use_exact_search = use_exact_search

    def _generate_cache_key(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> str:
        """Generate a cache key for search parameters.

        Args:
            query: Search query
            limit: Maximum number of results
            project_ids: Optional project ID filters

        Returns:
            SHA256 hash of search parameters for cache key
        """
        # Create a deterministic string from search parameters
        project_str = ",".join(sorted(project_ids)) if project_ids else "none"
        cache_input = (
            f"{query}|{limit}|{project_str}|{self.min_score}|{self.collection_name}"
        )
        return hashlib.sha256(cache_input.encode()).hexdigest()

    def _cleanup_expired_cache(self) -> None:
        """Remove expired entries from cache."""
        if not self.cache_enabled:
            return

        current_time = time.time()
        expired_keys = [
            key
            for key, value in self._search_cache.items()
            if current_time - value["timestamp"] > self.cache_ttl
        ]

        for key in expired_keys:
            del self._search_cache[key]

        # Also enforce max size limit
        if len(self._search_cache) > self.cache_max_size:
            # Remove oldest entries (simple FIFO eviction)
            sorted_items = sorted(
                self._search_cache.items(), key=lambda x: x[1]["timestamp"]
            )
            items_to_remove = len(self._search_cache) - self.cache_max_size
            for key, _ in sorted_items[:items_to_remove]:
                del self._search_cache[key]

    async def _get_collection_capabilities(self) -> CollectionVectorCapabilities:
        """Probe the collection for named-dense and sparse vector support.

        Transient ``get_collection`` failures are logged and returned as
        empty capabilities for the current call only — they are never cached,
        so the next call retries.
        """
        if self._collection_capabilities is not None:
            return self._collection_capabilities

        async with self._capabilities_lock:
            if self._collection_capabilities is not None:
                return self._collection_capabilities
            try:
                info = await self.qdrant_client.get_collection(
                    collection_name=self.collection_name
                )
            except Exception as e:
                # Don't cache: a transient outage would otherwise pin every
                # subsequent query to the dense fallback path for this
                # service's lifetime.
                self.logger.warning(
                    "Failed to inspect Qdrant collection schema; assuming dense-only",
                    collection=self.collection_name,
                    error=str(e),
                )
                return CollectionVectorCapabilities()
            self._collection_capabilities = parse_collection_capabilities(
                info, self.sparse_runtime
            )
        return self._collection_capabilities

    def _dense_using(self, caps: CollectionVectorCapabilities) -> str | None:
        """Return the named-dense vector key, or None for legacy unnamed collections."""
        return self.sparse_runtime.dense_vector_name if caps.has_named_dense else None

    def _hybrid_query_active(self, caps: CollectionVectorCapabilities) -> bool:
        """Combine collection schema with runtime config to decide on server-side fusion."""
        return (
            caps.hybrid_ready
            and self.sparse_runtime.enabled
            and self.sparse_runtime.use_qdrant_hybrid
        )

    async def supports_qdrant_hybrid(self) -> bool:
        """Return True if the collection is configured for Qdrant dense+sparse fusion.

        Used by HybridPipeline to decide whether to skip the separate keyword
        search; calling this lets the pipeline preserve parallelism in the
        dense-only path.
        """
        caps = await self._get_collection_capabilities()
        return self._hybrid_query_active(caps)

    def _encode_sparse_query(self, text: str):
        sparse = get_sparse_encoder(self.sparse_runtime.model).encode_query(text)
        if sparse.is_empty():
            return None
        return models.SparseVector(indices=sparse.indices, values=sparse.values)

    def used_qdrant_hybrid_last_query(self) -> bool:
        """Return whether the most recent vector_search in this task used Qdrant fusion.

        Backed by a ContextVar so concurrent searches across tasks (e.g. multiple
        MCP requests sharing this service) don't clobber each other.
        """
        return _used_qdrant_hybrid_ctx.get()

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI client when available, else provider.

        Args:
            text: Text to get embedding for

        Returns:
            List of embedding values

        Raises:
            Exception: If embedding generation fails
        """
        # Prefer provider when available
        if self.embeddings_provider is not None:
            # Accept either a provider (with .embeddings()) or a direct embeddings client
            client = (
                self.embeddings_provider.embeddings()
                if hasattr(self.embeddings_provider, "embeddings")
                else self.embeddings_provider
            )
            for _ in range(3):
                try:
                    vectors = await client.embed([text])
                    return vectors[0]
                except Exception as e:
                    self.logger.warning(
                        "Provider embedding failed, retrying...", error=str(e)
                    )
                    await asyncio.sleep(0.5)

        # Fallback to OpenAI (to keep backward compatibility & pass tests)
        if self.openai_client is not None:
            try:
                response = await self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text,
                )
                return response.data[0].embedding
            except Exception as e:
                self.logger.error("OpenAI fallback failed", error=str(e))
                raise

        # Nothing configured
        raise RuntimeError("No embeddings provider or OpenAI client configured")

    async def vector_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Perform vector search using Qdrant with caching support.

        Args:
            query: Search query
            limit: Maximum number of results
            project_ids: Optional project ID filters

        Returns:
            List of search results with scores, text, metadata, and source_type
        """
        cache_key = self._generate_cache_key(query, limit, project_ids)
        cached = await self._cache_get_if_valid(cache_key, query)
        if cached is not None:
            return cached

        _used_qdrant_hybrid_ctx.set(False)
        parsed_query = self.field_parser.parse_query(query)
        self.logger.debug(
            f"Parsed query: {len(parsed_query.field_queries)} field queries, "
            f"text: '{parsed_query.text_query}'"
        )

        if self.field_parser.should_use_filter_only(parsed_query):
            results = await self._run_filter_only_search(
                parsed_query, project_ids, limit
            )
        else:
            results = await self._run_vector_search(
                parsed_query, project_ids, query, limit
            )

        extracted = self._extract_hits(results)
        await self._cache_put(cache_key, extracted, query)
        return extracted

    async def _cache_get_if_valid(
        self, cache_key: str, query: str
    ) -> list[dict[str, Any]] | None:
        """Return cached results if present and not expired; otherwise increment the miss counter."""
        if self.cache_enabled:
            async with self._cache_lock:
                self._cleanup_expired_cache()
                cached_entry = self._search_cache.get(cache_key)
                if (
                    cached_entry is not None
                    and time.time() - cached_entry["timestamp"] <= self.cache_ttl
                ):
                    self._cache_hits += 1
                    self.logger.debug(
                        "Search cache hit",
                        query=query[:50],
                        cache_hits=self._cache_hits,
                        cache_misses=self._cache_misses,
                        hit_rate=(
                            f"{self._cache_hits / (self._cache_hits + self._cache_misses) * 100:.1f}%"
                        ),
                    )
                    return cached_entry["results"]

        self._cache_misses += 1
        self.logger.debug(
            "Search cache miss - performing QDrant search",
            query=query[:50],
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
        )
        return None

    async def _cache_put(
        self, cache_key: str, results: list[dict[str, Any]], query: str
    ) -> None:
        """Store ``results`` under ``cache_key`` when caching is enabled."""
        if not self.cache_enabled:
            return
        async with self._cache_lock:
            self._search_cache[cache_key] = {
                "results": results,
                "timestamp": time.time(),
            }
            self.logger.debug(
                "Cached search results",
                query=query[:50],
                results_count=len(results),
                cache_size=len(self._search_cache),
            )

    async def _run_filter_only_search(
        self,
        parsed_query,
        project_ids: list[str] | None,
        limit: int,
    ) -> list[FilterResult]:
        """Scroll-based exact-match path used when the query contains only field filters."""
        self.logger.debug("Using filter-only search for exact field matching")
        query_filter = self.field_parser.create_qdrant_filter(
            parsed_query.field_queries, project_ids
        )
        scroll_results = await self.qdrant_client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            scroll_filter=query_filter,
            with_payload=True,
            with_vectors=False,
        )
        return [FilterResult(1.0, point.payload) for point in scroll_results[0]]

    async def _run_vector_search(
        self,
        parsed_query,
        project_ids: list[str] | None,
        original_query: str,
        limit: int,
    ) -> list:
        """Dispatch to either the Qdrant hybrid query or the dense-only query."""
        search_query = parsed_query.text_query or original_query
        query_embedding = await self.get_embedding(search_query)
        search_params = models.SearchParams(
            hnsw_ef=self.hnsw_ef, exact=bool(self.use_exact_search)
        )
        query_filter = self.field_parser.create_qdrant_filter(
            parsed_query.field_queries, project_ids
        )
        # Routing is fully determined by the probed collection schema and the
        # runtime config — no silent fallback. If the collection supports
        # hybrid retrieval, we use hybrid; otherwise dense. Hybrid query
        # failures propagate so operators see them instead of degraded results.
        caps = await self._get_collection_capabilities()
        if self._hybrid_query_active(caps):
            return await self._run_qdrant_hybrid_query(
                query_embedding,
                search_query,
                query_filter,
                search_params,
                caps,
                limit,
            )
        return await self._run_dense_query(
            query_embedding, query_filter, search_params, caps, limit
        )

    async def _run_qdrant_hybrid_query(
        self,
        query_embedding: list[float],
        search_query: str,
        query_filter,
        search_params,
        caps: CollectionVectorCapabilities,
        limit: int,
    ) -> list:
        """Issue a server-side RRF fusion query over the dense + sparse prefetches."""
        sparse_query = self._encode_sparse_query(search_query)
        if sparse_query is None:
            raise ValueError("Sparse query generation returned empty vector")

        prefetch_limit = limit * 3
        query_response = await self.qdrant_client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=query_embedding,
                    using=self._dense_using(caps),
                    filter=query_filter,
                    params=search_params,
                    limit=prefetch_limit,
                ),
                models.Prefetch(
                    query=sparse_query,
                    using=self.sparse_runtime.sparse_vector_name,
                    filter=query_filter,
                    limit=prefetch_limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
        _used_qdrant_hybrid_ctx.set(True)
        return query_response.points

    async def _run_dense_query(
        self,
        query_embedding: list[float],
        query_filter,
        search_params,
        caps: CollectionVectorCapabilities,
        limit: int,
    ) -> list:
        """Plain dense vector search — used when hybrid isn't available or has failed."""
        query_kwargs: dict[str, Any] = {
            "collection_name": self.collection_name,
            "query": query_embedding,
            "limit": limit,
            "score_threshold": self.min_score,
            "search_params": search_params,
            "query_filter": query_filter,
            "with_payload": True,
        }
        using = self._dense_using(caps)
        if using:
            query_kwargs["using"] = using
        query_response = await self.qdrant_client.query_points(**query_kwargs)
        return query_response.points

    @staticmethod
    def _extract_hits(results: list) -> list[dict[str, Any]]:
        """Project Qdrant scored points to the dict shape consumed downstream."""
        extracted: list[dict[str, Any]] = []
        for hit in results:
            payload = getattr(hit, "payload", None) or {}
            extracted.append(
                {
                    "score": hit.score,
                    "text": payload.get("content", ""),
                    "metadata": payload.get("metadata", {}),
                    "source_type": payload.get("source_type", "unknown"),
                    "title": payload.get("title", ""),
                    "url": payload.get("url", ""),
                    "document_id": payload.get("document_id", ""),
                    "source": payload.get("source", ""),
                    "created_at": payload.get("created_at", ""),
                    "updated_at": payload.get("updated_at", ""),
                    "contextual_content": payload.get("contextual_content", ""),
                }
            )
        return extracted

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics.

        Returns:
            Dictionary with cache hit rate, size, and other metrics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        )

        return {
            "cache_enabled": self.cache_enabled,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._search_cache),
            "cache_max_size": self.cache_max_size,
            "cache_ttl_seconds": self.cache_ttl,
        }

    def clear_cache(self) -> None:
        """Clear all cached search results."""
        self._search_cache.clear()
        self.logger.info("Search result cache cleared")

    def _build_filter(
        self, project_ids: list[str] | None = None
    ) -> qdrant_models.Filter | None:
        """Legacy method for backward compatibility - use FieldQueryParser instead.

        Args:
            project_ids: Optional project ID filters

        Returns:
            Qdrant Filter object or None
        """
        if project_ids:
            return models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_id", match=models.MatchAny(any=project_ids)
                    )
                ]
            )
        return None

    def build_filter(
        self, project_ids: list[str] | None = None
    ) -> qdrant_models.Filter | None:
        """Public wrapper for building a Qdrant filter for project constraints.

        Prefer using `FieldQueryParser.create_qdrant_filter` for field queries. This
        method exists to expose project filter building via a public API and wraps the
        legacy `_build_filter` implementation for compatibility.

        Args:
            project_ids: Optional list of project IDs to filter by.

        Returns:
            A Qdrant `models.Filter` or `None` if no filtering is needed.
        """
        return self._build_filter(project_ids)
