"""
Tests for the ingestion pipeline.
"""

import logging
from datetime import datetime
from logging import getLogger
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.connectors.public_docs.config import PublicDocsSourceConfig, SelectorsConfig
from qdrant_loader.core.chunking_service import ChunkingService
from qdrant_loader.core.document import Document
from qdrant_loader.core.ingestion_pipeline import IngestionPipeline
from qdrant_loader.connectors.git.config import GitRepoConfig

logger = getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mock_documents():
    """Create mock documents."""
    return [
        Document(
            content="Test content 1",
            source="test-source",
            source_type="confluence",
            metadata={"space": "SPACE1", "content_type": "page"},
            created_at=datetime.now(),
            url="https://test.com/doc1",
        )
    ]


@pytest_asyncio.fixture
async def async_session():
    """Create an async session for testing."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_chunking_service():
    """Create a mock chunking service."""
    mock = MagicMock()
    mock.chunk_document.return_value = []
    return mock


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    mock = MagicMock()
    mock.embed_documents.return_value = []
    return mock


@pytest.fixture
def mock_qdrant_manager():
    """Create a mock Qdrant manager."""
    mock = MagicMock()
    mock.client.get_collections.return_value = MagicMock(collections=[])
    return mock


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    mock = MagicMock()
    return mock


@pytest.mark.asyncio
async def test_ingestion_pipeline_init(test_settings):
    """Test pipeline initialization."""
    with (
        patch(
            "qdrant_loader.core.ingestion_pipeline.ChunkingService.__new__"
        ) as mock_chunking_service_new,
        patch(
            "qdrant_loader.core.ingestion_pipeline.EmbeddingService"
        ) as mock_embedding_service_cls,
        patch("qdrant_loader.core.ingestion_pipeline.QdrantManager") as mock_qdrant_manager_cls,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager_cls,
    ):
        # Set up mock instances
        mock_chunking_service = MagicMock()
        mock_embedding_service = MagicMock()
        mock_qdrant_manager = MagicMock()
        mock_state_manager = MagicMock()

        # Configure mock classes to return their instances
        mock_chunking_service_new.return_value = mock_chunking_service
        mock_embedding_service_cls.return_value = mock_embedding_service
        mock_qdrant_manager_cls.return_value = mock_qdrant_manager
        mock_state_manager_cls.return_value = mock_state_manager

        # Create pipeline
        pipeline = IngestionPipeline(test_settings)

        # Verify initialization
        assert pipeline.settings == test_settings
        assert pipeline.config == test_settings.global_config
        assert pipeline.chunking_service == mock_chunking_service
        assert pipeline.embedding_service == mock_embedding_service
        assert pipeline.qdrant_manager == mock_qdrant_manager
        assert pipeline.state_manager == mock_state_manager

        # Verify ChunkingService was called with correct arguments
        mock_chunking_service_new.assert_called_once_with(
            ChunkingService, config=test_settings.global_config, settings=test_settings
        )


@pytest.mark.asyncio
async def test_ingestion_pipeline_init_no_settings():
    """Test pipeline initialization with no settings."""
    with pytest.raises(
        ValueError,
        match="Global configuration not available. Please check your configuration file.",
    ):
        # Create pipeline with invalid settings
        mock_settings = MagicMock(spec=Settings)
        mock_settings.global_config = None
        IngestionPipeline(mock_settings)


@pytest.mark.asyncio
async def test_process_documents_no_sources(test_settings):
    """Test processing with no sources."""
    with (
        patch(
            "qdrant_loader.core.ingestion_pipeline.ChunkingService.__new__"
        ) as mock_chunking_service_new,
        patch(
            "qdrant_loader.core.ingestion_pipeline.EmbeddingService"
        ) as mock_embedding_service_cls,
        patch("qdrant_loader.core.ingestion_pipeline.QdrantManager") as mock_qdrant_manager_cls,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager_cls,
        patch(
            "qdrant_loader.connectors.git.connector.GitConnector.get_documents"
        ) as mock_get_documents,
        patch("qdrant_loader.core.ingestion_pipeline.Settings") as mock_settings,
    ):
        # Set up mock instances
        mock_chunking_service = MagicMock()
        mock_embedding_service = MagicMock()
        mock_qdrant_manager = MagicMock()
        mock_state_manager = MagicMock()

        # Configure mock classes to return their instances
        mock_chunking_service_new.return_value = mock_chunking_service
        mock_embedding_service_cls.return_value = mock_embedding_service
        mock_qdrant_manager_cls.return_value = mock_qdrant_manager
        mock_state_manager_cls.return_value = mock_state_manager

        # Mock Git documents
        mock_get_documents.return_value = []

        # Make mock methods return coroutines
        mock_state_manager.update_document_state = AsyncMock(return_value=None)
        mock_embedding_service.get_embeddings = AsyncMock(return_value=[])
        mock_qdrant_manager.upsert_points = AsyncMock(return_value=None)

        # Create mock settings with no sources
        mock_settings_instance = MagicMock()
        mock_settings_instance.sources_config = None
        mock_settings.return_value = mock_settings_instance

        # Create pipeline
        pipeline = IngestionPipeline(mock_settings_instance)

        # Test processing with no sources
        result = await pipeline.process_documents()
        assert result == []


@pytest.mark.asyncio
async def test_process_documents_public_docs(test_settings, mock_documents):
    """Test processing public docs."""
    with (
        patch("qdrant_loader.core.ingestion_pipeline.PublicDocsConnector") as mock_connector,
        patch("qdrant_loader.core.ingestion_pipeline.ChunkingService") as mock_chunking_service,
        patch("qdrant_loader.core.ingestion_pipeline.EmbeddingService") as mock_embedding_service,
        patch("qdrant_loader.core.ingestion_pipeline.QdrantManager") as mock_qdrant_manager,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager,
    ):
        # Set up mocks
        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documentation = AsyncMock(return_value=mock_documents)
        mock_connector.return_value = mock_connector_instance

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [mock_documents[0]]
        mock_chunking_service.return_value = mock_chunking

        mock_embedding = AsyncMock()
        mock_embedding.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        mock_embedding_service.return_value = mock_embedding

        mock_qdrant = AsyncMock()
        mock_qdrant.upsert_points = AsyncMock()
        mock_qdrant_manager.return_value = mock_qdrant

        mock_state = AsyncMock()
        mock_state.update_document_state = AsyncMock()
        mock_state_manager.return_value = mock_state

        pipeline = IngestionPipeline(test_settings)

        # Process the documents
        documents = await pipeline.process_documents(
            test_settings.sources_config, source_type="public-docs"
        )

        # Verify the mocks were called
        mock_connector_instance.get_documentation.assert_awaited_once()
        mock_chunking.chunk_document.assert_called_once_with(mock_documents[0])
        mock_embedding.get_embeddings.assert_awaited_once_with([mock_documents[0].content])
        mock_qdrant.upsert_points.assert_awaited_once()
        mock_state.update_document_state.assert_awaited_once()
        assert len(documents) == 1


@pytest.mark.asyncio
async def test_process_documents_error(test_settings):
    """Test error handling in document processing."""
    with (
        patch(
            "qdrant_loader.core.ingestion_pipeline.ChunkingService.__new__"
        ) as mock_chunking_service_new,
        patch(
            "qdrant_loader.core.ingestion_pipeline.EmbeddingService"
        ) as mock_embedding_service_cls,
        patch("qdrant_loader.core.ingestion_pipeline.QdrantManager") as mock_qdrant_manager_cls,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager_cls,
        patch("qdrant_loader.connectors.git.connector.GitOperations") as mock_git_ops,
    ):
        # Set up mock instances
        mock_chunking_service = MagicMock()
        mock_embedding_service = MagicMock()
        mock_qdrant_manager = MagicMock()
        mock_state_manager = MagicMock()

        # Configure mock classes to return their instances
        mock_chunking_service_new.return_value = mock_chunking_service
        mock_embedding_service_cls.return_value = mock_embedding_service
        mock_qdrant_manager_cls.return_value = mock_qdrant_manager
        mock_state_manager_cls.return_value = mock_state_manager

        # Mock Git operations to raise an error
        mock_git_ops.return_value.list_files.side_effect = ValueError("Repository not initialized")

        # Create pipeline
        pipeline = IngestionPipeline(test_settings)

        # Create sources config with Git repository
        sources_config = SourcesConfig()
        sources_config.git_repos = {
            "test-repo": GitRepoConfig(
                base_url=HttpUrl("https://github.com/test/repo.git"),
                branch="main",
                depth=1,
                file_types=["*.md"],
                token="",  # No token needed for public repo
                temp_dir="",  # Will be set by GitConnector
                source_type="git",
                source_name="test-repo",
            )
        }

        # Test error handling
        with pytest.raises(ValueError, match="Repository not initialized"):
            await pipeline.process_documents(sources_config)


def test_filter_sources(test_settings):
    """Test source filtering."""
    with (
        patch(
            "qdrant_loader.core.ingestion_pipeline.ChunkingService.__new__"
        ) as mock_chunking_service_new,
        patch(
            "qdrant_loader.core.ingestion_pipeline.EmbeddingService"
        ) as mock_embedding_service_cls,
        patch("qdrant_loader.core.ingestion_pipeline.QdrantManager") as mock_qdrant_manager_cls,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager_cls,
    ):
        # Set up mock instances
        mock_chunking_service = MagicMock()
        mock_embedding_service = MagicMock()
        mock_qdrant_manager = MagicMock()
        mock_state_manager = MagicMock()

        # Configure mock classes to return their instances
        mock_chunking_service_new.return_value = mock_chunking_service
        mock_embedding_service_cls.return_value = mock_embedding_service
        mock_qdrant_manager_cls.return_value = mock_qdrant_manager
        mock_state_manager_cls.return_value = mock_state_manager

        # Create pipeline
        pipeline = IngestionPipeline(test_settings)

        # Test source filtering
        filtered_config = pipeline._filter_sources(test_settings.sources_config)
        assert isinstance(filtered_config, SourcesConfig)


@pytest.mark.asyncio
async def test_process_documents_with_jira(test_settings):
    """Test processing documents from Jira."""
    logger.debug("Starting test_process_documents_with_jira")

    # Configure sources
    jira_config = JiraProjectConfig(
        base_url=HttpUrl("https://test.atlassian.net"),
        source_type="jira",
        source_name="TEST",
        project_key="TEST",
        page_size=100,
        requests_per_minute=60,
        token="test-token",
        email="test@example.com",
    )
    sources_config = SourcesConfig()
    sources_config.jira = {"TEST": jira_config}

    # Mock services
    with (
        patch("qdrant_loader.core.ingestion_pipeline.JiraConnector") as mock_jira_connector_class,
        patch("qdrant_loader.core.ingestion_pipeline.ChunkingService") as mock_chunking_service,
        patch("qdrant_loader.core.ingestion_pipeline.EmbeddingService") as mock_embedding_service,
        patch("qdrant_loader.core.ingestion_pipeline.QdrantManager") as mock_qdrant_manager,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager,
    ):
        # Set up mock services
        test_doc = Document(
            id="TEST-1",
            content="Test Description",
            source="TEST",
            source_type="jira",
            url="https://test.atlassian.net/browse/TEST-1",
            metadata={"key": "TEST-1", "summary": "Test Issue"},
            last_updated=datetime.now(),
        )

        mock_connector = AsyncMock()
        mock_connector.get_documents = AsyncMock(return_value=[test_doc])
        mock_jira_connector_class.return_value = mock_connector

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [
            Document(
                id="TEST-1-chunk-1",
                content="Test Description",
                source="TEST",
                source_type="jira",
                url="https://test.atlassian.net/browse/TEST-1",
                metadata={"key": "TEST-1", "summary": "Test Issue"},
                last_updated=datetime.now(),
            )
        ]
        mock_chunking_service.return_value = mock_chunking

        mock_embedding = AsyncMock()
        mock_embedding.get_embeddings = AsyncMock(return_value=[[0.1] * 1536])
        mock_embedding_service.return_value = mock_embedding

        mock_qdrant = AsyncMock()
        mock_qdrant.upsert_points = AsyncMock(return_value=None)
        mock_qdrant_manager.return_value = mock_qdrant

        mock_state = AsyncMock()
        mock_state.update_document_state = AsyncMock(return_value=None)
        mock_state_manager.return_value = mock_state

        # Create and test pipeline
        pipeline = IngestionPipeline(test_settings)
        documents = await pipeline.process_documents(sources_config, source_type="jira")

        # Verify service calls
        assert mock_connector.get_documents.await_count == 1
        mock_chunking.chunk_document.assert_called_once()
        mock_embedding.get_embeddings.assert_awaited_once()
        mock_qdrant.upsert_points.assert_awaited_once()
        mock_state.update_document_state.assert_awaited_once()
        assert len(documents) == 1


@pytest.mark.asyncio
async def test_pipeline_process_empty_document(test_settings):
    """Test processing an empty document."""
    with (
        patch("qdrant_loader.core.ingestion_pipeline.ChunkingService") as mock_chunking_service,
        patch("qdrant_loader.core.ingestion_pipeline.EmbeddingService") as mock_embedding_service,
        patch("qdrant_loader.core.ingestion_pipeline.QdrantManager") as mock_qdrant_manager,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager,
        patch("qdrant_loader.core.ingestion_pipeline.PublicDocsConnector") as mock_connector,
    ):
        # Set up connector mock
        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documentation = AsyncMock(return_value=[])
        mock_connector.return_value = mock_connector_instance

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = []
        mock_chunking_service.return_value = mock_chunking

        mock_embedding = AsyncMock()
        mock_embedding_service.return_value = mock_embedding

        mock_qdrant = AsyncMock()
        mock_qdrant_manager.return_value = mock_qdrant

        mock_state = AsyncMock()
        mock_state_manager.return_value = mock_state

        pipeline = IngestionPipeline(test_settings)

        documents = await pipeline.process_documents(
            SourcesConfig(
                public_docs={
                    "test": PublicDocsSourceConfig(
                        source_type="public-docs",
                        source_name="test",
                        base_url=HttpUrl("https://test.com"),
                        version="1.0",
                        content_type="html",
                        selectors=SelectorsConfig(content="article"),
                    )
                }
            ),
            source_type="public-docs",
        )

        assert len(documents) == 0
        mock_chunking.chunk_document.assert_not_called()
        mock_embedding.get_embeddings.assert_not_awaited()
        mock_qdrant.upsert_points.assert_not_awaited()


@pytest.mark.asyncio
async def test_pipeline_process_invalid_document(test_settings):
    """Test processing an invalid document."""
    with (
        patch("qdrant_loader.core.ingestion_pipeline.PublicDocsConnector") as mock_connector,
        patch("qdrant_loader.core.ingestion_pipeline.ChunkingService") as mock_chunking_service,
        patch("qdrant_loader.core.ingestion_pipeline.StateManager") as mock_state_manager,
    ):
        # Set up mocks to raise an error
        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documentation = AsyncMock(
            return_value=[
                Document(
                    id="invalid-doc",
                    content="invalid content",
                    source="test",
                    source_type="test",
                    url="https://test.com",
                    last_updated=datetime.now(),
                )
            ]
        )
        mock_connector.return_value = mock_connector_instance

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.side_effect = ValueError("Invalid document")
        mock_chunking_service.return_value = mock_chunking

        # Create a proper mock state manager object
        mock_state = MagicMock()
        mock_state.update_document_state = AsyncMock()
        mock_state_manager.return_value = mock_state

        pipeline = IngestionPipeline(test_settings)

        with pytest.raises(ValueError, match="Invalid document"):
            await pipeline.process_documents(
                SourcesConfig(
                    public_docs={
                        "test": PublicDocsSourceConfig(
                            source_type="public-docs",
                            source_name="test",
                            base_url=HttpUrl("https://test.com"),
                            version="1.0",
                            content_type="html",
                            selectors=SelectorsConfig(content="article"),
                        )
                    }
                ),
                source_type="public-docs",
            )
