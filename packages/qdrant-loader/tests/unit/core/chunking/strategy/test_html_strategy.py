"""Unit tests for HTML chunking strategy."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.config.types import SourceType
from qdrant_loader.core.chunking.strategy.html_strategy import (
    HTMLChunkingStrategy,
    SectionType,
)
from qdrant_loader.core.document import Document


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

    # Mock embedding config
    embedding_config = Mock()
    embedding_config.tokenizer = "cl100k_base"

    # Attach configs to global_config
    global_config.chunking = chunking_config
    global_config.semantic_analysis = semantic_analysis_config
    global_config.embedding = embedding_config

    # Attach global_config to settings
    settings.global_config = global_config

    return settings


@pytest.fixture
def html_strategy(mock_settings):
    """Create HTML chunking strategy for testing."""
    strategy = HTMLChunkingStrategy(mock_settings)
    return strategy


@pytest.fixture
def sample_html_document():
    """Create a sample HTML document for testing."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Document</title>
    </head>
    <body>
        <header>
            <h1>Main Title</h1>
            <nav>Navigation content</nav>
        </header>
        <main>
            <article>
                <h2>Section 1</h2>
                <p>This is the first paragraph of section 1. It contains some meaningful content that should be chunked appropriately.</p>
                <p>This is the second paragraph of section 1. It also contains meaningful content.</p>

                <section>
                    <h3>Subsection 1.1</h3>
                    <p>This is content in a subsection. It should be part of the same chunk as its parent section.</p>
                    <ul>
                        <li>List item 1</li>
                        <li>List item 2</li>
                        <li>List item 3</li>
                    </ul>
                </section>
            </article>

            <article>
                <h2>Section 2</h2>
                <p>This is the content of section 2. It should be in a separate chunk from section 1.</p>
                <blockquote>
                    <p>This is a quote that should be preserved in the chunk.</p>
                </blockquote>
                <pre><code>
