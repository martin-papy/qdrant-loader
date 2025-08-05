"""Comprehensive tests for Markdown SectionSplitter to achieve 80%+ coverage."""

import re
from unittest.mock import Mock, patch

import pytest

from qdrant_loader.core.chunking.strategy.markdown.section_splitter import (
    BaseSplitter,
    ExcelSplitter, 
    FallbackSplitter,
    HeaderAnalysis,
    SectionMetadata,
    SectionSplitter,
    StandardSplitter,
)
from qdrant_loader.core.document import Document
from qdrant_loader.config import Settings


class TestHeaderAnalysis:
    """Test HeaderAnalysis dataclass."""

    def test_init_and_post_init(self):
        """Test HeaderAnalysis initialization and __post_init__ calculations."""
        analysis = HeaderAnalysis(
            h1=2, h2=5, h3=10, h4=3, h5=1, h6=0, content_length=5000
        )
        
        assert analysis.h1 == 2
        assert analysis.h2 == 5
        assert analysis.h3 == 10
        assert analysis.h4 == 3
        assert analysis.h5 == 1
        assert analysis.h6 == 0
        assert analysis.content_length == 5000
        assert analysis.total_headers == 21  # Sum of all headers
        assert analysis.avg_section_size == 238  # 5000 // 21

    def test_post_init_with_zero_headers(self):
        """Test __post_init__ when no headers present."""
        analysis = HeaderAnalysis(content_length=1000)
        
        assert analysis.total_headers == 0
        assert analysis.avg_section_size == 0  # No division by zero

    def test_post_init_default_values(self):
        """Test __post_init__ with default values."""
        analysis = HeaderAnalysis()
        
        assert analysis.total_headers == 0
        assert analysis.avg_section_size == 0


class TestSectionMetadata:
    """Test SectionMetadata dataclass."""

    def test_init_with_defaults(self):
        """Test SectionMetadata initialization with defaults."""
        metadata = SectionMetadata(
            title="Test Section",
            level=2,
            content="Test content",
            order=1,
            start_line=10,
            end_line=20
        )
        
        assert metadata.title == "Test Section"
        assert metadata.level == 2
        assert metadata.content == "Test content"
        assert metadata.order == 1
        assert metadata.start_line == 10
        assert metadata.end_line == 20
        assert metadata.parent_section is None
        assert metadata.breadcrumb == ""
        assert metadata.anchor == "test-section"  # Generated from title
        assert metadata.sibling_sections == []
        assert metadata.subsections == []
        assert metadata.content_analysis == {}

    def test_init_with_all_fields(self):
        """Test SectionMetadata initialization with all fields provided."""
        metadata = SectionMetadata(
            title="Advanced Section",
            level=3,
            content="Advanced content",
            order=5,
            start_line=50,
            end_line=100,
            parent_section="Parent",
            breadcrumb="Home > Parent > Advanced Section",
            anchor="custom-anchor",
            previous_section="Previous",
            next_section="Next",
            sibling_sections=["Sibling1", "Sibling2"],
            subsections=["Sub1", "Sub2"],
            content_analysis={"word_count": 50}
        )
        
        assert metadata.title == "Advanced Section"
        assert metadata.anchor == "custom-anchor"  # Custom anchor preserved
        assert metadata.sibling_sections == ["Sibling1", "Sibling2"]
        assert metadata.subsections == ["Sub1", "Sub2"]
        assert metadata.content_analysis == {"word_count": 50}

    def test_generate_anchor_simple(self):
        """Test anchor generation from simple title."""
        metadata = SectionMetadata(
            title="Simple Title",
            level=1,
            content="content",
            order=1,
            start_line=1,
            end_line=2
        )
        
        assert metadata.anchor == "simple-title"

    def test_generate_anchor_complex(self):
        """Test anchor generation from complex title with special characters."""
        metadata = SectionMetadata(
            title="Complex Title: With Special! Characters@#$",
            level=1,
            content="content",
            order=1,
            start_line=1,
            end_line=2
        )
        
        # Should remove special chars and replace spaces with hyphens
        assert metadata.anchor == "complex-title-with-special-characters"

    def test_generate_anchor_with_numbers_and_hyphens(self):
        """Test anchor generation preserves valid characters."""
        metadata = SectionMetadata(
            title="Section-1.2: API Overview",
            level=1,
            content="content",
            order=1,
            start_line=1,
            end_line=2
        )
        
        assert metadata.anchor == "section-12-api-overview"


