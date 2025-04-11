"""
Tests for the ingestion pipeline.
"""
import pytest
from unittest.mock import patch, MagicMock, call, AsyncMock
from qdrant_loader.core.ingestion_pipeline import IngestionPipeline
from qdrant_loader.config import SourcesConfig, GlobalConfig, EmbeddingConfig, initialize_config
from qdrant_loader.config.settings import Settings
from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.public_docs.config import PublicDocsSourceConfig, SelectorsConfig
from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.connectors.jira.models import JiraIssue, JiraUser
from qdrant_loader.core.document import Document
from datetime import datetime
import tempfile
import yaml
from pathlib import Path
import logging
from qdrant_loader.config.types import JiraConfig
from qdrant_loader.config.global_ import GlobalConfig
from qdrant_loader.config.chunking import ChunkingConfig
from qdrant_loader.config.embedding import EmbeddingConfig
from qdrant_loader.connectors.jira.jira_connector import JiraConnector
import structlog

logger = structlog.get_logger()

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture(autouse=True)
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test-key"
    settings.QDRANT_URL = "https://test-url"
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

@pytest.mark.asyncio
async def test_ingestion_pipeline_init(mock_settings):
    """Test pipeline initialization."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=mock_settings) as mock_get_settings:
        pipeline = IngestionPipeline(mock_settings)
        assert pipeline.settings == mock_settings
        assert pipeline.embedding_service is not None
        assert pipeline.qdrant_manager is not None
        assert pipeline.chunking_strategy is not None

@pytest.mark.asyncio
async def test_ingestion_pipeline_init_no_settings():
    """Test pipeline initialization with no settings."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=None), \
         pytest.raises(Exception, match="Failed to initialize pipeline: Settings not available. Please check your environment variables."):
        pipeline = IngestionPipeline(None)

@pytest.mark.asyncio
async def test_process_documents_no_sources(mock_settings, mock_config):
    """Test processing with no sources."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=mock_settings):
        pipeline = IngestionPipeline(mock_settings)
        empty_config = SourcesConfig()
        documents = await pipeline.process_documents(empty_config)
        assert documents == []

@pytest.mark.asyncio
async def test_process_documents_public_docs(mock_settings, mock_config, mock_documents):
    """Test processing public docs."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.core.ingestion_pipeline.PublicDocsConnector') as mock_connector:
        mock_connector.return_value.get_documentation.return_value = ["Test content 1"]
        pipeline = IngestionPipeline(mock_settings)
        pipeline.chunking_strategy.chunk_document = MagicMock(return_value=[mock_documents[0]])
        pipeline.embedding_service.get_embeddings = MagicMock(return_value=[[0.1, 0.2, 0.3]])
        pipeline.qdrant_manager.upsert_points = MagicMock()

        # Process the documents
        documents = await pipeline.process_documents(mock_config, source_type="public-docs")

        # Verify the mocks were called
        mock_connector.return_value.get_documentation.assert_called_once()
        pipeline.chunking_strategy.chunk_document.assert_called_once()
        pipeline.embedding_service.get_embeddings.assert_called_once()
        pipeline.qdrant_manager.upsert_points.assert_called_once()
        assert len(documents) == 1

@pytest.mark.asyncio
async def test_process_documents_error(mock_settings, mock_config):
    """Test error handling in document processing."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=mock_settings), \
         patch('qdrant_loader.core.ingestion_pipeline.PublicDocsConnector') as mock_connector:
        mock_connector.return_value.get_documentation.side_effect = Exception("Test error")
        pipeline = IngestionPipeline(mock_settings)
        with pytest.raises(Exception, match="Test error"):
            await pipeline.process_documents(mock_config, source_type="public-docs")

def test_filter_sources(mock_settings, mock_config):
    """Test source filtering."""
    with patch('qdrant_loader.config.settings.get_settings', return_value=mock_settings):
        pipeline = IngestionPipeline(mock_settings)
        
        # Test filtering by type
        filtered = pipeline._filter_sources(mock_config, source_type="public-docs")
        assert filtered.public_docs == mock_config.public_docs
        assert not filtered.confluence
        assert not filtered.git_repos
        
        # Test filtering by name
        filtered = pipeline._filter_sources(mock_config, source_type="public-docs", source_name="test-docs")
        assert filtered.public_docs["test-docs"] == mock_config.public_docs["test-docs"]
        assert len(filtered.public_docs) == 1

@pytest.mark.asyncio
async def test_process_documents_with_jira():
    logger.debug("Starting test_process_documents_with_jira")

    # Configure settings
    global_config = GlobalConfig(
        chunking=ChunkingConfig(chunk_size=1000, chunk_overlap=100),
        embedding=EmbeddingConfig(model="text-embedding-3-small", batch_size=10)
    )
    settings = Settings(
        OPENAI_API_KEY="test-openai-key",
        QDRANT_URL="https://localhost:6333",
        QDRANT_API_KEY="test-qdrant-key",
        QDRANT_COLLECTION_NAME="test-collection",
        global_config=global_config
    )

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

    # Create a mock issue
    mock_issue = JiraIssue(
        id="TEST-1",
        key="TEST-1",
        summary="Test Issue",
        description="Test Description",
        issue_type="Story",
        status="Open",
        project_key="TEST",
        created=datetime.now(),
        updated=datetime.now(),
        reporter=JiraUser(
            account_id="test-account",
            display_name="Test User",
            email_address="test@example.com"
        ),
        assignee=None,
        parent_key=None,
        subtasks=[],
        linked_issues=[],
        attachments=[]
    )

    # Create an async iterator for the mock issues
    async def mock_get_issues():
        yield mock_issue

    # Mock get_settings
    with patch('qdrant_loader.config.settings.get_settings') as mock_get_settings, \
         patch('qdrant_loader.core.ingestion_pipeline.JiraConnector') as mock_jira_connector_class:
        mock_get_settings.return_value = settings

        # Set up the mock connector
        mock_connector = AsyncMock()
        mock_connector.get_issues = mock_get_issues
        mock_jira_connector_class.return_value = mock_connector

        # Mock chunking strategy
        mock_chunking_strategy = MagicMock()
        mock_chunking_strategy.chunk_document.return_value = [Document(
            id="TEST-1-chunk-1",
            content="Test Description",
            source="TEST",
            source_type="jira",
            url="https://test.atlassian.net/browse/TEST-1",
            last_updated=datetime.now(),
            metadata={"key": "TEST-1", "summary": "Test Issue"}
        )]

        # Mock embedding service
        mock_embedding_service = MagicMock()
        mock_embedding_service.get_embeddings.return_value = [[0.1] * 1536]  # Mock embedding vector

        # Mock Qdrant manager
        mock_qdrant = MagicMock()
        mock_qdrant.upsert_points.return_value = None

        # Create pipeline with mocked services
        pipeline = IngestionPipeline(settings)
        pipeline.embedding_service = mock_embedding_service
        pipeline.qdrant_manager = mock_qdrant
        pipeline.chunking_strategy = mock_chunking_strategy

        # Process documents
        documents = await pipeline.process_documents(sources_config, source_type="jira")

        # Verify that get_embeddings was called
        mock_embedding_service.get_embeddings.assert_called_once()

        # Verify that upsert_points was called
        mock_qdrant.upsert_points.assert_called_once()

        # Verify that documents were returned
        assert len(documents) > 0

        logger.debug("Test completed successfully") 