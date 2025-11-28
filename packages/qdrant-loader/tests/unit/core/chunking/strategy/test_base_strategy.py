"""Tests for the BaseChunkingStrategy."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document


# Create a concrete implementation for testing
class ConcreteChunkingStrategy(BaseChunkingStrategy):
    """Concrete implementation of BaseChunkingStrategy for testing."""

    def chunk_document(self, document: Document) -> list[Document]:
        """Test implementation of chunk_document."""
        return [document]

    def _split_text(self, text: str) -> list[str]:
        """Test implementation of _split_text."""
        return [text]


class TestBaseChunkingStrategy:
    """Test cases for the BaseChunkingStrategy."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 1000
        settings.global_config.chunking.chunk_overlap = 200
        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = "cl100k_base"
        return settings

    @pytest.fixture
    def mock_settings_no_tokenizer(self):
        """Create mock settings with no tokenizer."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 1000
        settings.global_config.chunking.chunk_overlap = 200
        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = "none"
        return settings

    def test_initialization_with_tokenizer(self, mock_settings):
        """Test initialization with tokenizer."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = ConcreteChunkingStrategy(mock_settings)

                assert strategy.settings == mock_settings
                assert strategy.chunk_size == 1000
                assert strategy.chunk_overlap == 200
                assert strategy.tokenizer == "cl100k_base"
                assert strategy.encoding == mock_encoding
                mock_tiktoken.get_encoding.assert_called_once_with("cl100k_base")

    def test_initialization_without_tokenizer(self, mock_settings_no_tokenizer):
        """Test initialization without tokenizer."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings_no_tokenizer)

            assert strategy.encoding is None
            assert strategy.tokenizer == "none"

    def test_initialization_tokenizer_error(self, mock_settings):
        """Test initialization when tokenizer fails to load."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_tiktoken.get_encoding.side_effect = Exception("Tokenizer error")

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = ConcreteChunkingStrategy(mock_settings)

                assert strategy.encoding is None

    def test_initialization_with_custom_chunk_params(self, mock_settings):
        """Test initialization with custom chunk size and overlap."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(
                mock_settings, chunk_size=500, chunk_overlap=50
            )

            assert strategy.chunk_size == 500
            assert strategy.chunk_overlap == 50

    def test_initialization_invalid_overlap(self, mock_settings):
        """Test initialization with invalid overlap (>= chunk_size)."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            with pytest.raises(
                ValueError, match="Chunk overlap must be less than chunk size"
            ):
                ConcreteChunkingStrategy(
                    mock_settings, chunk_size=100, chunk_overlap=100
                )

    def test_count_tokens_with_tokenizer(self, mock_settings):
        """Test token counting with tokenizer."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.tiktoken"
        ) as mock_tiktoken:
            mock_encoding = Mock()
            mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
            mock_tiktoken.get_encoding.return_value = mock_encoding

            with patch(
                "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
            ):
                strategy = ConcreteChunkingStrategy(mock_settings)

                count = strategy._count_tokens("test text")
                assert count == 5
                mock_encoding.encode.assert_called_once_with("test text")

    def test_count_tokens_without_tokenizer(self, mock_settings_no_tokenizer):
        """Test token counting without tokenizer (character fallback)."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings_no_tokenizer)

            count = strategy._count_tokens("test text")
            assert count == 9  # Character count

    def test_process_text(self, mock_settings):
        """Test text processing delegation."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_text.return_value = {"entities": [], "pos_tags": []}
            mock_processor_class.return_value = mock_processor

            strategy = ConcreteChunkingStrategy(mock_settings)
            result = strategy._process_text("test text")

            assert result == {"entities": [], "pos_tags": []}
            mock_processor.process_text.assert_called_once_with("test text")

    def test_should_apply_nlp_text_files(self, mock_settings):
        """Test NLP application decision for text files."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Text extensions should apply NLP
            assert strategy._should_apply_nlp("content", "file.md") is True
            assert strategy._should_apply_nlp("content", "file.txt") is True
            assert strategy._should_apply_nlp("content", "file.rst") is True

    def test_should_apply_nlp_code_files(self, mock_settings):
        """Test NLP application decision for code files."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Code extensions should not apply NLP
            assert strategy._should_apply_nlp("content", "file.py") is False
            assert strategy._should_apply_nlp("content", "file.js") is False
            assert strategy._should_apply_nlp("content", "file.java") is False

    def test_should_apply_nlp_structured_files(self, mock_settings):
        """Test NLP application decision for structured files."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Structured data extensions should not apply NLP
            assert strategy._should_apply_nlp("content", "file.json") is False
            assert strategy._should_apply_nlp("content", "file.xml") is False
            assert strategy._should_apply_nlp("content", "file.yaml") is False

    def test_should_apply_nlp_binary_files(self, mock_settings):
        """Test NLP application decision for binary files."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Binary extensions should not apply NLP
            assert strategy._should_apply_nlp("content", "file.pdf") is False
            assert strategy._should_apply_nlp("content", "file.jpg") is False
            assert strategy._should_apply_nlp("content", "file.zip") is False

    def test_should_apply_nlp_html_files(self, mock_settings):
        """Test NLP application decision for HTML files."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # HTML should apply NLP
            assert strategy._should_apply_nlp("content", "file.html") is True
            assert strategy._should_apply_nlp("content", "", "html") is True

    def test_should_apply_nlp_large_content(self, mock_settings):
        """Test NLP application decision for large content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Large content should not apply NLP
            large_content = "x" * 25000  # > 20KB limit
            assert strategy._should_apply_nlp(large_content, "file.txt") is False

    def test_should_apply_nlp_unknown_extension_code_like(self, mock_settings):
        """Test NLP application decision for unknown extension with code-like content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Code-like content should not apply NLP
            code_like = "function test() { return {}; }"
            assert strategy._should_apply_nlp(code_like, "file") is False

    def test_should_apply_nlp_unknown_extension_structured_like(self, mock_settings):
        """Test NLP application decision for unknown extension with structured content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Structured-like content should not apply NLP
            structured_like = '{"key": "value"}'
            assert strategy._should_apply_nlp(structured_like, "file") is False

    def test_should_apply_nlp_unknown_extension_text_like(self, mock_settings):
        """Test NLP application decision for unknown extension with text-like content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            # Text-like content should apply NLP
            text_like = "This is a normal text document with sentences."
            assert strategy._should_apply_nlp(text_like, "file") is True

    def test_extract_nlp_worthy_content_comment(self, mock_settings):
        """Test NLP content extraction for comments."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            content = "This is a comment"
            result = strategy._extract_nlp_worthy_content(content, "comment")
            assert result == content

    def test_extract_nlp_worthy_content_docstring(self, mock_settings):
        """Test NLP content extraction for docstrings."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            content = "This is a docstring"
            result = strategy._extract_nlp_worthy_content(content, "docstring")
            assert result == content

    def test_extract_nlp_worthy_content_code_element(self, mock_settings):
        """Test NLP content extraction for code elements."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            code_content = '''
def test_function():
    """This is a docstring."""
    # This is a comment
    return True
'''
            result = strategy._extract_nlp_worthy_content(code_content, "function")
            assert "This is a docstring." in result
            assert "This is a comment" in result

    def test_extract_nlp_worthy_content_non_code(self, mock_settings):
        """Test NLP content extraction for non-code content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            content = "This is regular text content."
            result = strategy._extract_nlp_worthy_content(content, "")
            assert result == content

    def test_extract_comments_and_docstrings_python_comments(self, mock_settings):
        """Test extraction of Python-style comments."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            code = """
