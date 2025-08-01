"""Unit tests for BaseDocumentParser."""
import pytest
from qdrant_loader.core.chunking.strategy.base.document_parser import BaseDocumentParser


class ConcreteDocumentParser(BaseDocumentParser):
    """Concrete implementation for testing."""
    
    def parse_document_structure(self, content: str):
        return {"structure_type": "test", "content_length": len(content)}
    
    def extract_section_metadata(self, section):
        return {"section_type": "test_section", "length": len(str(section))}


class TestBaseDocumentParser:
    """Test cases for BaseDocumentParser base class."""
    
    @pytest.fixture
    def parser(self):
        """Create a concrete parser for testing."""
        return ConcreteDocumentParser()
    
    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract methods raise NotImplementedError."""
        # Abstract classes cannot be instantiated directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseDocumentParser()
    
    def test_extract_section_title_default_implementation(self, parser):
        """Test the default extract_section_title implementation."""
        # Test with simple title
        content = "This is a title\nWith some content below"
        title = parser.extract_section_title(content)
        assert title == "This is a title"
        
        # Test with empty content
        title = parser.extract_section_title("")
        assert title == ""
        
        # Test with whitespace only
        title = parser.extract_section_title("   \n  ")
        assert title == ""
        
        # Test with long title (should be truncated)
        long_content = "This is a very long title that should be truncated because it exceeds the maximum length limit of 100 characters which is the default limit"
        title = parser.extract_section_title(long_content)
        assert len(title) <= 100
        assert title.startswith("This is a very long title")
    
    def test_analyze_content_characteristics(self, parser):
        """Test the analyze_content_characteristics method."""
        content = """This is a test document.
        It has multiple lines.
        Some lines are empty.
        
        And some unicode characters: café, naïve, résumé."""
        
        analysis = parser.analyze_content_characteristics(content)
        
        # Check required fields
        assert "line_count" in analysis
        assert "word_count" in analysis
        assert "character_count" in analysis
        assert "non_empty_line_count" in analysis
        assert "avg_line_length" in analysis
        assert "avg_word_length" in analysis
        assert "has_unicode" in analysis
        
        # Verify calculations
        lines = content.split('\n')
        words = content.split()
        
        assert analysis["line_count"] == len(lines)
        assert analysis["word_count"] == len(words)
        assert analysis["character_count"] == len(content)
        assert analysis["non_empty_line_count"] == len([line for line in lines if line.strip()])
        assert analysis["has_unicode"] is True  # Due to café, naïve, résumé
        
        # Check averages are reasonable
        assert analysis["avg_line_length"] > 0
        assert analysis["avg_word_length"] > 0
    
    def test_analyze_content_characteristics_empty_content(self, parser):
        """Test analyze_content_characteristics with empty content."""
        analysis = parser.analyze_content_characteristics("")
        
        assert analysis["line_count"] == 1  # Empty string splits to one empty line
        assert analysis["word_count"] == 0
        assert analysis["character_count"] == 0
        assert analysis["non_empty_line_count"] == 0
        assert analysis["avg_line_length"] == 0
        assert analysis["avg_word_length"] == 0
        assert analysis["has_unicode"] is False
    
    def test_analyze_content_characteristics_ascii_only(self, parser):
        """Test analyze_content_characteristics with ASCII-only content."""
        content = "This is simple ASCII text with no special characters."
        analysis = parser.analyze_content_characteristics(content)
        assert analysis["has_unicode"] is False
    
    def test_concrete_implementation_methods(self, parser):
        """Test that concrete implementation methods work."""
        content = "Test content for parsing"
        
        # Test parse_document_structure
        structure = parser.parse_document_structure(content)
        assert structure["structure_type"] == "test"
        assert structure["content_length"] == len(content)
        
        # Test extract_section_metadata
        section = "Test section content"
        metadata = parser.extract_section_metadata(section)
        assert metadata["section_type"] == "test_section"
        assert metadata["length"] == len(section)
    
    def test_extract_section_title_with_multiple_lines(self, parser):
        """Test extract_section_title with various line formats."""
        # Test with leading whitespace
        content = "   \n  \n  Actual Title\nContent below"
        title = parser.extract_section_title(content)
        assert title == "Actual Title"
        
        # Test with no actual content
        content = "\n\n   \n  "
        title = parser.extract_section_title(content)
        assert title == ""
    
    def test_content_characteristics_edge_cases(self, parser):
        """Test content characteristics with edge cases."""
        # Test with only whitespace
        whitespace_content = "   \n  \t\n   "
        analysis = parser.analyze_content_characteristics(whitespace_content)
        assert analysis["word_count"] == 0
        assert analysis["non_empty_line_count"] == 0
        
        # Test with single word
        single_word = "word"
        analysis = parser.analyze_content_characteristics(single_word)
        assert analysis["word_count"] == 1
        assert analysis["line_count"] == 1
        assert analysis["avg_word_length"] == 4 