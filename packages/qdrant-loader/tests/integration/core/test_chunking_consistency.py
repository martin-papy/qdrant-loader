"""Integration test to verify chunking consistency between strategies."""

import pytest
from unittest.mock import Mock, patch

from qdrant_loader.core.chunking.strategy.default_strategy import DefaultChunkingStrategy
from qdrant_loader.core.chunking.strategy.markdown.markdown_strategy import MarkdownChunkingStrategy
from qdrant_loader.core.document import Document


class TestChunkingConsistency:
    """Test consistency between different chunking strategies."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with consistent configuration."""
        settings = Mock()
        settings.global_config.chunking.chunk_size = 200  # characters
        settings.global_config.chunking.chunk_overlap = 50  # characters
        settings.global_config.chunking.max_chunks_per_document = 1000
        settings.global_config.embedding.tokenizer = "cl100k_base"
        settings.global_config.semantic_analysis.spacy_model = "en_core_web_sm"
        return settings

    @pytest.fixture
    def test_document(self):
        """Create a test document with markdown content."""
        content = """# Introduction

This is the introduction section with some content that explains the basics. It contains multiple sentences to ensure we have enough content for testing chunking behavior.

## Getting Started

This section provides getting started information. It includes step-by-step instructions and examples to help users understand the concepts.

### Prerequisites

Before you begin, make sure you have the following prerequisites installed and configured properly.

### Installation

Follow these steps to install the software:

1. Download the package
2. Extract the files
3. Run the installer
4. Configure the settings

## Advanced Topics

This section covers advanced topics that require more detailed explanation and understanding of the fundamental concepts.

### Performance Optimization

Optimizing performance requires understanding of the underlying algorithms and data structures used in the implementation.

### Security Considerations

Security is a critical aspect that must be considered throughout the development process. This includes proper authentication, authorization, and data protection measures.

## Conclusion

This concludes the documentation with a summary of all the topics covered and references for further reading.
"""
        return Document(
            content=content,
            url="http://example.com/test.md",
            content_type="md",
            source_type="test",
            source="test_source",
            title="Test Document",
            metadata={"file_name": "test.md", "source": "test"},
        )

    def test_both_strategies_use_character_based_chunking(self, mock_settings, test_document):
        """Test that both strategies interpret chunk_size as characters."""
        
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.tiktoken") as mock_tiktoken:
            # Mock tokenizer for default strategy
            mock_encoding = Mock()
            mock_encoding.encode.side_effect = lambda text: list(range(len(text.split())))
            mock_encoding.decode.side_effect = lambda tokens: "decoded_text"
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with (
                patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"),
                patch("spacy.load") as mock_spacy_load,
            ):
                # Setup spacy mock
                mock_nlp = Mock()
                mock_nlp.pipe_names = []
                mock_spacy_load.return_value = mock_nlp
                
                # Test default strategy
                default_strategy = DefaultChunkingStrategy(mock_settings)
                default_chunks = default_strategy.chunk_document(test_document)

                # Test markdown strategy  
                markdown_strategy = MarkdownChunkingStrategy(mock_settings)
                markdown_chunks = markdown_strategy.chunk_document(test_document)

                # Both should create multiple chunks (document is ~1000+ chars, chunk_size=200)
                assert len(default_chunks) > 1, "Default strategy should create multiple chunks"
                assert len(markdown_chunks) > 1, "Markdown strategy should create multiple chunks"

                # Verify that all chunks respect the character-based size limit
                max_size = mock_settings.global_config.chunking.chunk_size
                
                for chunk in default_chunks:
                    # Allow some tolerance for boundary detection and overlap
                    assert len(chunk.content) <= max_size + 100, \
                        f"Default chunk too large: {len(chunk.content)} chars (max: {max_size})"
                
                for chunk in markdown_chunks:
                    # Markdown strategy may have slightly larger chunks due to semantic boundaries
                    # but should still be reasonable relative to the target size
                    assert len(chunk.content) <= max_size * 2, \
                        f"Markdown chunk too large: {len(chunk.content)} chars (max: {max_size})"
                
                # Verify chunking is roughly proportional to content size
                content_length = len(test_document.content)
                expected_chunks = content_length // max_size
                
                # Default strategy should be close to expected (allow ±50% variance)
                assert expected_chunks * 0.5 <= len(default_chunks) <= expected_chunks * 2, \
                    f"Default strategy chunks ({len(default_chunks)}) not in expected range for {content_length} chars"
                
                # Markdown strategy may differ more due to semantic boundaries
                assert len(markdown_chunks) >= 2, "Markdown strategy should create at least 2 chunks"

    def test_character_size_consistency(self, mock_settings):
        """Test that both strategies interpret the same chunk_size consistently."""
        
        # Test with different chunk sizes
        for chunk_size in [100, 300, 500]:
            mock_settings.global_config.chunking.chunk_size = chunk_size
            
            # Simple text content 
            simple_content = "This is a simple text. " * 50  # ~1150 characters
            
            simple_doc = Document(
                content=simple_content,
                url="http://example.com/simple.txt",
                content_type="txt",
                source_type="test",
                source="test_source",
                title="Simple Document",
                metadata={"file_name": "simple.txt"},
            )

            with (
                patch("qdrant_loader.core.chunking.strategy.base_strategy.tiktoken") as mock_tiktoken,
                patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"),
                patch("spacy.load") as mock_spacy_load,
            ):
                mock_encoding = Mock()
                
                # Setup spacy mock
                mock_nlp = Mock()
                mock_nlp.pipe_names = []
                mock_spacy_load.return_value = mock_nlp
                mock_encoding.encode.side_effect = lambda text: list(range(len(text.split())))
                mock_encoding.decode.side_effect = lambda tokens: "decoded_text"
                mock_tiktoken.get_encoding.return_value = mock_encoding

                default_strategy = DefaultChunkingStrategy(mock_settings)
                default_chunks = default_strategy.chunk_document(simple_doc)

                # Verify default strategy respects character-based limits
                assert len(default_chunks) > 0, "Default strategy should create at least one chunk"
                
                for chunk in default_chunks:
                    # Allow tolerance for overlap and boundary detection
                    assert len(chunk.content) <= chunk_size + 100, \
                        f"Default chunk too large: {len(chunk.content)} chars for chunk_size={chunk_size}"
                
                # Verify reasonable chunk count based on content length
                content_length = len(simple_content)
                expected_chunks = max(1, content_length // chunk_size)
                
                # Default strategy should create a reasonable number of chunks
                assert len(default_chunks) >= expected_chunks * 0.5, \
                    f"Too few chunks: {len(default_chunks)} for content_length={content_length}, chunk_size={chunk_size}"

    def test_tokenizer_boundary_detection_still_character_based(self, mock_settings):
        """Test that tokenizer boundary detection doesn't violate character-based sizing."""
        
        # Enable tokenizer
        mock_settings.global_config.embedding.tokenizer = "cl100k_base"
        mock_settings.global_config.chunking.chunk_size = 200  # characters
        
        # Content with clear word boundaries
        test_content = ("This is a sentence with clear word boundaries. " * 10)  # ~460 characters
        
        test_doc = Document(
            content=test_content,
            url="http://example.com/boundaries.txt",
            content_type="txt",
            source_type="test",
            source="test_source", 
            title="Boundary Test Document",
            metadata={"file_name": "boundaries.txt"},
        )

        with (
            patch("qdrant_loader.core.chunking.strategy.base_strategy.tiktoken") as mock_tiktoken,
            patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"),
            patch("spacy.load") as mock_spacy_load,
        ):
            # Setup spacy mock
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            mock_spacy_load.return_value = mock_nlp
            
            mock_encoding = Mock()
            mock_encoding.encode.side_effect = lambda text: list(range(len(text)))  # 1 token per char
            mock_encoding.decode.side_effect = lambda tokens: "decoded"
            mock_tiktoken.get_encoding.return_value = mock_encoding

            default_strategy = DefaultChunkingStrategy(mock_settings)
            chunks = default_strategy.chunk_document(test_doc)

            # Should create multiple chunks
            assert len(chunks) >= 2, "Should create multiple chunks for long content"

            # All chunks should respect character-based size limit (with tolerance for boundaries)
            max_size = mock_settings.global_config.chunking.chunk_size
            for i, chunk in enumerate(chunks):
                assert len(chunk.content) <= max_size + 50, \
                    f"Chunk {i} too large: {len(chunk.content)} chars (max: {max_size} + boundary tolerance)" 