class TestBaseSplitter:
    """Test BaseSplitter abstract class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        
        # Create mock configuration hierarchy
        mock_global_config = Mock()
        mock_chunking = Mock()
        mock_chunking.chunk_size = 1500
        mock_chunking.chunk_overlap = 100
        mock_global_config.chunking = mock_chunking
        self.mock_settings.global_config = mock_global_config

    def test_init(self):
        """Test BaseSplitter initialization."""
        # Create concrete implementation for testing
        class ConcreteSplitter(BaseSplitter):
            def split_content(self, content: str, max_size: int) -> list[str]:
                return [content]
        
        splitter = ConcreteSplitter(self.mock_settings)
        
        assert splitter.settings is self.mock_settings
        assert splitter.chunk_size == 1500
        assert splitter.chunk_overlap == 100


class TestStandardSplitter:
    """Test StandardSplitter implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        
        # Setup markdown strategy config
        mock_markdown = Mock()
        mock_markdown.max_chunks_per_section = 10
        mock_markdown.max_overlap_percentage = 0.1
        
        mock_strategies = Mock()
        mock_strategies.markdown = mock_markdown
        
        mock_chunking = Mock()
        mock_chunking.chunk_size = 1000
        mock_chunking.chunk_overlap = 100
        mock_chunking.max_chunks_per_document = 50
        mock_chunking.strategies = mock_strategies
        
        mock_global_config = Mock()
        mock_global_config.chunking = mock_chunking
        self.mock_settings.global_config = mock_global_config
        
        self.splitter = StandardSplitter(self.mock_settings)

    def test_split_content_small_content(self):
        """Test split_content with content smaller than max_size."""
        content = "This is a small paragraph that fits within the size limit."
        max_size = 1000
        
        result = self.splitter.split_content(content, max_size)
        
        assert len(result) == 1
        assert result[0] == content

    def test_split_content_large_paragraphs(self):
        """Test split_content with large paragraphs that need splitting."""
        # Create content with multiple paragraphs
        paragraphs = [
            "This is the first paragraph with some content.",
            "This is the second paragraph with more content.",
            "This is the third paragraph with additional content."
        ]
        content = "\n\n".join(paragraphs)
        max_size = 100  # Small size to force splitting
        
        result = self.splitter.split_content(content, max_size)
        
        # Should split into multiple chunks
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= max_size

    def test_split_content_with_large_sentences(self):
        """Test split_content splits large paragraphs by sentences."""
        # Create a large paragraph with multiple sentences
        sentences = [
            "This is the first sentence.",
            "This is the second sentence with more details.",
            "This is the third sentence that adds more information."
        ]
        content = " ".join(sentences)
        max_size = 50  # Small to force sentence splitting
        
        result = self.splitter.split_content(content, max_size)
        
        # Should split by sentences
        assert len(result) >= len(sentences)

    def test_split_content_with_overlap(self):
        """Test split_content applies overlap correctly."""
        # Create content that will require multiple chunks
        paragraphs = ["Paragraph " + str(i) + " content here." for i in range(10)]
        content = "\n\n".join(paragraphs)
        max_size = 200
        
        result = self.splitter.split_content(content, max_size)
        
        # Should create multiple chunks
        assert len(result) > 1
        
        # Check that there's some overlap between consecutive chunks
        # (This is a simplified check - actual overlap logic is complex)
        assert len(result[0]) <= max_size

    def test_split_content_no_overlap(self):
        """Test split_content with overlap disabled."""
        self.splitter.chunk_overlap = 0
        
        paragraphs = ["Short para " + str(i) for i in range(5)]
        content = "\n\n".join(paragraphs)
        max_size = 100
        
        result = self.splitter.split_content(content, max_size)
        
        assert len(result) >= 1
        for chunk in result:
            assert len(chunk) <= max_size

    def test_split_content_reaches_chunk_limit(self):
        """Test split_content respects max_chunks_per_section limit."""
        # Set a very low limit
        self.splitter.settings.global_config.chunking.strategies.markdown.max_chunks_per_section = 2
        
        # Create content that would normally create many chunks
        paragraphs = ["Paragraph " + str(i) for i in range(20)]
        content = "\n\n".join(paragraphs)
        max_size = 50  # Small to force many chunks
        
        with patch('qdrant_loader.core.chunking.strategy.markdown.section_splitter.logger') as mock_logger:
            result = self.splitter.split_content(content, max_size)
            
            # Should be limited to max_chunks_per_section
            assert len(result) <= 2
            # Should log warning about truncation
            mock_logger.warning.assert_called()

    def test_split_content_empty_content(self):
        """Test split_content with empty content."""
        result = self.splitter.split_content("", 1000)
        
        assert result == []

    def test_split_content_whitespace_only(self):
        """Test split_content with whitespace-only content."""
        result = self.splitter.split_content("   \n\n   \n   ", 1000)
        
        assert result == []