def example_code():
    return "This is code content"
                </code></pre>
            </article>
        </main>
        <footer>
            <p>Footer content</p>
        </footer>
    </body>
    </html>
    """

    return Document(
        id="test-doc-1",
        content=html_content,
        content_type="html",
        source="test_source",
        source_type=SourceType.PUBLICDOCS,
        title="Test HTML Document",
        url="file://test.html",
        metadata={"file_name": "test.html"},
    )


class TestHTMLChunkingStrategy:
    """Test cases for HTML chunking strategy."""

    def test_initialization(self, mock_settings):
        """Test that the HTML strategy initializes correctly."""
        strategy = HTMLChunkingStrategy(mock_settings)

        assert strategy.section_elements == {
            "article",
            "section",
            "main",
            "header",
            "footer",
            "nav",
            "aside",
        }
        assert strategy.heading_elements == {"h1", "h2", "h3", "h4", "h5", "h6"}
        assert "div" in strategy.block_elements
        assert "p" in strategy.block_elements

    def test_identify_section_type(self, html_strategy):
        """Test section type identification."""
        from bs4 import BeautifulSoup

        # Test different HTML elements
        soup = BeautifulSoup("<h1>Title</h1>", "html.parser")
        h1_tag = soup.find("h1")
        assert html_strategy._identify_section_type(h1_tag) == SectionType.HEADER

        soup = BeautifulSoup("<article>Content</article>", "html.parser")
        article_tag = soup.find("article")
        assert html_strategy._identify_section_type(article_tag) == SectionType.ARTICLE

        soup = BeautifulSoup("<p>Paragraph</p>", "html.parser")
        p_tag = soup.find("p")
        assert html_strategy._identify_section_type(p_tag) == SectionType.PARAGRAPH

    def test_get_heading_level(self, html_strategy):
        """Test heading level extraction."""
        from bs4 import BeautifulSoup

        for i in range(1, 7):
            soup = BeautifulSoup(f"<h{i}>Heading</h{i}>", "html.parser")
            heading_tag = soup.find(f"h{i}")
            assert html_strategy._get_heading_level(heading_tag) == i

        # Test non-heading element
        soup = BeautifulSoup("<p>Not a heading</p>", "html.parser")
        p_tag = soup.find("p")
        assert html_strategy._get_heading_level(p_tag) == 0

    def test_extract_title_from_content(self, html_strategy):
        """Test title extraction from content."""
        # Test short content
        title = html_strategy._extract_title_from_content("Short title")
        assert title == "Short title"

        # Test content with multiple lines - should take first line
        title = html_strategy._extract_title_from_content(
            "This is a sentence. This is another."
        )
        assert title == "This is a sentence. This is another."

        # Test long content - should truncate at 100 characters
        long_content = "This is a very long piece of content that exceeds one hundred characters and should be truncated"
        title = html_strategy._extract_title_from_content(long_content)
        assert len(title) <= 100

    def test_extract_section_title(self, html_strategy):
        """Test section title extraction from HTML chunks."""
        # Test with heading
        html_with_heading = "<div><h2>Section Title</h2><p>Content</p></div>"
        title = html_strategy._extract_section_title(html_with_heading)
        assert title == "Section Title"

        # Test with no heading - should extract from text content
        html_with_no_heading = "<div><p>Content text here</p></div>"
        title = html_strategy._extract_section_title(html_with_no_heading)
        assert title == "Content text here"

        # Test with semantic element
        html_with_article = "<article><p>Article content here</p></article>"
        title = html_strategy._extract_section_title(html_with_article)
        assert title == "Article content here"

    def test_parse_html_structure(self, html_strategy):
        """Test HTML structure parsing."""
        simple_html = """
        <article>
            <h2>Title</h2>
            <p>Paragraph content</p>
        </article>
        """

        structure = html_strategy._parse_html_structure(simple_html)

        # Should have at least one section element
        assert len(structure) > 0

        # Check that we have elements with section_type
        section_elements = [elem for elem in structure if elem.get("section_type")]
        assert len(section_elements) > 0

    def test_chunk_document(self, html_strategy, sample_html_document):
        """Test document chunking with HTML content."""
        chunks = html_strategy.chunk_document(sample_html_document)

        # Should produce multiple chunks
        assert len(chunks) > 1

        # Each chunk should be a Document instance
        for chunk in chunks:
            assert isinstance(chunk, Document)
            assert chunk.content_type == "html"
            assert chunk.source == sample_html_document.source
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata
            assert "parent_document_id" in chunk.metadata

    def test_chunk_document_with_empty_content(self, html_strategy):
        """Test chunking with empty HTML content."""
        empty_doc = Document(
            id="empty-doc",
            content="",
            content_type="html",
            source="test",
            source_type=SourceType.PUBLICDOCS,
            title="Empty Document",
            url="file://empty.html",
            metadata={},
        )

        chunks = html_strategy.chunk_document(empty_doc)

        # Empty content should result in no chunks (skipped empty chunks)
        assert len(chunks) == 0

    def test_fallback_chunking(self, html_strategy, sample_html_document):
        """Test fallback chunking mechanism."""
        chunks = html_strategy._fallback_chunking(sample_html_document)

        # Should produce at least one chunk
        assert len(chunks) >= 1

        # Each chunk should be a Document instance
        for chunk in chunks:
            assert isinstance(chunk, Document)
            assert "parent_document_id" in chunk.metadata

    def test_merge_small_sections(self, html_strategy):
        """Test merging of small sections."""
        sections = [
            {
                "content": "<p>Small content</p>",
                "text_content": "Small content",
                "tag_name": "p",
                "level": 0,
            },
            {
                "content": "<p>Another small content</p>",
                "text_content": "Another small content",
                "tag_name": "p",
                "level": 0,
            },
        ]

        merged = html_strategy._merge_small_sections(sections)

        # Should merge small sections
        assert len(merged) <= len(sections)

    def test_shutdown(self, html_strategy):
        """Test strategy shutdown."""
        # Should not raise any exceptions
        html_strategy.shutdown()

        # Executor should be None after shutdown
        assert html_strategy._executor is None
