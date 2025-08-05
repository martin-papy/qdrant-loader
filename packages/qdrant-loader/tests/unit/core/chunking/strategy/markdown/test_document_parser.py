"""Comprehensive tests for Markdown Document Parser to achieve 80%+ coverage."""

import pytest

from qdrant_loader.core.chunking.strategy.markdown.document_parser import (
    DocumentParser,
    HierarchyBuilder,
    Section,
    SectionIdentifier, 
    SectionType,
)


class TestSectionType:
    """Test SectionType enum."""

    def test_section_type_values(self):
        """Test that all section types have correct values."""
        assert SectionType.HEADER.value == "header"
        assert SectionType.CODE_BLOCK.value == "code_block"
        assert SectionType.LIST.value == "list"
        assert SectionType.TABLE.value == "table"
        assert SectionType.QUOTE.value == "quote"
        assert SectionType.PARAGRAPH.value == "paragraph"


class TestSection:
    """Test Section dataclass."""

    def test_section_initialization_defaults(self):
        """Test Section initialization with default values."""
        section = Section(content="Test content")
        
        assert section.content == "Test content"
        assert section.level == 0
        assert section.type == SectionType.PARAGRAPH
        assert section.parent is None
        assert section.children == []

    def test_section_initialization_custom_values(self):
        """Test Section initialization with custom values."""
        section = Section(
            content="Header content",
            level=2,
            type=SectionType.HEADER
        )
        
        assert section.content == "Header content"
        assert section.level == 2
        assert section.type == SectionType.HEADER
        assert section.parent is None
        assert section.children == []

    def test_add_child_method(self):
        """Test adding child sections."""
        parent = Section(content="Parent section", level=1, type=SectionType.HEADER)
        child = Section(content="Child section", level=2, type=SectionType.HEADER)
        
        parent.add_child(child)
        
        assert len(parent.children) == 1
        assert parent.children[0] is child
        assert child.parent is parent

    def test_add_multiple_children(self):
        """Test adding multiple child sections."""
        parent = Section(content="Parent", level=1, type=SectionType.HEADER)
        child1 = Section(content="Child 1", level=2, type=SectionType.HEADER)
        child2 = Section(content="Child 2", level=2, type=SectionType.PARAGRAPH)
        child3 = Section(content="Child 3", level=3, type=SectionType.LIST)
        
        parent.add_child(child1)
        parent.add_child(child2)
        parent.add_child(child3)
        
        assert len(parent.children) == 3
        assert parent.children[0] is child1
        assert parent.children[1] is child2
        assert parent.children[2] is child3
        assert child1.parent is parent
        assert child2.parent is parent
        assert child3.parent is parent

    def test_nested_hierarchy(self):
        """Test creating nested section hierarchy."""
        root = Section(content="Root", level=1, type=SectionType.HEADER)
        child1 = Section(content="Child 1", level=2, type=SectionType.HEADER)
        grandchild = Section(content="Grandchild", level=3, type=SectionType.HEADER)
        child2 = Section(content="Child 2", level=2, type=SectionType.PARAGRAPH)
        
        root.add_child(child1)
        child1.add_child(grandchild)
        root.add_child(child2)
        
        assert len(root.children) == 2
        assert root.children[0] is child1
        assert root.children[1] is child2
        assert len(child1.children) == 1
        assert child1.children[0] is grandchild
        assert grandchild.parent is child1
        assert child1.parent is root