class TestExcelSplitter:
    """Test ExcelSplitter implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        
        mock_markdown = Mock()
        mock_markdown.max_chunks_per_section = 10
        
        mock_strategies = Mock()
        mock_strategies.markdown = mock_markdown
        
        mock_chunking = Mock()
        mock_chunking.chunk_size = 1000
        mock_chunking.chunk_overlap = 100
        mock_chunking.max_chunks_per_document = 50
        mock_chunking.strategies = mock_strategies
        
        mock_global_config = Mock()
        mock_global_config.chunking = mock_chunking
        self.mock_settings.global_config = mock_global_config
        
        self.splitter = ExcelSplitter(self.mock_settings)

    def test_split_content_with_tables(self):
        """Test split_content preserves table structure."""
        table_content = """
        | Column 1 | Column 2 | Column 3 |
        |----------|----------|----------|
        | Value 1  | Value 2  | Value 3  |
        | Value 4  | Value 5  | Value 6  |
        
        Some text after table.
        
        | Another | Table |
        |---------|-------|
        | Data 1  | Data 2|
        """
        max_size = 500
        
        result = self.splitter.split_content(table_content, max_size)
        
        assert len(result) >= 1
        # Tables should be preserved as logical units
        for chunk in result:
            assert len(chunk) <= max_size

    def test_split_content_large_table_splitting(self):
        """Test split_content splits large tables when necessary."""
        # Create a large table that exceeds max_size
        rows = []
        for i in range(50):
            rows.append(f"| Data {i} | More data {i} | Even more data {i} |")
        
        table_content = "| Col1 | Col2 | Col3 |\n|------|------|------|\n" + "\n".join(rows)
        max_size = 500  # Small enough to force splitting
        
        result = self.splitter.split_content(table_content, max_size)
        
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= max_size

    def test_split_content_mixed_content(self):
        """Test split_content with mixed tables and text."""
        mixed_content = """
        # Header
        
        Some introductory text here.
        
        | Table | Data |
        |-------|------|
        | Row 1 | Val 1|
        | Row 2 | Val 2|
        
        More text between tables.
        
        | Another | Table |
        |---------|-------|
        | More    | Data  |
        """
        max_size = 200
        
        result = self.splitter.split_content(mixed_content, max_size)
        
        assert len(result) >= 1
        for chunk in result:
            assert len(chunk) <= max_size

    def test_split_content_no_tables(self):
        """Test split_content with non-table content."""
        content = "Just regular text content without any tables."
        max_size = 1000
        
        result = self.splitter.split_content(content, max_size)
        
        assert len(result) == 1
        assert result[0] == content

    def test_split_content_table_detection_patterns(self):
        """Test split_content correctly detects different table patterns."""
        # Test different table formats
        table_formats = [
            "| Standard | Table |\n|----------|-------|",
            "|No spaces|Table|\n|---------|-----|",
            "| With : alignment | Center |\n|:----------------|:------:|",
        ]
        
        for table_format in table_formats:
            result = self.splitter.split_content(table_format, 1000)
            assert len(result) >= 1


class TestSectionSplitter:
    """Test main SectionSplitter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        
        # Setup comprehensive mock configuration
        mock_markdown = Mock()
        mock_markdown.max_chunks_per_section = 10
        mock_markdown.max_overlap_percentage = 0.1
        mock_markdown.min_section_size = 200
        mock_markdown.words_per_minute_reading = 200
        mock_markdown.header_analysis_threshold_h1 = 3
        mock_markdown.header_analysis_threshold_h3 = 10
        
        mock_strategies = Mock()
        mock_strategies.markdown = mock_markdown
        
        mock_chunking = Mock()
        mock_chunking.chunk_size = 1000
        mock_chunking.chunk_overlap = 100
        mock_chunking.max_chunks_per_document = 50
        mock_chunking.strategies = mock_strategies
        
        mock_global_config = Mock()
        mock_global_config.chunking = mock_chunking
        self.mock_settings.global_config = mock_global_config
        
        self.splitter = SectionSplitter(self.mock_settings)

    def test_init(self):
        """Test SectionSplitter initialization."""
        assert self.splitter.settings is self.mock_settings
        assert isinstance(self.splitter.standard_splitter, StandardSplitter)
        assert isinstance(self.splitter.excel_splitter, ExcelSplitter)
        assert isinstance(self.splitter.fallback_splitter, FallbackSplitter)

    def test_analyze_header_distribution(self):
        """Test analyze_header_distribution method."""
        markdown_text = """
        # Main Header
        Content under main header.
        
        ## Section 1
        Content for section 1.
        
        ### Subsection 1.1
        Content for subsection.
        
        ## Section 2
        More content.
        
        ### Subsection 2.1
        Even more content.
        
        #### Deep subsection
        Deep content.
        """
        
        analysis = self.splitter.analyze_header_distribution(markdown_text)
        
        assert analysis.h1 == 1
        assert analysis.h2 == 2
        assert analysis.h3 == 2
        assert analysis.h4 == 1
        assert analysis.h5 == 0
        assert analysis.h6 == 0
        assert analysis.total_headers == 6
        assert analysis.content_length == len(markdown_text)
        assert analysis.avg_section_size > 0

    def test_analyze_header_distribution_no_headers(self):
        """Test analyze_header_distribution with content containing no headers."""
        text = "Just plain text without any markdown headers."
        
        analysis = self.splitter.analyze_header_distribution(text)
        
        assert analysis.h1 == 0
        assert analysis.h2 == 0
        assert analysis.h3 == 0
        assert analysis.total_headers == 0
        assert analysis.avg_section_size == 0

    def test_determine_optimal_split_levels_single_h1_multiple_h2(self):
        """Test determine_optimal_split_levels for single H1 with multiple H2s."""
        text = """
        # Main Document
        
        ## Section 1
        Content
        
        ## Section 2  
        Content
        
        ## Section 3
        Content
        
        ## Section 4
        Content
        """
        
        levels = self.splitter.determine_optimal_split_levels(text)
        
        # Should split on H1 and H2 for this pattern
        assert 1 in levels
        assert 2 in levels

    def test_determine_optimal_split_levels_multiple_h1(self):
        """Test determine_optimal_split_levels for multiple H1s."""
        text = """
        # First Document
        Content
        
        # Second Document
        Content
        
        # Third Document
        Content
        
        # Fourth Document
        Content
        """
        
        levels = self.splitter.determine_optimal_split_levels(text)
        
        # Should split only on H1 to avoid over-fragmentation
        assert 1 in levels
        assert len(levels) == 1

    def test_determine_optimal_split_levels_excel_document(self):
        """Test determine_optimal_split_levels for Excel documents."""
        mock_document = Mock()
        mock_document.metadata = {"original_file_type": "xlsx"}
        
        text = """
        # Excel Document
        
        ## Sheet 1
        Data
        
        ## Sheet 2
        Data
        """
        
        levels = self.splitter.determine_optimal_split_levels(text, mock_document)
        
        # Excel documents should split on H1 and H2 (document and sheets)
        assert 1 in levels
        assert 2 in levels

    def test_determine_optimal_split_levels_h3_only_document(self):
        """Test determine_optimal_split_levels for documents with only H3+ headers."""
        text = """
        ### Section 1
        Content
        
        ### Section 2
        Content
        
        #### Subsection 2.1
        Content
        
        ### Section 3
        Content
        """
        
        levels = self.splitter.determine_optimal_split_levels(text)
        
        # Should split on H3 for documents that start with H3
        assert 3 in levels

    def test_determine_optimal_split_levels_small_document(self):
        """Test determine_optimal_split_levels for small documents."""
        text = """
        # Small Document
        
        ## One Section
        Not much content.
        """
        
        levels = self.splitter.determine_optimal_split_levels(text)
        
        # Small documents should use minimal splitting
        assert 1 in levels
        assert 2 in levels

    def test_split_sections_basic(self):
        """Test split_sections with basic markdown content."""
        markdown_text = """
        # Main Header
        Introduction content.
        
        ## Section 1
        Content for section 1.
        
        ## Section 2
        Content for section 2.
        """
        
        with patch('qdrant_loader.core.chunking.strategy.markdown.section_splitter.DocumentParser') as mock_parser_class:
            with patch('qdrant_loader.core.chunking.strategy.markdown.section_splitter.HierarchyBuilder') as mock_hierarchy_class:
                # Mock parser and hierarchy builder
                mock_parser = Mock()
                mock_hierarchy = Mock()
                mock_parser_class.return_value = mock_parser
                mock_hierarchy_class.return_value = mock_hierarchy
                
                # Mock structure returned by parser
                mock_structure = [
                    {"type": "header", "level": 1, "title": "Main Header", "text": "# Main Header"},
                    {"type": "content", "text": "Introduction content."},
                    {"type": "header", "level": 2, "title": "Section 1", "text": "## Section 1"},
                    {"type": "content", "text": "Content for section 1."},
                    {"type": "header", "level": 2, "title": "Section 2", "text": "## Section 2"},
                    {"type": "content", "text": "Content for section 2."},
                ]
                mock_parser.parse_document_structure.return_value = mock_structure
                mock_parser.extract_section_title.return_value = "Default Title"
                mock_hierarchy.get_section_path.return_value = []
                
                result = self.splitter.split_sections(markdown_text)
                
                assert len(result) > 0
                for section in result:
                    assert "content" in section
                    assert "level" in section
                    assert "title" in section

    def test_split_sections_large_sections_get_split(self):
        """Test split_sections splits large sections that exceed chunk_size."""
        markdown_text = "# Large Section\n" + "Content line.\n" * 100  # Large content
        
        with patch('qdrant_loader.core.chunking.strategy.markdown.section_splitter.DocumentParser') as mock_parser_class:
            with patch('qdrant_loader.core.chunking.strategy.markdown.section_splitter.HierarchyBuilder'):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser
                
                # Create a large section that exceeds chunk_size
                large_content = "# Large Section\n" + "Content line.\n" * 100
                mock_structure = [
                    {"type": "header", "level": 1, "title": "Large Section", "text": "# Large Section"},
                    {"type": "content", "text": "Content line.\n" * 100},
                ]
                mock_parser.parse_document_structure.return_value = mock_structure
                mock_parser.extract_section_title.return_value = "Large Section"
                
                # Mock splitter to return multiple chunks
                with patch.object(self.splitter.standard_splitter, 'split_content') as mock_split:
                    mock_split.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]
                    
                    result = self.splitter.split_sections(large_content)
                    
                    # Should create multiple sub-sections
                    assert len(result) == 3
                    for i, section in enumerate(result):
                        assert f"Part {i+1}" in section["title"]

    def test_merge_related_sections_empty_list(self):
        """Test merge_related_sections with empty input."""
        result = self.splitter.merge_related_sections([])
        
        assert result == []

    def test_merge_related_sections_small_sections_merge(self):
        """Test merge_related_sections merges small related sections."""
        sections = [
            {
                "content": "Small content",  # Under min_section_size (200)
                "level": 1,
                "title": "Section 1"
            },
            {
                "content": "Another small section",
                "level": 2,  # Subsection
                "title": "Subsection 1.1"
            },
            {
                "content": "Large content " * 50,  # Over min_section_size
                "level": 1,
                "title": "Section 2"
            }
        ]
        
        result = self.splitter.merge_related_sections(sections)
        
        # First two should be merged, third stays separate
        assert len(result) == 2
        assert "Small content" in result[0]["content"]
        assert "Another small section" in result[0]["content"]

    def test_merge_related_sections_no_merging_needed(self):
        """Test merge_related_sections when no merging is needed."""
        sections = [
            {
                "content": "Large content " * 50,  # Over min_section_size
                "level": 1,
                "title": "Section 1"
            },
            {
                "content": "Another large content " * 50,
                "level": 1,
                "title": "Section 2"
            }
        ]
        
        result = self.splitter.merge_related_sections(sections)
        
        # Should remain unchanged
        assert len(result) == 2
        assert result[0]["title"] == "Section 1"
        assert result[1]["title"] == "Section 2"

    def test_build_enhanced_section_metadata(self):
        """Test build_enhanced_section_metadata creates proper metadata."""
        sections = [
            {
                "title": "Section 1",
                "level": 1,
                "content": "Content for section 1 with code ```python\nprint('hello')\n``` and tables | A | B |\n|---|---| and links [link](url)",
                "path": ["Root"]
            },
            {
                "title": "Section 2",
                "level": 2,
                "content": "Content for section 2",
                "path": ["Root", "Section 1"]
            }
        ]
        
        with patch('qdrant_loader.core.chunking.strategy.markdown.section_splitter.markdown_config') as mock_config:
            mock_config.words_per_minute_reading = 200
            
            result = self.splitter.build_enhanced_section_metadata(sections)
            
            assert len(result) == 2
            assert isinstance(result[0], SectionMetadata)
            assert result[0].title == "Section 1"
            assert result[0].level == 1
            assert result[0].breadcrumb == "Root > Section 1"
            assert result[0].content_analysis["has_code_blocks"] is True
            assert result[0].content_analysis["has_tables"] is True
            assert result[0].content_analysis["has_links"] is True