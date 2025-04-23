"""Unit tests for PublicDocs connector title extraction functionality."""

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


class TestPublicDocsTitleExtraction:
    """Test the title extraction functionality of PublicDocsConnector."""

    def test_extract_title_from_title_tag(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test title extraction from HTML title tag."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_with_title = """
        <html>
            <head>
                <title>Test Title</title>
            </head>
            <body>
                <div class="content">
                    <p>Content</p>
                </div>
            </body>
        </html>
        """
        
        title = connector._extract_title(html_with_title)
        assert title == "Test Title"

    def test_extract_title_from_h1(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test title extraction from H1 when title tag is missing."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_with_h1 = """
        <html>
            <body>
                <div class="content">
                    <h1>H1 Title</h1>
                    <p>Content</p>
                </div>
            </body>
        </html>
        """
        
        title = connector._extract_title(html_with_h1)
        assert title == "H1 Title"

    def test_extract_title_from_other_heading(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test title extraction from other heading elements when title and h1 are missing."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_with_h2 = """
        <html>
            <body>
                <div class="content">
                    <h2>H2 Title</h2>
                    <p>Content</p>
                </div>
            </body>
        </html>
        """
        
        title = connector._extract_title(html_with_h2)
        assert title == "H2 Title"

    def test_extract_title_fallback(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test title extraction fallback to default when no title elements are found."""
        connector = PublicDocsConnector(publicdocs_config)
        
        html_no_title = """
        <html>
            <body>
                <div class="content">
                    <p>Content only</p>
                </div>
            </body>
        </html>
        """
        
        title = connector._extract_title(html_no_title)
        assert title == "Untitled Document"

    def test_extract_title_with_empty_html(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test title extraction with empty HTML."""
        connector = PublicDocsConnector(publicdocs_config)
        
        title = connector._extract_title("")
        assert title == "Untitled Document"

    def test_extract_title_with_malformed_html(
        self, publicdocs_config: PublicDocsSourceConfig
    ) -> None:
        """Test title extraction with malformed HTML."""
        connector = PublicDocsConnector(publicdocs_config)
        
        malformed_html = """
        <html>
            <head>
                <title>Malformed Title
            </head>
            <body>
                <div class="content">
                    <h1>Malformed H1
                    <p>Content</p>
                </div>
            </body>
        """
        
        # Should still extract title despite malformed HTML
        title = connector._extract_title(malformed_html)
        assert title in [
            "Malformed Title",
            "Malformed H1",
            "Untitled Document"
        ]