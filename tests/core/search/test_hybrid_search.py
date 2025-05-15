"""Tests for hybrid search implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_loader.core.search.hybrid_search import HybridSearchService, SearchResult
from qdrant_loader.core.embedding.embedding_service import EmbeddingService

@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = MagicMock(spec=QdrantClient)
    return client

@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = AsyncMock(spec=EmbeddingService)
    service.get_embedding.return_value = [0.1] * 1536  # Mock embedding vector
    return service

@pytest.fixture
def hybrid_search(mock_qdrant_client, mock_embedding_service):
    """Create a HybridSearchService instance with mocked dependencies."""
    return HybridSearchService(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        collection_name="test_collection"
    )

@pytest.mark.asyncio
async def test_vector_search(hybrid_search, mock_qdrant_client, mock_embedding_service):
    """Test vector search functionality."""
    # Mock search results
    mock_results = [
        models.ScoredPoint(
            id="1",
            version=1,
            score=0.8,
            payload={"content": "Test content 1", "metadata": {"source": "test"}}
        ),
        models.ScoredPoint(
            id="2",
            version=1,
            score=0.6,
            payload={"content": "Test content 2", "metadata": {"source": "test"}}
        )
    ]
    mock_qdrant_client.search.return_value = mock_results
    
    # Test vector search
    results = await hybrid_search._vector_search("test query", limit=2)
    
    # Verify results
    assert len(results) == 2
    assert results[0]["id"] == "1"
    assert results[0]["score"] == 0.8
    assert results[0]["content"] == "Test content 1"
    assert results[1]["id"] == "2"
    assert results[1]["score"] == 0.6
    assert results[1]["content"] == "Test content 2"
    
    # Verify embedding service was called
    mock_embedding_service.get_embedding.assert_called_once_with("test query")
    
    # Verify Qdrant search was called with correct parameters
    mock_qdrant_client.search.assert_called_once()
    call_args = mock_qdrant_client.search.call_args[1]
    assert call_args["collection_name"] == "test_collection"
    assert call_args["limit"] == 2
    assert call_args["score_threshold"] == 0.3

@pytest.mark.asyncio
async def test_keyword_search(hybrid_search, mock_qdrant_client):
    """Test keyword search functionality."""
    # Mock scroll results
    mock_points = [
        models.Record(
            id="1",
            payload={"content": "This is a test document about Python programming"}
        ),
        models.Record(
            id="2",
            payload={"content": "Another document about machine learning"}
        )
    ]
    mock_qdrant_client.scroll.return_value = ([mock_points], None)
    
    # Test keyword search
    results = await hybrid_search._keyword_search("Python programming", limit=2)
    
    # Verify results
    assert len(results) == 2
    assert results[0]["id"] in ["1", "2"]
    assert "content" in results[0]
    assert isinstance(results[0]["score"], float)
    
    # Verify Qdrant scroll was called
    mock_qdrant_client.scroll.assert_called_once()
    call_args = mock_qdrant_client.scroll.call_args[1]
    assert call_args["collection_name"] == "test_collection"
    assert call_args["limit"] == 10000
    assert call_args["with_payload"] is True
    assert call_args["with_vectors"] is False

@pytest.mark.asyncio
async def test_hybrid_search(hybrid_search):
    """Test combined hybrid search functionality."""
    # Mock vector search results
    vector_results = [
        {
            "id": "1",
            "score": 0.8,
            "content": "Test content 1",
            "metadata": {"source": "test"}
        },
        {
            "id": "2",
            "score": 0.6,
            "content": "Test content 2",
            "metadata": {"source": "test"}
        }
    ]
    
    # Mock keyword search results
    keyword_results = [
        {
            "id": "1",
            "score": 0.9,
            "content": "Test content 1",
            "metadata": {}
        },
        {
            "id": "3",
            "score": 0.7,
            "content": "Test content 3",
            "metadata": {}
        }
    ]
    
    # Mock the internal search methods
    hybrid_search._vector_search = AsyncMock(return_value=vector_results)
    hybrid_search._keyword_search = AsyncMock(return_value=keyword_results)
    
    # Test hybrid search
    results = await hybrid_search.search("test query", limit=2)
    
    # Verify results
    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    assert results[0].id == "1"  # Should be first due to high scores in both searches
    assert 0 <= results[0].score <= 1
    assert results[0].vector_score > 0
    assert results[0].keyword_score > 0
    
    # Verify search methods were called
    hybrid_search._vector_search.assert_called_once_with("test query", 4, None)
    hybrid_search._keyword_search.assert_called_once_with("test query", 4, None)

@pytest.mark.asyncio
async def test_search_with_filters(hybrid_search):
    """Test search with filter conditions."""
    # Mock search results
    vector_results = [
        {
            "id": "1",
            "score": 0.8,
            "content": "Test content 1",
            "metadata": {"source": "test"}
        }
    ]
    keyword_results = [
        {
            "id": "1",
            "score": 0.9,
            "content": "Test content 1",
            "metadata": {}
        }
    ]
    
    # Mock the internal search methods
    hybrid_search._vector_search = AsyncMock(return_value=vector_results)
    hybrid_search._keyword_search = AsyncMock(return_value=keyword_results)
    
    # Test search with filters
    filter_conditions = {"source": "test"}
    results = await hybrid_search.search("test query", limit=1, filter_conditions=filter_conditions)
    
    # Verify results
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].metadata["source"] == "test"
    
    # Verify search methods were called with filters
    hybrid_search._vector_search.assert_called_once_with("test query", 2, filter_conditions)
    hybrid_search._keyword_search.assert_called_once_with("test query", 2, filter_conditions) 