"""Tests for the chunking service."""

import pytest
from unittest.mock import patch, MagicMock
from qdrant_loader.config import GlobalConfig, ChunkingConfig, EmbeddingConfig, Settings
from qdrant_loader.core.chunking_service import ChunkingService
from qdrant_loader.core.document import Document
from datetime import datetime

@pytest.fixture
def config():
    """Create a test configuration."""
    return GlobalConfig(
        chunking=ChunkingConfig(chunk_size=500, chunk_overlap=50),
        embedding=EmbeddingConfig(
            model="text-embedding-3-small",
            tokenizer="cl100k_base"
        )
    )

@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        OPENAI_API_KEY="test-key",
        QDRANT_URL="https://test-url",
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection"
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

def test_invalid_chunk_size(config, settings):
    """Test initialization with invalid chunk size."""
    config.chunking.chunk_size = 0
    with pytest.raises(ValueError, match="Chunk size must be greater than 0"):
        ChunkingService(config, settings)

def test_invalid_chunk_overlap(config, settings):
    """Test initialization with invalid chunk overlap."""
    config.chunking.chunk_overlap = -1
    with pytest.raises(ValueError, match="Chunk overlap must be non-negative"):
        ChunkingService(config, settings)

    config.chunking.chunk_overlap = 1001
    config.chunking.chunk_size = 1000
    with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
        ChunkingService(config, settings)

def test_valid_initialization(config, settings):
    """Test that valid configuration initializes successfully."""
    service = ChunkingService(config, settings)
    assert service.config == config
    assert service.settings == settings
    assert service.chunking_strategy.chunk_size == config.chunking.chunk_size
    assert service.chunking_strategy.chunk_overlap == config.chunking.chunk_overlap

def test_chunk_document(config, settings):
    """Test document chunking."""
    # Set a smaller chunk size for testing
    config.chunking.chunk_size = 20
    config.chunking.chunk_overlap = 5
    
    service = ChunkingService(config, settings)
    doc = Document(
        content="This is a test document that should be split into multiple chunks. "
                "It contains enough text to ensure that it will be split into at least two chunks. "
                "The chunking service should handle this text correctly and create multiple chunks.",
        source="test",
        source_type="test_type",
        metadata={"key": "value"},
        created_at=datetime.now()
    )
    chunked_docs = service.chunk_document(doc)
    assert len(chunked_docs) > 1
    for chunk_doc in chunked_docs:
        assert chunk_doc.source == doc.source
        assert chunk_doc.source_type == doc.source_type
        assert chunk_doc.metadata["key"] == doc.metadata["key"]
        assert "chunk_index" in chunk_doc.metadata
        assert "total_chunks" in chunk_doc.metadata

def test_chunk_document_empty_content(config, settings):
    """Test chunking a document with empty content."""
    service = ChunkingService(config, settings)
    empty_doc = Document(
        content="",
        source="test_source",
        source_type="test_type",
        metadata={},
        created_at=datetime.now()
    )
    chunked_docs = service.chunk_document(empty_doc)
    assert len(chunked_docs) == 1
    assert chunked_docs[0].content == ""
    assert chunked_docs[0].metadata["chunk_index"] == 0
    assert chunked_docs[0].metadata["total_chunks"] == 1

def test_chunk_document_error_handling(config, settings):
    """Test error handling in document chunking."""
    service = ChunkingService(config, settings)
    with pytest.raises(Exception):
        service.chunk_document(None)