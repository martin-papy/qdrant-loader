import pytest
from unittest.mock import patch, MagicMock
from qdrant_loader.config import Config
from qdrant_loader.chunking_service import ChunkingService
from qdrant_loader.core.document import Document
from datetime import datetime

@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return Config(
        qdrant_url="http://localhost:6333",
        qdrant_api_key="test_key",
        collection_name="test_collection",
        chunk_size=1000,
        chunk_overlap=100,
        openai_api_key="test_key",
        sources=[],
    )

@pytest.fixture
def test_document():
    """Create a test document."""
    return Document(
        content="This is a test document. It contains multiple sentences. "
                "Each sentence should be properly chunked. The chunking service "
                "should handle this text correctly.",
        source="test_source",
        source_type="test_type",
        metadata={"key": "value"},
        created_at=datetime.now(),
        url="http://test.com",
        project="test_project",
        author="test_author",
        last_updated=datetime.now()
    )

def test_invalid_chunk_size(mock_config):
    """Test that invalid chunk size raises ValueError."""
    mock_config.chunk_size = 0
    with pytest.raises(ValueError, match="Chunk size must be greater than 0"):
        ChunkingService(mock_config)

def test_invalid_chunk_overlap(mock_config):
    """Test that invalid chunk overlap raises ValueError."""
    mock_config.chunk_overlap = -1
    with pytest.raises(ValueError, match="Chunk overlap must be non-negative"):
        ChunkingService(mock_config)

    mock_config.chunk_overlap = 1001
    mock_config.chunk_size = 1000
    with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
        ChunkingService(mock_config)

def test_valid_initialization(mock_config):
    """Test that valid configuration initializes successfully."""
    service = ChunkingService(mock_config)
    assert service.config == mock_config
    assert service.chunking_strategy is not None
    assert service.chunking_strategy.chunk_size == mock_config.chunk_size
    assert service.chunking_strategy.chunk_overlap == mock_config.chunk_overlap

def test_chunk_document(mock_config, test_document):
    """Test document chunking functionality."""
    # Create a mock chunking strategy
    mock_strategy = MagicMock()
    mock_chunks = ["chunk1", "chunk2"]
    mock_strategy._split_text.return_value = mock_chunks
    
    with patch('qdrant_loader.chunking_service.ChunkingStrategy', return_value=mock_strategy):
        service = ChunkingService(mock_config)
        chunked_docs = service.chunk_document(test_document)
        
        # Verify chunking strategy was called correctly
        mock_strategy._split_text.assert_called_once_with(test_document.content)
        
        # Verify chunked documents
        assert len(chunked_docs) == len(mock_chunks)
        for i, doc in enumerate(chunked_docs):
            assert doc.content == mock_chunks[i]
            assert doc.source == test_document.source
            assert doc.source_type == test_document.source_type
            assert doc.metadata["chunk_index"] == i
            assert doc.metadata["total_chunks"] == len(mock_chunks)
            assert doc.url == test_document.url
            assert doc.project == test_document.project
            assert doc.author == test_document.author

def test_chunk_document_empty_content(mock_config):
    """Test chunking a document with empty content."""
    empty_doc = Document(
        content="",
        source="test_source",
        source_type="test_type",
        metadata={},
        created_at=datetime.now()
    )
    
    # Create a mock chunking strategy
    mock_strategy = MagicMock()
    mock_strategy._split_text.return_value = [""]
    
    with patch('qdrant_loader.chunking_service.ChunkingStrategy', return_value=mock_strategy):
        service = ChunkingService(mock_config)
        chunked_docs = service.chunk_document(empty_doc)
        
        assert len(chunked_docs) == 1
        assert chunked_docs[0].content == ""
        assert chunked_docs[0].metadata["chunk_index"] == 0
        assert chunked_docs[0].metadata["total_chunks"] == 1

def test_chunk_document_error_handling(mock_config, test_document):
    """Test error handling during document chunking."""
    # Create a mock chunking strategy that raises an exception
    mock_strategy = MagicMock()
    mock_strategy._split_text.side_effect = Exception("Chunking error")
    
    with patch('qdrant_loader.chunking_service.ChunkingStrategy', return_value=mock_strategy):
        service = ChunkingService(mock_config)
        with pytest.raises(Exception, match="Chunking error"):
            service.chunk_document(test_document) 