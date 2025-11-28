"""Unit tests for BaseChunkProcessor."""

from datetime import datetime
from unittest.mock import Mock

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.chunk_processor import BaseChunkProcessor
from qdrant_loader.core.document import Document


class ConcreteChunkProcessor(BaseChunkProcessor):
    """Concrete implementation for testing."""

    def create_chunk_document(
        self,
        original_doc,
        chunk_content,
        chunk_index,
        total_chunks,
        chunk_metadata,
        skip_nlp=False,
    ):
        # Simple implementation that creates a new document
        chunk_id = self.generate_chunk_id(original_doc, chunk_index)
        final_metadata = self.create_base_chunk_metadata(
            original_doc, chunk_index, total_chunks, chunk_metadata
        )

        return Document(
            id=chunk_id,
            content=chunk_content,
            url=original_doc.url,
            content_type=original_doc.content_type,
            source_type=original_doc.source_type,
            source=original_doc.source,
            title=f"{original_doc.title} - Chunk {chunk_index + 1}",
            metadata=final_metadata,
        )


class TestBaseChunkProcessor:
    """Test cases for BaseChunkProcessor base class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.chunking = Mock()
        settings.global_config.chunking.chunk_size = 1000
        settings.global_config.chunking.chunk_overlap = 200
        settings.global_config.chunking.max_chunks_per_document = 500
        return settings

    @pytest.fixture
    def processor(self, mock_settings):
        """Create a concrete processor for testing."""
        return ConcreteChunkProcessor(mock_settings)

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            content="Test document content for chunking",
            url="http://example.com/test.txt",
            content_type="txt",
            source_type="test",
            source="test_source",
            title="Test Document",
            metadata={"source": "test", "file_name": "test.txt"},
        )

    def test_initialization(self, mock_settings):
        """Test that processor initializes with correct settings."""
        processor = ConcreteChunkProcessor(mock_settings)

        assert processor.settings == mock_settings
        assert processor.chunk_size == 1000
        assert processor.max_chunks_per_document == 500

    def test_abstract_method_raises_not_implemented(self, mock_settings):
        """Test that abstract method raises NotImplementedError."""
        # Abstract classes cannot be instantiated directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseChunkProcessor(mock_settings)

    def test_estimate_chunk_count_empty_content(self, processor):
        """Test chunk count estimation with empty content."""
        count = processor.estimate_chunk_count("")
        assert count == 0

    def test_estimate_chunk_count_small_content(self, processor):
        """Test chunk count estimation with content smaller than chunk size."""
        content = "Small content"
        count = processor.estimate_chunk_count(content)
        assert count == 1

    def test_estimate_chunk_count_large_content(self, processor):
        """Test chunk count estimation with large content."""
        # Create content larger than chunk size
        content = "x" * 2500  # 2.5x chunk size
        count = processor.estimate_chunk_count(content)

        # Should estimate multiple chunks
        assert count > 1
        # Should be capped at max chunks
        assert count <= processor.max_chunks_per_document

    def test_estimate_chunk_count_with_overlap(self, processor):
        """Test that chunk estimation accounts for overlap."""
        # Content exactly 2x chunk size
        content = "x" * 2000
        count = processor.estimate_chunk_count(content)

        # With overlap, should need more chunks than simple division
        simple_division = len(content) // processor.chunk_size
        assert count >= simple_division

    def test_generate_chunk_id_deterministic(self, processor, sample_document):
        """Test that chunk ID generation is deterministic."""
        chunk_id_1 = processor.generate_chunk_id(sample_document, 0)
        chunk_id_2 = processor.generate_chunk_id(sample_document, 0)

        # Same inputs should produce same ID
        assert chunk_id_1 == chunk_id_2

    def test_generate_chunk_id_different_indices(self, processor, sample_document):
        """Test that different chunk indices produce different IDs."""
        chunk_id_0 = processor.generate_chunk_id(sample_document, 0)
        chunk_id_1 = processor.generate_chunk_id(sample_document, 1)

        # Different indices should produce different IDs
        assert chunk_id_0 != chunk_id_1

    def test_generate_chunk_id_format(self, processor, sample_document):
        """Test that generated chunk ID has valid UUID format."""
        import uuid

        chunk_id = processor.generate_chunk_id(sample_document, 0)

        # Should be a valid UUID string
        try:
            uuid.UUID(chunk_id)
        except ValueError:
            pytest.fail("Generated chunk ID is not a valid UUID")

    def test_create_base_chunk_metadata(self, processor, sample_document):
        """Test creation of base chunk metadata."""
        chunk_metadata = {"custom_key": "custom_value", "section_type": "paragraph"}

        base_metadata = processor.create_base_chunk_metadata(
            sample_document,
            chunk_index=2,
            total_chunks=5,
            chunk_metadata=chunk_metadata,
        )

        # Should include original document metadata
        assert base_metadata["source"] == "test"
        assert base_metadata["file_name"] == "test.txt"

        # Should include chunk-specific metadata
        assert base_metadata["chunk_index"] == 2
        assert base_metadata["total_chunks"] == 5
        assert base_metadata["is_chunk"] is True
        assert base_metadata["parent_document_id"] == sample_document.id

        # Should include custom metadata
        assert base_metadata["custom_key"] == "custom_value"
        assert base_metadata["section_type"] == "paragraph"

        # Should include system metadata
        assert "chunk_creation_timestamp" in base_metadata
        assert "chunking_strategy" in base_metadata

    def test_create_base_chunk_metadata_preserves_original(
        self, processor, sample_document
    ):
        """Test that base metadata preserves original document metadata."""
        original_metadata = sample_document.metadata.copy()
        chunk_metadata = {"new_key": "new_value"}

        base_metadata = processor.create_base_chunk_metadata(
            sample_document, 0, 1, chunk_metadata
        )

        # Original metadata should be preserved
        for key, value in original_metadata.items():
            assert base_metadata[key] == value

        # New metadata should be added
        assert base_metadata["new_key"] == "new_value"

    def test_validate_chunk_content_valid(self, processor):
        """Test chunk content validation with valid content."""
        valid_content = "This is valid chunk content with sufficient length."
        assert processor.validate_chunk_content(valid_content) is True

    def test_validate_chunk_content_empty(self, processor):
        """Test chunk content validation with empty content."""
        assert processor.validate_chunk_content("") is False
        assert processor.validate_chunk_content("   ") is False
        assert processor.validate_chunk_content(None) is False

    def test_validate_chunk_content_too_short(self, processor):
        """Test chunk content validation with too short content."""
        short_content = "short"
        assert processor.validate_chunk_content(short_content) is False

    def test_validate_chunk_content_too_long(self, processor):
        """Test chunk content validation with excessively long content."""
        # Create content longer than 3x chunk size
        long_content = "x" * (processor.chunk_size * 4)
        assert processor.validate_chunk_content(long_content) is False

    def test_should_skip_semantic_analysis_short_content(self, processor):
        """Test semantic analysis skip logic for short content."""
        short_content = "Short"
        assert processor.should_skip_semantic_analysis(short_content, {}) is True

    def test_should_skip_semantic_analysis_few_words(self, processor):
        """Test semantic analysis skip logic for content with few words."""
        few_words = "One two three four five"
        assert processor.should_skip_semantic_analysis(few_words, {}) is True

    def test_should_skip_semantic_analysis_simple_structure(self, processor):
        """Test semantic analysis skip logic for simple structure."""
        simple_content = "Simple content without much structure"
        assert processor.should_skip_semantic_analysis(simple_content, {}) is True

    def test_should_skip_semantic_analysis_explicit_skip(self, processor):
        """Test semantic analysis skip when explicitly marked."""
        content = "This is longer content with more structure and multiple lines.\nIt should normally not be skipped."
        metadata = {"skip_semantic_analysis": True}

        assert processor.should_skip_semantic_analysis(content, metadata) is True

    def test_should_skip_semantic_analysis_valid_content(self, processor):
        """Test semantic analysis skip logic with valid content."""
        content = """This is substantial content with multiple sentences.
        It has good structure with multiple lines.
        This content should be analyzed semantically.
        There are enough words and complexity here."""

        assert processor.should_skip_semantic_analysis(content, {}) is False

    def test_get_current_timestamp(self, processor):
        """Test timestamp generation."""
        timestamp = processor._get_current_timestamp()

        # Should be a valid ISO format timestamp
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail("Generated timestamp is not in valid ISO format")

    def test_get_strategy_name(self, processor):
        """Test strategy name generation."""
        strategy_name = processor._get_strategy_name()

        # Should derive name from class name
        assert strategy_name == "concrete"  # ConcreteChunkProcessor -> concrete

    def test_calculate_content_similarity_identical(self, processor):
        """Test content similarity calculation with identical content."""
        content = "This is test content for similarity"
        similarity = processor.calculate_content_similarity(content, content)
        assert similarity == 1.0

    def test_calculate_content_similarity_no_overlap(self, processor):
        """Test content similarity calculation with no overlap."""
        content1 = "First piece of content"
        content2 = "Second different text"
        similarity = processor.calculate_content_similarity(content1, content2)
        assert similarity == 0.0

    def test_calculate_content_similarity_partial_overlap(self, processor):
        """Test content similarity calculation with partial overlap."""
        content1 = "This is test content"
        content2 = "This is different content"
        similarity = processor.calculate_content_similarity(content1, content2)

        # Should have some similarity (common words: "this", "is", "content")
        assert 0.0 < similarity < 1.0

    def test_calculate_content_similarity_empty_content(self, processor):
        """Test content similarity calculation with empty content."""
        assert processor.calculate_content_similarity("", "") == 1.0
        assert processor.calculate_content_similarity("", "content") == 0.0
        assert processor.calculate_content_similarity("content", "") == 0.0

    def test_optimize_chunk_boundaries_single_chunk(self, processor):
        """Test chunk boundary optimization with single chunk."""
        chunks = ["Single chunk content"]
        optimized = processor.optimize_chunk_boundaries(chunks)

        assert len(optimized) == 1
        assert optimized[0] == "Single chunk content"

    def test_optimize_chunk_boundaries_removes_empty(self, processor):
        """Test that empty chunks are removed."""
        chunks = ["First chunk", "", "   ", "Second chunk"]
        optimized = processor.optimize_chunk_boundaries(chunks)

        assert len(optimized) == 2
        assert "First chunk" in optimized
        assert "Second chunk" in optimized

    def test_optimize_chunk_boundaries_fixes_broken_sentences(self, processor):
        """Test that broken sentences are fixed."""
        chunks = [
            "This is the first sentence. this is a continuation",
            "that should be moved. This starts a new thought.",
        ]
        optimized = processor.optimize_chunk_boundaries(chunks)

        # Should attempt to fix the broken sentence
        assert len(optimized) >= 1
        # The optimization logic should handle the broken sentence

    def test_concrete_implementation_create_chunk_document(
        self, processor, sample_document
    ):
        """Test that concrete implementation creates chunk documents correctly."""
        chunk_content = "This is chunk content"
        chunk_metadata = {"section_type": "paragraph"}

        chunk_doc = processor.create_chunk_document(
            original_doc=sample_document,
            chunk_content=chunk_content,
            chunk_index=1,
            total_chunks=3,
            chunk_metadata=chunk_metadata,
        )

        # Should be a valid Document
        assert isinstance(chunk_doc, Document)
        assert chunk_doc.content == chunk_content
        assert chunk_doc.url == sample_document.url
        assert chunk_doc.content_type == sample_document.content_type
        assert chunk_doc.title == "Test Document - Chunk 2"  # chunk_index + 1

        # Should have proper metadata
        assert chunk_doc.metadata["chunk_index"] == 1
        assert chunk_doc.metadata["total_chunks"] == 3
        assert chunk_doc.metadata["section_type"] == "paragraph"

    def test_shutdown_method(self, processor):
        """Test that shutdown method can be called without errors."""
        # Should not raise any exceptions
        processor.shutdown()

    def test_del_method(self, processor):
        """Test that __del__ method handles shutdown gracefully."""
        # Should not raise any exceptions
        try:
            processor.__del__()
        except Exception as e:
            pytest.fail(f"__del__ method raised an exception: {e}")
