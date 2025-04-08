import pytest
from unittest.mock import patch, MagicMock
from qdrant_loader.config import GlobalConfig, ChunkingConfig
from qdrant_loader.chunking_service import ChunkingService
from qdrant_loader.core.document import Document
from datetime import datetime

@pytest.fixture
def config():
    """Create a test configuration."""
    return GlobalConfig(
        chunking=ChunkingConfig(chunk_size=500, chunk_overlap=50)
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

def test_invalid_chunk_size(config):
    """Test that invalid chunk size raises ValueError."""
    config.chunking.chunk_size = 0
    with pytest.raises(ValueError, match="Chunk size must be greater than 0"):
        ChunkingService(config)

def test_invalid_chunk_overlap(config):
    """Test that invalid chunk overlap raises ValueError."""
    config.chunking.chunk_overlap = -1
    with pytest.raises(ValueError, match="Chunk overlap must be non-negative"):
        ChunkingService(config)

    config.chunking.chunk_overlap = 1001
    config.chunking.chunk_size = 1000
    with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
        ChunkingService(config)

def test_valid_initialization(config):
    """Test that valid configuration initializes successfully."""
    service = ChunkingService(config)
    assert service.config == config
    assert service.chunking_strategy is not None
    assert service.chunking_strategy.chunk_size == config.chunking.chunk_size
    assert service.chunking_strategy.chunk_overlap == config.chunking.chunk_overlap

def test_chunk_document(config, test_document):
    """Test document chunking functionality."""
    # Create a mock chunking strategy
    mock_strategy = MagicMock()
    mock_chunks = [test_document.copy(), test_document.copy()]
    mock_chunks[0].content = "chunk1"
    mock_chunks[1].content = "chunk2"
    mock_strategy.chunk_document.return_value = mock_chunks
    
    with patch('qdrant_loader.chunking_service.ChunkingStrategy', return_value=mock_strategy):
        service = ChunkingService(config)
        chunked_docs = service.chunk_document(test_document)
        
        # Verify chunking strategy was called correctly
        mock_strategy.chunk_document.assert_called_once_with(test_document)
        
        # Verify chunked documents
        assert len(chunked_docs) == len(mock_chunks)
        for i, doc in enumerate(chunked_docs):
            assert doc.content == mock_chunks[i].content
            assert doc.source == test_document.source
            assert doc.source_type == test_document.source_type
            assert doc.url == test_document.url
            assert doc.project == test_document.project
            assert doc.author == test_document.author

def test_chunk_document_empty_content(config):
    """Test chunking a document with empty content."""
    empty_doc = Document(
        content="",
        source="test_source",
        source_type="test_type",
        metadata={},
        created_at=datetime.now()
    )
    
    service = ChunkingService(config)
    chunked_docs = service.chunk_document(empty_doc)
    
    assert len(chunked_docs) == 1
    assert chunked_docs[0].content == ""
    assert chunked_docs[0].metadata["chunk_index"] == 0
    assert chunked_docs[0].metadata["total_chunks"] == 1

def test_chunk_document_error_handling(config, test_document):
    """Test error handling during document chunking."""
    # Create a mock chunking strategy that raises an exception
    mock_strategy = MagicMock()
    mock_strategy.chunk_document.side_effect = Exception("Chunking error")
    
    with patch('qdrant_loader.chunking_service.ChunkingStrategy', return_value=mock_strategy):
        service = ChunkingService(config)
        with pytest.raises(Exception, match="Chunking error"):
            service.chunk_document(test_document)