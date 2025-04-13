"""
Tests for the ingestion pipeline.
"""
import logging
from datetime import datetime
from logging import getLogger
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qdrant_loader.config import SourcesConfig
from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.connectors.public_docs.config import PublicDocsSourceConfig, SelectorsConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.ingestion_pipeline import IngestionPipeline

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
            metadata={
                "space": "SPACE1",
                "content_type": "page"
            },
            created_at=datetime.now(),
            url="https://test.com/doc1"
        )
    ]

@pytest.mark.asyncio
async def test_ingestion_pipeline_init(test_settings,test_global_config):
    """Test pipeline initialization."""
    with patch('qdrant_loader.core.ingestion_pipeline.ChunkingService') as mock_chunking_service, \
         patch('qdrant_loader.core.ingestion_pipeline.EmbeddingService') as mock_embedding_service, \
         patch('qdrant_loader.core.ingestion_pipeline.QdrantManager') as mock_qdrant_manager, \
         patch('qdrant_loader.core.ingestion_pipeline.StateManager') as mock_state_manager:
        
        mock_chunking_service.return_value = MagicMock()
        mock_embedding_service.return_value = MagicMock()
        mock_qdrant_manager.return_value = MagicMock()
        mock_state_manager.return_value = MagicMock()
        
        pipeline = IngestionPipeline(test_settings)
        
        assert pipeline.settings == test_settings
        assert pipeline.config == test_global_config
        mock_chunking_service.assert_called_once_with(config=test_global_config, settings=test_settings)
        mock_embedding_service.assert_called_once_with(test_settings)
        mock_qdrant_manager.assert_called_once_with(test_settings)
        mock_state_manager.assert_called_once_with(test_settings.STATE_DB_PATH)

@pytest.mark.asyncio
async def test_ingestion_pipeline_init_no_settings():
    """Test pipeline initialization with no settings."""
    with pytest.raises(ValueError, match="Settings not available. Please check your environment variables."):
        pipeline = IngestionPipeline(None)

@pytest.mark.asyncio
async def test_process_documents_no_sources(test_settings):
    """Test processing with no sources."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=test_settings):
        pipeline = IngestionPipeline(test_settings)
        empty_config = SourcesConfig()
        documents = await pipeline.process_documents(empty_config)
        assert documents == []

@pytest.mark.asyncio
async def test_process_documents_public_docs(test_settings, mock_documents):
    """Test processing public docs."""
    with patch('qdrant_loader.core.ingestion_pipeline.PublicDocsConnector') as mock_connector, \
         patch('qdrant_loader.core.ingestion_pipeline.ChunkingService') as mock_chunking_service, \
         patch('qdrant_loader.core.ingestion_pipeline.EmbeddingService') as mock_embedding_service, \
         patch('qdrant_loader.core.ingestion_pipeline.QdrantManager') as mock_qdrant_manager, \
         patch('qdrant_loader.core.ingestion_pipeline.StateManager') as mock_state_manager:
        
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
        documents = await pipeline.process_documents(test_settings.sources_config, source_type="public-docs")

        # Verify the mocks were called
        mock_connector_instance.get_documentation.assert_awaited_once()
        mock_chunking.chunk_document.assert_called_once_with(mock_documents[0])
        mock_embedding.get_embeddings.assert_awaited_once_with([mock_documents[0]])
        mock_qdrant.upsert_points.assert_awaited_once()
        mock_state.update_document_state.assert_awaited_once_with(mock_documents[0])
        assert len(documents) == 1

@pytest.mark.asyncio
async def test_process_documents_error(test_settings):
    """Test error handling in document processing."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=test_settings), \
         patch('qdrant_loader.core.ingestion_pipeline.PublicDocsConnector') as mock_connector:
        mock_connector.return_value.get_documentation.side_effect = Exception("Test error")
        pipeline = IngestionPipeline(test_settings)
        with pytest.raises(Exception, match="Test error"):
            await pipeline.process_documents(test_settings.sources_config, source_type="public-docs")

