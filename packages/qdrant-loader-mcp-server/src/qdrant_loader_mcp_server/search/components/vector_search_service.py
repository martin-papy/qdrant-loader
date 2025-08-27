"""Vector search service for hybrid search."""

import hashlib
import time
from asyncio import Lock
from dataclasses import dataclass
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from ...utils.logging import LoggingConfig
from .field_query_parser import FieldQueryParser


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
            try:
                # Accept either a provider (with .embeddings()) or a direct embeddings client
                client = (
                    self.embeddings_provider.embeddings()
                    if hasattr(self.embeddings_provider, "embeddings")
                    else self.embeddings_provider
                )
                vectors = await client.embed([text])
                return vectors[0]
            except Exception as e:
                self.logger.error("Provider embeddings failed", error=str(e))
                raise

        # Fallback to OpenAI client when provider is not configured
        if self.openai_client is not None:
            try:
                response = await self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text,
                )
                return response.data[0].embedding
            except Exception as e:
                # Do not fall back silently; propagate error as tests expect
                self.logger.error("Failed to get embedding", error=str(e))
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
        # Generate cache key and check cache first
        cache_key = self._generate_cache_key(query, limit, project_ids)

        if self.cache_enabled:
            # Guard cache reads/cleanup with the async lock
            async with self._cache_lock:
                self._cleanup_expired_cache()

                # Check cache for existing results
                cached_entry = self._search_cache.get(cache_key)
                if cached_entry is not None:
                    current_time = time.time()

                    # Verify cache entry is still valid
                    if current_time - cached_entry["timestamp"] <= self.cache_ttl:
                        self._cache_hits += 1
                        self.logger.debug(
                            "Search cache hit",
                            query=query[:50],  # Truncate for logging
                            cache_hits=self._cache_hits,
                            cache_misses=self._cache_misses,
                            hit_rate=f"{self._cache_hits / (self._cache_hits + self._cache_misses) * 100:.1f}%",
                        )
                        return cached_entry["results"]

        # Cache miss - perform actual search
        self._cache_misses += 1

        self.logger.debug(
            "Search cache miss - performing QDrant search",
            query=query[:50],  # Truncate for logging
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
        )

        # ✅ Parse query for field-specific filters
        parsed_query = self.field_parser.parse_query(query)
        self.logger.debug(
            f"Parsed query: {len(parsed_query.field_queries)} field queries, text: '{parsed_query.text_query}'"
        )

        # Determine search strategy based on parsed query
        if self.field_parser.should_use_filter_only(parsed_query):
            # Filter-only search (exact field matching)
            self.logger.debug("Using filter-only search for exact field matching")
            query_filter = self.field_parser.create_qdrant_filter(
                parsed_query.field_queries, project_ids
            )

            # For filter-only searches, use scroll with filter instead of vector search
            scroll_results = await self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                scroll_filter=query_filter,
                with_payload=True,
                with_vectors=False,
            )

            results = []
            for point in scroll_results[
                0
            ]:  # scroll_results is (points, next_page_offset)
                results.append(FilterResult(1.0, point.payload))
        else:
            # Hybrid search (vector search + field filters)
            search_query = parsed_query.text_query if parsed_query.text_query else query
            query_embedding = await self.get_embedding(search_query)

            search_params = models.SearchParams(
                hnsw_ef=self.hnsw_ef, exact=bool(self.use_exact_search)
            )

            # Combine field filters with project filters
            query_filter = self.field_parser.create_qdrant_filter(
                parsed_query.field_queries, project_ids
            )

            results = await self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=self.min_score,
                search_params=search_params,
                query_filter=query_filter,
                with_payload=True,  # 🔧 CRITICAL: Explicitly request payload data
            )

        extracted_results = []
        for hit in results:
            extracted = {
                "score": hit.score,
                "text": hit.payload.get("content", "") if hit.payload else "",
                "metadata": hit.payload.get("metadata", {}) if hit.payload else {},
                "source_type": (
                    hit.payload.get("source_type", "unknown")
                    if hit.payload
                    else "unknown"
                ),
                # Extract fields directly from Qdrant payload
                "title": hit.payload.get("title", "") if hit.payload else "",
                "url": hit.payload.get("url", "") if hit.payload else "",
                "document_id": (
                    hit.payload.get("document_id", "") if hit.payload else ""
                ),
                "source": hit.payload.get("source", "") if hit.payload else "",
                "created_at": hit.payload.get("created_at", "") if hit.payload else "",
                "updated_at": hit.payload.get("updated_at", "") if hit.payload else "",
            }

            extracted_results.append(extracted)

        # Store results in cache if caching is enabled
        if self.cache_enabled:
            async with self._cache_lock:
                self._search_cache[cache_key] = {
                    "results": extracted_results,
                    "timestamp": time.time(),
                }

                self.logger.debug(
                    "Cached search results",
                    query=query[:50],
                    results_count=len(extracted_results),
                    cache_size=len(self._search_cache),
                )

        return extracted_results

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
    ) -> models.Filter | None:
        """Legacy method for backward compatibility - use FieldQueryParser instead.

        Args:
            project_ids: Optional project ID filters

        Returns:
            Qdrant Filter object or None
        """
        if project_ids:
            from qdrant_client.http import models

            return models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_id", match=models.MatchAny(any=project_ids)
                    )
                ]
            )
        return None

    # Note: _build_filter method added back for backward compatibility - prefer FieldQueryParser.create_qdrant_filter()

    def build_filter(
        self, project_ids: list[str] | None = None
    ) -> models.Filter | None:
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
