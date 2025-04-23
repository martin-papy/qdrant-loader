"""Unit tests for Public Docs connector."""

from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import HttpUrl

import pytest
from aiohttp import (
    ClientResponseError,
    ClientConnectionError,
)

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig, SelectorsConfig
from qdrant_loader.connectors.publicdocs.connector import PublicDocsConnector
from qdrant_loader.connectors.exceptions import (
    DocumentProcessingError,
    HTTPRequestError,
)

HTML_CONTENT = """
    <html>
        <body>
            <article class="content">
                <h1>Test Page</h1>
                <div class="article-content">
                    <p>Test content</p>
                    <pre><code>def test():
    pass</code></pre>
                </div>
                <a href="/docs/page1">Link 1</a>
                <a href="/blog/post1">Blog Post</a>
                <a href="https://external.com">External Link</a>
            </article>
            <nav>Should be removed</nav>
            <footer>Should be removed</footer>
        </body>
    </html>
"""

LINKED_PAGE_CONTENT = """
    <html>
        <body>
            <article class="content">
                <h1>Page 1</h1>
                <div class="article-content">
                    <p>Page 1 content</p>
                </div>
            </article>
        </body>
    </html>
"""


@pytest.fixture
def mock_html() -> str:
    return HTML_CONTENT


@pytest.fixture
def publicdocs_config() -> PublicDocsSourceConfig:
    """Create a test configuration."""
    return PublicDocsSourceConfig(
        source_type=SourceType.PUBLICDOCS,
        source="test_docs",
        base_url=HttpUrl("https://test.docs.com/"),
        version="1.0",
        content_type="html",
        path_pattern="*",  # Allow all paths except excluded ones
        exclude_paths=["blog/*"],
        selectors=SelectorsConfig(
            content="article, main, .content",
            remove=["nav", "header", "footer", ".sidebar"],
            code_blocks="pre code",
        ),
    )


@pytest.fixture
def mock_response() -> AsyncMock:
    """Mock HTTP response."""
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value=HTML_CONTENT)
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_session(mock_response: AsyncMock) -> AsyncMock:
    """Mock aiohttp client session."""
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    session.get = AsyncMock(return_value=mock_response)
    session.close = AsyncMock()
    return session


@pytest.fixture
async def connector(publicdocs_config: PublicDocsSourceConfig) -> PublicDocsConnector:
    """Create a test connector instance."""
    connector = PublicDocsConnector(publicdocs_config)
    connector.url_queue.append(str(publicdocs_config.base_url))
    return connector


