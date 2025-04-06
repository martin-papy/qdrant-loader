import pytest
from unittest.mock import Mock, patch, MagicMock
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_loader.qdrant_manager import QdrantManager

@pytest.fixture
def mock_qdrant_client():
    mock_client = MagicMock()
    return mock_client

@pytest.fixture
def qdrant_manager(test_settings):
    with patch('qdrant_loader.qdrant_manager.QdrantClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        manager = QdrantManager(settings=test_settings)
        return manager

def test_init_no_settings():
    """Test initialization with no settings provided."""
    with patch('qdrant_loader.qdrant_manager.get_settings', return_value=None):
        with pytest.raises(ValueError, match="Settings must be provided either through environment or constructor"):
            QdrantManager()

def test_init_connection_error():
    """Test initialization with connection error."""
    with patch('qdrant_loader.qdrant_manager.QdrantClient', side_effect=Exception("Connection Error")):
        with pytest.raises(Exception, match="Connection Error"):
            QdrantManager(settings=Mock(QDRANT_URL="test", QDRANT_API_KEY="test", QDRANT_COLLECTION_NAME="test"))

def test_connect(qdrant_manager):
    assert qdrant_manager.client is not None

def test_connect_error():
    """Test connection error handling."""
    with patch('qdrant_loader.qdrant_manager.QdrantClient', side_effect=Exception("Connection Error")):
        with pytest.raises(Exception, match="Connection Error"):
            QdrantManager(settings=Mock(QDRANT_URL="test", QDRANT_API_KEY="test", QDRANT_COLLECTION_NAME="test"))

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

def test_create_collection_error(qdrant_manager):
    """Test create collection error handling."""
    error = UnexpectedResponse(
        status_code=400,
        reason_phrase="Bad Request",
        content=b"API Error",
        headers={"Content-Type": "text/plain"}
    )
    qdrant_manager.client.get_collections.side_effect = error
    
    with pytest.raises(UnexpectedResponse):
        qdrant_manager.create_collection()

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

def test_upsert_points_error(qdrant_manager):
    """Test upsert points error handling."""
    qdrant_manager.client.upsert.side_effect = Exception("API Error")
    
    with pytest.raises(Exception, match="API Error"):
        qdrant_manager.upsert_points([Mock()])

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

def test_search_error(qdrant_manager):
    """Test search error handling."""
    qdrant_manager.client.search.side_effect = Exception("API Error")
    
    with pytest.raises(Exception, match="API Error"):
        qdrant_manager.search([0.1] * 1536)

def test_delete_collection(qdrant_manager):
    qdrant_manager.delete_collection()
    
    qdrant_manager.client.delete_collection.assert_called_once_with(
        collection_name=qdrant_manager.collection_name
    )

def test_delete_collection_error(qdrant_manager):
    """Test delete collection error handling."""
    qdrant_manager.client.delete_collection.side_effect = Exception("API Error")
    
    with pytest.raises(Exception, match="API Error"):
        qdrant_manager.delete_collection() 