# This is a comment
def function():
    # Another comment
    pass
"""
            result = strategy._extract_comments_and_docstrings(code)
            assert "This is a comment" in result
            assert "Another comment" in result

    def test_extract_comments_and_docstrings_c_style_comments(self, mock_settings):
        """Test extraction of C-style comments."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            code = """
// Single line comment
function test() {
    /* Multi-line
       comment */
    return true;
}
"""
            result = strategy._extract_comments_and_docstrings(code)
            assert "Single line comment" in result
            assert "Multi-line" in result
            assert "comment" in result

    def test_extract_comments_and_docstrings_python_docstrings(self, mock_settings):
        """Test extraction of Python docstrings."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            code = '''
def function():
    """This is a docstring."""
    pass

class TestClass:
    \'\'\'
    Multi-line docstring
    with multiple lines.
    \'\'\'
    pass
'''
            result = strategy._extract_comments_and_docstrings(code)
            assert "This is a docstring." in result
            assert "Multi-line docstring" in result
            assert "with multiple lines." in result

    def test_extract_comments_and_docstrings_mixed(self, mock_settings):
        """Test extraction of mixed comment types."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            code = '''
# Python comment
def function():
    """Python docstring."""
    // C-style comment
    /* Multi-line
       C-style comment */
    pass