class TestPublicDocsConnector:
    """Test the PublicDocsConnector class."""

    @pytest.mark.asyncio
    async def test_initialization(self, publicdocs_config: PublicDocsSourceConfig) -> None:
        """Test connector initialization."""
        connector = PublicDocsConnector(publicdocs_config)
        assert connector.config == publicdocs_config
        assert connector.base_url == str(publicdocs_config.base_url)
        assert connector.version == publicdocs_config.version

    @pytest.mark.asyncio
    async def test_process_url(
        self, publicdocs_config: PublicDocsSourceConfig, mock_html: str
    ) -> None:
        """Test page processing."""
        connector = PublicDocsConnector(publicdocs_config)
        links = connector._extract_links(mock_html, str(publicdocs_config.base_url))

        # Test that relative URLs are converted to absolute
        assert any(link.startswith(str(publicdocs_config.base_url)) for link in links)
        # Test that we get the expected number of links that match our base URL
        assert (
            len([link for link in links if link.startswith(str(publicdocs_config.base_url))]) == 2
        )

    @pytest.mark.asyncio
    async def test_link_extraction(
        self, publicdocs_config: PublicDocsSourceConfig, mock_html: str
    ) -> None:
        """Test link extraction."""
        connector = PublicDocsConnector(publicdocs_config)
        links = connector._extract_links(mock_html, str(publicdocs_config.base_url))

        # Test that we get the expected number of links that match our base URL
        assert (
            len([link for link in links if link.startswith(str(publicdocs_config.base_url))]) == 2
        )
        # Test that external URLs are not included (as per connector implementation)
        assert not any(link.startswith("https://docs.example.com") for link in links)

    @pytest.mark.asyncio
    async def test_error_handling(self, publicdocs_config: PublicDocsSourceConfig) -> None:
        """Test error handling."""
        connector = PublicDocsConnector(publicdocs_config)
        with pytest.raises(RuntimeError, match="Connector not initialized"):
            await connector.get_documents()

    @pytest.mark.asyncio
    async def test_path_filtering(
        self, publicdocs_config: PublicDocsSourceConfig, mock_html: str
    ) -> None:
        """Test path filtering."""
        connector = PublicDocsConnector(publicdocs_config)
        base_url = str(publicdocs_config.base_url)
        links = connector._extract_links(mock_html, base_url)

        # Test that excluded paths are filtered out
        filtered_links = [link for link in links if connector._should_process_url(link)]
        assert not any("/blog/" in link for link in filtered_links)
        # Test that we get only the docs link after filtering
        assert len(filtered_links) == 1
        assert filtered_links[0] == f"{base_url}docs/page1"

    @pytest.mark.asyncio
    async def test_get_documents(
        self,
        publicdocs_config: PublicDocsSourceConfig,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting documents from the PublicDocs connector.

        This test verifies:
        1. Basic document retrieval
        2. Document content and metadata
        3. URL processing and filtering
        4. Error handling
        """
        connector = PublicDocsConnector(publicdocs_config)
        base_url = str(publicdocs_config.base_url)

        # Create mock responses for both the base URL and the linked page
        base_response = AsyncMock()
        base_response.status = 200
        base_response.text = AsyncMock(return_value=HTML_CONTENT)
        base_response.raise_for_status = MagicMock()  # Use regular Mock for synchronous method

        page_response = AsyncMock()
        page_response.status = 200
        page_response.text = AsyncMock(return_value=LINKED_PAGE_CONTENT)
        page_response.raise_for_status = MagicMock()  # Use regular Mock for synchronous method

        # Set up the mock session to return different responses based on URL
        async def mock_get(url: str, **kwargs) -> AsyncMock:
            if url == base_url:
                return base_response
            elif url == f"{base_url}docs/page1":
                return page_response
            raise ValueError(f"Unexpected URL: {url}")

        mock_session.get = AsyncMock(side_effect=mock_get)

        # Mock _get_all_pages to return our test URLs
        async def mock_get_all_pages() -> list[str]:
            return [base_url, f"{base_url}docs/page1"]

        # Initialize the connector with our mock session and mock _get_all_pages
        with (
            patch("aiohttp.ClientSession", return_value=mock_session),
            patch.object(connector, "_get_all_pages", side_effect=mock_get_all_pages),
        ):
            async with connector:
                documents = await connector.get_documents()

        # Verify the results
        assert len(documents) == 2  # We should get both the base page and the linked page

        # Verify base page document
        base_doc = next(doc for doc in documents if doc.url == base_url)
        assert base_doc.title == "Test Page"
        assert "Test content" in base_doc.content
        assert base_doc.metadata["version"] == publicdocs_config.version

        # Verify linked page document
        linked_doc = next(doc for doc in documents if doc.url == f"{base_url}docs/page1")
        assert linked_doc.title == "Page 1"
        assert "Page 1 content" in linked_doc.content
        assert linked_doc.metadata["version"] == publicdocs_config.version

        # Verify that blog post was not included (due to exclude_paths)
        assert not any(doc.url == f"{base_url}blog/post1" for doc in documents)

    @pytest.mark.asyncio
    async def test_get_documents_error_handling(
        self,
        publicdocs_config: PublicDocsSourceConfig,
        mock_session: AsyncMock,
    ) -> None:
        """Test error handling in document retrieval.

        This test verifies:
        1. HTTP error handling during _process_page
        2. Network error handling during _process_page
        3. Content processing error handling
        4. Error recovery (continuing despite errors)
        """
        # Test HTTP error in _process_page
        connector = PublicDocsConnector(publicdocs_config)
        base_url = str(publicdocs_config.base_url)
        error_url = f"{base_url}error-page"
        valid_url = f"{base_url}valid-page"

        # Create mixed responses - one that succeeds and one that fails with 404
        error_response = AsyncMock()
        error_response.status = 404
        error_response.raise_for_status = MagicMock(
            side_effect=ClientResponseError(
                request_info=MagicMock(), history=(), status=404, message="Not Found", headers=None
            )
        )

        valid_response = AsyncMock()
        valid_response.status = 200
        valid_response.text = AsyncMock(return_value=LINKED_PAGE_CONTENT)
        valid_response.raise_for_status = MagicMock()  # No error

        # Create session that returns different responses based on URL
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None

        async def mock_get(url: str, **kwargs) -> AsyncMock:
            if url == error_url:
                return error_response
            elif url == valid_url:
                return valid_response
            raise ValueError(f"Unexpected URL: {url}")

        session.get = AsyncMock(side_effect=mock_get)
        session.close = AsyncMock()

        # Test direct call to _process_page to verify it raises expected exceptions
        with patch("aiohttp.ClientSession", return_value=session):
            async with connector:
                # First verify _process_page raises HTTPRequestError when it fails
                with pytest.raises(HTTPRequestError):
                    await connector._process_page(error_url)

                # Verify _process_page works with valid URL
                content, title = await connector._process_page(valid_url)
                assert content is not None
                assert title == "Page 1"

                # Now test get_documents with a mix of valid and error URLs
                # It should handle errors and return only valid documents
                async def mock_get_all_pages() -> list[str]:
                    return [valid_url, error_url]

                with patch.object(connector, "_get_all_pages", side_effect=mock_get_all_pages):
                    # get_documents should not raise an exception but should log the error
                    documents = await connector.get_documents()

                    # We should get only the valid document
                    assert len(documents) == 1
                    assert documents[0].url == valid_url
                    assert documents[0].title == "Page 1"
                    assert "Page 1 content" in documents[0].content

        # Test network error in _process_page
        connector = PublicDocsConnector(publicdocs_config)

        # Create a session that raises a connection error
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session.get = AsyncMock(side_effect=ClientConnectionError("Connection failed"))
        session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=session):
            async with connector:
                # Verify _process_page raises HTTPRequestError
                with pytest.raises(HTTPRequestError):
                    await connector._process_page(base_url)

        # Test content processing error
        connector = PublicDocsConnector(publicdocs_config)

        # Create a response with invalid HTML
        invalid_response = AsyncMock()
        invalid_response.status = 200
        invalid_response.text = AsyncMock(return_value="<invalid>html</invalid>")
        invalid_response.raise_for_status = MagicMock()

        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session.get = AsyncMock(return_value=invalid_response)
        session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=session):
            async with connector:
                # For content processing error, we'll mock _extract_content to raise an exception
                with patch.object(
                    connector, "_extract_content", side_effect=Exception("Content processing error")
                ):
                    # Direct call to _process_page should raise DocumentProcessingError
                    with pytest.raises(DocumentProcessingError):
                        await connector._process_page(base_url)

    @pytest.mark.asyncio
    async def test_get_documents_with_version(
        self,
        publicdocs_config: PublicDocsSourceConfig,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting documents with version metadata."""
        config_with_version = publicdocs_config.model_copy(update={"version": "1.0.0"})
        connector = PublicDocsConnector(config_with_version)
        base_url = str(config_with_version.base_url)
        connector.url_queue.append(base_url)

        # Create mock responses for both the base URL and the linked page
        base_response = AsyncMock()
        base_response.status = 200
        base_response.text = AsyncMock(return_value=HTML_CONTENT)
        base_response.raise_for_status = MagicMock()

        page_response = AsyncMock()
        page_response.status = 200
        page_response.text = AsyncMock(return_value=LINKED_PAGE_CONTENT)
        page_response.raise_for_status = MagicMock()

        # Configure session to return different responses based on URL
        async def mock_get(url: str, **kwargs) -> AsyncMock:
            if url == base_url:
                return base_response
            elif url == f"{base_url}docs/page1":
                return page_response
            raise Exception(f"Unexpected URL: {url}")

        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session.get = AsyncMock(side_effect=mock_get)
        session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=session):
            async with connector:
                # Mock the client session to use our mock session
                connector._client = session
                documents = await connector.get_documents()
                assert len(documents) == 2
                assert documents[0].title == "Test Page"
                assert documents[1].title == "Page 1"
                assert all(doc.metadata.get("version") == "1.0.0" for doc in documents)
