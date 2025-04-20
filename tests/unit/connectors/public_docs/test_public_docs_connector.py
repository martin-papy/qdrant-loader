from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import HttpUrl

from qdrant_loader.config import PublicDocsSourceConfig, SelectorsConfig
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.publicdocs import PublicDocsConnector
from qdrant_loader.core.state.state_manager import StateManager


class AsyncContextManagerMock:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture
def mock_config():
    return PublicDocsSourceConfig(
        source_type=SourceType.PUBLICDOCS,
        source="test",
        base_url=HttpUrl("https://docs.example.com"),
        version="1.0",
        content_type="html",
        selectors=SelectorsConfig(
            content="article.main-content",
            remove=["nav", "header", "footer", ".sidebar"],
            code_blocks="pre code",
        ),
    )


@pytest.fixture
def mock_html():
    return """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <nav>Navigation</nav>
            <article class="main-content">
                <h1>Main Content</h1>
                <p>This is the main content.</p>
                <pre><code>print("Hello World")</code></pre>
            </article>
            <footer>Footer</footer>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
            <a href="https://external.com">External</a>
        </body>
    </html>
    """


@pytest.fixture
def mock_state_manager():
    manager = Mock(spec=StateManager)
    manager.get_last_ingestion = AsyncMock(
        return_value=Mock(last_successful_ingestion=datetime.now(UTC))
    )
    manager.get_document_states = AsyncMock(return_value=[])
    manager.update_document_state = AsyncMock()
    manager.mark_document_deleted = AsyncMock()
    manager.update_ingestion = AsyncMock()
    return manager


@pytest.fixture
def mock_session_and_response(mock_html):
    """Fixture that provides a mock aiohttp session and response setup."""
    # Create mock response
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value=mock_html)
    mock_response.raise_for_status = AsyncMock()
    mock_response.status = 200

    # Create mock session
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()

    # Set up the get method to return an async context manager
    mock_context = AsyncContextManagerMock(mock_response)
    mock_session.get = Mock(return_value=mock_context)

    # Ensure the text() method returns the HTML string directly
    mock_response.text.return_value = mock_html

    return mock_session, mock_response


def test_should_process_url(mock_config):
    connector = PublicDocsConnector(mock_config)

    # Test base URL
    assert connector._should_process_url("https://docs.example.com/page") is True

    # Test excluded path
    mock_config.exclude_paths = ["/page1"]
    assert connector._should_process_url("https://docs.example.com/page1") is False

    # Test path pattern
    mock_config.path_pattern = r"/docs/1\.0/.*"
    assert connector._should_process_url("https://docs.example.com/docs/1.0/page") is True
    assert connector._should_process_url("https://docs.example.com/other/page") is False

    # Test external URL
    assert connector._should_process_url("https://other.com/page") is False


def test_extract_links(mock_config, mock_html):
    connector = PublicDocsConnector(mock_config)
    links = connector._extract_links(mock_html, "https://docs.example.com")

    assert len(links) == 2
    assert "https://docs.example.com/page1" in links
    assert "https://docs.example.com/page2" in links
    assert "https://external.com" not in links


def test_extract_content(mock_config, mock_html):
    connector = PublicDocsConnector(mock_config)
    content = connector._extract_content(mock_html)

    assert "Main Content" in content
    assert "Navigation" not in content
    assert "Footer" not in content
    assert "```" in content
    assert 'print("Hello World")' in content


@pytest.mark.asyncio
async def test_process_page(mock_config, mock_session_and_response):
    mock_session, _ = mock_session_and_response

    with patch("aiohttp.ClientSession", return_value=mock_session):
        connector = PublicDocsConnector(mock_config)
        async with connector:
            content, title = await connector._process_page("https://docs.example.com/page")

            assert content is not None
            assert "Main Content" in content
            assert "Navigation" not in content
            assert "Footer" not in content
            assert title == "Test Page"


@pytest.mark.asyncio
async def test_get_documentation(mock_config, mock_session_and_response):
    mock_session, _ = mock_session_and_response

    with patch("aiohttp.ClientSession", return_value=mock_session):
        connector = PublicDocsConnector(mock_config)
        async with connector:
            documents = await connector.get_documentation()

            # We expect 3 documents: base URL, page1, and page2
            assert len(documents) == 3

            # Check base URL document
            base_doc = next(doc for doc in documents if doc.url == "https://docs.example.com/")
            assert "Main Content" in base_doc.content
            assert base_doc.metadata.get("title") == "Test Page"

            # Check page1 document
            page1_doc = next(
                doc for doc in documents if doc.url == "https://docs.example.com/page1"
            )
            assert "Main Content" in page1_doc.content
            assert page1_doc.metadata.get("title") == "Test Page"

            # Check page2 document
            page2_doc = next(
                doc for doc in documents if doc.url == "https://docs.example.com/page2"
            )
            assert "Main Content" in page2_doc.content
            assert page2_doc.metadata.get("title") == "Test Page"
