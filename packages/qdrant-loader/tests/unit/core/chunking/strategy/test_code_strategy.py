"""Unit tests for code chunking strategy."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.config.types import SourceType
from qdrant_loader.core.chunking.strategy.code_strategy import (
    CodeChunkingStrategy,
    CodeElementType,
)
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
def sample_python_code():
    """Sample Python code for testing."""
    return '''
import os
import sys
from typing import List, Dict

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

def main():
    """Main function."""
    calc = Calculator()
    print(calc.add(5, 3))
    print(calc.multiply(4, 6))

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def sample_java_code():
    """Sample Java code for testing."""
    return """
package com.example;

import java.util.ArrayList;
import java.util.List;

public class Calculator {
    private List<String> history;

    public Calculator() {
        this.history = new ArrayList<>();
    }

    public int add(int a, int b) {
        int result = a + b;
        history.add(a + " + " + b + " = " + result);
        return result;
    }

    public int multiply(int a, int b) {
        int result = a * b;
        history.add(a + " * " + b + " = " + result);
        return result;
    }

    public static void main(String[] args) {
        Calculator calc = new Calculator();
        System.out.println(calc.add(5, 3));
        System.out.println(calc.multiply(4, 6));
    }
}
"""


class TestCodeChunkingStrategy:
    """Test CodeChunkingStrategy functionality."""

    @patch("spacy.load")
    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    def test_initialization(self, mock_semantic_analyzer, mock_spacy_load, mock_settings):
        """Test strategy initialization."""
        # Setup spacy mock
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp
        
        strategy = CodeChunkingStrategy(mock_settings)

        assert strategy is not None
        assert hasattr(strategy, "language_patterns")
        assert ".py" in strategy.language_patterns
        assert ".java" in strategy.language_patterns
        assert ".js" in strategy.language_patterns

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    @patch("qdrant_loader.core.text_processing.text_processor.TextProcessor")
    @patch("aiohttp.ClientSession")
    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    def test_detect_language_python(
        self,
        mock_set_event_loop,
        mock_new_event_loop,
        mock_client_session,
        mock_text_processor,
        mock_semantic_analyzer,
        mock_settings,
        sample_python_code,
    ):
        """Test language detection for Python."""
        # Mock event loop to prevent real loop creation
        mock_loop = Mock()
        mock_loop.is_closed.return_value = False
        mock_loop.close = Mock()
        mock_new_event_loop.return_value = mock_loop

        strategy = CodeChunkingStrategy(mock_settings)

        # Test with file extension
        language = strategy._detect_language("test.py", sample_python_code)
        assert language == "python"

        # Test with unknown extension
        language = strategy._detect_language("test", sample_python_code)
        assert language == "unknown"

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    def test_detect_language_java(
        self, mock_semantic_analyzer, mock_settings, sample_java_code
    ):
        """Test language detection for Java."""
        strategy = CodeChunkingStrategy(mock_settings)

        # Test with file extension
        language = strategy._detect_language("Calculator.java", sample_java_code)
        assert language == "java"

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    def test_parse_python_ast(
        self, mock_semantic_analyzer, mock_settings, sample_python_code
    ):
        """Test Python AST parsing."""
        strategy = CodeChunkingStrategy(mock_settings)

        elements = strategy._parse_python_ast(sample_python_code)

        assert len(elements) > 0

        # Check for imports
        import_elements = [
            e for e in elements if e.element_type == CodeElementType.IMPORT
        ]
        assert len(import_elements) >= 2  # os, sys, typing imports

        # Check for class
        class_elements = [
            e for e in elements if e.element_type == CodeElementType.CLASS
        ]
        assert len(class_elements) == 1
        assert class_elements[0].name == "Calculator"

        # Check for functions
        function_elements = [
            e for e in elements if e.element_type == CodeElementType.FUNCTION
        ]
        assert len(function_elements) >= 1  # main function

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    def test_tree_sitter_parsing(
        self, mock_semantic_analyzer, mock_settings, sample_python_code
    ):
        """Test tree-sitter parsing (if available)."""
        strategy = CodeChunkingStrategy(mock_settings)

        # This test will pass regardless of tree-sitter availability
        elements = strategy._parse_with_tree_sitter(sample_python_code, "python")

        # If tree-sitter is available, we should get elements
        # If not, we should get an empty list
        assert isinstance(elements, list)

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    @patch("qdrant_loader.core.text_processing.text_processor.TextProcessor")
    def test_chunk_python_document(
        self,
        mock_text_processor,
        mock_semantic_analyzer,
        mock_settings,
        sample_python_code,
    ):
        """Test chunking a Python document."""
        # Mock the text processor
        mock_text_processor_instance = Mock()
        mock_text_processor_instance.process_text.return_value = {
            "entities": [],
            "pos_tags": [],
        }
        mock_text_processor.return_value = mock_text_processor_instance

        strategy = CodeChunkingStrategy(mock_settings)

        # Create a test document
        document = Document(
            content=sample_python_code,
            source="test.py",
            source_type=SourceType.GIT,
            content_type="py",
            title="Test Python File",
            url="file://test.py",
            metadata={"file_name": "test.py"},
        )

        chunks = strategy.chunk_document(document)

        assert len(chunks) > 0

        # Check that chunks have proper metadata
        for chunk in chunks:
            # Should have either element_type (from AST parsing) or chunking_method (from fallback)
            assert (
                "element_type" in chunk.metadata or "chunking_method" in chunk.metadata
            )
            assert "parent_document_id" in chunk.metadata
            assert chunk.metadata["parent_document_id"] == document.id

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    @patch("qdrant_loader.core.text_processing.text_processor.TextProcessor")
    def test_chunk_java_document(
        self,
        mock_text_processor,
        mock_semantic_analyzer,
        mock_settings,
        sample_java_code,
    ):
        """Test chunking a Java document."""
        # Mock the text processor
        mock_text_processor_instance = Mock()
        mock_text_processor_instance.process_text.return_value = {
            "entities": [],
            "pos_tags": [],
        }
        mock_text_processor.return_value = mock_text_processor_instance

        strategy = CodeChunkingStrategy(mock_settings)

        # Create a test document
        document = Document(
            content=sample_java_code,
            source="Calculator.java",
            source_type=SourceType.GIT,
            content_type="java",
            title="Test Java File",
            url="file://Calculator.java",
            metadata={"file_name": "Calculator.java"},
        )

        chunks = strategy.chunk_document(document)

        assert len(chunks) > 0

        # Check that chunks have proper metadata
        for chunk in chunks:
            # Should have either element_type (from AST parsing) or chunking_method (from fallback)
            assert (
                "element_type" in chunk.metadata or "chunking_method" in chunk.metadata
            )

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    def test_extract_code_metadata(self, mock_semantic_analyzer, mock_settings):
        """Test code metadata extraction."""
        strategy = CodeChunkingStrategy(mock_settings)

        # Create a mock code element
        from qdrant_loader.core.chunking.strategy.code_strategy import CodeElement

        element = CodeElement(
            name="test_function",
            element_type=CodeElementType.FUNCTION,
            content="def test_function(a, b):\n    return a + b",
            start_line=1,
            end_line=2,
            parameters=["a", "b"],
            complexity=1,
        )

        metadata = strategy._extract_code_metadata(element, "python")

        assert metadata["element_type"] == "function"
        assert metadata["name"] == "test_function"
        assert metadata["language"] == "python"
        assert metadata["parameter_count"] == 2
        assert metadata["complexity"] == 1
        assert "parameters" in metadata

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    def test_merge_small_elements(self, mock_semantic_analyzer, mock_settings):
        """Test merging small code elements."""
        strategy = CodeChunkingStrategy(mock_settings)

        from qdrant_loader.core.chunking.strategy.code_strategy import CodeElement

        # Create small elements
        elements = [
            CodeElement(
                name="import1",
                element_type=CodeElementType.IMPORT,
                content="import os",
                start_line=1,
                end_line=1,
            ),
            CodeElement(
                name="import2",
                element_type=CodeElementType.IMPORT,
                content="import sys",
                start_line=2,
                end_line=2,
            ),
            CodeElement(
                name="large_function",
                element_type=CodeElementType.FUNCTION,
                content="def large_function():\n" + "    pass\n" * 50,  # Large function
                start_line=3,
                end_line=53,
            ),
        ]

        merged = strategy._merge_small_elements(elements, min_size=50)

        # Should merge small imports but keep large function separate
        assert len(merged) == 2
        assert merged[0].element_type == CodeElementType.MODULE  # Merged imports
        assert merged[1].element_type == CodeElementType.FUNCTION  # Large function

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    @patch("qdrant_loader.core.text_processing.text_processor.TextProcessor")
    def test_fallback_chunking(
        self, mock_text_processor, mock_semantic_analyzer, mock_settings
    ):
        """Test fallback chunking when parsing fails."""
        # Mock the text processor
        mock_text_processor_instance = Mock()
        mock_text_processor_instance.process_text.return_value = {
            "entities": [],
            "pos_tags": [],
        }
        mock_text_processor.return_value = mock_text_processor_instance

        strategy = CodeChunkingStrategy(mock_settings)

        # Create a document with invalid code
        document = Document(
            content="invalid code that cannot be parsed",
            source="test.py",
            source_type=SourceType.GIT,
            content_type="py",
            title="Invalid Python File",
            url="file://test.py",
            metadata={"file_name": "test.py"},
        )

        chunks = strategy._fallback_chunking(document)

        assert len(chunks) > 0
        assert chunks[0].metadata["chunking_method"] == "fallback_text"

    @patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer")
    def test_unsupported_language(self, mock_semantic_analyzer, mock_settings):
        """Test handling of unsupported languages."""
        strategy = CodeChunkingStrategy(mock_settings)

        # Test with unsupported extension
        language = strategy._detect_language("test.xyz", "some content")
        assert language == "unknown"