def test_filter_sources(test_settings):
    """Test source filtering."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=test_settings):
        pipeline = IngestionPipeline(test_settings)
        
        # Test filtering by type
        filtered = pipeline._filter_sources(test_settings.sources_config, source_type="public-docs")
        assert filtered.public_docs == test_settings.sources_config.public_docs
        assert not filtered.confluence
        assert not filtered.git_repos
        
        # Test filtering by name
        filtered = pipeline._filter_sources(test_settings.sources_config, source_type="public-docs", source_name="test-docs")
        assert len(filtered.public_docs) == 1
        assert "test-docs" in filtered.public_docs

@pytest.mark.asyncio
async def test_process_documents_with_jira(test_settings):
    """Test processing documents from Jira."""
    logger.debug("Starting test_process_documents_with_jira")

    # Configure sources
    jira_config = JiraProjectConfig(
        base_url="https://test.atlassian.net",
        project_key="TEST",
        page_size=100,
        requests_per_minute=60,
        token="test-token",
        email="test@example.com"
    )
    sources_config = SourcesConfig()
    sources_config.jira = {"TEST": jira_config}

    # Mock services
    with patch('qdrant_loader.core.ingestion_pipeline.JiraConnector') as mock_jira_connector_class, \
         patch('qdrant_loader.core.ingestion_pipeline.ChunkingService') as mock_chunking_service, \
         patch('qdrant_loader.core.ingestion_pipeline.EmbeddingService') as mock_embedding_service, \
         patch('qdrant_loader.core.ingestion_pipeline.QdrantManager') as mock_qdrant_manager, \
         patch('qdrant_loader.core.ingestion_pipeline.StateManager') as mock_state_manager:

        # Set up mock services
        mock_connector = AsyncMock()
        mock_connector.get_documentation = AsyncMock(return_value=[Document(
            id="TEST-1",
            content="Test Description",
            source="TEST",
            source_type="jira",
            url="https://test.atlassian.net/browse/TEST-1",
            metadata={"key": "TEST-1", "summary": "Test Issue"},
            last_updated=datetime.now()
        )])
        mock_jira_connector_class.return_value = mock_connector

        mock_chunking = MagicMock()
        mock_chunking.chunk_document.return_value = [Document(
            id="TEST-1-chunk-1",
            content="Test Description",
            source="TEST",
            source_type="jira",
            url="https://test.atlassian.net/browse/TEST-1",
            metadata={"key": "TEST-1", "summary": "Test Issue"},
            last_updated=datetime.now()
        )]
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
        mock_connector.get_documentation.assert_awaited_once()
        mock_chunking.chunk_document.assert_called_once()
        mock_embedding.get_embeddings.assert_awaited_once()
        mock_qdrant.upsert_points.assert_awaited_once()
        mock_state.update_document_state.assert_awaited_once()
        assert len(documents) == 1

@pytest.mark.asyncio
async def test_pipeline_process_empty_document(test_settings):
    """Test processing an empty document."""
    with patch('qdrant_loader.core.ingestion_pipeline.ChunkingService') as mock_chunking_service, \
         patch('qdrant_loader.core.ingestion_pipeline.EmbeddingService') as mock_embedding_service, \
         patch('qdrant_loader.core.ingestion_pipeline.QdrantManager') as mock_qdrant_manager, \
         patch('qdrant_loader.core.ingestion_pipeline.StateManager') as mock_state_manager, \
         patch('qdrant_loader.core.ingestion_pipeline.PublicDocsConnector') as mock_connector:
        
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
            SourcesConfig(public_docs={"test": PublicDocsSourceConfig(
                base_url="http://test.com",
                version="1.0",
                content_type="html",
                selectors=SelectorsConfig(title="h1", content="article")
            )}),
            source_type="public-docs"
        )

        assert len(documents) == 0
        mock_chunking.chunk_document.assert_not_called()
        mock_embedding.get_embeddings.assert_not_awaited()
        mock_qdrant.upsert_points.assert_not_awaited()

@pytest.mark.asyncio
async def test_pipeline_process_invalid_document(test_settings):
    """Test processing an invalid document."""
    with patch('qdrant_loader.core.ingestion_pipeline.PublicDocsConnector') as mock_connector, \
         patch('qdrant_loader.core.ingestion_pipeline.ChunkingService') as mock_chunking_service, \
         patch('qdrant_loader.core.ingestion_pipeline.StateManager') as mock_state_manager:
        
        # Set up mocks to raise an error
        mock_connector_instance = AsyncMock()
        mock_connector_instance.get_documentation = AsyncMock(return_value=[Document(
            id="invalid-doc",
            content="invalid content",
            source="test",
            source_type="test",
            url="http://test.com",
            last_updated=datetime.now()
        )])
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
                SourcesConfig(public_docs={"test": PublicDocsSourceConfig(
                    base_url="http://test.com",
                    version="1.0",
                    content_type="html",
                    selectors=SelectorsConfig(title="h1", content="article")
                )}),
                source_type="public-docs"
            )