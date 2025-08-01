"""Tests for MarkdownChunkingStrategy."""

import pytest
from unittest.mock import Mock, patch

from qdrant_loader.core.chunking.strategy.markdown.markdown_strategy import MarkdownChunkingStrategy
from qdrant_loader.core.document import Document


@pytest.fixture
def settings():
    """Create mock settings for testing."""
    mock_settings = Mock()
    mock_settings.global_config.chunking.chunk_size = 1000
    mock_settings.global_config.chunking.chunk_overlap = 100
    mock_settings.global_config.chunking.max_chunks_per_document = 50
    mock_settings.global_config.embedding.tokenizer = "none"
    mock_settings.global_config.semantic_analysis.spacy_model = "en_core_web_sm"
    mock_settings.global_config.semantic_analysis.enable_entity_extraction = True
    
    # Create proper mock object structure for markdown strategy settings
    markdown_config = Mock()
    markdown_config.min_chunk_size = 50
    markdown_config.max_chunk_size = 2000
    markdown_config.enable_semantic_splitting = True
    markdown_config.min_content_length_for_nlp = 100
    markdown_config.min_word_count_for_nlp = 10
    markdown_config.min_line_count_for_nlp = 3
    markdown_config.enable_header_based_splitting = True
    markdown_config.enable_table_detection = True
    markdown_config.enable_cross_reference_extraction = True
    markdown_config.max_workers = 4
    markdown_config.estimation_buffer = 0.2  # 20% estimation buffer
    
    mock_settings.global_config.chunking.strategies.markdown = markdown_config
    return mock_settings


@pytest.fixture  
def markdown_strategy(settings):
    """Create a MarkdownChunkingStrategy instance for testing."""
    with patch("qdrant_loader.core.text_processing.text_processor.TextProcessor"), \
         patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
        return MarkdownChunkingStrategy(settings)


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    return Document(
        title="Test Markdown Document",
        content="# Main Header\nThis is the main content.\n\n## Sub Header\nThis is sub content.",
        content_type="md",
        metadata={"file_name": "test.md"},
        source="test.md",
        source_type="markdown", 
        url="file:///test.md",
    )


class TestMarkdownChunkingStrategy:
    """Test MarkdownChunkingStrategy functionality."""

    def test_initialization(self, markdown_strategy):
        """Test that MarkdownChunkingStrategy initializes properly."""
        assert markdown_strategy is not None
        assert hasattr(markdown_strategy, 'document_parser')
        assert hasattr(markdown_strategy, 'section_splitter')
        assert hasattr(markdown_strategy, 'metadata_extractor') 
        assert hasattr(markdown_strategy, 'chunk_processor')

    def test_chunk_document_basic(self, markdown_strategy, sample_document):
        """Test basic document chunking functionality."""
        chunks = markdown_strategy.chunk_document(sample_document)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, Document)
            assert len(chunk.content) > 0

    def test_chunk_document_with_headers(self, markdown_strategy):
        """Test chunking document with multiple headers."""
        content = """# Level 1 Header
Content for level 1.

## Level 2 Header  
Content for level 2.

### Level 3 Header
Content for level 3.
"""
        document = Document(
            title="Multi-level Document",
            content=content,
            content_type="md",
            metadata={},
            source="multi.md",
            source_type="markdown",
            url="file:///multi.md",
        )
        
        chunks = markdown_strategy.chunk_document(document)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_fallback_chunking(self, markdown_strategy, sample_document):
        """Test fallback chunking when main strategy fails."""
        # Access the fallback method directly
        chunks = markdown_strategy._fallback_chunking(sample_document)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, Document)

    def test_chunk_overlap_property(self, markdown_strategy):
        """Test chunk overlap property getter/setter."""
        # Test setting overlap before components are initialized
        markdown_strategy.chunk_overlap = 150
        assert markdown_strategy.chunk_overlap == 150

    def test_shutdown_method(self, markdown_strategy):
        """Test shutdown method doesn't raise exceptions."""
        # Should not raise an exception
        markdown_strategy.shutdown()

    def test_destructor_method(self, markdown_strategy):
        """Test destructor method doesn't raise exceptions."""
        # Should not raise an exception  
        del markdown_strategy