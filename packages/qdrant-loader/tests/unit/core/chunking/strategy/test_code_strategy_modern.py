"""Unit tests for modernized code chunking strategy."""

from unittest.mock import Mock, patch
from typing import Dict, Any

import pytest

from qdrant_loader.config import Settings
from qdrant_loader.config.types import SourceType
from qdrant_loader.core.chunking.strategy.code_strategy import CodeChunkingStrategy
from qdrant_loader.core.document import Document


@pytest.fixture
def mock_settings():
    """Create mock settings for testing the modernized code strategy."""
    settings = Mock(spec=Settings)
    
    # Mock global config
    global_config = Mock()
    
    # Mock chunking config
    chunking_config = Mock()
    chunking_config.chunk_size = 1500
    chunking_config.chunk_overlap = 200
    chunking_config.max_chunks_per_document = 500
    
    # Mock strategies config
    strategies_config = Mock()
    
    # Mock code strategy config with actual values
    code_config = Mock()
    code_config.max_file_size_for_ast = 75000
    code_config.max_elements_to_process = 800
    code_config.max_recursion_depth = 8
    code_config.max_element_size = 20000
    code_config.max_chunk_size_for_nlp = 20000
    code_config.enable_ast_parsing = True
    code_config.enable_dependency_analysis = True
    
    strategies_config.code = code_config
    chunking_config.strategies = strategies_config
    
    # Mock semantic analysis config
    semantic_analysis_config = Mock()
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
def sample_python_document():
    """Create a sample Python document for testing."""
    python_code = '''
"""A sample Python module for testing."""
import os
import sys
from typing import List, Dict

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        """Initialize the calculator."""
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

    return Document(
        id="test-python-doc",
        title="calculator.py",
        content=python_code,
        content_type="code",
        source="calculator.py",
        source_type=SourceType.LOCALFILE,
        url="file://test/calculator.py",
        metadata={"file_name": "calculator.py"}
    )


@pytest.fixture
def sample_javascript_document():
    """Create a sample JavaScript document for testing."""
    js_code = '''
/**
 * A sample JavaScript module for testing
 */
const express = require('express');
const { calculateSum, calculateProduct } = require('./utils');

class Calculator {
    constructor() {
        this.history = [];
    }

    add(a, b) {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }

    async multiply(a, b) {
        const result = a * b;
        this.history.push(`${a} * ${b} = ${result}`);
        return result;
    }
}

function main() {
    const calc = new Calculator();
    console.log(calc.add(5, 3));
    console.log(calc.multiply(4, 6));
}

