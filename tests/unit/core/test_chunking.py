"""
Tests for the core chunking module.
"""
import pytest
import structlog
from unittest.mock import patch, MagicMock
from qdrant_loader.core.document import Document
from qdrant_loader.core.chunking_strategy import ChunkingStrategy
from datetime import datetime
from qdrant_loader.config import Settings, GlobalConfig, EmbeddingConfig

# Configure logger for testing
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False
)

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.global_config = GlobalConfig(
        embedding=EmbeddingConfig(
            model="text-embedding-3-small",
            tokenizer="cl100k_base"
        )
    )
    return settings

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

def test_chunking_strategy_initialization(mock_settings):
    """Test chunking strategy initialization."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=100, chunk_overlap=20)
    assert strategy.chunk_size == 100
    assert strategy.chunk_overlap == 20
    
    # Test invalid overlap
    with pytest.raises(ValueError):
        ChunkingStrategy(settings=mock_settings, chunk_size=100, chunk_overlap=100)

def test_chunking_simple_text(mock_settings):
    """Test chunking with simple text."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=10, chunk_overlap=2)
    text = "This is a test sentence that will be chunked."
    chunks = strategy._split_text(text)
    
    assert len(chunks) > 1
    assert all(strategy._count_tokens(chunk) <= 10 for chunk in chunks)

def test_chunking_document(mock_settings):
    """Test chunking a document with metadata."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=10, chunk_overlap=2)
    doc = Document(
        content="This is a test sentence that will be chunked.",
        source="test_source",
        source_type="test_type",
        url="http://example.com",
        project="test_project"
    )
    
    chunked_docs = strategy.chunk_document(doc)
    
    assert len(chunked_docs) > 1
    for i, chunk_doc in enumerate(chunked_docs):
        assert chunk_doc.source == doc.source
        assert chunk_doc.source_type == doc.source_type
        assert chunk_doc.url == doc.url
        assert chunk_doc.project == doc.project
        assert chunk_doc.metadata['chunk_index'] == i
        assert chunk_doc.metadata['total_chunks'] == len(chunked_docs)
        assert strategy._count_tokens(chunk_doc.content) <= 10

def test_chunking_empty_document(mock_settings):
    """Test chunking an empty document."""
    strategy = ChunkingStrategy(settings=mock_settings)
    doc = Document(
        content="",
        source="test_source",
        source_type="test_type"
    )
    
    chunked_docs = strategy.chunk_document(doc)
    assert len(chunked_docs) == 1
    assert chunked_docs[0].content == ""
    assert chunked_docs[0].metadata['chunk_index'] == 0
    assert chunked_docs[0].metadata['total_chunks'] == 1

def test_chunking_strategy_init(mock_settings):
    """Test initialization of chunking strategy."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=500, chunk_overlap=50)
    assert strategy.chunk_size == 500
    assert strategy.chunk_overlap == 50
    assert strategy.encoding is not None

def test_chunking_strategy_init_invalid_overlap(mock_settings):
    """Test initialization with invalid overlap."""
    with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
        ChunkingStrategy(settings=mock_settings, chunk_size=500, chunk_overlap=500)

def test_count_tokens(mock_settings):
    """Test token counting."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=500, chunk_overlap=50)
    text = "This is a test."
    token_count = strategy._count_tokens(text)
    assert token_count > 0

def test_split_text_empty(mock_settings):
    """Test splitting empty text."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=500, chunk_overlap=50)
    chunks = strategy._split_text("")
    assert len(chunks) == 1
    assert chunks[0] == ""

def test_split_text_small(mock_settings):
    """Test splitting text smaller than chunk size."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=500, chunk_overlap=50)
    text = "This is a small text."
    chunks = strategy._split_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_split_text_large(mock_settings):
    """Test splitting large text."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=10, chunk_overlap=2)
    text = "This is a longer text that should be split into multiple chunks."
    chunks = strategy._split_text(text)
    assert len(chunks) > 1
    # Verify that chunks are not empty
    assert all(chunk for chunk in chunks)
    # Verify that each chunk is not longer than the maximum size
    assert all(strategy._count_tokens(chunk) <= 10 for chunk in chunks)

def test_split_text_with_overlap(mock_settings):
    """Test text splitting with overlap."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=10, chunk_overlap=5)
    text = "This is a text that should have overlapping chunks."
    chunks = strategy._split_text(text)
    # Verify that chunks overlap
    for i in range(len(chunks) - 1):
        # Get the tokens of consecutive chunks
        current_tokens = strategy.encoding.encode(chunks[i])
        next_tokens = strategy.encoding.encode(chunks[i + 1])
        # Check if there are overlapping tokens
        overlap = len(set(current_tokens[-5:]).intersection(set(next_tokens[:5])))
        assert overlap > 0

def test_chunk_document(mock_settings):
    """Test document chunking."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=10, chunk_overlap=2)
    doc = Document(
        content="This is a test document that should be split into multiple chunks.",
        source="test",
        source_type="test_type",
        metadata={"key": "value"}
    )
    chunked_docs = strategy.chunk_document(doc)
    assert len(chunked_docs) > 1
    # Verify that metadata is preserved
    for chunk_doc in chunked_docs:
        assert chunk_doc.source == doc.source
        assert chunk_doc.source_type == doc.source_type
        assert chunk_doc.metadata["key"] == doc.metadata["key"]
        assert "chunk_index" in chunk_doc.metadata
        assert "total_chunks" in chunk_doc.metadata

def test_chunk_document_empty(mock_settings):
    """Test chunking empty document."""
    strategy = ChunkingStrategy(settings=mock_settings, chunk_size=500, chunk_overlap=50)
    doc = Document(
        content="",
        source="test",
        source_type="test_type",
        metadata={"key": "value"}
    )
    chunked_docs = strategy.chunk_document(doc)
    assert len(chunked_docs) == 1
    assert chunked_docs[0].content == ""
    assert chunked_docs[0].metadata["chunk_index"] == 0
    assert chunked_docs[0].metadata["total_chunks"] == 1

def test_chunk_document_with_model(mock_settings):
    """Test chunking with different model."""
    strategy = ChunkingStrategy(
        settings=mock_settings,
        chunk_size=500,
        chunk_overlap=50
    )
    doc = Document(
        content="This is a test document.",
        source="test",
        source_type="test_type"
    )
    chunked_docs = strategy.chunk_document(doc)
    assert len(chunked_docs) == 1 