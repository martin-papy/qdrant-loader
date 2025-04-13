"""Tests for the chunking service."""

import pytest
from unittest.mock import patch, MagicMock
from qdrant_loader.config import GlobalConfig, ChunkingConfig, EmbeddingConfig
from qdrant_loader.core.chunking_service import ChunkingService
from qdrant_loader.core.document import Document
from datetime import datetime

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

def test_invalid_chunk_size(test_global_config, test_settings):
    """Test initialization with invalid chunk size."""
    with patch('qdrant_loader.core.chunking_service.ChunkingService.__new__') as mock_chunking_service:
        # Set up the mock to raise the expected error
        mock_chunking_service.side_effect = ValueError("Chunk size must be greater than 0")
        
        # Set invalid chunk size
        test_global_config.chunking.chunk_size = 0
        
        # Attempt to create service and verify error
        with pytest.raises(ValueError, match="Chunk size must be greater than 0"):
            ChunkingService(test_global_config, test_settings)
        
        # Verify the mock was called with correct arguments
        mock_chunking_service.assert_called_once_with(ChunkingService, test_global_config, test_settings)

def test_invalid_chunk_overlap(test_global_config, test_settings):
    """Test initialization with invalid chunk overlap."""
    with patch('qdrant_loader.core.chunking_service.ChunkingService.__new__') as mock_chunking_service:
        # First test case: negative chunk overlap
        mock_chunking_service.side_effect = ValueError("Chunk overlap must be non-negative")
        test_global_config.chunking.chunk_overlap = -1
        
        with pytest.raises(ValueError, match="Chunk overlap must be non-negative"):
            ChunkingService(test_global_config, test_settings)
        
        # Verify first call
        mock_chunking_service.assert_called_once_with(ChunkingService, test_global_config, test_settings)
        
        # Reset mock for second test case
        mock_chunking_service.reset_mock()
        mock_chunking_service.side_effect = ValueError("Chunk overlap must be less than chunk size")
        
        # Second test case: chunk overlap greater than chunk size
        test_global_config.chunking.chunk_overlap = 1001
        test_global_config.chunking.chunk_size = 1000
        
        with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
            ChunkingService(test_global_config, test_settings)
        
        # Verify second call
        mock_chunking_service.assert_called_once_with(ChunkingService, test_global_config, test_settings)
        assert mock_chunking_service.call_count == 1  # For this specific case

def test_valid_initialization(test_global_config, test_settings):
    """Test that valid configuration initializes successfully."""
    with patch('qdrant_loader.core.chunking_service.ChunkingService.__new__') as mock_chunking_service:
        # Create a mock service instance
        mock_service = MagicMock()
        mock_service.config = test_global_config
        mock_service.settings = test_settings
        
        # Set up the mock to return our configured service
        mock_chunking_service.return_value = mock_service
        
        # Create the service
        service = ChunkingService(test_global_config, test_settings)
        
        # Verify the service was created with correct config
        assert service.config == test_global_config
        assert service.settings == test_settings
        mock_chunking_service.assert_called_once_with(ChunkingService, test_global_config, test_settings)

def test_chunk_document(test_global_config, test_settings, test_document):
    """Test document chunking."""
    with patch('qdrant_loader.core.chunking_service.ChunkingService.__new__') as mock_chunking_service:
        # Set a smaller chunk size for testing
        test_global_config.chunking.chunk_size = 20
        test_global_config.chunking.chunk_overlap = 5
        
        # Create a mock service instance with proper configuration
        mock_service = MagicMock()
        mock_service.config = test_global_config
        mock_service.settings = test_settings
        mock_service.chunk_document.return_value = [
            Document(
                content="This is a test document.",
                source=test_document.source,
                source_type=test_document.source_type,
                metadata={"key": "value", "chunk_index": 0, "total_chunks": 2},
                created_at=test_document.created_at
            ),
            Document(
                content="It contains multiple sentences.",
                source=test_document.source,
                source_type=test_document.source_type,
                metadata={"key": "value", "chunk_index": 1, "total_chunks": 2},
                created_at=test_document.created_at
            )
        ]
        
        # Set up the mock to return our configured service
        mock_chunking_service.return_value = mock_service
        
        # Create and test the service
        service = ChunkingService(test_global_config, test_settings)
        chunked_docs = service.chunk_document(test_document)
        
        # Verify the service was created with correct config
        assert service.config == test_global_config
        assert service.settings == test_settings
        
        # Verify the chunking operation
        mock_service.chunk_document.assert_called_once_with(test_document)
        assert len(chunked_docs) == 2
        for chunk_doc in chunked_docs:
            assert chunk_doc.source == test_document.source
            assert chunk_doc.source_type == test_document.source_type
            assert chunk_doc.metadata["key"] == test_document.metadata["key"]
            assert "chunk_index" in chunk_doc.metadata
            assert "total_chunks" in chunk_doc.metadata

def test_chunk_document_empty_content(test_global_config, test_settings):
    """Test chunking a document with empty content."""
    with patch('qdrant_loader.core.chunking_service.ChunkingService.__new__') as mock_chunking_service:
        # Create a mock service instance with proper configuration
        mock_service = MagicMock()
        mock_service.config = test_global_config
        mock_service.settings = test_settings
        mock_service.chunk_document.return_value = [
            Document(
                content="",
                source="test_source",
                source_type="test_type",
                metadata={"chunk_index": 0, "total_chunks": 1},
                created_at=datetime.now()
            )
        ]
        
        # Set up the mock to return our configured service
        mock_chunking_service.return_value = mock_service
        
        # Create and test the service
        service = ChunkingService(test_global_config, test_settings)
        empty_doc = Document(
            content="",
            source="test_source",
            source_type="test_type",
            metadata={},
            created_at=datetime.now()
        )
        chunked_docs = service.chunk_document(empty_doc)
        
        # Verify the service was created with correct config
        assert service.config == test_global_config
        assert service.settings == test_settings
        
        # Verify the chunking operation
        mock_service.chunk_document.assert_called_once_with(empty_doc)
        assert len(chunked_docs) == 1
        assert chunked_docs[0].content == ""
        assert chunked_docs[0].metadata["chunk_index"] == 0
        assert chunked_docs[0].metadata["total_chunks"] == 1

def test_chunk_document_error_handling(test_global_config, test_settings):
    """Test error handling in document chunking."""
    with patch('qdrant_loader.core.chunking_service.ChunkingService.__new__') as mock_chunking_service:
        # Create a mock service instance with proper configuration
        mock_service = MagicMock()
        mock_service.config = test_global_config
        mock_service.settings = test_settings
        mock_service.chunk_document.side_effect = ValueError("Invalid document")
        
        # Set up the mock to return our configured service
        mock_chunking_service.return_value = mock_service
        
        # Create and test the service
        service = ChunkingService(test_global_config, test_settings)
        
        # Verify the service was created with correct config
        assert service.config == test_global_config
        assert service.settings == test_settings
        
        # Test error handling
        with pytest.raises(ValueError, match="Invalid document"):
            service.chunk_document(None)
        
        # Verify the chunking operation
        mock_service.chunk_document.assert_called_once_with(None)