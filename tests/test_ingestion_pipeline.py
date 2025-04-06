import pytest
from unittest.mock import Mock, patch
from qdrant_loader.ingestion_pipeline import IngestionPipeline
from qdrant_loader.config import (
    SourcesConfig,
    PublicDocsSourceConfig,
    SelectorsConfig,
    GlobalConfig
)
from qdrant_loader.core.document import Document

@pytest.fixture
def mock_settings():
    return Mock(
        QDRANT_URL="http://localhost:6333",
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection",
        OPENAI_API_KEY="test-key",
        LOG_LEVEL="INFO"
    )

@pytest.fixture
def mock_sources_config():
    return SourcesConfig(
        global_config=GlobalConfig(),
        public_docs={
            "test_docs": PublicDocsSourceConfig(
                base_url="https://docs.example.com",
                version="1.0",
                content_type="html",
                selectors=SelectorsConfig()
            )
        }
    )

@pytest.fixture
def mock_documents():
    return [
        Document(
            content="Test content 1",
            source="test_docs",
            source_type="public_docs",
            url="https://docs.example.com/page1",
            metadata={"version": "1.0"}
        ),
        Document(
            content="Test content 2",
            source="test_docs",
            source_type="public_docs",
            url="https://docs.example.com/page2",
            metadata={"version": "1.0"}
        )
    ]

@patch("qdrant_loader.ingestion_pipeline.get_settings")
@patch("qdrant_loader.ingestion_pipeline.EmbeddingService")
@patch("qdrant_loader.ingestion_pipeline.QdrantManager")
def test_ingestion_pipeline_initialization(
    mock_qdrant_manager,
    mock_embedding_service,
    mock_get_settings,
    mock_settings
):
    mock_get_settings.return_value = mock_settings
    
    pipeline = IngestionPipeline()
    
    assert pipeline.settings == mock_settings
    mock_embedding_service.assert_called_once_with(mock_settings)
    mock_qdrant_manager.assert_called_once_with(mock_settings)

@patch("qdrant_loader.ingestion_pipeline.get_settings")
@patch("qdrant_loader.ingestion_pipeline.PublicDocsConnector")
@patch("qdrant_loader.embedding_service.get_global_config")
def test_process_public_docs(
    mock_global_config,
    mock_connector,
    mock_get_settings,
    mock_settings,
    mock_sources_config
):
    mock_get_settings.return_value = mock_settings
    mock_global_config.return_value = GlobalConfig()
    mock_connector.return_value.get_documentation.return_value = [
        "Test content 1",
        "Test content 2"
    ]
    
    pipeline = IngestionPipeline()
    documents = pipeline._process_public_docs(mock_sources_config.public_docs)
    
    assert len(documents) == 2
    assert all(doc.source_type == "public_docs" for doc in documents)
    assert all(doc.source == "test_docs" for doc in documents)
    mock_connector.assert_called_once()

@patch("qdrant_loader.ingestion_pipeline.get_settings")
@patch("qdrant_loader.ingestion_pipeline.EmbeddingService")
@patch("qdrant_loader.ingestion_pipeline.QdrantManager")
@patch("qdrant_loader.ingestion_pipeline.ChunkingStrategy")
def test_process_documents(
    mock_chunking_strategy,
    mock_qdrant_manager,
    mock_embedding_service,
    mock_get_settings,
    mock_settings,
    mock_sources_config,
    mock_documents
):
    mock_get_settings.return_value = mock_settings
    mock_embedding_service.return_value.get_embeddings.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6]
    ]
    
    # Mock chunking strategy to return the same documents
    mock_chunking_strategy.return_value.chunk_document.side_effect = lambda doc: [doc]
    
    pipeline = IngestionPipeline()
    pipeline._process_public_docs = Mock(return_value=mock_documents)
    
    pipeline.process_documents(mock_sources_config)
    
    # Verify embeddings were generated
    mock_embedding_service.return_value.get_embeddings.assert_called_once_with(
        ["Test content 1", "Test content 2"]
    )
    
    # Verify points were uploaded to qDrant
    mock_qdrant_manager.return_value.upsert_points.assert_called_once()
    points = mock_qdrant_manager.return_value.upsert_points.call_args[0][0]
    assert len(points) == 2
    assert all("vector" in point for point in points)
    assert all("payload" in point for point in points) 