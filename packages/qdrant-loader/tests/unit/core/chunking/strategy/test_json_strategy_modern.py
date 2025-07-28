"""Tests for the modern JSON chunking strategy with modular architecture."""

import json
import pytest
from unittest.mock import Mock, patch

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.json_strategy import JSONChunkingStrategy
from qdrant_loader.core.document import Document


class TestJSONChunkingStrategyModern:
    """Test the modernized JSON chunking strategy."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 1500
        settings.global_config.chunking.chunk_overlap = 200
        settings.global_config.chunking.max_chunks_per_document = 500
        
        # JSON-specific config
        settings.global_config.chunking.strategies = Mock()
        settings.global_config.chunking.strategies.json_strategy = Mock()
        settings.global_config.chunking.strategies.json_strategy.max_json_size_for_parsing = 1000000
        settings.global_config.chunking.strategies.json_strategy.max_objects_to_process = 200
        settings.global_config.chunking.strategies.json_strategy.max_chunk_size_for_nlp = 20000
        settings.global_config.chunking.strategies.json_strategy.max_recursion_depth = 5
        settings.global_config.chunking.strategies.json_strategy.max_array_items_per_chunk = 50
        settings.global_config.chunking.strategies.json_strategy.max_object_keys_to_process = 100
        settings.global_config.chunking.strategies.json_strategy.enable_schema_inference = True
        
        # Semantic analysis config (needed to avoid spaCy errors)
        settings.global_config.semantic_analysis = Mock()
        settings.global_config.semantic_analysis.enabled = True
        settings.global_config.semantic_analysis.spacy_model = "en_core_web_sm"  # Real string value
        
        # Embedding config (needed to avoid tokenizer errors)
        settings.global_config.embedding = Mock()
        settings.global_config.embedding.tokenizer = "cl100k_base"  # Real string value
        
        return settings

    @pytest.fixture
    def strategy(self, settings):
        """Create strategy instance."""
        with patch("qdrant_loader.core.chunking.strategy.base_strategy.TextProcessor"), \
             patch("qdrant_loader.core.chunking.strategy.base_strategy.tiktoken.get_encoding"):
            return JSONChunkingStrategy(settings)

    @pytest.fixture
    def sample_json_document(self):
        """Create a sample JSON document."""
        json_data = {
            "users": [
                {"id": 1, "name": "John Doe", "email": "john@example.com"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
            ],
            "config": {
                "api_version": "v1",
                "timeout": 30,
                "features": {
                    "auth_enabled": True,
                    "debug_mode": False
                }
            },
            "metadata": {
                "created_at": "2024-01-15T10:00:00Z",
                "version": "1.2.3"
            }
        }
        
        return Document(
            content=json.dumps(json_data, indent=2),
            source="test.json",
            source_type="file",
            title="Test JSON Document",
            url="file://test.json",
            content_type="application/json",
            metadata={"file_name": "test.json"}
        )

    def test_strategy_initialization(self, strategy, settings):
        """Test that strategy initializes correctly with modular components."""
        assert strategy.document_parser is not None
        assert strategy.section_splitter is not None
        assert strategy.metadata_extractor is not None
        assert strategy.chunk_processor is not None
        assert strategy.json_config is settings.global_config.chunking.strategies.json_strategy

    def test_supports_json_document(self, strategy, sample_json_document):
        """Test that strategy correctly identifies JSON documents."""
        assert strategy.supports_document_type(sample_json_document) is True

    def test_supports_json_by_extension(self, strategy, settings):
        """Test JSON support detection by file extension."""
        doc = Document(
            content='{"test": "value"}',
            source="data.json",
            source_type="file",
            title="JSON File",
            url="file://data.json",
            content_type="application/json",
            metadata={}
        )
        assert strategy.supports_document_type(doc) is True

    def test_supports_json_by_content_type(self, strategy, settings):
        """Test JSON support detection by content type."""
        doc = Document(
            content='{"test": "value"}',
            source="data",
            source_type="file", 
            title="JSON Data",
            url="file://data",
            content_type="application/json",
            metadata={"content_type": "application/json"}
        )
        assert strategy.supports_document_type(doc) is True

    def test_chunk_json_document(self, strategy, sample_json_document):
        """Test chunking a JSON document."""
        chunks = strategy.chunk_document(sample_json_document)
        
        # Should create chunks
        assert len(chunks) > 0
        assert all(isinstance(chunk, Document) for chunk in chunks)
        
        # Check chunk metadata
        for chunk in chunks:
            assert chunk.metadata.get("content_type") == "json"
            assert chunk.metadata.get("chunking_strategy") == "json"
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata
            assert chunk.metadata.get("processed_with_json_components") is True

    def test_invalid_json_fallback(self, strategy, settings):
        """Test fallback behavior for invalid JSON."""
        invalid_doc = Document(
            content='{"invalid": json, content}',
            source="invalid.json",
            source_type="file",
            title="Invalid JSON",
            url="file://invalid.json",
            content_type="application/json",
            metadata={}
        )
        
        chunks = strategy.chunk_document(invalid_doc)
        
        # Should still create chunks using fallback
        assert len(chunks) > 0
        assert chunks[0].metadata.get("chunking_strategy") == "json_fallback"

    def test_get_strategy_name(self, strategy):
        """Test strategy name."""
        assert strategy.get_strategy_name() == "json_modular"

    def test_estimate_chunk_count(self, strategy, sample_json_document):
        """Test chunk count estimation."""
        estimate = strategy.estimate_chunk_count(sample_json_document)
        assert isinstance(estimate, int)
        assert estimate > 0

    def test_strategy_string_representation(self, strategy, settings):
        """Test string representations."""
        str_repr = str(strategy)
        assert "JSONChunkingStrategy" in str_repr
        assert "modular" in str_repr
        
        repr_str = repr(strategy)
        assert "JSONChunkingStrategy" in repr_str
        assert "modular=True" in repr_str

    def test_shutdown(self, strategy):
        """Test strategy shutdown."""
        # Should not raise any exceptions
        strategy.shutdown() 