class TestSectionIdentifier:
    """Test SectionIdentifier class."""

    def test_identify_header_sections(self):
        """Test identification of header sections."""
        test_cases = [
            "# Main Header",
            "## Sub Header",
            "### Third Level",
            "#### Fourth Level",
            "##### Fifth Level",
            "###### Sixth Level",
        ]
        
        for header in test_cases:
            section_type = SectionIdentifier.identify_section_type(header)
            assert section_type == SectionType.HEADER

    def test_identify_code_block_sections(self):
        """Test identification of code block sections."""
        test_cases = [
            "```python\nprint('hello')\n```",
            "```javascript\nconsole.log('hello');\n```",
            "```\ngeneric code\n```",
            "~~~python\nprint('hello')\n~~~",
            "    indented code block",
            "\tindented with tab",
        ]
        
        for code_block in test_cases:
            section_type = SectionIdentifier.identify_section_type(code_block)
            assert section_type == SectionType.CODE_BLOCK

    def test_identify_list_sections(self):
        """Test identification of list sections."""
        test_cases = [
            "- Item 1\n- Item 2",
            "* Item 1\n* Item 2",
            "+ Item 1\n+ Item 2",
            "1. First item\n2. Second item",
            "1) First item\n2) Second item",
            "- Nested list\n  - Sub item\n  - Another sub item",
        ]
        
        for list_content in test_cases:
            section_type = SectionIdentifier.identify_section_type(list_content)
            assert section_type == SectionType.LIST

    def test_identify_table_sections(self):
        """Test identification of table sections."""
        test_cases = [
            "| Column 1 | Column 2 |\n|----------|----------|\n| Data 1   | Data 2   |",
            "| Name | Age | City |\n|------|-----|------|\n| John | 30  | NYC  |",
            "Column 1 | Column 2\n---------|----------\nData 1   | Data 2",
        ]
        
        for table in test_cases:
            section_type = SectionIdentifier.identify_section_type(table)
            assert section_type == SectionType.TABLE

    def test_identify_quote_sections(self):
        """Test identification of quote sections."""
        test_cases = [
            "> This is a quote",
            "> Multi-line quote\n> with multiple lines",
            "> Nested quote\n>> Even more nested",
            "> Quote with *emphasis*\n> and **bold** text",
        ]
        
        for quote in test_cases:
            section_type = SectionIdentifier.identify_section_type(quote)
            assert section_type == SectionType.QUOTE

    def test_identify_paragraph_sections(self):
        """Test identification of paragraph sections (default)."""
        test_cases = [
            "This is a regular paragraph.",
            "A paragraph with some **bold** and *italic* text.",
            "Paragraph with [links](https://example.com) and ![images](img.png).",
            "Multiple\nlines\nin a\nparagraph.",
            "",  # Empty content
            "   ",  # Whitespace only
        ]
        
        for paragraph in test_cases:
            section_type = SectionIdentifier.identify_section_type(paragraph)
            assert section_type == SectionType.PARAGRAPH

    def test_identify_mixed_content_priority(self):
        """Test section type identification with mixed content."""
        # Headers should take priority
        mixed_header = "# Header\nSome paragraph text\n- A list item"
        assert SectionIdentifier.identify_section_type(mixed_header) == SectionType.HEADER
        
        # Code blocks should take priority over other content
        mixed_code = "Some text\n```python\ncode here\n```\nMore text"
        assert SectionIdentifier.identify_section_type(mixed_code) == SectionType.CODE_BLOCK
        
        # Tables should take priority over paragraphs
        mixed_table = "Some intro text\n| Col1 | Col2 |\n|------|------|\n| A | B |"
        assert SectionIdentifier.identify_section_type(mixed_table) == SectionType.TABLE

    def test_identify_edge_cases(self):
        """Test edge cases for section identification."""
        # Not actual headers (no space after #)
        assert SectionIdentifier.identify_section_type("#notaheader") == SectionType.PARAGRAPH
        
        # Not actual lists (no space after -)
        assert SectionIdentifier.identify_section_type("-notalist") == SectionType.PARAGRAPH
        
        # Not actual quotes (no space after >)
        assert SectionIdentifier.identify_section_type(">notquote") == SectionType.PARAGRAPH
        
        # Empty string
        assert SectionIdentifier.identify_section_type("") == SectionType.PARAGRAPH


