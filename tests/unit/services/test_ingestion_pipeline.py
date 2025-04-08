"""
Tests for the ingestion pipeline.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from qdrant_loader.ingestion_pipeline import IngestionPipeline
from qdrant_loader.config import SourcesConfig, GlobalConfig, EmbeddingConfig, initialize_config
from qdrant_loader.core.document import Document
import uuid
from datetime import datetime
import tempfile
import yaml
from pathlib import Path

@pytest.fixture(autouse=True)
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test-key"
    settings.QDRANT_URL = "http://test-url"
    settings.QDRANT_API_KEY = "test-key"
    settings.QDRANT_COLLECTION_NAME = "test-collection"
    settings.global_config = GlobalConfig(
        chunking={"size": 500, "overlap": 50},
        embedding=EmbeddingConfig(model="text-embedding-3-small", batch_size=100),
        logging={"level": "INFO", "format": "json", "file": "qdrant-loader.log"}
    )
    settings.sources_config = SourcesConfig(
        public_docs={},
        confluence={},
        git_repos={}
    )
    
    # Create a temporary YAML config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
        config = {
            'global': {
                'chunking': {'size': 500, 'overlap': 50},
                'embedding': {'model': 'text-embedding-3-small', 'batch_size': 100},
                'logging': {'level': 'INFO', 'format': 'json', 'file': 'qdrant-loader.log'}
            },
            'sources': {
                'confluence': {},
                'git_repos': {},
                'public_docs': {}
            }
        }
        yaml.dump(config, temp_file)
        temp_path = Path(temp_file.name)
    
    try:
        # Initialize the config with our mock settings
        with patch('qdrant_loader.config.get_settings', return_value=settings):
            initialize_config(temp_path)
            yield settings
    finally:
        # Clean up the temporary file
        temp_path.unlink()

@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return SourcesConfig(
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
            created_at=datetime.now(),
            url="https://test.com/doc1"  # Add a valid URL string
        )
    ]

def test_ingestion_pipeline_init(mock_settings):
    """Test pipeline initialization."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings) as mock_get_settings:
        pipeline = IngestionPipeline()
        assert pipeline.settings == mock_settings
        assert pipeline.embedding_service is not None
        assert pipeline.qdrant_manager is not None
        assert pipeline.chunking_strategy is not None
        mock_get_settings.assert_called_once()

def test_ingestion_pipeline_init_no_settings():
    """Test pipeline initialization with no settings."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=None), \
         pytest.raises(ValueError, match="Settings not available"):
        IngestionPipeline()

def test_process_documents_no_sources(mock_settings, mock_config):
    """Test processing with no sources."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings):
        pipeline = IngestionPipeline()
        empty_config = SourcesConfig()
        pipeline.process_documents(empty_config)

def test_process_documents_public_docs(mock_settings, mock_config, mock_documents):
    """Test processing public docs."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.ingestion_pipeline.PublicDocsConnector') as mock_connector:

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
         patch('qdrant_loader.ingestion_pipeline.PublicDocsConnector') as mock_connector:

        # Setup mock connector to raise an error
        mock_connector.return_value.get_documentation.side_effect = Exception("Test error")

        pipeline = IngestionPipeline()

        # Process the documents
        with pytest.raises(Exception, match="Failed to process documents"):
            pipeline.process_documents(mock_config, source_type="public-docs")

def test_filter_sources(mock_settings, mock_config):
    """Test source filtering."""
    with patch('qdrant_loader.ingestion_pipeline.get_settings', return_value=mock_settings):
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