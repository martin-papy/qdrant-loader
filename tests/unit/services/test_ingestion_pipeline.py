"""
Tests for the ingestion pipeline.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from qdrant_loader.ingestion_pipeline import IngestionPipeline
from qdrant_loader.config import SourcesConfig, GlobalConfig, EmbeddingConfig
from qdrant_loader.core.document import Document
import uuid
from datetime import datetime

@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test-key"
    settings.QDRANT_URL = "http://test-url"
    settings.QDRANT_API_KEY = "test-key"
    settings.QDRANT_COLLECTION_NAME = "test-collection"
    return settings

@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return SourcesConfig(
        global_config=GlobalConfig(
            chunking={"size": 500, "overlap": 50},
            embedding=EmbeddingConfig(model="text-embedding-3-small")
        ),
        public_docs={
            "test-docs": {
                "base_url": "https://test.com",
                "version": "1.0",
                "content_type": "html"
            }
        }
    )

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
            created_at=datetime.now()
        )
    ]

def test_ingestion_pipeline_init(mock_settings):
    """Test pipeline initialization."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.ingestion_pipeline.get_global_config') as mock_global_config:
        
        mock_global_config.return_value.chunking = {"size": 500, "overlap": 50}
        mock_global_config.return_value.embedding.model = "text-embedding-3-small"
        
        pipeline = IngestionPipeline()
        assert pipeline.settings == mock_settings
        assert pipeline.embedding_service is not None
        assert pipeline.qdrant_manager is not None
        assert pipeline.chunking_strategy is not None

def test_ingestion_pipeline_init_no_settings():
    """Test pipeline initialization with no settings."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=None), \
         pytest.raises(ValueError, match="Settings not available"):
        IngestionPipeline()

def test_process_documents_no_sources(mock_settings, mock_config):
    """Test processing with no sources."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.ingestion_pipeline.get_global_config') as mock_global_config:
        
        mock_global_config.return_value.chunking = {"size": 500, "overlap": 50}
        mock_global_config.return_value.embedding.model = "text-embedding-3-small"
        
        pipeline = IngestionPipeline()
        empty_config = SourcesConfig()
        pipeline.process_documents(empty_config)

def test_process_documents_public_docs(mock_settings, mock_config, mock_documents):
    """Test processing public docs."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.ingestion_pipeline.get_global_config') as mock_global_config, \
         patch('qdrant_loader.ingestion_pipeline.PublicDocsConnector') as mock_connector:

        mock_global_config.return_value.chunking = {"size": 500, "overlap": 50}
        mock_global_config.return_value.embedding.model = "text-embedding-3-small"

        # Setup mock connector
        mock_connector.return_value.get_documentation.return_value = ["Test content 1"]

        pipeline = IngestionPipeline()
        pipeline.chunking_strategy.chunk_document = MagicMock(return_value=[mock_documents[0]])
        pipeline.embedding_service.get_embeddings = MagicMock(return_value=[[0.1, 0.2, 0.3]])
        pipeline.qdrant_manager.upsert_points = MagicMock()

        # Process the documents
        pipeline.process_documents(mock_config, source_type="public-docs")

        # Verify the mocks were called
        mock_connector.return_value.get_documentation.assert_called_once()
        pipeline.chunking_strategy.chunk_document.assert_called_once()
        pipeline.embedding_service.get_embeddings.assert_called_once()
        pipeline.qdrant_manager.upsert_points.assert_called_once()

def test_process_documents_error(mock_settings, mock_config):
    """Test error handling in document processing."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.ingestion_pipeline.get_global_config') as mock_global_config, \
         patch('qdrant_loader.ingestion_pipeline.PublicDocsConnector') as mock_connector:

        mock_global_config.return_value.chunking = {"size": 500, "overlap": 50}
        mock_global_config.return_value.embedding.model = "text-embedding-3-small"

        # Setup mock connector to return some content
        mock_connector.return_value.get_documentation.return_value = ["Test content"]

        pipeline = IngestionPipeline()
        # Mock chunking strategy to raise an error
        pipeline.chunking_strategy.chunk_document = MagicMock(side_effect=Exception("Chunking error"))

        # Process the documents
        with pytest.raises(Exception, match="Failed to process documents"):
            pipeline.process_documents(mock_config, source_type="public-docs")

def test_filter_sources(mock_settings, mock_config):
    """Test source filtering."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.ingestion_pipeline.get_global_config') as mock_global_config:
        
        mock_global_config.return_value.chunking = {"size": 500, "overlap": 50}
        mock_global_config.return_value.embedding.model = "text-embedding-3-small"
        
        pipeline = IngestionPipeline()
        
        # Test filtering by type
        filtered = pipeline._filter_sources(mock_config, "public-docs", None)
        assert filtered.public_docs == mock_config.public_docs
        assert not filtered.confluence
        assert not filtered.git_repos
        
        # Test filtering by name
        filtered = pipeline._filter_sources(mock_config, "public-docs", "test-docs")
        assert filtered.public_docs["test-docs"] == mock_config.public_docs["test-docs"]
        assert len(filtered.public_docs) == 1 