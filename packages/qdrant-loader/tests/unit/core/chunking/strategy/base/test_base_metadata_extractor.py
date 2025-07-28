"""Unit tests for BaseMetadataExtractor."""

from unittest.mock import Mock
import pytest
import re
from qdrant_loader.core.chunking.strategy.base.metadata_extractor import BaseMetadataExtractor
from qdrant_loader.core.document import Document


class ConcreteMetadataExtractor(BaseMetadataExtractor):
    """Concrete implementation for testing."""
    
    def extract_hierarchical_metadata(self, content: str, chunk_metadata: dict, document):
        # Simple implementation that adds test metadata
        metadata = chunk_metadata.copy()
        metadata.update({
            "test_hierarchical": True,
            "content_length": len(content),
            "document_title": document.title if document else "unknown"
        })
        return metadata
    
    def extract_entities(self, text: str):
        # Simple implementation that finds capitalized words
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        return list(set(words))  # Remove duplicates


class TestBaseMetadataExtractor:
    """Test cases for BaseMetadataExtractor base class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a concrete extractor for testing."""
        return ConcreteMetadataExtractor()
    
    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            content="Test document content",
            url="http://example.com/test.txt",
            content_type="txt",
            source_type="test",
            source="test_source",
            title="Test Document",
            metadata={"source": "test"}
        )
    
    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract methods raise NotImplementedError."""
        # Abstract classes cannot be instantiated directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseMetadataExtractor()
    
    def test_extract_cross_references_section_references(self, extractor):
        """Test extraction of section references."""
        content = "Please see Section 1.2 for details. Refer to Chapter 3 for more information."
        
        refs = extractor.extract_cross_references(content)
        
        # Should find section and chapter references
        section_refs = [ref for ref in refs if ref["type"] == "section_reference"]
        assert len(section_refs) >= 1
        
        # Check that we found the section reference
        found_section_ref = any("1.2" in ref["reference"] for ref in section_refs)
        assert found_section_ref
    
    def test_extract_cross_references_figure_references(self, extractor):
        """Test extraction of figure and table references."""
        content = "As shown in Figure 2.1, the data indicates trends. Table A shows results."
        
        refs = extractor.extract_cross_references(content)
        
        # Should find figure references
        figure_refs = [ref for ref in refs if ref["type"] == "figure_reference"]
        assert len(figure_refs) >= 1
        
        # Check that we found figure reference
        found_figure_ref = any("2.1" in ref["reference"] for ref in figure_refs)
        assert found_figure_ref
    
    def test_extract_cross_references_no_references(self, extractor):
        """Test that no references are found in plain text."""
        content = "This is simple text with no references to anything special."
        
        refs = extractor.extract_cross_references(content)
        assert len(refs) == 0
    
    def test_analyze_content_type_with_code(self, extractor):
        """Test content type analysis with code indicators."""
        content = """
        def my_function():
            return "Hello, World!"
        
        ```python
        import os
        ```
        """
        
        analysis = extractor.analyze_content_type(content)
        
        assert analysis["has_code"] is True
        assert analysis["content_category"] == "technical"
        assert analysis["complexity_score"] >= 2  # Code adds complexity
    
    def test_analyze_content_type_with_math(self, extractor):
        """Test content type analysis with mathematical content."""
        content = "The formula is $E = mc^2$ and we can use ∑ for summation."
        
        analysis = extractor.analyze_content_type(content)
        
        assert analysis["has_math"] is True
        assert analysis["content_category"] == "academic"
        assert analysis["complexity_score"] >= 2  # Math adds complexity
    
    def test_analyze_content_type_with_lists(self, extractor):
        """Test content type analysis with lists."""
        content = """
        Here are the items:
        - First item
        - Second item
        1. Numbered item
        2. Another numbered item
        """
        
        analysis = extractor.analyze_content_type(content)
        
        assert analysis["has_lists"] is True
        assert analysis["content_category"] == "informational"
    
    def test_analyze_content_type_with_headers(self, extractor):
        """Test content type analysis with headers."""
        content = """
        # Main Header
        ## Sub Header
        
        Some content here.
        """
        
        analysis = extractor.analyze_content_type(content)
        
        assert analysis["has_headers"] is True
    
    def test_analyze_content_type_with_links(self, extractor):
        """Test content type analysis with links."""
        content = "Visit https://example.com or www.test.com for more info."
        
        analysis = extractor.analyze_content_type(content)
        
        assert analysis["has_links"] is True
    
    def test_analyze_content_type_with_tables(self, extractor):
        """Test content type analysis with tables."""
        content = """
        | Column 1 | Column 2 | Column 3 |
        |----------|----------|----------|
        | Data 1   | Data 2   | Data 3   |
        """
        
        analysis = extractor.analyze_content_type(content)
        
        assert analysis["has_tables"] is True
    
    def test_analyze_content_type_narrative(self, extractor):
        """Test content type analysis for narrative content."""
        content = "This is a simple narrative text without any special formatting or technical content."
        
        analysis = extractor.analyze_content_type(content)
        
        assert analysis["content_category"] == "narrative"
        assert analysis["complexity_score"] == 0
        assert analysis["primary_language"] == "en"
    
    def test_detect_primary_language_english(self, extractor):
        """Test language detection for English content."""
        content = "This is an English sentence with common words like the, and, of, to."
        
        language = extractor._detect_primary_language(content)
        assert language == "en"
    
    def test_detect_primary_language_unknown(self, extractor):
        """Test language detection for non-English content."""
        content = "Ceci est un texte français sans mots anglais communs."
        
        language = extractor._detect_primary_language(content)
        assert language == "unknown"  # Our basic detector only recognizes English
    
    def test_categorize_content_types(self, extractor):
        """Test content categorization logic."""
        # Technical content
        tech_analysis = {"has_code": True, "has_math": False, "has_tables": False, "has_lists": False, "has_headers": False}
        assert extractor._categorize_content(tech_analysis) == "technical"
        
        # Academic content
        academic_analysis = {"has_code": False, "has_math": True, "has_tables": False, "has_lists": False, "has_headers": False}
        assert extractor._categorize_content(academic_analysis) == "academic"
        
        # Structured content
        structured_analysis = {"has_code": False, "has_math": False, "has_tables": True, "has_lists": False, "has_headers": True}
        assert extractor._categorize_content(structured_analysis) == "structured"
        
        # Informational content
        info_analysis = {"has_code": False, "has_math": False, "has_tables": False, "has_lists": True, "has_headers": False}
        assert extractor._categorize_content(info_analysis) == "informational"
        
        # Narrative content
        narrative_analysis = {"has_code": False, "has_math": False, "has_tables": False, "has_lists": False, "has_headers": False}
        assert extractor._categorize_content(narrative_analysis) == "narrative"
    
    def test_extract_keyword_density(self, extractor):
        """Test keyword density extraction."""
        content = "Python programming is great. Python developers love Python for its simplicity."
        
        keywords = extractor.extract_keyword_density(content, top_n=5)
        
        assert "python" in keywords
        assert keywords["python"] > 0
        assert len(keywords) <= 5
        
        # Python should have high density (appears 3 times)
        assert keywords["python"] > keywords.get("programming", 0)
    
    def test_extract_keyword_density_with_stop_words(self, extractor):
        """Test that stop words are filtered out."""
        content = "The quick brown fox jumps over the lazy dog. The fox is quick."
        
        keywords = extractor.extract_keyword_density(content)
        
        # Stop words should not appear
        stop_words = ["the", "is", "over"]
        for stop_word in stop_words:
            assert stop_word not in keywords
        
        # Content words should appear
        assert "fox" in keywords
        assert "quick" in keywords
    
    def test_extract_keyword_density_empty_content(self, extractor):
        """Test keyword density with empty content."""
        keywords = extractor.extract_keyword_density("")
        assert keywords == {}
    
    def test_create_breadcrumb_metadata(self, extractor):
        """Test breadcrumb metadata creation."""
        current_section = "Section 1.2"
        parent_sections = ["Chapter 1", "Introduction"]
        
        breadcrumb = extractor.create_breadcrumb_metadata(current_section, parent_sections)
        
        assert breadcrumb["breadcrumb_path"] == ["Chapter 1", "Introduction", "Section 1.2"]
        assert breadcrumb["breadcrumb_string"] == "Chapter 1 > Introduction > Section 1.2"
        assert breadcrumb["section_depth"] == 3
        assert breadcrumb["parent_section"] == "Introduction"
        assert breadcrumb["root_section"] == "Chapter 1"
    
    def test_create_breadcrumb_metadata_no_current_section(self, extractor):
        """Test breadcrumb metadata with no current section."""
        parent_sections = ["Chapter 1", "Introduction"]
        
        breadcrumb = extractor.create_breadcrumb_metadata("", parent_sections)
        
        assert breadcrumb["breadcrumb_path"] == ["Chapter 1", "Introduction"]
        assert breadcrumb["section_depth"] == 2
    
    def test_create_breadcrumb_metadata_empty_parents(self, extractor):
        """Test breadcrumb metadata with empty parent sections."""
        current_section = "Standalone Section"
        
        breadcrumb = extractor.create_breadcrumb_metadata(current_section, [])
        
        assert breadcrumb["breadcrumb_path"] == ["Standalone Section"]
        assert breadcrumb["section_depth"] == 1
        assert breadcrumb["parent_section"] is None
        assert breadcrumb["root_section"] == "Standalone Section"
    
    def test_concrete_implementation_methods(self, extractor, sample_document):
        """Test that concrete implementation methods work."""
        content = "This is Test Content with Some Entities."
        chunk_metadata = {"existing_key": "existing_value"}
        
        # Test extract_hierarchical_metadata
        enriched_metadata = extractor.extract_hierarchical_metadata(content, chunk_metadata, sample_document)
        
        assert enriched_metadata["existing_key"] == "existing_value"  # Preserves existing
        assert enriched_metadata["test_hierarchical"] is True
        assert enriched_metadata["content_length"] == len(content)
        assert enriched_metadata["document_title"] == "Test Document"
        
        # Test extract_entities
        entities = extractor.extract_entities(content)
        expected_entities = ["This", "Test", "Content", "Some", "Entities"]
        
        for entity in expected_entities:
            assert entity in entities 