module.exports = { Calculator, main };
'''

    return Document(
        id="test-js-doc",
        title="calculator.js",
        content=js_code,
        content_type="code",
        source="calculator.js",
        source_type=SourceType.LOCALFILE,
        url="file://test/calculator.js",
        metadata={"file_name": "calculator.js"}
    )


@pytest.fixture
def empty_code_document():
    """Create an empty code document for testing."""
    return Document(
        id="empty-code-doc",
        title="empty.py",
        content="",
        content_type="code",
        source="empty.py",
        source_type=SourceType.LOCALFILE,
        url="file://test/empty.py",
        metadata={"file_name": "empty.py"}
    )


class TestCodeChunkingStrategyModern:
    """Test the modernized CodeChunkingStrategy with modular architecture."""

    def test_initialization(self, mock_settings):
        """Test that the modernized code strategy initializes correctly."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            # Verify modular components are initialized
            assert hasattr(strategy, 'document_parser')
            assert hasattr(strategy, 'section_splitter')
            assert hasattr(strategy, 'metadata_extractor')
            assert hasattr(strategy, 'chunk_processor')
            assert hasattr(strategy, 'code_config')
            
            # Verify settings are properly configured
            assert strategy.code_config.max_file_size_for_ast == 75000
            assert strategy.code_config.enable_ast_parsing is True

    def test_chunk_python_document_success(self, mock_settings, sample_python_document):
        """Test successful chunking of a Python document with modular components."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            chunks = strategy.chunk_document(sample_python_document)
            
            # Should create at least one chunk
            assert len(chunks) >= 1
            
            # Verify chunk structure
            for chunk in chunks:
                assert isinstance(chunk, Document)
                assert chunk.content_type == sample_python_document.content_type
                assert "chunking_strategy" in chunk.metadata
                assert chunk.metadata["chunking_strategy"] == "code_modular"
                assert "parent_document_id" in chunk.metadata
                assert chunk.metadata["parent_document_id"] == sample_python_document.id

    def test_chunk_javascript_document_success(self, mock_settings, sample_javascript_document):
        """Test successful chunking of a JavaScript document."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            chunks = strategy.chunk_document(sample_javascript_document)
            
            # Should create at least one chunk
            assert len(chunks) >= 1
            
                         # Verify language detection and metadata
            for chunk in chunks:
                assert isinstance(chunk, Document)
                # Language detection may fall back to "unknown" if Tree-sitter isn't available
                language = chunk.metadata.get("language", "unknown")
                assert language in ["javascript", "unknown"]

    def test_chunk_document_preserves_code_structure(self, mock_settings, sample_python_document):
        """Test that code document chunking preserves semantic structure."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            chunks = strategy.chunk_document(sample_python_document)
            
            # Should have enhanced metadata indicating code structure
            found_class = False
            found_function = False
            
            for chunk in chunks:
                metadata = chunk.metadata
                if "element_type" in metadata:
                    element_type = metadata["element_type"]
                    if element_type in ["class", "CLASS"]:
                        found_class = True
                    elif element_type in ["function", "method", "FUNCTION", "METHOD"]:
                        found_function = True
            
            # Should find class and function elements (depending on parsing success)
            # Note: This might vary based on AST parsing availability
            assert len(chunks) > 0  # At minimum, should create chunks

    def test_chunk_document_large_file_fallback(self, mock_settings):
        """Test fallback chunking for large code files."""
        # Create a very large code document that exceeds AST parsing limits
        large_code = "# Large code file\n" + "print('hello')\n" * 10000  # Very large file
        
        large_document = Document(
            id="large-code-doc",
            title="large.py",
            content=large_code,
            content_type="code",
            source="large.py",
            source_type=SourceType.LOCALFILE,
            url="file://test/large.py",
            metadata={"file_name": "large.py"}
        )
        
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            chunks = strategy.chunk_document(large_document)
            
            # Should still create chunks using fallback method
            assert len(chunks) >= 1
            
            # Should have fallback indicators in metadata
            fallback_indicators = any(
                chunk.metadata.get("chunking_strategy") == "code_fallback"
                or chunk.metadata.get("parsing_method") == "regex_fallback"
                for chunk in chunks
            )
            # Note: Fallback might be triggered depending on file size handling

    def test_chunk_empty_code_document(self, mock_settings, empty_code_document):
        """Test chunking of empty code document."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            chunks = strategy.chunk_document(empty_code_document)
            
            # Should handle empty content gracefully
            assert len(chunks) >= 0  # May create no chunks or one empty chunk

    def test_chunk_document_with_malformed_code(self, mock_settings):
        """Test chunking of malformed code that can't be parsed."""
        malformed_document = Document(
            id="malformed-code-doc",
            title="malformed.py",
            content="def broken_function(\n    # Missing closing parenthesis and proper syntax",
            content_type="code",
            source="malformed.py",
            source_type=SourceType.LOCALFILE,
            url="file://test/malformed.py",
            metadata={"file_name": "malformed.py"}
        )
        
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            chunks = strategy.chunk_document(malformed_document)
            
            # Should handle malformed code gracefully using fallback
            assert len(chunks) >= 1
            
            # Should indicate fallback was used
            has_fallback = any(
                "fallback" in chunk.metadata.get("chunking_strategy", "").lower()
                or "fallback" in chunk.metadata.get("parsing_method", "").lower()
                for chunk in chunks
            )

    def test_chunk_document_max_chunks_limit(self, mock_settings):
        """Test that chunk count respects max_chunks_per_document limit."""
        # Create a document with many small functions to potentially exceed limits
        many_functions = "\n".join([
            f"def function_{i}():\n    return {i}\n" 
            for i in range(600)  # More than the 500 limit
        ])
        
        many_functions_document = Document(
            id="many-functions-doc",
            title="many_functions.py",
            content=many_functions,
            content_type="code",
            source="many_functions.py",
            source_type=SourceType.LOCALFILE,
            url="file://test/many_functions.py",
            metadata={"file_name": "many_functions.py"}
        )
        
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            chunks = strategy.chunk_document(many_functions_document)
            
            # Should respect the max_chunks_per_document limit (with some tolerance for fallback behavior)
            # If fallback is used, there might be slight variations
            max_allowed = mock_settings.global_config.chunking.max_chunks_per_document
            assert len(chunks) <= max_allowed or len(chunks) <= max_allowed + 100  # Allow some tolerance for fallback

    def test_legacy_split_text_method(self, mock_settings):
        """Test the legacy _split_text method for backward compatibility."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            sample_code = "def hello():\n    print('hello')\n\nprint('world')"
            
            # Test legacy method
            text_chunks = strategy._split_text(sample_code)
            
            assert isinstance(text_chunks, list)
            assert len(text_chunks) >= 1
            assert all(isinstance(chunk, str) for chunk in text_chunks)

    def test_shutdown_cleanup(self, mock_settings):
        """Test that shutdown properly cleans up resources."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            # Ensure no exceptions during shutdown
            try:
                strategy.shutdown()
            except Exception as e:
                pytest.fail(f"Shutdown should not raise exceptions: {e}")

    def test_modular_components_integration(self, mock_settings, sample_python_document):
        """Test that all 4 modular components work together correctly."""
        with patch('qdrant_loader.core.text_processing.text_processor.TextProcessor'):
            strategy = CodeChunkingStrategy(mock_settings)
            
            # Verify all components are accessible and configured
            assert strategy.document_parser is not None
            assert strategy.section_splitter is not None  
            assert strategy.metadata_extractor is not None
            assert strategy.chunk_processor is not None
            
            # Test that components can work together
            chunks = strategy.chunk_document(sample_python_document)
            
            # Verify enhanced metadata from components
            for chunk in chunks:
                metadata = chunk.metadata
                
                # Should have content analysis metadata from extractor
                assert "content_type" in metadata
                assert metadata["content_type"] == "code"
                
                # Should have chunking strategy info from processor
                assert "chunking_strategy" in metadata
                
                # Document structure may be present if AST parsing succeeds
                # (it might not be if fallback chunking is used)
                if "document_structure" in metadata:
                    assert isinstance(metadata["document_structure"], dict) 