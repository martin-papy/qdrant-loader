"""Unit tests for TextDocumentParser."""

import pytest
from qdrant_loader.core.chunking.strategy.default.text_document_parser import (
    TextDocumentParser,
)


class TestTextDocumentParser:
    """Test cases for TextDocumentParser."""

    @pytest.fixture
    def parser(self):
        """Create a text document parser for testing."""
        return TextDocumentParser()

    def test_parse_document_structure_simple_text(self, parser):
        """Test parsing simple text structure."""
        content = """This is the first paragraph.
        It has multiple sentences.

        This is the second paragraph.
        It also has content."""

        structure = parser.parse_document_structure(content)

        # Check required fields
        assert structure["structure_type"] == "plain_text"
        assert structure["paragraph_count"] == 2
        assert structure["sentence_count"] >= 2
        assert structure["avg_paragraph_length"] > 0
        assert structure["avg_sentence_length"] > 0
        assert structure["has_list_items"] is False
        assert structure["has_numbered_sections"] is False

        # Check content characteristics are included
        assert "line_count" in structure
        assert "word_count" in structure
        assert "character_count" in structure

    def test_parse_document_structure_with_lists(self, parser):
        """Test parsing text with list items."""
        content = """Introduction paragraph.

        Here are the items:
        - First item
        - Second item
        * Another item

        1. Numbered item
        2. Another numbered

        Conclusion paragraph."""

        structure = parser.parse_document_structure(content)

        assert structure["has_list_items"] is True
        assert structure["paragraph_count"] >= 3

    def test_parse_document_structure_with_numbered_sections(self, parser):
        """Test parsing text with numbered sections."""
        content = """1. Introduction
        This is the introduction section.

        Section 2
        This is another section.

        Chapter 3
        Final chapter here."""

        structure = parser.parse_document_structure(content)

        assert structure["has_numbered_sections"] is True

    def test_parse_document_structure_formatting_indicators(self, parser):
        """Test detection of formatting indicators."""
        content = """This has **bold text** and *italic text*.

        It also has "quoted text" and (parenthetical remarks).

        Some [bracketed] content and CAPS WORDS.

        Email: user@example.com
        URL: https://example.com"""

        structure = parser.parse_document_structure(content)

        formatting = structure["formatting_indicators"]
        assert formatting["has_bold_text"] is True
        assert formatting["has_italic_text"] is True
        assert formatting["has_quotes"] is True
        assert formatting["has_parenthetical"] is True
        assert formatting["has_brackets"] is True
        assert formatting["has_caps_words"] is True
        assert formatting["has_email_addresses"] is True
        assert formatting["has_urls"] is True

    def test_parse_document_structure_content_density(self, parser):
        """Test content density calculation."""
        # Dense content (little whitespace)
        dense_content = "Verydensecontent"
        dense_structure = parser.parse_document_structure(dense_content)

        # Sparse content (lots of whitespace)
        sparse_content = "Very   sparse   content   with   spaces"
        sparse_structure = parser.parse_document_structure(sparse_content)

        assert dense_structure["content_density"] > sparse_structure["content_density"]

    def test_extract_section_metadata(self, parser):
        """Test extraction of section metadata."""
        section = """This is a test section.
        It has multiple lines.
        - And a list item
        1. And a numbered item"""

        metadata = parser.extract_section_metadata(section)

        expected_keys = {
            "section_type",
            "length",
            "word_count",
            "sentence_count",
            "has_formatting",
            "is_list_item",
            "is_numbered_item",
            "content_type",
        }
        assert set(metadata.keys()) == expected_keys

        assert metadata["section_type"] == "text_paragraph"
        assert metadata["length"] == len(section)
        assert metadata["word_count"] == len(section.split())
        assert metadata["sentence_count"] >= 1
        assert metadata["has_formatting"] is False  # No markdown formatting
        assert metadata["is_list_item"] is False
        assert metadata["is_numbered_item"] is False
        assert metadata["content_type"] == "paragraph"

    def test_split_paragraphs_double_newlines(self, parser):
        """Test paragraph splitting on double newlines."""
        content = """First paragraph here.

        Second paragraph here.

        Third paragraph here."""

        paragraphs = parser._split_paragraphs(content)

        assert len(paragraphs) == 3
        assert "First paragraph" in paragraphs[0]
        assert "Second paragraph" in paragraphs[1]
        assert "Third paragraph" in paragraphs[2]

    def test_split_paragraphs_list_detection(self, parser):
        """Test that list items are split into separate paragraphs."""
        content = """Introduction paragraph.
        - First item
        - Second item
        Conclusion paragraph."""

        paragraphs = parser._split_paragraphs(content)

        # Should split list items from regular paragraphs
        assert len(paragraphs) >= 3
        assert any("Introduction" in p for p in paragraphs)
        assert any("Conclusion" in p for p in paragraphs)

    def test_split_sentences_basic(self, parser):
        """Test basic sentence splitting."""
        content = "First sentence. Second sentence! Third sentence? Fourth statement."

        sentences = parser._split_sentences(content)

        assert len(sentences) == 4
        assert sentences[0].startswith("First")
        assert sentences[1].startswith("Second")
        assert sentences[2].startswith("Third")
        assert sentences[3].startswith("Fourth")

    def test_split_sentences_filters_short_fragments(self, parser):
        """Test that very short fragments are filtered out."""
        content = "Real sentence. A. Another real sentence. B."

        sentences = parser._split_sentences(content)

        # Should filter out very short fragments like "A." and "B."
        long_sentences = [s for s in sentences if len(s) > 10]
        assert len(long_sentences) >= 2

    def test_has_list_items_detection(self, parser):
        """Test detection of various list item formats."""
        # Bullet points
        assert parser._has_list_items("- Item 1\n- Item 2") is True
        assert parser._has_list_items("* Item 1\n* Item 2") is True
        assert parser._has_list_items("+ Item 1\n+ Item 2") is True

        # Numbered lists
        assert parser._has_list_items("1. Item 1\n2. Item 2") is True

        # Lettered lists
        assert parser._has_list_items("a. Item 1\nb. Item 2") is True

        # Roman numerals
        assert parser._has_list_items("i. Item 1\nii. Item 2") is True

        # No lists
        assert parser._has_list_items("Regular paragraph text") is False

    def test_has_numbered_sections_detection(self, parser):
        """Test detection of numbered sections."""
        # Various numbered section formats
        assert parser._has_numbered_sections("1. Introduction\nContent here") is True
        assert parser._has_numbered_sections("Section 1\nContent") is True
        assert parser._has_numbered_sections("Chapter 1\nContent") is True
        assert parser._has_numbered_sections("Part 1\nContent") is True

        # No numbered sections
        assert parser._has_numbered_sections("Regular content") is False

    def test_analyze_formatting_detection(self, parser):
        """Test detection of various formatting elements."""
        content_with_formatting = """
        **Bold text** and *italic text*.
        "Quoted text" and (parenthetical).
        [Bracketed] and CAPS text.
        Email: test@example.com
        URL: https://example.com
        """

        formatting = parser._analyze_formatting(content_with_formatting)

        assert formatting["has_bold_text"] is True
        assert formatting["has_italic_text"] is True
        assert formatting["has_quotes"] is True
        assert formatting["has_parenthetical"] is True
        assert formatting["has_brackets"] is True
        assert formatting["has_caps_words"] is True
        assert formatting["has_email_addresses"] is True
        assert formatting["has_urls"] is True

    def test_analyze_formatting_no_formatting(self, parser):
        """Test formatting analysis with plain text."""
        plain_content = "This is plain text with no special formatting."

        formatting = parser._analyze_formatting(plain_content)

        for _key, value in formatting.items():
            assert value is False

    def test_calculate_content_density(self, parser):
        """Test content density calculation."""
        # Very dense content
        dense = "NoSpacesHere"
        dense_ratio = parser._calculate_content_density(dense)
        assert dense_ratio == 1.0

        # All whitespace
        sparse = "   \n\t  "
        sparse_ratio = parser._calculate_content_density(sparse)
        assert sparse_ratio == 0.0

        # Mixed content
        mixed = "Text with spaces"
        mixed_ratio = parser._calculate_content_density(mixed)
        assert 0.0 < mixed_ratio < 1.0

    def test_is_new_paragraph_start_list_items(self, parser):
        """Test paragraph start detection for list items."""
        current_paragraph = ["Previous content"]

        # List items should start new paragraphs
        assert parser._is_new_paragraph_start("- List item", current_paragraph) is True
        assert (
            parser._is_new_paragraph_start("1. Numbered item", current_paragraph)
            is True
        )

        # Regular text should not
        assert (
            parser._is_new_paragraph_start("Regular text", current_paragraph) is False
        )

    def test_is_new_paragraph_start_headers(self, parser):
        """Test paragraph start detection for headers."""
        current_paragraph = ["Previous content"]

        # Headers should start new paragraphs
        assert (
            parser._is_new_paragraph_start("1. Section Title", current_paragraph)
            is True
        )
        assert parser._is_new_paragraph_start("SHORT TITLE", current_paragraph) is True

    def test_classify_content_type(self, parser):
        """Test content type classification."""
        assert parser._classify_content_type("- List item") == "list_item"
        assert parser._classify_content_type("1. Numbered item") == "numbered_item"
        assert (
            parser._classify_content_type("1. Section Header") == "numbered_item"
        )  # Could be header too
        assert parser._classify_content_type("Short") == "fragment"
        assert (
            parser._classify_content_type("Title Without Period") == "header"
        )  # This looks like a header
        assert (
            parser._classify_content_type("This is a proper sentence.") == "paragraph"
        )

    def test_looks_like_header(self, parser):
        """Test header detection logic."""
        # Should be headers
        assert parser._looks_like_header("Section Title") is True
        assert parser._looks_like_header("1. Introduction") is True
        assert parser._looks_like_header("CAPS TITLE") is True
        assert parser._looks_like_header("Title Case Words") is True

        # Should not be headers
        assert parser._looks_like_header("This is a sentence.") is False
        assert (
            parser._looks_like_header(
                "This is way too long to be a reasonable header title for any document"
            )
            is False
        )
        assert parser._looks_like_header("Question?") is False

    def test_has_significant_indentation_change(self, parser):
        """Test detection of significant indentation changes."""
        # No significant change
        prev_line = "    Regular indented line"
        current_line = "    Same indentation"
        assert (
            parser._has_significant_indentation_change(prev_line, current_line) is False
        )

        # Significant change (>4 spaces)
        prev_line = "Regular line"
        current_line = "        Heavily indented"
        assert (
            parser._has_significant_indentation_change(prev_line, current_line) is True
        )

        # Empty previous line
        assert parser._has_significant_indentation_change("", "    Indented") is False

    def test_edge_cases(self, parser):
        """Test edge cases and error conditions."""
        # Empty content
        empty_structure = parser.parse_document_structure("")
        assert empty_structure["paragraph_count"] == 0
        assert empty_structure["sentence_count"] == 0

        # Only whitespace
        whitespace_structure = parser.parse_document_structure("   \n\n   ")
        assert whitespace_structure["paragraph_count"] == 0

        # Single word
        single_word = parser.parse_document_structure("Word")
        assert single_word["paragraph_count"] == 1
        assert single_word["word_count"] == 1

    def test_extract_section_metadata_non_string_input(self, parser):
        """Test that non-string input is handled gracefully."""
        # Should convert to string
        metadata = parser.extract_section_metadata(123)
        assert metadata["length"] == len("123")
        assert metadata["word_count"] == 1
