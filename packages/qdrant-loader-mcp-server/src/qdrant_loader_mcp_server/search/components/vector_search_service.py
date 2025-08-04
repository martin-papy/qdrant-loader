"""Vector search service for hybrid search."""

import hashlib
import time
from typing import Any

from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

from ...utils.logging import LoggingConfig


class VectorSearchService:
    """Handles vector search operations using Qdrant."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: AsyncOpenAI,
        collection_name: str,
        min_score: float = 0.3,
        dense_vector_name: str = "dense",
        sparse_vector_name: str = "sparse",
        alpha: float = 0.5,
        cache_enabled: bool = True,
        cache_ttl: int = 300,
        cache_max_size: int = 500,
    ):
        """Initialize the vector search service.
        
        Args:
            qdrant_client: Qdrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            min_score: Minimum score threshold
            dense_vector_name: Name of the dense vector field
            sparse_vector_name: Name of the sparse vector field
            alpha: Weight for dense search (1-alpha for sparse search)
            cache_enabled: Whether to enable search result caching
            cache_ttl: Cache time-to-live in seconds
            cache_max_size: Maximum number of cached results
        """
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.min_score = min_score
        self.dense_vector_name = dense_vector_name
        self.sparse_vector_name = sparse_vector_name
        self.alpha = alpha
        
        # Search result caching configuration
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.cache_max_size = cache_max_size
        self._search_cache: dict[str, dict[str, Any]] = {}
        
        # Cache performance metrics
        self._cache_hits = 0
        self._cache_misses = 0
        
        self.logger = LoggingConfig.get_logger(__name__)

    def _generate_cache_key(self, query: str, limit: int, project_ids: list[str] | None = None) -> str:
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
        cache_input = f"{query}|{limit}|{project_str}|{self.min_score}|{self.collection_name}"
        return hashlib.sha256(cache_input.encode()).hexdigest()

    def _cleanup_expired_cache(self) -> None:
        """Remove expired entries from cache."""
        if not self.cache_enabled:
            return
            
        current_time = time.time()
        expired_keys = [
            key for key, value in self._search_cache.items()
            if current_time - value["timestamp"] > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self._search_cache[key]
            
        # Also enforce max size limit
        if len(self._search_cache) > self.cache_max_size:
            # Remove oldest entries (simple FIFO eviction)
            sorted_items = sorted(
                self._search_cache.items(), 
                key=lambda x: x[1]["timestamp"]
            )
            items_to_remove = len(self._search_cache) - self.cache_max_size
            for key, _ in sorted_items[:items_to_remove]:
                del self._search_cache[key]

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            List of embedding values
            
        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error("Failed to get embedding", error=str(e))
            raise

    async def vector_search(
        self, 
        query: str, 
        limit: int, 
        project_ids: list[str] | None = None
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
            self._cleanup_expired_cache()
            
            # Check cache for existing results
            if cache_key in self._search_cache:
                cached_entry = self._search_cache[cache_key]
                current_time = time.time()
                
                # Verify cache entry is still valid
                if current_time - cached_entry["timestamp"] <= self.cache_ttl:
                    self._cache_hits += 1
                    self.logger.debug(
                        "Search cache hit",
                        query=query[:50],  # Truncate for logging
                        cache_hits=self._cache_hits,
                        cache_misses=self._cache_misses,
                        hit_rate=f"{self._cache_hits / (self._cache_hits + self._cache_misses) * 100:.1f}%"
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
        
        query_embedding = await self.get_embedding(query)

        search_params = models.SearchParams(hnsw_ef=128, exact=False)

        results = await self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=self.min_score,
            search_params=search_params,
            query_filter=self._build_filter(project_ids),
            with_payload=True,  # 🔧 CRITICAL: Explicitly request payload data
        )

        extracted_results = []
        for hit in results:
            extracted = {
                "score": hit.score,
                "text": hit.payload.get("content", "") if hit.payload else "",
                "metadata": hit.payload.get("metadata", {}) if hit.payload else {},
                "source_type": hit.payload.get("source_type", "unknown") if hit.payload else "unknown",
                # Extract fields directly from Qdrant payload
                "title": hit.payload.get("title", "") if hit.payload else "",
                "url": hit.payload.get("url", "") if hit.payload else "",
                "document_id": hit.payload.get("document_id", "") if hit.payload else "",
                "source": hit.payload.get("source", "") if hit.payload else "",
                "created_at": hit.payload.get("created_at", "") if hit.payload else "",
                "updated_at": hit.payload.get("updated_at", "") if hit.payload else "",
            }
            
            extracted_results.append(extracted)
        
        # Store results in cache if caching is enabled
        if self.cache_enabled:
            self._search_cache[cache_key] = {
                "results": extracted_results,
                "timestamp": time.time()
            }
            
            self.logger.debug(
                "Cached search results",
                query=query[:50],
                results_count=len(extracted_results),
                cache_size=len(self._search_cache)
            )
            
        return extracted_results

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics.
        
        Returns:
            Dictionary with cache hit rate, size, and other metrics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "cache_enabled": self.cache_enabled,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._search_cache),
            "cache_max_size": self.cache_max_size,
            "cache_ttl_seconds": self.cache_ttl
        }

    def clear_cache(self) -> None:
        """Clear all cached search results."""
        self._search_cache.clear()
        self.logger.info("Search result cache cleared")

    def _build_filter(
        self, project_ids: list[str] | None = None
    ) -> models.Filter | None:
        """Build a Qdrant filter based on project IDs.
        
        Args:
            project_ids: Optional list of project IDs to filter by
            
        Returns:
            Qdrant filter object or None if no filtering needed
        """
        if not project_ids:
            return None

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="project_id", match=models.MatchAny(any=project_ids)
                )
            ]
        )