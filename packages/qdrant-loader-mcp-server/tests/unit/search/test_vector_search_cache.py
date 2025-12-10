"""Unit tests for vector search caching functionality."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader_mcp_server.search.components.vector_search_service import (
    VectorSearchService,
)


@pytest.fixture
def mock_qdrant_client():
    """Mock QDrant client for testing."""
    client = MagicMock()
    client.search = AsyncMock()
    return client


@pytest.fixture
def mock_embeddings_provider():
    class _EmbeddingsClient:
        async def embed(self, inputs):  # type: ignore[no-untyped-def]
            return [[0.1, 0.2, 0.3] for _ in inputs]

    class _Provider:
        def embeddings(self):
            return _EmbeddingsClient()

    return _Provider()


@pytest.fixture
def vector_search_service(mock_qdrant_client, mock_embeddings_provider):
    """Create vector search service with caching enabled."""
    return VectorSearchService(
        qdrant_client=mock_qdrant_client,
        embeddings_provider=mock_embeddings_provider,
        collection_name="test_collection",
        cache_enabled=True,
        cache_ttl=300,  # 5 minutes
        cache_max_size=100,
    )


@pytest.fixture
def vector_search_service_no_cache(mock_qdrant_client, mock_embeddings_provider):
    """Create vector search service with caching disabled."""
    return VectorSearchService(
        qdrant_client=mock_qdrant_client,
        embeddings_provider=mock_embeddings_provider,
        collection_name="test_collection",
        cache_enabled=False,
    )


@pytest.fixture
def sample_search_results():
    """Sample search results from QDrant."""
    hit1 = MagicMock()
    hit1.score = 0.95
    hit1.payload = {
        "content": "Test content 1",
        "metadata": {"key1": "value1"},
        "source_type": "test",
        "title": "Test Title 1",
        "url": "https://example.com/1",
        "document_id": "doc1",
        "source": "test_source",
        "created_at": "2023-01-01",
        "updated_at": "2023-01-02",
    }

    hit2 = MagicMock()
    hit2.score = 0.87
    hit2.payload = {
        "content": "Test content 2",
        "metadata": {"key2": "value2"},
        "source_type": "test",
        "title": "Test Title 2",
        "url": "https://example.com/2",
        "document_id": "doc2",
        "source": "test_source",
        "created_at": "2023-01-01",
        "updated_at": "2023-01-02",
    }

    return [hit1, hit2]


class TestVectorSearchCache:
    """Test cases for vector search caching functionality."""

    def test_cache_key_generation(self, vector_search_service):
        """Test cache key generation with different parameters."""
        # Same parameters should generate same key
        key1 = vector_search_service._generate_cache_key("test query", 10)
        key2 = vector_search_service._generate_cache_key("test query", 10)
        assert key1 == key2

        # Different queries should generate different keys
        key3 = vector_search_service._generate_cache_key("different query", 10)
        assert key1 != key3

        # Different limits should generate different keys
        key4 = vector_search_service._generate_cache_key("test query", 20)
        assert key1 != key4

        # Different project IDs should generate different keys
        key5 = vector_search_service._generate_cache_key("test query", 10, ["project1"])
        assert key1 != key5

        # Same project IDs in different order should generate same key
        key6 = vector_search_service._generate_cache_key(
            "test query", 10, ["project1", "project2"]
        )
        key7 = vector_search_service._generate_cache_key(
            "test query", 10, ["project2", "project1"]
        )
        assert key6 == key7

    def test_cache_initialization(
        self, vector_search_service, vector_search_service_no_cache
    ):
        """Test cache initialization with different settings."""
        # Cache enabled service
        assert vector_search_service.cache_enabled is True
        assert vector_search_service.cache_ttl == 300
        assert vector_search_service.cache_max_size == 100
        assert vector_search_service._cache_hits == 0
        assert vector_search_service._cache_misses == 0
        assert len(vector_search_service._search_cache) == 0

        # Cache disabled service
        assert vector_search_service_no_cache.cache_enabled is False

    @patch("qdrant_loader_mcp_server.search.components.vector_search_service.time.time")
    @pytest.mark.asyncio
    async def test_cache_hit(
        self, mock_time, vector_search_service, sample_search_results
    ):
        """Test cache hit scenario."""
        mock_time.return_value = 1000.0

        # Mock the get_embedding method
        vector_search_service.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        # Mock QDrant query_points response (qdrant-client 1.10+)
        mock_query_response = MagicMock()
        mock_query_response.points = sample_search_results
        vector_search_service.qdrant_client.query_points = AsyncMock(
            return_value=mock_query_response
        )

        # First call - should be a cache miss
        results1 = await vector_search_service.vector_search("test query", 10)
        assert vector_search_service._cache_misses == 1
        assert vector_search_service._cache_hits == 0
        assert len(results1) == 2

        # Second call with same parameters - should be a cache hit
        results2 = await vector_search_service.vector_search("test query", 10)
        assert vector_search_service._cache_misses == 1
        assert vector_search_service._cache_hits == 1
        assert results1 == results2

        # Verify QDrant was only called once
        assert vector_search_service.qdrant_client.query_points.call_count == 1

    @patch("qdrant_loader_mcp_server.search.components.vector_search_service.time.time")
    @pytest.mark.asyncio
    async def test_cache_expiry(
        self, mock_time, vector_search_service, sample_search_results
    ):
        """Test cache expiry functionality."""
        # Mock the get_embedding method
        vector_search_service.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        # Mock QDrant query_points response (qdrant-client 1.10+)
        mock_query_response = MagicMock()
        mock_query_response.points = sample_search_results
        vector_search_service.qdrant_client.query_points = AsyncMock(
            return_value=mock_query_response
        )

        # First call at time 1000
        mock_time.return_value = 1000.0
        await vector_search_service.vector_search("test query", 10)
        assert vector_search_service._cache_misses == 1

        # Second call at time 1200 (within TTL of 300 seconds) - should be cache hit
        mock_time.return_value = 1200.0
        await vector_search_service.vector_search("test query", 10)
        assert vector_search_service._cache_hits == 1

        # Third call at time 1400 (beyond TTL) - should be cache miss
        mock_time.return_value = 1400.0
        await vector_search_service.vector_search("test query", 10)
        assert vector_search_service._cache_misses == 2

    @pytest.mark.asyncio
    async def test_cache_disabled(
        self, vector_search_service_no_cache, sample_search_results
    ):
        """Test behavior when caching is disabled."""
        # Mock the get_embedding method
        vector_search_service_no_cache.get_embedding = AsyncMock(
            return_value=[0.1, 0.2, 0.3]
        )

        # Mock QDrant query_points response (qdrant-client 1.10+)
        mock_query_response = MagicMock()
        mock_query_response.points = sample_search_results
        vector_search_service_no_cache.qdrant_client.query_points = AsyncMock(
            return_value=mock_query_response
        )

        # Multiple calls with same parameters
        await vector_search_service_no_cache.vector_search("test query", 10)
        await vector_search_service_no_cache.vector_search("test query", 10)

        # Both should be cache misses since caching is disabled
        assert vector_search_service_no_cache._cache_misses == 2
        assert vector_search_service_no_cache._cache_hits == 0

        # QDrant should be called twice
        assert vector_search_service_no_cache.qdrant_client.query_points.call_count == 2

    def test_cache_cleanup_expired_entries(self, vector_search_service):
        """Test cleanup of expired cache entries."""
        with patch(
            "qdrant_loader_mcp_server.search.components.vector_search_service.time.time"
        ) as mock_time:
            # Add some cache entries at different times
            mock_time.return_value = 1000.0
            vector_search_service._search_cache["key1"] = {
                "results": [],
                "timestamp": 1000.0,
            }
            vector_search_service._search_cache["key2"] = {
                "results": [],
                "timestamp": 1100.0,
            }

            # Move time forward beyond TTL for first entry
            mock_time.return_value = 1400.0  # 400 seconds later
            vector_search_service._cleanup_expired_cache()

            # First entry should be removed, second should remain
            assert "key1" not in vector_search_service._search_cache
            assert "key2" in vector_search_service._search_cache

    def test_cache_size_limit(self, vector_search_service):
        """Test cache size limit enforcement."""
        # Set small cache size for testing
        vector_search_service.cache_max_size = 2

        with patch(
            "qdrant_loader_mcp_server.search.components.vector_search_service.time.time"
        ) as mock_time:
            mock_time.return_value = 1000.0

            # Add entries up to the limit
            vector_search_service._search_cache["key1"] = {
                "results": [],
                "timestamp": 1000.0,
            }
            vector_search_service._search_cache["key2"] = {
                "results": [],
                "timestamp": 1001.0,
            }
            vector_search_service._search_cache["key3"] = {
                "results": [],
                "timestamp": 1002.0,
            }

            # Cleanup should remove oldest entry
            vector_search_service._cleanup_expired_cache()

            assert len(vector_search_service._search_cache) == 2
            assert "key1" not in vector_search_service._search_cache
            assert "key2" in vector_search_service._search_cache
            assert "key3" in vector_search_service._search_cache

    def test_cache_stats(self, vector_search_service):
        """Test cache statistics functionality."""
        # Initial stats
        stats = vector_search_service.get_cache_stats()
        assert stats["cache_enabled"] is True
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate_percent"] == 0.0
        assert stats["cache_size"] == 0

        # Simulate some cache activity
        vector_search_service._cache_hits = 7
        vector_search_service._cache_misses = 3
        vector_search_service._search_cache["test"] = {
            "results": [],
            "timestamp": time.time(),
        }

        stats = vector_search_service.get_cache_stats()
        assert stats["cache_hits"] == 7
        assert stats["cache_misses"] == 3
        assert stats["hit_rate_percent"] == 70.0
        assert stats["cache_size"] == 1

    def test_clear_cache(self, vector_search_service):
        """Test cache clearing functionality."""
        # Add some cache entries
        vector_search_service._search_cache["key1"] = {
            "results": [],
            "timestamp": time.time(),
        }
        vector_search_service._search_cache["key2"] = {
            "results": [],
            "timestamp": time.time(),
        }

        assert len(vector_search_service._search_cache) == 2

        # Clear cache
        vector_search_service.clear_cache()

        assert len(vector_search_service._search_cache) == 0

    @pytest.mark.asyncio
    async def test_project_filter_caching(
        self, vector_search_service, sample_search_results
    ):
        """Test caching with project ID filters."""
        # Mock the get_embedding method
        vector_search_service.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        # Mock QDrant query_points response (qdrant-client 1.10+)
        mock_query_response = MagicMock()
        mock_query_response.points = sample_search_results
        vector_search_service.qdrant_client.query_points = AsyncMock(
            return_value=mock_query_response
        )

        # Search with different project filters should create separate cache entries
        await vector_search_service.vector_search("test query", 10, ["project1"])
        await vector_search_service.vector_search("test query", 10, ["project2"])
        await vector_search_service.vector_search(
            "test query", 10, ["project1"]
        )  # Should hit cache

        assert vector_search_service._cache_misses == 2  # First two calls
        assert vector_search_service._cache_hits == 1  # Third call
        assert vector_search_service.qdrant_client.query_points.call_count == 2

    @pytest.mark.asyncio
    async def test_result_format_consistency(
        self, vector_search_service, sample_search_results
    ):
        """Test that cached results maintain the same format as fresh results."""
        # Mock the get_embedding method
        vector_search_service.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        # Mock QDrant query_points response (qdrant-client 1.10+)
        mock_query_response = MagicMock()
        mock_query_response.points = sample_search_results
        vector_search_service.qdrant_client.query_points = AsyncMock(
            return_value=mock_query_response
        )

        # Get fresh results
        fresh_results = await vector_search_service.vector_search("test query", 10)

        # Get cached results
        cached_results = await vector_search_service.vector_search("test query", 10)

        # Results should be identical
        assert fresh_results == cached_results

        # Verify structure of results
        assert len(cached_results) == 2
        assert "score" in cached_results[0]
        assert "text" in cached_results[0]
        assert "metadata" in cached_results[0]
        assert "source_type" in cached_results[0]
        assert "title" in cached_results[0]
        assert cached_results[0]["score"] == 0.95
        assert cached_results[0]["text"] == "Test content 1"
