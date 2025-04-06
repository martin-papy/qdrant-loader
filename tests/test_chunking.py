import pytest
import structlog
from qdrant_loader.core.document import Document
from qdrant_loader.core.chunking import ChunkingStrategy

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

def test_chunking_strategy_initialization():
    """Test chunking strategy initialization."""
    strategy = ChunkingStrategy(chunk_size=100, chunk_overlap=20)
    assert strategy.chunk_size == 100
    assert strategy.chunk_overlap == 20
    
    # Test invalid overlap
    with pytest.raises(ValueError):
        ChunkingStrategy(chunk_size=100, chunk_overlap=100)

def test_chunking_simple_text():
    """Test chunking with simple text."""
    strategy = ChunkingStrategy(chunk_size=10, chunk_overlap=2)
    text = "This is a test sentence that will be chunked."
    chunks = strategy._split_text(text)
    
    assert len(chunks) > 1
    assert all(strategy._count_tokens(chunk) <= 10 for chunk in chunks)

def test_chunking_document():
    """Test chunking a document with metadata."""
    strategy = ChunkingStrategy(chunk_size=10, chunk_overlap=2)
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

def test_chunking_empty_document():
    """Test chunking an empty document."""
    strategy = ChunkingStrategy()
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