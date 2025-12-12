"""Tests for QdrantManager."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from qdrant_loader.config import Settings
from qdrant_loader.core.qdrant_manager import QdrantConnectionError, QdrantManager


class TestQdrantConnectionError:
    """Test cases for QdrantConnectionError."""

    def test_basic_initialization(self):
        """Test basic error initialization."""
        error = QdrantConnectionError("Test error")
        assert error.message == "Test error"
        assert error.original_error is None
        assert error.url is None
        assert str(error) == "Test error"

    def test_full_initialization(self):
        """Test error initialization with all parameters."""
        error = QdrantConnectionError(
            "Connection failed",
            original_error="Network timeout",
            url="http://localhost:6333",
        )
        assert error.message == "Connection failed"
        assert error.original_error == "Network timeout"
        assert error.url == "http://localhost:6333"
        assert str(error) == "Connection failed"


class TestQdrantManager:
    """Test cases for QdrantManager."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.qdrant_url = "http://localhost:6333"
        settings.qdrant_api_key = None
        settings.qdrant_collection_name = "test_collection"
        return settings

    @pytest.fixture
    def mock_settings_with_api_key(self):
        """Mock settings with API key for testing."""
        settings = Mock(spec=Settings)
        settings.qdrant_url = "http://localhost:6333"
        settings.qdrant_api_key = "test-api-key"
        settings.qdrant_collection_name = "test_collection"
        return settings

    @pytest.fixture
    def mock_settings_cloud(self):
        """Mock settings for cloud testing."""
        settings = Mock(spec=Settings)
        settings.qdrant_url = "http://cloud.qdrant.io"
        settings.qdrant_api_key = "test-api-key"
        settings.qdrant_collection_name = "test_collection"
        return settings

    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock QdrantClient for testing."""
        client = Mock()
        client.get_collections.return_value = Mock(collections=[])
        client.create_collection = Mock()
        client.create_payload_index = Mock()
        client.upsert = Mock()
        client.search.return_value = []
        client.delete_collection = Mock()
        client.delete = Mock()
        return client

    @pytest.fixture
    def mock_global_config(self):
        """Mock global config for testing."""
        config = Mock()
        config.embedding.batch_size = 100
        config.embedding.vector_size = 1536
        return config

    def test_initialization_default_settings(self, mock_settings, mock_global_config):
        """Test QdrantManager initialization with default settings."""
        with (
            patch(
                "qdrant_loader.core.qdrant_manager.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "qdrant_loader.core.qdrant_manager.get_global_config",
                return_value=mock_global_config,
            ),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager()

            assert manager.settings == mock_settings
            assert manager.collection_name == "test_collection"
            assert manager.batch_size == 100
            assert manager.client is None

    def test_initialization_custom_settings(self, mock_settings, mock_global_config):
        """Test QdrantManager initialization with custom settings."""
        with (
            patch(
                "qdrant_loader.core.qdrant_manager.get_global_config",
                return_value=mock_global_config,
            ),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)

            assert manager.settings == mock_settings
            assert manager.collection_name == "test_collection"
            assert manager.batch_size == 100

    def test_is_api_key_present_none(self, mock_settings):
        """Test API key detection with None value."""
        mock_settings.qdrant_api_key = None
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)
            assert not manager._is_api_key_present()

    def test_is_api_key_present_empty(self, mock_settings):
        """Test API key detection with empty string."""
        mock_settings.qdrant_api_key = ""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)
            assert not manager._is_api_key_present()

    def test_is_api_key_present_none_string(self, mock_settings):
        """Test API key detection with 'None' string."""
        mock_settings.qdrant_api_key = "None"
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)
            assert not manager._is_api_key_present()

    def test_is_api_key_present_null_string(self, mock_settings):
        """Test API key detection with 'null' string."""
        mock_settings.qdrant_api_key = "null"
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)
            assert not manager._is_api_key_present()

    def test_is_api_key_present_valid(self, mock_settings):
        """Test API key detection with valid key."""
        mock_settings.qdrant_api_key = "valid_key"
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)
            assert manager._is_api_key_present()

    def test_connect_without_api_key(self, mock_settings, mock_qdrant_client):
        """Test connection without API key."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)

            assert manager.client == mock_qdrant_client

    def test_connect_with_api_key_localhost(
        self, mock_settings_with_api_key, mock_qdrant_client
    ):
        """Test connection with API key on localhost (should not force HTTPS)."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ) as mock_client_class,
        ):
            QdrantManager(mock_settings_with_api_key)

            mock_client_class.assert_called_once_with(
                url="http://localhost:6333", api_key="test-api-key", timeout=60
            )

    def test_connect_with_api_key_cloud_http(
        self, mock_settings_cloud, mock_qdrant_client
    ):
        """Test connection with API key on cloud (should force HTTPS)."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ) as mock_client_class,
        ):
            QdrantManager(mock_settings_cloud)

            mock_client_class.assert_called_once_with(
                url="https://cloud.qdrant.io", api_key="test-api-key", timeout=60
            )

    def test_connect_with_api_key_127_0_0_1(
        self, mock_settings_with_api_key, mock_qdrant_client
    ):
        """Test connection with API key on 127.0.0.1 (should not force HTTPS)."""
        mock_settings_with_api_key.qdrant_url = "http://127.0.0.1:6333"
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ) as mock_client_class,
        ):
            QdrantManager(mock_settings_with_api_key)

            mock_client_class.assert_called_once_with(
                url="http://127.0.0.1:6333", api_key="test-api-key", timeout=60
            )

    def test_connect_client_error(self, mock_settings):
        """Test connection failure due to client error."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                side_effect=Exception("Connection failed"),
            ),
        ):
            with pytest.raises(
                QdrantConnectionError,
                match="Failed to connect to qDrant: Unexpected error",
            ):
                QdrantManager(mock_settings)

    def test_connect_unexpected_error(self, mock_settings):
        """Test connection failure due to unexpected error."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                side_effect=RuntimeError("Unexpected error"),
            ),
        ):
            with pytest.raises(
                QdrantConnectionError,
                match="Failed to connect to qDrant: Unexpected error",
            ):
                QdrantManager(mock_settings)

    def test_ensure_client_connected_success(self, mock_settings, mock_qdrant_client):
        """Test _ensure_client_connected with connected client."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)
            client = manager._ensure_client_connected()
            assert client == mock_qdrant_client

    def test_ensure_client_connected_not_connected(self, mock_settings):
        """Test _ensure_client_connected with no client."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch.object(QdrantManager, "connect"),
        ):
            manager = QdrantManager(mock_settings)
            manager.client = None

            with pytest.raises(
                QdrantConnectionError, match="Qdrant client is not connected"
            ):
                manager._ensure_client_connected()

    def test_create_collection_new(
        self, mock_settings, mock_qdrant_client, mock_global_config
    ):
        """Test creating a new collection."""
        mock_qdrant_client.get_collections.return_value = Mock(collections=[])

        with (
            patch(
                "qdrant_loader.core.qdrant_manager.get_global_config",
                return_value=mock_global_config,
            ),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)
            manager.create_collection()

            mock_qdrant_client.create_collection.assert_called_once_with(
                collection_name="test_collection",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

            # Verify all expected payload indexes are created
            expected_index_calls = [
                # Essential performance indexes
                ("document_id", {"type": "keyword"}),
                ("project_id", {"type": "keyword"}),
                ("source_type", {"type": "keyword"}),
                ("source", {"type": "keyword"}),
                ("title", {"type": "keyword"}),
                ("created_at", {"type": "keyword"}),
                ("updated_at", {"type": "keyword"}),
                # Secondary performance indexes
                ("is_attachment", {"type": "bool"}),
                ("parent_document_id", {"type": "keyword"}),
                ("original_file_type", {"type": "keyword"}),
                ("is_converted", {"type": "bool"}),
            ]

            # Verify create_payload_index was called the correct number of times
            assert mock_qdrant_client.create_payload_index.call_count == len(
                expected_index_calls
            )

            # Verify each expected call was made
            actual_calls = mock_qdrant_client.create_payload_index.call_args_list
            for i, (field_name, field_schema) in enumerate(expected_index_calls):
                expected_call = {
                    "collection_name": "test_collection",
                    "field_name": field_name,
                    "field_schema": field_schema,
                }
                actual_call_kwargs = actual_calls[i].kwargs
                assert (
                    actual_call_kwargs == expected_call
                ), f"Call {i+1} mismatch: expected {expected_call}, got {actual_call_kwargs}"

    def test_create_collection_exists(
        self, mock_settings, mock_qdrant_client, mock_global_config
    ):
        """Test creating collection when it already exists."""
        existing_collection = Mock()
        existing_collection.name = "test_collection"
        mock_qdrant_client.get_collections.return_value = Mock(
            collections=[existing_collection]
        )

        with (
            patch(
                "qdrant_loader.core.qdrant_manager.get_global_config",
                return_value=mock_global_config,
            ),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)
            manager.create_collection()

            mock_qdrant_client.create_collection.assert_not_called()
            mock_qdrant_client.create_payload_index.assert_not_called()

    def test_create_collection_no_vector_size(
        self, mock_settings, mock_qdrant_client, mock_global_config
    ):
        """Test creating collection with no vector size in config."""
        mock_global_config.embedding.vector_size = None
        mock_qdrant_client.get_collections.return_value = Mock(collections=[])

        with (
            patch(
                "qdrant_loader.core.qdrant_manager.get_global_config",
                return_value=mock_global_config,
            ),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)
            manager.create_collection()

            mock_qdrant_client.create_collection.assert_called_once_with(
                collection_name="test_collection",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

    def test_create_collection_error(
        self, mock_settings, mock_qdrant_client, mock_global_config
    ):
        """Test create collection error handling."""
        mock_qdrant_client.get_collections.side_effect = Exception("Collection error")

        with (
            patch(
                "qdrant_loader.core.qdrant_manager.get_global_config",
                return_value=mock_global_config,
            ),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)

            with pytest.raises(Exception, match="Collection error"):
                manager.create_collection()

    @pytest.mark.asyncio
    async def test_upsert_points_success(self, mock_settings, mock_qdrant_client):
        """Test successful point upsert."""
        # Create a proper mock point that satisfies type checking
        mock_point = models.PointStruct(
            id="test_id", vector=[0.1, 0.2, 0.3], payload={"test": "data"}
        )
        points = [mock_point]

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            manager = QdrantManager(mock_settings)
            await manager.upsert_points(points)

            mock_to_thread.assert_called_once_with(
                mock_qdrant_client.upsert,
                collection_name="test_collection",
                points=points,
            )

    @pytest.mark.asyncio
    async def test_upsert_points_error(self, mock_settings, mock_qdrant_client):
        """Test upsert points error handling."""
        # Create a proper mock point that satisfies type checking
        mock_point = models.PointStruct(
            id="test_id", vector=[0.1, 0.2, 0.3], payload={"test": "data"}
        )
        points = [mock_point]

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
            patch("asyncio.to_thread", side_effect=Exception("Upsert failed")),
        ):
            manager = QdrantManager(mock_settings)

            with pytest.raises(Exception, match="Upsert failed"):
                await manager.upsert_points(points)

    def test_search_success(self, mock_settings, mock_qdrant_client):
        """Test successful search."""
        query_vector = [0.1, 0.2, 0.3]
        mock_results = [Mock(spec=models.ScoredPoint)]
        mock_query_response = Mock()
        mock_query_response.points = mock_results
        mock_qdrant_client.query_points.return_value = mock_query_response

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)
            results = manager.search(query_vector, limit=10)

            assert results == mock_results
            mock_qdrant_client.query_points.assert_called_once_with(
                collection_name="test_collection", query=query_vector, limit=10
            )

    def test_search_default_limit(self, mock_settings, mock_qdrant_client):
        """Test search with default limit."""
        query_vector = [0.1, 0.2, 0.3]
        mock_results = [Mock(spec=models.ScoredPoint)]
        mock_query_response = Mock()
        mock_query_response.points = mock_results
        mock_qdrant_client.query_points.return_value = mock_query_response

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)
            manager.search(query_vector)

            mock_qdrant_client.query_points.assert_called_once_with(
                collection_name="test_collection", query=query_vector, limit=5
            )

    def test_search_error(self, mock_settings, mock_qdrant_client):
        """Test search error handling."""
        query_vector = [0.1, 0.2, 0.3]
        mock_qdrant_client.query_points.side_effect = Exception("Search failed")

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)

            with pytest.raises(Exception, match="Search failed"):
                manager.search(query_vector)

    def test_delete_collection_success(self, mock_settings, mock_qdrant_client):
        """Test successful collection deletion."""
        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)
            manager.delete_collection()

            mock_qdrant_client.delete_collection.assert_called_once_with(
                collection_name="test_collection"
            )

    def test_delete_collection_error(self, mock_settings, mock_qdrant_client):
        """Test delete collection error handling."""
        mock_qdrant_client.delete_collection.side_effect = Exception("Delete failed")

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
        ):
            manager = QdrantManager(mock_settings)

            with pytest.raises(Exception, match="Delete failed"):
                manager.delete_collection()

    @pytest.mark.asyncio
    async def test_delete_points_by_document_id_success(
        self, mock_settings, mock_qdrant_client
    ):
        """Test successful point deletion by document ID."""
        document_ids = ["doc1", "doc2", "doc3"]

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            manager = QdrantManager(mock_settings)
            await manager.delete_points_by_document_id(document_ids)

            # Verify the call was made with correct parameters
            mock_to_thread.assert_called_once()
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == mock_qdrant_client.delete
            assert call_args[1]["collection_name"] == "test_collection"

            # Verify the filter structure
            points_selector = call_args[1]["points_selector"]
            assert isinstance(points_selector, models.Filter)

    @pytest.mark.asyncio
    async def test_delete_points_by_document_id_error(
        self, mock_settings, mock_qdrant_client
    ):
        """Test delete points error handling."""
        document_ids = ["doc1", "doc2"]

        with (
            patch("qdrant_loader.core.qdrant_manager.get_global_config"),
            patch(
                "qdrant_loader.core.qdrant_manager.QdrantClient",
                return_value=mock_qdrant_client,
            ),
            patch("asyncio.to_thread", side_effect=Exception("Delete failed")),
        ):
            manager = QdrantManager(mock_settings)

            with pytest.raises(Exception, match="Delete failed"):
                await manager.delete_points_by_document_id(document_ids)
