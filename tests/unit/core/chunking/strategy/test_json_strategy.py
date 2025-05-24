"""Unit tests for JSON chunking strategy."""

import pytest
from unittest.mock import Mock

from qdrant_loader.core.chunking.strategy.json_strategy import JSONChunkingStrategy, JSONElementType
from qdrant_loader.core.document import Document
from qdrant_loader.config import Settings
from qdrant_loader.config.types import SourceType


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

    global_config.chunking = chunking_config
    global_config.semantic_analysis = semantic_analysis_config
    settings.global_config = global_config

    return settings


@pytest.fixture
def json_strategy(mock_settings):
    """Create a JSON chunking strategy instance."""
    return JSONChunkingStrategy(mock_settings)


@pytest.fixture
def sample_json_document():
    """Create a sample JSON document for testing."""
    json_content = """
    {
        "users": [
            {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "profile": {
                    "age": 30,
                    "city": "New York"
                }
            },
            {
                "id": 2,
                "name": "Jane Smith",
                "email": "jane@example.com",
                "profile": {
                    "age": 25,
                    "city": "Los Angeles"
                }
            }
        ],
        "metadata": {
            "version": "1.0",
            "created": "2023-01-01",
            "total_users": 2
        }
    }
    """

    return Document(
        content=json_content.strip(),
        metadata={"file_name": "users.json"},
        source="test_source",
        source_type=SourceType.LOCALFILE,
        url="file://test_source",
        title="Test JSON Document",
        content_type="json",
    )


class TestJSONChunkingStrategy:
    """Test cases for JSON chunking strategy."""

    def test_initialization(self, json_strategy):
        """Test that the strategy initializes correctly."""
        assert json_strategy is not None
        assert json_strategy.min_chunk_size == 200
        assert json_strategy.max_array_items_per_chunk == 50

    def test_parse_json_structure(self, json_strategy, sample_json_document):
        """Test JSON structure parsing."""
        root_element = json_strategy._parse_json_structure(sample_json_document.content)

        assert root_element is not None
        assert root_element.name == "root"
        assert root_element.element_type == JSONElementType.ROOT
        assert len(root_element.children) == 2  # users and metadata

    def test_chunk_document(self, json_strategy, sample_json_document):
        """Test document chunking."""
        chunks = json_strategy.chunk_document(sample_json_document)

        assert len(chunks) > 0
        assert all(isinstance(chunk, Document) for chunk in chunks)

        # Check that chunks have proper metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert chunk.metadata["parent_document_id"] == sample_json_document.id
            assert "element_type" in chunk.metadata
            assert "chunking_method" in chunk.metadata

    def test_invalid_json(self, json_strategy):
        """Test handling of invalid JSON."""
        invalid_json_doc = Document(
            content='{"invalid": json content}',
            metadata={"file_name": "invalid.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Invalid JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(invalid_json_doc)

        # Should fallback to text chunking
        assert len(chunks) > 0
        assert chunks[0].metadata.get("chunking_method") == "fallback_text"

    def test_large_json_fallback(self, json_strategy):
        """Test fallback for very large JSON files."""
        # Create a large JSON content
        large_content = '{"data": [' + ",".join([f'{{"id": {i}}}' for i in range(10000)]) + "]}"

        large_json_doc = Document(
            content=large_content,
            metadata={"file_name": "large.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Large JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(large_json_doc)

        # Should use simple chunking for large files
        assert len(chunks) > 0

    def test_empty_json(self, json_strategy):
        """Test handling of empty JSON."""
        empty_json_doc = Document(
            content="{}",
            metadata={"file_name": "empty.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Empty JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(empty_json_doc)

        assert len(chunks) >= 1
        assert chunks[0].content == "{}"

    def test_array_json(self, json_strategy):
        """Test handling of JSON arrays."""
        array_json_doc = Document(
            content='[{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]',
            metadata={"file_name": "array.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Array JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(array_json_doc)

        assert len(chunks) >= 1
        # Should have array-related metadata (either array or array_item)
        element_types = [chunk.metadata.get("element_type", "") for chunk in chunks]
        assert any(
            "array" in element_type.lower() or "object" in element_type.lower()
            for element_type in element_types
        )