class TestDocumentParser:
    """Test DocumentParser class."""

    def test_initialization(self):
        """Test parser initialization."""
        parser = DocumentParser()
        assert parser is not None
        assert parser.section_identifier is not None
        assert parser.hierarchy_builder is not None

    def test_parse_document_structure_simple(self):
        """Test parsing a simple markdown document structure."""
        content = """# Main Title

This is the introduction paragraph.

## Section 1

Content for section 1.

### Subsection 1.1

More detailed content.

## Section 2

Content for section 2.
"""
        
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Should have parsed multiple elements
        assert len(elements) > 0
        
        # Should have headers and content
        header_elements = [e for e in elements if e["type"] == "header"]
        content_elements = [e for e in elements if e["type"] == "content"]
        
        assert len(header_elements) >= 3  # Main Title, Section 1, Subsection 1.1, Section 2
        assert len(content_elements) >= 1  # At least some content

    def test_parse_document_structure_with_code_blocks(self):
        """Test parsing document with code blocks."""
        content = """# Code Examples

Here are some code examples:

```python
def hello():
    print("Hello, World!")
```

```javascript
function hello() {
    console.log("Hello, World!");
}
```

That's all for now.
"""
        
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Should have header and content elements
        assert len(elements) > 0
        header_elements = [e for e in elements if e["type"] == "header"]
        assert len(header_elements) >= 1

    def test_extract_section_title(self):
        """Test extracting section titles from chunks."""
        parser = DocumentParser()
        
        # Test with header
        chunk_with_header = "# Main Title\n\nSome content here."
        title = parser.extract_section_title(chunk_with_header)
        assert title == "Main Title"
        
        # Test with different header levels
        chunk_h2 = "## Subsection\n\nMore content."
        title = parser.extract_section_title(chunk_h2)
        assert title == "Subsection"
        
        # Test with sentence
        chunk_sentence = "This is the first sentence. Here's another sentence."
        title = parser.extract_section_title(chunk_sentence)
        assert "This is the first sentence." in title
        
        # Test with no clear title
        chunk_no_title = "some random text without proper structure"
        title = parser.extract_section_title(chunk_no_title)
        assert title == "Untitled Section"

    def test_extract_section_metadata(self):
        """Test extracting metadata from sections."""
        parser = DocumentParser()
        
        # Create a test section
        section = Section(
            content="# Test Header\n\nThis is some content with [a link](https://example.com) and ![image](img.png).\n\n```python\ncode here\n```",
            level=1,
            type=SectionType.HEADER
        )
        
        metadata = parser.extract_section_metadata(section)
        
        assert metadata["type"] == "header"
        assert metadata["level"] == 1
        assert metadata["word_count"] > 0
        assert metadata["char_count"] > 0
        assert metadata["has_code"] is True
        assert metadata["has_links"] is True
        assert metadata["has_images"] is True
        assert metadata["is_top_level"] is True

    def test_extract_section_metadata_with_parent(self):
        """Test extracting metadata from sections with parent relationships."""
        parser = DocumentParser()
        
        # Create parent and child sections
        parent = Section(
            content="# Parent Section\n\nParent content.",
            level=1,
            type=SectionType.HEADER
        )
        
        child = Section(
            content="## Child Section\n\nChild content.",
            level=2,
            type=SectionType.HEADER
        )
        
        parent.add_child(child)
        
        metadata = parser.extract_section_metadata(child)
        
        assert metadata["parent_title"] == "Parent Section"
        assert metadata["parent_level"] == 1
        assert "breadcrumb" in metadata

    def test_parse_complex_document_structure(self):
        """Test parsing a complex document with mixed content."""
        content = """# Complete Guide

## Introduction

This guide covers multiple markdown features.

### Code Examples

Here's some Python code:

```python
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
```

### Lists and Tasks

Things to remember.

## Conclusion

That concludes our guide.
"""
        
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Should parse multiple elements
        assert len(elements) > 0
        
        # Should have headers
        header_elements = [e for e in elements if e["type"] == "header"]
        assert len(header_elements) >= 4  # Complete Guide, Introduction, Code Examples, Conclusion
        
        # Check header levels
        levels = [e["level"] for e in header_elements]
        assert 1 in levels  # H1
        assert 2 in levels  # H2
        assert 3 in levels  # H3

    def test_parse_empty_document(self):
        """Test parsing an empty document."""
        parser = DocumentParser()
        elements = parser.parse_document_structure("")
        
        # Should handle empty input gracefully
        assert isinstance(elements, list)

    def test_parse_whitespace_only_document(self):
        """Test parsing document with only whitespace."""
        content = "   \n\n  \t  \n\n   "
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Should handle whitespace-only input gracefully
        assert isinstance(elements, list)

    def test_parse_single_line_document(self):
        """Test parsing a single line document."""
        content = "# Single Header"
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        assert len(elements) >= 1
        header_elements = [e for e in elements if e["type"] == "header"]
        assert len(header_elements) >= 1
        assert "Single Header" in header_elements[0]["title"]

    def test_parse_document_structure_hierarchy(self):
        """Test that parser identifies proper section hierarchy."""
        content = """# Level 1

Content for level 1.

## Level 2A

Content for level 2A.

### Level 3

Content for level 3.

## Level 2B

Content for level 2B.

# Another Level 1

Content for another level 1.
"""
        
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Should have proper hierarchy
        header_elements = [e for e in elements if e["type"] == "header"]
        assert len(header_elements) >= 5
        
        # Check level structure
        levels = [e["level"] for e in header_elements]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels

    def test_parse_malformed_markdown(self):
        """Test parsing malformed or edge-case markdown."""
        content = """#Missing space after hash
##Also missing space
# Good header

```
Unclosed code block

Regular text
"""
        
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Should handle malformed content gracefully
        assert isinstance(elements, list)
        assert len(elements) > 0
        
        # Should identify the good header
        header_elements = [e for e in elements if e["type"] == "header"]
        assert len(header_elements) >= 1

    def test_parser_preserves_content(self):
        """Test that parser preserves original content in elements."""
        content = """# Title with **bold** and *italic*

Paragraph with [link](https://example.com) and ![image](img.png).

```python
# Code with comments
def func():
    return "string with special chars: éñüñøß"
```
"""
        
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Content should be preserved as-is
        all_content = "\n".join(e["text"] for e in elements)
        assert "**bold**" in all_content
        assert "*italic*" in all_content
        assert "[link]" in all_content
        assert "éñüñøß" in all_content

    def test_parser_performance_with_large_document(self):
        """Test parser performance with a large document."""
        # Create a large document
        large_content = []
        for i in range(50):  # Reduced for faster testing
            large_content.append(f"# Section {i}")
            large_content.append(f"Content for section {i} with some text.")
            large_content.append("")
            large_content.append(f"## Subsection {i}.1")
            large_content.append(f"More content for subsection {i}.1.")
            large_content.append("")
        
        content = "\n".join(large_content)
        
        parser = DocumentParser()
        elements = parser.parse_document_structure(content)
        
        # Should handle large documents
        assert len(elements) > 50
        header_elements = [e for e in elements if e["type"] == "header"]
        content_elements = [e for e in elements if e["type"] == "content"]
        assert len(header_elements) >= 50  # Should have many headers
        assert len(content_elements) >= 1   # Should have content


