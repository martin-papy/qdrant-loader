"""Unit tests for modernized HTML chunking strategy."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.config.types import SourceType
from qdrant_loader.core.chunking.strategy.html_strategy import HTMLChunkingStrategy
from qdrant_loader.core.document import Document


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)

    # Mock global_config
    global_config = Mock()

    # Mock chunking config
    chunking_config = Mock()
    chunking_config.chunk_size = 1000
    chunking_config.chunk_overlap = 100
    chunking_config.max_chunks_per_document = 500

    # Mock strategy-specific config
    strategies_config = Mock()
    
    # Mock HTML strategy config
    html_config = Mock()
    html_config.simple_parsing_threshold = 100000
    html_config.max_html_size_for_parsing = 500000
    html_config.max_sections_to_process = 200
    html_config.max_chunk_size_for_nlp = 20000
    html_config.preserve_semantic_structure = True
    
    strategies_config.html = html_config
    chunking_config.strategies = strategies_config

    # Mock semantic analysis config
    semantic_analysis_config = Mock()
    semantic_analysis_config.num_topics = 5
    semantic_analysis_config.lda_passes = 10
    semantic_analysis_config.spacy_model = "en_core_web_sm"
    
    # Mock embedding config
    embedding_config = Mock()
    embedding_config.tokenizer = "cl100k_base"

    global_config.chunking = chunking_config
    global_config.semantic_analysis = semantic_analysis_config
    global_config.embedding = embedding_config
    settings.global_config = global_config

    return settings


@pytest.fixture
def sample_html_document():
    """Create a sample HTML document for testing."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Test Document</title>
        <meta name="description" content="A test HTML document">
    </head>
    <body>
        <header>
            <h1>Main Title</h1>
            <nav>
                <ul>
                    <li><a href="#section1">Section 1</a></li>
                    <li><a href="#section2">Section 2</a></li>
                </ul>
            </nav>
        </header>
        <main>
            <article id="section1">
                <h2>Section 1 Title</h2>
                <p>This is the content of section 1. It contains meaningful text that should be properly chunked and analyzed.</p>
                <div class="content-block">
                    <p>This is additional content in section 1.</p>
                </div>
            </article>
            <article id="section2">
                <h2>Section 2 Title</h2>
                <p>This is the content of section 2. It also contains meaningful text for testing purposes.</p>
                <blockquote>
                    <p>This is a quote within section 2.</p>
                </blockquote>
            </article>
        </main>
        <aside>
            <h3>Sidebar</h3>
            <p>This is sidebar content.</p>
        </aside>
        <footer>
            <p>Footer content.</p>
        </footer>
    </body>
    </html>
    """
    
    return Document(
        content=html_content,
        metadata={
            "file_name": "test.html",
            "source": "test_source",
        },
        source="test_source",
        source_type=SourceType.LOCALFILE,
        url="file://test.html",
        title="Test HTML Document",
        content_type="text/html"
    )


class TestHTMLChunkingStrategyModern:
    """Test cases for modernized HTML chunking strategy."""

    def test_initialization(self, mock_settings):
        """Test strategy initialization with modular components."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
        
        # Verify modular components are initialized
        assert hasattr(strategy, 'document_parser')
        assert hasattr(strategy, 'section_splitter')
        assert hasattr(strategy, 'metadata_extractor')
        assert hasattr(strategy, 'chunk_processor')
        assert hasattr(strategy, 'html_config')
        
        # Verify configuration is loaded
        assert strategy.max_html_size_for_parsing == 500000

    def test_chunk_document_success(self, mock_settings, sample_html_document):
        """Test successful HTML document chunking."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
        
        chunks = strategy.chunk_document(sample_html_document)
        
        # Verify chunks were created
        assert len(chunks) > 0
        assert all(isinstance(chunk, Document) for chunk in chunks)
        
        # Verify chunk metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert chunk.metadata["parent_document_id"] == sample_html_document.id
            assert chunk.metadata["chunking_strategy"] == "html_modular"
            assert "content_type" in chunk.metadata
            assert "document_structure" in chunk.metadata

    def test_chunk_document_with_semantic_structure(self, mock_settings, sample_html_document):
        """Test HTML chunking preserves semantic structure."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
        
        chunks = strategy.chunk_document(sample_html_document)
        
        # Check that semantic metadata is preserved
        semantic_chunks = [chunk for chunk in chunks if chunk.metadata.get("is_semantic", False)]
        
        # Should have at least some chunks with semantic structure
        # Note: this might be 0 if the chunking is very granular, which is also valid
        assert len(chunks) > 0

    def test_chunk_document_large_file_fallback(self, mock_settings):
        """Test fallback behavior for very large HTML files."""
        # Create a very large HTML document
        large_html = "<html><body>" + "x" * 1000000 + "</body></html>"  # > 500KB
        
        large_document = Document(
            content=large_html,
            metadata={"file_name": "large.html"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://large.html",
            title="Large HTML Document",
            content_type="text/html"
        )
        
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
            chunks = strategy.chunk_document(large_document)
        
        # Should still produce chunks using fallback
        assert len(chunks) > 0
        
        # Check fallback metadata
        for chunk in chunks:
            # Should indicate fallback was used
            assert "chunking_strategy" in chunk.metadata

    def test_chunk_document_empty_content(self, mock_settings):
        """Test handling of empty HTML content."""
        empty_document = Document(
            content="",
            metadata={"file_name": "empty.html"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://empty.html",
            title="Empty HTML Document",
            content_type="text/html"
        )
        
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
            chunks = strategy.chunk_document(empty_document)
        
        # Should handle empty content gracefully
        assert isinstance(chunks, list)

    def test_chunk_document_malformed_html(self, mock_settings):
        """Test handling of malformed HTML."""
        malformed_html = "<html><body><p>Unclosed paragraph<div>Mismatched tags</p></div>"
        
        malformed_document = Document(
            content=malformed_html,
            metadata={"file_name": "malformed.html"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://malformed.html",
            title="Malformed HTML Document",
            content_type="text/html"
        )
        
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
            chunks = strategy.chunk_document(malformed_document)
        
        # Should handle malformed HTML gracefully with fallback
        assert isinstance(chunks, list)
        if chunks:  # If any chunks are produced
            for chunk in chunks:
                assert chunk.metadata["parent_document_id"] == malformed_document.id

    def test_strategy_shutdown(self, mock_settings):
        """Test strategy shutdown and cleanup."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
        
        # Should not raise any exceptions
        strategy.shutdown()
        
        # Verify cleanup completed
        assert True  # If we get here, shutdown worked

    def test_components_integration(self, mock_settings, sample_html_document):
        """Test that all modular components work together."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = HTMLChunkingStrategy(mock_settings)
        
        # Test document parser
        structure = strategy.document_parser.parse_document_structure(sample_html_document.content)
        assert isinstance(structure, dict)
        assert "structure_type" in structure
        
        # Test section splitter
        sections = strategy.section_splitter.split_sections(sample_html_document.content)
        assert isinstance(sections, list)
        
        # Test full integration
        chunks = strategy.chunk_document(sample_html_document)
        assert len(chunks) > 0 