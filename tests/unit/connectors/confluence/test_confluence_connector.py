"""Unit tests for the Confluence connector."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from pydantic import HttpUrl
import logging

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
from qdrant_loader.connectors.confluence.connector import ConfluenceConnector
from qdrant_loader.core.document import Document


@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables."""
    with patch.dict(
        os.environ,
        {
            "CONFLUENCE_TOKEN": "test-token",
            "CONFLUENCE_EMAIL": "test@example.com",
        },
    ):
        yield


@pytest.fixture
def config():
    """Create a test configuration."""
    return ConfluenceSpaceConfig(
        source="test-confluence",
        source_type=SourceType.CONFLUENCE,
        base_url=HttpUrl("https://test.atlassian.net"),
        space_key="TEST",
        content_types=["page", "blogpost"],
        include_labels=["include-test"],
        exclude_labels=["exclude-test"],
        token="test-token",
        email="test@example.com",
    )


@pytest.fixture
def connector(config, mock_env_vars):
    """Create a test connector instance."""
    return ConfluenceConnector(config)


@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests."""
    from qdrant_loader.utils.logging import LoggingConfig

    LoggingConfig.setup(level="ERROR")
    yield


class TestConfluenceConnector:
    """Test suite for the ConfluenceConnector class."""

    @pytest.mark.asyncio
    async def test_initialization(self, config, mock_env_vars):
        """Test connector initialization."""
        connector = ConfluenceConnector(config)
        assert connector.config == config
        assert connector.base_url == config.base_url
        assert connector.token == "test-token"
        assert connector.email == "test@example.com"
        assert connector.session.auth is not None

    @pytest.mark.asyncio
    async def test_initialization_missing_env_vars(self, config):
        """Test initialization with missing environment variables."""
        config_without_auth = ConfluenceSpaceConfig(
            source="test-confluence",
            source_type=SourceType.CONFLUENCE,
            base_url=HttpUrl("https://test.atlassian.net"),
            space_key="TEST",
            content_types=["page", "blogpost"],
            include_labels=["include-test"],
            exclude_labels=["exclude-test"],
            token=None,
            email=None,
        )
        with patch.dict(os.environ, {}, clear=True):  # Clear all environment variables
            with pytest.raises(
                ValueError, match="CONFLUENCE_TOKEN environment variable is not set"
            ):
                ConfluenceConnector(config_without_auth)

    @pytest.mark.asyncio
    async def test_api_url_construction(self, connector):
        """Test API URL construction."""
        endpoint = "content/search"
        expected_url = f"{connector.base_url}/rest/api/{endpoint}"
        assert connector._get_api_url(endpoint) == expected_url

    @pytest.mark.asyncio
    async def test_make_request_success(self, connector):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None

        with patch("requests.Session.request", return_value=mock_response):
            result = await connector._make_request("GET", "content/search")
            assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_make_request_failure(self, connector):
        """Test failed API request."""
        with patch(
            "requests.Session.request",
            side_effect=requests.exceptions.RequestException("API Error"),
        ):
            with pytest.raises(requests.exceptions.RequestException, match="API Error"):
                await connector._make_request("GET", "content/search")

    @pytest.mark.asyncio
    async def test_get_space_content(self, connector):
        """Test fetching space content."""
        mock_response = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "Test content"}},
                }
            ]
        }

        with patch.object(
            connector, "_make_request", AsyncMock(return_value=mock_response)
        ) as mock_request:
            result = await connector._get_space_content()
            assert result == mock_response
            mock_request.assert_called_once()

    def test_should_process_content(self, connector):
        """Test content processing decision based on labels."""
        # Test with include labels
        content_with_include = {"metadata": {"labels": {"results": [{"name": "include-test"}]}}}
        assert connector._should_process_content(content_with_include) is True

        # Test with exclude labels
        content_with_exclude = {"metadata": {"labels": {"results": [{"name": "exclude-test"}]}}}
        assert connector._should_process_content(content_with_exclude) is False

        # Test with no matching labels and no include labels specified
        connector.config.include_labels = []
        content_no_labels = {"metadata": {"labels": {"results": []}}}
        assert connector._should_process_content(content_no_labels) is True

    def test_clean_html(self, connector):
        """Test HTML cleaning functionality."""
        html = "<p>Test <b>content</b> with <i>HTML</i> tags &amp; special chars</p>"
        expected = "Test content with HTML tags and special chars"
        assert connector._clean_html(html).strip() == expected

    @pytest.mark.asyncio
    async def test_get_documents(self, connector):
        """Test document retrieval and processing."""
        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "Test content"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 1
            assert isinstance(documents[0], Document)
            assert documents[0].title == "Test Page"
            assert documents[0].content == "Test content"
            assert documents[0].source_type == SourceType.CONFLUENCE

    @pytest.mark.asyncio
    async def test_change_tracking_version_comparison(self, connector):
        """Test version comparison for change tracking."""
        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page 1",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content 1</p>"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                },
                {
                    "id": "456",
                    "title": "Test Page 2",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content 2</p>"}},
                    "version": {"number": 2, "when": "2024-01-02T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-02T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                },
            ],
            "_links": {},
        }

        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 2
            # Verify metadata instead of direct ID comparison
            assert documents[0].metadata["id"] == "123"
            assert documents[1].metadata["id"] == "456"
            assert documents[0].metadata["version"] == 1
            assert documents[1].metadata["version"] == 2

    @pytest.mark.asyncio
    async def test_change_tracking_missing_version(self, connector):
        """Test handling of content with missing version information."""
        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content</p>"}},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                    },
                    "version": {"when": "2024-01-01T00:00:00Z"},
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 1
            # Verify metadata instead of direct ID comparison
            assert documents[0].metadata["id"] == "123"
            assert documents[0].metadata["version"] == 1  # Default version when missing

    @pytest.mark.asyncio
    async def test_change_tracking_invalid_version(self, connector):
        """Test handling of content with invalid version information."""
        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content</p>"}},
                    "version": {"number": "invalid", "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 1
            # Verify metadata instead of direct ID comparison
            assert documents[0].metadata["id"] == "123"
            # The connector preserves the invalid version as a string
            assert documents[0].metadata["version"] == "invalid"

    @pytest.mark.asyncio
    async def test_pagination_multiple_pages(self, connector):
        """Test handling of multiple pages of results."""
        mock_content_page1 = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page 1",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content 1</p>"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {"next": "/rest/api/content?cursor=next_cursor"},
        }

        mock_content_page2 = {
            "results": [
                {
                    "id": "456",
                    "title": "Test Page 2",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content 2</p>"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        with patch.object(
            connector,
            "_get_space_content",
            AsyncMock(side_effect=[mock_content_page1, mock_content_page2]),
        ):
            documents = await connector.get_documents()
            assert len(documents) == 2
            # Verify metadata instead of direct ID comparison
            assert documents[0].metadata["id"] == "123"
            assert documents[1].metadata["id"] == "456"

    @pytest.mark.asyncio
    async def test_pagination_invalid_cursor(self, connector):
        """Test handling of invalid cursor in pagination."""
        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content</p>"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {"next": "invalid-cursor"},
        }

        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 1
            # Verify metadata instead of direct ID comparison
            assert documents[0].metadata["id"] == "123"

    @pytest.mark.asyncio
    async def test_pagination_missing_next_link(self, connector):
        """Test handling of missing next link in pagination."""
        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content</p>"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 1
            # Verify metadata instead of direct ID comparison
            assert documents[0].metadata["id"] == "123"

    @pytest.mark.asyncio
    async def test_network_error_handling(self, connector):
        """Test handling of network errors during API requests."""
        with patch.object(
            connector,
            "_make_request",
            side_effect=requests.exceptions.RequestException("Network error"),
        ):
            with pytest.raises(requests.exceptions.RequestException, match="Network error"):
                await connector.get_documents()

    @pytest.mark.asyncio
    async def test_invalid_response_format(self, connector):
        """Test handling of invalid response format from API."""
        invalid_response = {
            "invalid_key": "invalid_value",  # Missing required 'results' key
        }

        # Configure connector to process all content
        connector.config.include_labels = []
        connector.config.exclude_labels = []

        with patch.object(
            connector, "_get_space_content", AsyncMock(return_value=invalid_response)
        ):
            documents = await connector.get_documents()
            assert len(documents) == 0

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, connector):
        """Test handling of content with missing required fields."""
        mock_content = {
            "results": [
                {
                    # Missing id
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content</p>"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 0  # Content with missing fields should be skipped

    @pytest.mark.asyncio
    async def test_malformed_content(self, connector):
        """Test handling of malformed content."""
        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    # Malformed body structure
                    "body": "Invalid body structure",
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            documents = await connector.get_documents()
            assert len(documents) == 0  # Malformed content should be skipped

    @pytest.mark.asyncio
    async def test_error_during_content_processing(self, connector):
        """Test handling of errors during content processing."""
        mock_content = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "type": "page",
                    "space": {"key": "TEST"},
                    "body": {"storage": {"value": "<p>Test content</p>"}},
                    "version": {"number": 1, "when": "2024-01-01T00:00:00Z"},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-01-01T00:00:00Z",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                    },
                    "metadata": {"labels": {"results": []}},
                    "children": {"comment": {"results": []}},
                }
            ],
            "_links": {},
        }

        def process_content_error(*args, **kwargs):
            raise Exception("Error processing content")

        with patch.object(connector, "_get_space_content", AsyncMock(return_value=mock_content)):
            with patch.object(connector, "_process_content", side_effect=process_content_error):
                documents = await connector.get_documents()
                assert len(documents) == 0  # Content with processing errors should be skipped
