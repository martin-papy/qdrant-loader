"""Tests for the FAISSSearchService class."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_loader.core.embedding import EmbeddingService
from qdrant_loader.core.search.faiss_search import FAISSSearchService


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = MagicMock(spec=QdrantClient)

    # Mock collection info
    collection_info = MagicMock()
    collection_info.config = MagicMock()
    collection_info.config.params = MagicMock()
    collection_info.config.params.vectors = MagicMock()
    collection_info.config.params.vectors.size = 384
    client.get_collection.return_value = collection_info

    # Mock scroll response
    client.scroll.return_value = (
        [
            models.Record(
                id=1,
                vector=[0.1] * 384,
                payload={"content": "Test content 1", "metadata": {"source": "test1"}},
            ),
            models.Record(
                id=2,
                vector=[0.2] * 384,
                payload={"content": "Test content 2", "metadata": {"source": "test2"}},
            ),
        ],
        None,
    )

    # Mock retrieve response
    client.retrieve.return_value = [
        models.Record(
            id=1,
            vector=[0.1] * 384,
            payload={"content": "Test content 1", "metadata": {"source": "test1"}},
        )
    ]

    return client


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = AsyncMock(spec=EmbeddingService)
    service.generate_embedding.return_value = [0.1] * 384
    return service


@pytest.fixture
def mock_faiss_index():
    """Create a mock FAISS index."""
    index = MagicMock()
    index.search.return_value = (np.array([[0.8, 0.6]]), np.array([[0, 1]]))
    index.is_trained = True
    return index


@pytest.fixture
def faiss_search(mock_qdrant_client, mock_embedding_service, mock_faiss_index):
    """Create a FAISSSearchService instance for testing."""
    with patch("faiss.IndexIVFFlat", return_value=mock_faiss_index):
        service = FAISSSearchService(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
            collection_name="test_collection",
        )
        service.index = mock_faiss_index
        return service


@pytest.mark.asyncio
async def test_search(faiss_search, mock_qdrant_client, mock_embedding_service):
    """Test basic search functionality."""
    results = await faiss_search.search("test query")

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["score"] == 0.8
    assert results[0]["content"] == "Test content 1"
    assert results[0]["metadata"]["source"] == "test1"

    mock_embedding_service.generate_embedding.assert_called_once_with("test query")
    mock_qdrant_client.retrieve.assert_called_once()


@pytest.mark.asyncio
async def test_search_with_filters(faiss_search, mock_qdrant_client):
    """Test search with filter conditions."""
    # Mock point with matching filter
    mock_qdrant_client.retrieve.return_value = [
        models.Record(
            id=1,
            vector=[0.1] * 384,
            payload={
                "content": "Test content",
                "metadata": {"source": "test1", "category": "test"},
            },
        )
    ]

    results = await faiss_search.search(
        "test query", filter_conditions={"category": "test"}
    )

    assert len(results) == 1
    assert results[0]["metadata"]["category"] == "test"


@pytest.mark.asyncio
async def test_search_below_min_score(faiss_search, mock_qdrant_client):
    """Test search with results below minimum score."""
    # Mock FAISS search results with low score
    faiss_search.index.search.return_value = (
        np.array([[0.5]]),  # Below default min_score of 0.7
        np.array([[0]]),
    )

    results = await faiss_search.search("test query")

    assert len(results) == 0


def test_index_initialization(faiss_search):
    """Test FAISS index initialization."""
    assert faiss_search.index is not None
    assert faiss_search.vector_dim == 384
    assert faiss_search.index_type == "IVFFlat"
    assert faiss_search.nlist == 100
    assert faiss_search.nprobe == 10


def test_update_index(faiss_search, mock_qdrant_client):
    """Test index update functionality."""
    faiss_search.update_index()

    # Verify index was reset and vectors were reloaded
    faiss_search.index.reset.assert_called_once()
    mock_qdrant_client.scroll.assert_called()
