"""Unit tests for PublicDocs connector content extraction functionality."""

import pytest

from qdrant_loader.connectors.publicdocs.config import (
    PublicDocsSourceConfig,
    SelectorsConfig,
)
from qdrant_loader.connectors.publicdocs.connector import PublicDocsConnector
from qdrant_loader.config.types import SourceType
from pydantic import HttpUrl


@pytest.fixture
def publicdocs_config() -> PublicDocsSourceConfig:
    """Create a test configuration."""
    return PublicDocsSourceConfig(
        source_type=SourceType.PUBLICDOCS,
        source="test_docs",
        base_url=HttpUrl("https://test.docs.com/"),
        version="1.0",
        content_type="html",
        path_pattern="*",
        exclude_paths=["blog/*"],
        selectors=SelectorsConfig(
            content="article, main, .content",
            remove=["nav", "header", "footer", ".sidebar"],
            code_blocks="pre code",
        ),
    )


@pytest.fixture
def custom_selectors_config() -> PublicDocsSourceConfig:
    """Create a test configuration with custom selectors."""
    return PublicDocsSourceConfig(
        source_type=SourceType.PUBLICDOCS,
        source="test_docs",
        base_url=HttpUrl("https://test.docs.com/"),
        version="1.0",
        content_type="html",
        path_pattern="*",
        exclude_paths=["blog/*"],
        selectors=SelectorsConfig(
            content=".custom-content",
            remove=[".remove-me", ".also-remove"],
            code_blocks=".code-example",
        ),
    )


class TestPublicDocsContentExtraction:
    """Test the content extraction functionality of PublicDocsConnector."""

    def test_extract_content_standard(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction with standard HTML structure."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_standard = """
        <html>
            <body>
                <article class="content">
                    <h1>Title</h1>
                    <p>Paragraph 1</p>
                    <p>Paragraph 2</p>
                </article>
            </body>
        </html>
        """
        
        content = connector._extract_content(html_standard)
        assert "Title" in content
        assert "Paragraph 1" in content
        assert "Paragraph 2" in content

    def test_extract_content_with_code_blocks(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction with code blocks."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_with_code = """
        <html>
            <body>
                <article class="content">
                    <h1>Title</h1>
                    <p>Text before code</p>
                    <pre><code>def test(): pass</code></pre>
                    <p>Text after code</p>
                </article>
            </body>
        </html>
        """
        
        content = connector._extract_content(html_with_code)
        assert "Text before code" in content
        assert "```" in content
        assert "def test(): pass" in content
        assert "Text after code" in content

    def test_extract_content_with_multiple_code_blocks(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction with multiple code blocks."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_with_multiple_code = """
        <html>
            <body>
                <article class="content">
                    <h1>Title</h1>
                    <p>First code example:</p>
                    <pre><code>def first(): pass</code></pre>
                    <p>Second code example:</p>
                    <pre><code>def second(): return True</code></pre>
                </article>
            </body>
        </html>
        """
        
        content = connector._extract_content(html_with_multiple_code)
        assert "First code example" in content
        assert "Second code example" in content
        # Opening and closing for each code block
        assert content.count("```") == 4
        assert "def first(): pass" in content
        assert "def second(): return True" in content

    def test_extract_content_with_elements_to_remove(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction with elements that should be removed."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_with_removable = """
        <html>
            <body>
                <article class="content">
                    <h1>Title</h1>
                    <p>Main content</p>
                    <nav>Navigation that should be removed</nav>
                    <footer>Footer that should be removed</footer>
                </article>
            </body>
        </html>
        """
        
        content = connector._extract_content(html_with_removable)
        assert "Title" in content
        assert "Main content" in content
        assert "Navigation that should be removed" not in content
        assert "Footer that should be removed" not in content

    def test_extract_content_with_custom_selectors(
        self, custom_selectors_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction with custom selectors."""
        connector = PublicDocsConnector(custom_selectors_config)
        
        html_with_custom_selectors = """
        <html>
            <body>
                <div class="custom-content">
                    <h1>Custom Title</h1>
                    <p>Custom content</p>
                    <div class="code-example">custom_function()</div>
                    <div class="remove-me">Should be removed</div>
                    <div class="also-remove">Should also be removed</div>
                </div>
            </body>
        </html>
        """
        
        content = connector._extract_content(html_with_custom_selectors)
        assert "Custom Title" in content
        assert "Custom content" in content
        assert "```" in content
        assert "custom_function()" in content
        assert "Should be removed" not in content
        assert "Should also be removed" not in content

    def test_extract_content_with_missing_selector(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction when the content selector doesn't match anything."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_no_selector_match = """
        <html>
            <body>
                <div class="not-content">
                    <p>This should not be found</p>
                </div>
            </body>
        </html>
        """
        
        content = connector._extract_content(html_no_selector_match)
        assert content == ""

    def test_extract_content_with_empty_html(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction with empty HTML."""
        connector = PublicDocsConnector(publicdocs_config)
        
        content = connector._extract_content("")
        assert content == ""

    def test_extract_content_with_malformed_html(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test content extraction with malformed HTML."""
        connector = PublicDocsConnector(publicdocs_config)
        
        malformed_html = """
        <html>
            <body>
                <article class="content">
                    <h1>Malformed HTML
                    <p>Content with unclosed tags
                    <pre><code>def unclosed(): pass
                </article>
            </body>
        """
        
        # Should still extract content despite malformed HTML
        content = connector._extract_content(malformed_html)
        assert "Malformed HTML" in content
        assert "Content with unclosed tags" in content
        assert "def unclosed(): pass" in content