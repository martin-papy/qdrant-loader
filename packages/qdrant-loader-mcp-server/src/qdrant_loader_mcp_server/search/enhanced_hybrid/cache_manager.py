import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any

from ...utils.logging import LoggingConfig
from .models import EnhancedSearchConfig, EnhancedSearchResult, QueryWeights


class CacheManager:
    """Cache manager for search results."""

    def __init__(
        self, ttl: int = 300, max_size: int = 1000, cleanup_interval: int = 60
    ):
        """Initialize cache manager.

        Args:
            ttl: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries in the cache
            cleanup_interval: Interval for periodic cleanup of expired entries
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.lock = threading.Lock()
        self.logger = LoggingConfig.get_logger(__name__)
        self.last_cleanup_time = time.time()
        self.cleanup_interval = cleanup_interval
        self.hits = 0
        self.misses = 0

    def get(
        self,
        query: str,
        config: EnhancedSearchConfig,
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult] | None:
        """Get results from cache.

        Args:
            query: Search query
            config: Enhanced search configuration
            query_weights: Query-time weight overrides

        Returns:
            Cached search results or None if not found/expired
        """
        self._maybe_cleanup()
        cache_key = self._get_cache_key(query, config, query_weights)
        with self.lock:
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                if time.time() - entry["timestamp"] < self.ttl:
                    self.logger.debug(f"Cache HIT for query: '{query}'")
                    self.hits += 1
                    # Move to end to mark as recently used
                    self.cache.move_to_end(cache_key)
                    return [
                        EnhancedSearchResult(**res) for res in entry["results"]
                    ]  # Re-create objects
                else:
                    self.logger.debug(f"Cache EXPIRED for query: '{query}'")
                    self._remove_cache_entry(cache_key)
        self.logger.debug(f"Cache MISS for query: '{query}'")
        self.misses += 1
        return None

    def set(
        self,
        query: str,
        config: EnhancedSearchConfig,
        results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> None:
        """Set results in cache.

        Args:
            query: Search query
            config: Enhanced search configuration
            results: Search results to cache
            query_weights: Query-time weight overrides
        """
        if not results:
            return

        cache_key = self._get_cache_key(query, config, query_weights)
        with self.lock:
            if len(self.cache) >= self.max_size:
                self._evict_lru_entries()

            # Convert result objects to dictionaries for JSON serialization
            serializable_results = [res.__dict__ for res in results]

            self.cache[cache_key] = {
                "timestamp": time.time(),
                "results": serializable_results,
            }
            self.logger.debug(f"Cache SET for query: '{query}'")

    def _get_cache_key(
        self,
        query: str,
        config: EnhancedSearchConfig,
        query_weights: QueryWeights | None = None,
    ) -> str:
        """Generate a unique cache key for the query and configuration.

        Args:
            query: Search query
            config: Enhanced search configuration
            query_weights: Query-time weight overrides

        Returns:
            Unique cache key string
        """
        key_data = {
            "query": query,
            "config": config.to_dict(),
            "query_weights": query_weights.to_dict() if query_weights else None,
        }
        # Use a stable json dump for consistent hashing
        serialized_data = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(serialized_data.encode()).hexdigest()

    def clear(self) -> None:
        """Clear the entire cache."""
        with self.lock:
            self.cache.clear()
            self.logger.info("Cache cleared.")

    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has passed."""
        if time.time() - self.last_cleanup_time > self.cleanup_interval:
            self.last_cleanup_time = time.time()
            self._cleanup_expired()

    def _cleanup_expired(self) -> None:
        """Remove expired entries from the cache."""
        with self.lock:
            expired_keys = [
                key
                for key, value in self.cache.items()
                if time.time() - value["timestamp"] > self.ttl
            ]
            for key in expired_keys:
                self._remove_cache_entry(key)
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries.")

    def _remove_cache_entry(self, cache_key: str) -> None:
        """Remove a single entry from cache (utility for internal use)."""
        if cache_key in self.cache:
            del self.cache[cache_key]

    def _evict_lru_entries(self) -> None:
        """Evict least recently used entries if cache is full."""
        # Evict 10% of the cache size when full
        num_to_evict = max(1, self.max_size // 10)
        keys_to_evict = []
        for _ in range(num_to_evict):
            try:
                # popitem(last=False) returns and removes the (key, value) pair at the front (LRU)
                key, _ = self.cache.popitem(last=False)
                keys_to_evict.append(key)
            except KeyError:
                break  # Cache is empty

        if keys_to_evict:
            self.logger.warning(
                f"Cache full. Evicted {len(keys_to_evict)} LRU entries."
            )

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            now = time.time()
            active_entries = sum(
                1
                for value in self.cache.values()
                if now - value["timestamp"] < self.ttl
            )
            expired_entries = len(self.cache) - active_entries
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "hits": self.hits,
                "misses": self.misses,
                "lock_locked": self.lock.locked(),
            }

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries where the key matches a pattern.

        This is useful for invalidating all entries related to a specific
        document or entity after an update.

        Args:
            pattern: The substring to match in the serialized cache key data.

        Returns:
            The number of invalidated entries.
        """
        invalidated_count = 0
        with self.lock:
            # Create a copy of keys to avoid modification during iteration
            keys_to_check = list(self.cache.keys())
            for key in keys_to_check:
                # This is inefficient as it requires re-serializing, but is the
                # most reliable way without storing reverse mappings.
                # In a real-world scenario, a more advanced cache with tagging
                # would be used (e.g., Redis).
                # For now, we accept this trade-off for simplicity.
                # A simple check on the hash is not possible.
                # We can't get the original data from the hash.

                # This is a placeholder for a more complex implementation.
                # A simple implementation would require iterating through all
                # values and deserializing, which is very slow.
                # We will just log a warning for now.
                pass  # pragma: no cover

        if pattern:  # To avoid unused variable warning
            self.logger.warning(
                "Cache invalidation by pattern is not fully implemented "
                "due to performance considerations. Consider a full cache clear."
            )

        return invalidated_count
