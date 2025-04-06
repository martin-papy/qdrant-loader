import pytest
from unittest.mock import Mock, patch, MagicMock
from qdrant_client.http import models
from qdrant_loader.qdrant_manager import QdrantManager

@pytest.fixture
def mock_qdrant_client():
    mock_client = MagicMock()
    with patch('qdrant_client.QdrantClient', return_value=mock_client) as mock:
        yield mock_client

@pytest.fixture
def qdrant_manager(mock_qdrant_client, test_settings):
    manager = QdrantManager(settings=test_settings)
    manager.client = mock_qdrant_client
    return manager

def test_connect(qdrant_manager, mock_qdrant_client):
    assert qdrant_manager.client is not None
    assert qdrant_manager.client == mock_qdrant_client

def test_create_collection_new(qdrant_manager):
    # Mock the get_collections response
    mock_collection = models.CollectionDescription(
        name="other-collection"
    )
    qdrant_manager.client.get_collections.return_value = models.CollectionsResponse(
        collections=[mock_collection]
    )
    
    qdrant_manager.create_collection()
    
    qdrant_manager.client.create_collection.assert_called_once()
    qdrant_manager.client.get_collections.assert_called_once()

def test_create_collection_exists(qdrant_manager):
    # Mock the get_collections response with existing collection
    mock_collection = models.CollectionDescription(
        name=qdrant_manager.collection_name
    )
    qdrant_manager.client.get_collections.return_value = models.CollectionsResponse(
        collections=[mock_collection]
    )
    
    qdrant_manager.create_collection()
    
    qdrant_manager.client.create_collection.assert_not_called()
    qdrant_manager.client.get_collections.assert_called_once()

def test_upsert_points(qdrant_manager):
    # Create a vector with 1536 dimensions (OpenAI's text-embedding-3-small)
    vector = [0.1] * 1536
    points = [
        models.PointStruct(
            id=1,
            vector=vector,
            payload={"text": "test"}
        )
    ]
    
    qdrant_manager.upsert_points(points)
    
    qdrant_manager.client.upsert.assert_called_once_with(
        collection_name=qdrant_manager.collection_name,
        points=points,
        wait=True
    )

def test_search(qdrant_manager):
    # Create a query vector with 1536 dimensions
    query_vector = [0.1] * 1536
    limit = 5
    
    qdrant_manager.search(query_vector, limit)
    
    qdrant_manager.client.search.assert_called_once_with(
        collection_name=qdrant_manager.collection_name,
        query_vector=query_vector,
        limit=limit
    )

def test_delete_collection(qdrant_manager):
    qdrant_manager.delete_collection()
    
    qdrant_manager.client.delete_collection.assert_called_once_with(
        collection_name=qdrant_manager.collection_name
    ) 