'''
            result = strategy._extract_comments_and_docstrings(code)
            assert "Python comment" in result
            assert "Python docstring." in result
            assert "C-style comment" in result
            assert "Multi-line" in result

    def test_create_chunk_document_basic(self, mock_settings):
        """Test basic chunk document creation."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={"source": "test"},
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="text",
            )

            chunk_doc = strategy._create_chunk_document(
                original_doc, "Chunk content", 0, 2, skip_nlp=True
            )

            assert chunk_doc.content == "Chunk content"
            assert chunk_doc.metadata["chunk_index"] == 0
            assert chunk_doc.metadata["total_chunks"] == 2
            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.source == "test_source"
            assert chunk_doc.url == "http://test.com"

    def test_create_chunk_document_with_nlp(self, mock_settings):
        """Test chunk document creation with NLP processing."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_text.return_value = {
                "entities": ["entity1"],
                "pos_tags": ["tag1"],
            }
            mock_processor_class.return_value = mock_processor

            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={"file_name": "test.txt"},
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="text",
            )

            chunk_doc = strategy._create_chunk_document(
                original_doc, "This is text content for NLP processing.", 0, 2
            )

            assert chunk_doc.metadata["nlp_skipped"] is False
            assert chunk_doc.metadata["entities"] == ["entity1"]
            assert chunk_doc.metadata["pos_tags"] == ["tag1"]

    def test_create_chunk_document_skip_large_chunk(self, mock_settings):
        """Test chunk document creation skipping NLP for large chunks."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={"file_name": "test.txt"},
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="text",
            )

            large_content = "x" * 15000  # > 10000 limit
            chunk_doc = strategy._create_chunk_document(
                original_doc, large_content, 0, 2
            )

            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.metadata["skip_reason"] == "chunk_too_large"

    def test_create_chunk_document_skip_many_chunks(self, mock_settings):
        """Test chunk document creation skipping NLP for too many chunks."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={"file_name": "test.txt"},
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="text",
            )

            chunk_doc = strategy._create_chunk_document(
                original_doc, "Small content", 0, 60  # > 50 limit
            )

            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.metadata["skip_reason"] == "too_many_chunks"

    def test_create_chunk_document_skip_inappropriate_content(self, mock_settings):
        """Test chunk document creation skipping NLP for inappropriate content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={"file_name": "test.py"},  # Code file
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="text",
            )

            chunk_doc = strategy._create_chunk_document(
                original_doc, "def function(): pass", 0, 2
            )

            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.metadata["skip_reason"] == "content_type_inappropriate"

    def test_create_chunk_document_nlp_error(self, mock_settings):
        """Test chunk document creation with NLP processing error."""
        with patch(
            "qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_text.side_effect = Exception("NLP error")
            mock_processor_class.return_value = mock_processor

            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={"file_name": "test.txt"},
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="text",
            )

            chunk_doc = strategy._create_chunk_document(
                original_doc, "Text content", 0, 2
            )

            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.metadata["skip_reason"] == "nlp_error"

    def test_create_chunk_document_no_nlp_worthy_content(self, mock_settings):
        """Test chunk document creation with no NLP-worthy content."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={"file_name": "test.txt", "element_type": "function"},
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="text",
            )

            # Code without comments/docstrings
            chunk_doc = strategy._create_chunk_document(
                original_doc, "def function(): pass", 0, 2
            )

            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.metadata["skip_reason"] == "no_nlp_worthy_content"

    def test_abstract_methods_defined(self):
        """Test that BaseChunkingStrategy has abstract methods defined."""
        # Verify that the abstract methods are defined in the class
        assert hasattr(BaseChunkingStrategy, "chunk_document")

        # Verify that the class has abstract methods
        assert getattr(BaseChunkingStrategy, "__abstractmethods__", None) is not None
        abstract_methods = BaseChunkingStrategy.__abstractmethods__
        assert "chunk_document" in abstract_methods

    def test_create_chunk_document_converted_file_enables_nlp(self, mock_settings):
        """Test chunk document creation enables NLP for converted files."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={
                    "file_name": "test.docx",  # Original binary file
                    "conversion_method": "markitdown",  # File was converted
                    "conversion_failed": False,
                    "original_file_type": "docx",
                },
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="md",  # Converted to markdown
            )

            chunk_doc = strategy._create_chunk_document(
                original_doc, "This is converted markdown content.", 0, 2
            )

            # Should NOT skip NLP for converted files
            assert chunk_doc.metadata["nlp_skipped"] is False
            assert "skip_reason" not in chunk_doc.metadata
            # Should have NLP processing results
            assert "entities" in chunk_doc.metadata
            assert "pos_tags" in chunk_doc.metadata
            assert "nlp_content_extracted" in chunk_doc.metadata
            assert "nlp_content_ratio" in chunk_doc.metadata

    def test_create_chunk_document_non_converted_binary_file_skips_nlp(
        self, mock_settings
    ):
        """Test chunk document creation skips NLP for non-converted binary files."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"):
            strategy = ConcreteChunkingStrategy(mock_settings)

            original_doc = Document(
                content="Original content",
                metadata={
                    "file_name": "test.docx",  # Original binary file
                    # No conversion_method - file was not converted
                },
                source="test_source",
                source_type="test",
                url="http://test.com",
                title="Test Title",
                content_type="docx",  # Still binary
            )

            chunk_doc = strategy._create_chunk_document(
                original_doc, "Raw binary content", 0, 2
            )

            # Should skip NLP for non-converted binary files
            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.metadata["skip_reason"] == "content_type_inappropriate"