class TestHierarchyBuilder:
    """Test HierarchyBuilder class."""

    def test_build_section_breadcrumb(self):
        """Test building section breadcrumb."""
        # Create hierarchy
        root = Section(content="# Root Section\n\nRoot content.", level=1, type=SectionType.HEADER)
        child = Section(content="## Child Section\n\nChild content.", level=2, type=SectionType.HEADER)
        grandchild = Section(content="### Grandchild Section\n\nGrandchild content.", level=3, type=SectionType.HEADER)
        
        root.add_child(child)
        child.add_child(grandchild)
        
        breadcrumb = HierarchyBuilder.build_section_breadcrumb(grandchild)
        assert "Root Section" in breadcrumb
        assert "Child Section" in breadcrumb
        assert "Grandchild Section" in breadcrumb
        assert " > " in breadcrumb

    def test_get_section_path(self):
        """Test getting section path from structure."""
        structure = [
            {"type": "header", "level": 1, "title": "Root", "text": "# Root"},
            {"type": "content", "level": 0, "text": "Some content"},
            {"type": "header", "level": 2, "title": "Child", "text": "## Child"},
            {"type": "content", "level": 0, "text": "More content"},
            {"type": "header", "level": 3, "title": "Grandchild", "text": "### Grandchild"},
        ]
        
        grandchild_item = structure[4]  # The level 3 header
        
        path = HierarchyBuilder.get_section_path(grandchild_item, structure)
        
        assert "Root" in path
        assert "Child" in path
        assert len(path) == 2  # Root and Child should be in path

    def test_get_section_path_no_parents(self):
        """Test getting section path for root level section."""
        structure = [
            {"type": "header", "level": 1, "title": "Root", "text": "# Root"},
            {"type": "content", "level": 0, "text": "Some content"},
        ]
        
        root_item = structure[0]
        path = HierarchyBuilder.get_section_path(root_item, structure)
        
        assert len(path) == 0  # No parents for root level