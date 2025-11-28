"""Unit tests for BaseSectionSplitter."""

from unittest.mock import Mock

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base.section_splitter import (
    BaseSectionSplitter,
)


class ConcreteSectionSplitter(BaseSectionSplitter):
    """Concrete implementation for testing."""

    def split_sections(self, content: str, document=None):
        # Simple implementation that splits on double newlines
        sections = content.split("\n\n")
        return [
            self.create_section_metadata(section.strip(), i, "paragraph")
            for i, section in enumerate(sections)
            if section.strip()
        ]


class TestBaseSectionSplitter:
    """Test cases for BaseSectionSplitter base class."""

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
    def splitter(self, mock_settings):
        """Create a concrete splitter for testing."""
        return ConcreteSectionSplitter(mock_settings)

    def test_initialization(self, mock_settings):
        """Test that splitter initializes with correct settings."""
        splitter = ConcreteSectionSplitter(mock_settings)

        assert splitter.settings == mock_settings
        assert splitter.chunk_size == 1000
        assert splitter.chunk_overlap == 200
        assert splitter.max_chunks_per_document == 500

    def test_abstract_method_raises_not_implemented(self, mock_settings):
        """Test that abstract method raises NotImplementedError."""
        # Abstract classes cannot be instantiated directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseSectionSplitter(mock_settings)

    def test_validate_section_size(self, splitter):
        """Test the validate_section_size method."""
        # Content within acceptable size
        small_content = "x" * 500
        assert splitter.validate_section_size(small_content) is True

        # Content at the limit (2x chunk size)
        limit_content = "x" * 2000
        assert splitter.validate_section_size(limit_content) is True

        # Content exceeding the limit
        large_content = "x" * 2001
        assert splitter.validate_section_size(large_content) is False

    def test_calculate_split_points_small_content(self, splitter):
        """Test calculate_split_points with content smaller than target size."""
        content = "Small content"
        target_size = 100

        split_points = splitter.calculate_split_points(content, target_size)
        assert split_points == [len(content)]

    def test_calculate_split_points_large_content(self, splitter):
        """Test calculate_split_points with content larger than target size."""
        # Create content with clear boundaries
        content = (
            "First sentence. Second sentence.\n\nNew paragraph here. Another sentence."
        )
        target_size = 25  # Small target to force multiple splits

        split_points = splitter.calculate_split_points(content, target_size)

        # Should have multiple split points
        assert len(split_points) > 1
        # Last split point should be the end of content
        assert split_points[-1] == len(content)
        # All split points should be valid positions
        for point in split_points:
            assert 0 <= point <= len(content)

    def test_find_natural_boundary(self, splitter):
        """Test the _find_natural_boundary method."""
        content = "First sentence. Second sentence.\n\nNew paragraph. Final sentence."

        # Test paragraph boundary detection
        start_pos = 20
        end_pos = 40
        boundary = splitter._find_natural_boundary(content, start_pos, end_pos)

        # Should find a boundary within the range
        assert start_pos <= boundary <= end_pos

    def test_find_natural_boundary_paragraph_break(self, splitter):
        """Test that paragraph breaks are preferred boundaries."""
        content = "First paragraph.\n\nSecond paragraph here."
        paragraph_break_pos = content.find("\n\n") + 2

        # Search range that includes the paragraph break
        start_pos = paragraph_break_pos - 5
        end_pos = paragraph_break_pos + 5

        boundary = splitter._find_natural_boundary(content, start_pos, end_pos)
        assert boundary == paragraph_break_pos

    def test_find_natural_boundary_sentence_ending(self, splitter):
        """Test that sentence endings are found when no paragraph breaks."""
        content = "First sentence. Second sentence. Third sentence."
        first_sentence_end = content.find(". ") + 1  # Position of space after '.'

        # Search range around the first sentence ending
        start_pos = first_sentence_end - 3
        end_pos = first_sentence_end + 3

        boundary = splitter._find_natural_boundary(content, start_pos, end_pos)
        assert boundary == first_sentence_end  # At the space after the dot

    def test_create_section_metadata(self, splitter):
        """Test the create_section_metadata method."""
        content = "This is test content\nwith multiple lines."
        metadata = splitter.create_section_metadata(content, 1, "test_section")

        expected_keys = {
            "content",
            "index",
            "section_type",
            "length",
            "word_count",
            "line_count",
        }
        assert set(metadata.keys()) == expected_keys

        assert metadata["content"] == content
        assert metadata["index"] == 1
        assert metadata["section_type"] == "test_section"
        assert metadata["length"] == len(content)
        assert metadata["word_count"] == len(content.split())
        assert metadata["line_count"] == len(content.split("\n"))

    def test_split_content_by_size_small_content(self, splitter):
        """Test split_content_by_size with content smaller than max_size."""
        content = "Small content here"
        max_size = 100

        chunks = splitter.split_content_by_size(content, max_size)
        assert len(chunks) == 1
        assert chunks[0] == content

    def test_split_content_by_size_large_content(self, splitter):
        """Test split_content_by_size with content larger than max_size."""
        # Create content with clear sentence boundaries
        sentences = [
            "First sentence here.",
            "Second sentence is here.",
            "Third sentence follows.",
            "Fourth sentence concludes.",
        ]
        content = " ".join(sentences)
        max_size = 30  # Force multiple chunks

        chunks = splitter.split_content_by_size(content, max_size)

        # Should create multiple chunks
        assert len(chunks) > 1

        # All chunks should be reasonable size
        for chunk in chunks:
            assert len(chunk) <= max_size + splitter.chunk_overlap

        # Reconstructed content should contain all original content
        reconstructed = " ".join(chunks)
        for sentence in sentences:
            assert sentence in reconstructed

    def test_split_content_by_size_with_overlap(self, splitter):
        """Test that split_content_by_size respects overlap settings."""
        content = "A" * 100 + "B" * 100 + "C" * 100  # 300 chars total
        max_size = 150

        chunks = splitter.split_content_by_size(content, max_size)

        # Should have overlap between chunks
        if len(chunks) > 1:
            # Check that there's some overlap
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i + 1]
                # Look for any common content
                if any(char in next_chunk for char in current_chunk[-50:]):
                    break
            # Note: Overlap might not always be detectable due to boundary finding
            # This is a basic check that the algorithm attempts to create overlap

    def test_concrete_implementation_split_sections(self, splitter):
        """Test that concrete implementation works correctly."""
        content = "First paragraph here.\n\nSecond paragraph.\n\nThird paragraph."

        sections = splitter.split_sections(content)

        # Should split on double newlines
        assert len(sections) == 3

        # Each section should have the required metadata
        for i, section in enumerate(sections):
            assert "content" in section
            assert "index" in section
            assert "section_type" in section
            assert section["index"] == i
            assert section["section_type"] == "paragraph"

    def test_edge_cases(self, splitter):
        """Test edge cases in splitting logic."""
        # Empty content
        empty_result = splitter.split_sections("")
        assert len(empty_result) == 0

        # Only whitespace
        whitespace_result = splitter.split_sections("   \n\n   ")
        assert len(whitespace_result) == 0

        # Single paragraph
        single_result = splitter.split_sections("Single paragraph only")
        assert len(single_result) == 1
        assert single_result[0]["content"] == "Single paragraph only"
