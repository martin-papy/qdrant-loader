"""Unit tests for the SharePoint connector."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from qdrant_loader.connectors.sharepoint.config import (
    SharePointConfig,
    SharePointAuthMethod,
)
from qdrant_loader.connectors.sharepoint.connector import SharePointConnector
from qdrant_loader.connectors.sharepoint.auth import SharePointAuthError


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create a test SharePoint configuration."""
    return SharePointConfig(
        source="test-sharepoint",
        source_type="sharepoint",
        base_url="https://company.sharepoint.com",
        site_url="https://company.sharepoint.com/sites/test-site",
        relative_url="/sites/test-site",
        auth_method=SharePointAuthMethod.CLIENT_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="client-app-id",
        client_secret="client-secret-value",
        document_libraries=["Documents"],
        file_types=["pdf", "docx", "txt"],
        max_file_size=10485760,  # 10MB
        exclude_paths=["archive/", "temp/"],
    )


@pytest.fixture
def mock_config_all_libraries():
    """Create config without document_libraries filter."""
    return SharePointConfig(
        source="test-sharepoint",
        source_type="sharepoint",
        base_url="https://company.sharepoint.com",
        site_url="https://company.sharepoint.com/sites/test-site",
        relative_url="/sites/test-site",
        auth_method=SharePointAuthMethod.CLIENT_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="client-app-id",
        client_secret="client-secret-value",
        document_libraries=[],  # Empty = all libraries
        file_types=[],  # Empty = all files
    )


@pytest.fixture
def mock_auth_functions():
    """Mock authentication functions from auth module."""
    with patch(
        "qdrant_loader.connectors.sharepoint.connector.create_graph_client"
    ) as mock_create, patch(
        "qdrant_loader.connectors.sharepoint.connector.validate_connection"
    ) as mock_validate:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        mock_validate.return_value = {
            "display_name": "Test Site",
            "web_url": "https://company.sharepoint.com/sites/test",
        }
        yield {
            "create_graph_client": mock_create,
            "validate_connection": mock_validate,
            "client": mock_client,
        }


@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests."""
    from qdrant_loader.utils.logging import LoggingConfig

    LoggingConfig.setup(level="ERROR")
    yield


# =============================================================================
# Test Classes
# =============================================================================


class TestSharePointConnectorInit:
    """Test SharePointConnector initialization."""

    def test_initialization(self, mock_config):
        """Test connector initialization."""
        connector = SharePointConnector(mock_config)

        assert connector.config == mock_config
        assert connector._initialized is False
        assert connector._client is None
        assert connector._site is None
        assert connector.metadata_extractor is not None

    def test_initialization_with_file_conversion(self, mock_config):
        """Test initialization with file conversion enabled."""
        mock_config.enable_file_conversion = True

        with patch(
            "qdrant_loader.connectors.sharepoint.connector.FileDetector"
        ) as mock_detector:
            connector = SharePointConnector(mock_config)

            assert connector.file_detector is not None
            mock_detector.assert_called_once()


class TestSharePointConnectorAsyncContext:
    """Test async context manager."""

    def test_async_context_manager_enter(self, mock_config, mock_auth_functions):
        """Test connector initialization via async context manager."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                assert connector._initialized is True
                assert connector._client is not None
                return connector

        connector = run_async(run_test())
        # After exiting context, should be uninitialized
        assert connector._initialized is False
        assert connector._client is None

    def test_async_context_manager_validates_connection(
        self, mock_config, mock_auth_functions
    ):
        """Test that entering context validates connection."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                pass

        run_async(run_test())

        mock_auth_functions["create_graph_client"].assert_called_once_with(mock_config)
        mock_auth_functions["validate_connection"].assert_called_once()

    def test_async_context_manager_auth_error(self, mock_config, mock_auth_functions):
        """Test handling of auth error during context entry."""
        mock_auth_functions["create_graph_client"].side_effect = SharePointAuthError(
            "Auth failed"
        )

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                pass

        with pytest.raises(SharePointAuthError):
            run_async(run_test())


class TestSharePointConnectorSite:
    """Test site connection functionality."""

    def test_get_site_caches_result(self, mock_config, mock_auth_functions):
        """Test that site is cached after first fetch."""
        mock_site = MagicMock()
        mock_site.properties = {"displayName": "Test Site"}

        mock_auth_functions["client"].sites.get_by_url.return_value = mock_site
        mock_auth_functions["client"].execute_query = MagicMock()

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                # First call
                site1 = connector._get_site()
                # Second call - should use cache
                site2 = connector._get_site()
                return site1, site2

        site1, site2 = run_async(run_test())

        assert site1 == site2
        # get_by_url should only be called once
        assert mock_auth_functions["client"].sites.get_by_url.call_count == 1

    def test_get_site_constructs_correct_path(self, mock_config, mock_auth_functions):
        """Test site path is constructed correctly."""
        mock_site = MagicMock()
        mock_auth_functions["client"].sites.get_by_url.return_value = mock_site
        mock_auth_functions["client"].execute_query = MagicMock()

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                connector._get_site()

        run_async(run_test())

        expected_path = "company.sharepoint.com:/sites/test-site"
        mock_auth_functions["client"].sites.get_by_url.assert_called_with(expected_path)


class TestSharePointConnectorFileFilters:
    """Test file filtering functionality."""

    def test_should_process_file_with_allowed_extension(self, mock_config):
        """Test file with allowed extension is processed."""
        connector = SharePointConnector(mock_config)

        assert connector._should_process_file("document.pdf") is True
        assert connector._should_process_file("report.docx") is True
        assert connector._should_process_file("readme.txt") is True

    def test_should_process_file_with_disallowed_extension(self, mock_config):
        """Test file with disallowed extension is skipped."""
        connector = SharePointConnector(mock_config)

        assert connector._should_process_file("image.jpg") is False
        assert connector._should_process_file("script.py") is False
        assert connector._should_process_file("data.xlsx") is False

    def test_should_process_file_no_extension_filter(self, mock_config_all_libraries):
        """Test all files processed when no extension filter."""
        connector = SharePointConnector(mock_config_all_libraries)

        assert connector._should_process_file("anything.xyz") is True
        assert connector._should_process_file("noext") is True

    def test_should_exclude_path(self, mock_config):
        """Test path exclusion."""
        connector = SharePointConnector(mock_config)

        assert connector._should_exclude("archive/old-doc.pdf") is True
        assert connector._should_exclude("temp/cache.txt") is True
        assert connector._should_exclude("docs/report.pdf") is False

    def test_should_exclude_no_patterns(self, mock_config_all_libraries):
        """Test no exclusion when patterns empty."""
        connector = SharePointConnector(mock_config_all_libraries)

        assert connector._should_exclude("any/path/file.txt") is False


class TestSharePointConnectorGetDocuments:
    """Test document retrieval."""

    def test_get_documents_empty_library(self, mock_config, mock_auth_functions):
        """Test get_documents with empty library."""
        # Setup mocks
        mock_site = MagicMock()
        mock_site.properties = {"displayName": "Test Site"}

        mock_drive = MagicMock()
        mock_drive.properties = {"name": "Documents"}
        mock_drive.root.children.get.return_value.execute_query.return_value = []

        mock_drives = MagicMock()
        mock_drives.__iter__ = lambda self: iter([mock_drive])
        mock_drives.__len__ = lambda self: 1

        mock_site.drives.get.return_value.execute_query.return_value = mock_drives

        mock_auth_functions["client"].sites.get_by_url.return_value = mock_site
        mock_auth_functions["client"].execute_query = MagicMock()

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                return await connector.get_documents()

        documents = run_async(run_test())

        assert documents == []

    def test_get_documents_filters_libraries(self, mock_config, mock_auth_functions):
        """Test that only specified libraries are processed."""
        mock_site = MagicMock()
        mock_site.properties = {"displayName": "Test Site"}

        # Create two drives - one matching filter, one not
        mock_drive_docs = MagicMock()
        mock_drive_docs.properties = {"name": "Documents"}
        mock_drive_docs.root.children.get.return_value.execute_query.return_value = []

        mock_drive_other = MagicMock()
        mock_drive_other.properties = {"name": "OtherLibrary"}

        mock_drives = MagicMock()
        mock_drives.__iter__ = lambda self: iter([mock_drive_docs, mock_drive_other])
        mock_drives.__len__ = lambda self: 2

        mock_site.drives.get.return_value.execute_query.return_value = mock_drives

        mock_auth_functions["client"].sites.get_by_url.return_value = mock_site
        mock_auth_functions["client"].execute_query = MagicMock()

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                await connector.get_documents()

        run_async(run_test())

        # Only Documents should be processed, not OtherLibrary
        mock_drive_docs.root.children.get.assert_called()
        mock_drive_other.root.children.get.assert_not_called()


class TestSharePointConnectorProcessFile:
    """Test file processing."""

    def test_process_file_creates_document(self, mock_config, mock_auth_functions):
        """Test that process_file creates a Document with correct fields."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                mock_item.properties = {
                    "name": "test-document.txt",
                    "id": "file-id-123",
                    "size": 1024,
                    "webUrl": "https://company.sharepoint.com/sites/test/doc.txt",
                    "createdDateTime": "2024-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2024-01-02T00:00:00Z",
                    "createdBy": {"user": {"displayName": "John Doe"}},
                    "lastModifiedBy": {"user": {"displayName": "Jane Doe"}},
                    "file": {"mimeType": "text/plain"},
                    "@microsoft.graph.downloadUrl": "https://download.url/file",
                }

                with patch.object(
                    connector, "_download_file_content", new_callable=AsyncMock
                ) as mock_download:
                    mock_download.return_value = "File content here"

                    doc = await connector._process_file(
                        mock_item, "Documents", "test-document.txt"
                    )

                    return doc

        doc = run_async(run_test())

        assert doc is not None
        assert doc.title == "test-document.txt"
        assert doc.content == "File content here"
        assert doc.content_type == "text"
        assert doc.source_type == "sharepoint"
        assert doc.source == "test-sharepoint"
        assert doc.metadata["file_name"] == "test-document.txt"
        assert doc.metadata["library_name"] == "Documents"

    def test_process_file_skips_large_files(self, mock_config, mock_auth_functions):
        """Test that files exceeding max_file_size are skipped."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                mock_item.properties = {
                    "name": "large-file.pdf",
                    "size": 20 * 1024 * 1024,  # 20MB > 10MB limit
                    "file": {"mimeType": "application/pdf"},
                }

                doc = await connector._process_file(
                    mock_item, "Documents", "large-file.pdf"
                )
                return doc

        doc = run_async(run_test())
        assert doc is None

    def test_process_file_skips_filtered_extensions(
        self, mock_config, mock_auth_functions
    ):
        """Test that files with non-matching extensions are skipped."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                mock_item.properties = {
                    "name": "image.jpg",  # jpg not in allowed extensions
                    "size": 1024,
                    "file": {"mimeType": "image/jpeg"},
                }

                doc = await connector._process_file(mock_item, "Documents", "image.jpg")
                return doc

        doc = run_async(run_test())
        assert doc is None


class TestSharePointConnectorDownloadContent:
    """Test file content download."""

    def test_download_file_content_success(self, mock_config, mock_auth_functions):
        """Test successful file content download."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                props = {
                    "name": "test.txt",
                    "@microsoft.graph.downloadUrl": "https://download.url/file",
                }

                with patch("requests.get") as mock_requests_get:
                    mock_response = MagicMock()
                    mock_response.content = b"File content"
                    mock_response.raise_for_status = MagicMock()
                    mock_requests_get.return_value = mock_response

                    content = await connector._download_file_content(mock_item, props)
                    return content

        content = run_async(run_test())
        assert content == "File content"

    def test_download_file_content_binary(self, mock_config, mock_auth_functions):
        """Test binary file returns placeholder."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                props = {
                    "name": "image.jpg",
                    "@microsoft.graph.downloadUrl": "https://download.url/file",
                }

                with patch("requests.get") as mock_requests_get:
                    mock_response = MagicMock()
                    # Binary content that can't be decoded as UTF-8
                    mock_response.content = bytes([0x89, 0x50, 0x4E, 0x47])  # PNG header
                    mock_response.raise_for_status = MagicMock()
                    mock_requests_get.return_value = mock_response

                    content = await connector._download_file_content(mock_item, props)
                    return content

        content = run_async(run_test())
        assert content == "[Binary file: image.jpg]"

    def test_download_file_content_no_url(self, mock_config, mock_auth_functions):
        """Test fallback when no download URL available."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                mock_item.get_content.return_value.execute_query.return_value.value = (
                    b"API content"
                )

                props = {
                    "name": "test.txt",
                    # No @microsoft.graph.downloadUrl
                }

                content = await connector._download_file_content(mock_item, props)
                return content

        content = run_async(run_test())
        assert content == "API content"

    def test_download_file_content_error(self, mock_config, mock_auth_functions):
        """Test error handling during download."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                props = {
                    "name": "test.txt",
                    "@microsoft.graph.downloadUrl": "https://download.url/file",
                }

                with patch("requests.get") as mock_requests_get:
                    mock_requests_get.side_effect = Exception("Network error")

                    content = await connector._download_file_content(mock_item, props)
                    return content

        content = run_async(run_test())
        assert content is None


class TestSharePointMetadataExtractorIntegration:
    """Test metadata extractor integration in connector."""

    def test_metadata_extractor_used_in_process_file(
        self, mock_config, mock_auth_functions
    ):
        """Test that metadata_extractor is used when processing files."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                mock_item.properties = {
                    "name": "test.txt",
                    "id": "file-id-123",
                    "size": 100,
                    "webUrl": "https://company.sharepoint.com/sites/test/test.txt",
                    "createdDateTime": "2024-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2024-01-02T00:00:00Z",
                    "createdBy": {
                        "user": {"displayName": "Author", "email": "author@test.com"}
                    },
                    "lastModifiedBy": {"user": {"displayName": "Modifier"}},
                    "file": {"mimeType": "text/plain"},
                    "@microsoft.graph.downloadUrl": "https://download.url/file",
                }

                with patch.object(
                    connector, "_download_file_content", new_callable=AsyncMock
                ) as mock_download:
                    mock_download.return_value = "Content"

                    doc = await connector._process_file(mock_item, "Documents", "test.txt")
                    return doc

        doc = run_async(run_test())

        # Verify metadata fields from SharePointMetadataExtractor
        assert doc.metadata["source_type"] == "sharepoint"
        assert doc.metadata["source"] == "test-sharepoint"
        assert doc.metadata["file_name"] == "test.txt"
        assert doc.metadata["library_name"] == "Documents"
        assert doc.metadata["author"] == "Author"
        assert doc.metadata["author_email"] == "author@test.com"
        assert doc.metadata["modified_by"] == "Modifier"
        assert doc.metadata["item_id"] == "file-id-123"

    def test_content_type_from_metadata_extractor(
        self, mock_config, mock_auth_functions
    ):
        """Test that content_type comes from metadata_extractor."""

        async def run_test():
            async with SharePointConnector(mock_config) as connector:
                mock_item = MagicMock()
                mock_item.properties = {
                    "name": "document.pdf",
                    "id": "file-id-123",
                    "size": 100,
                    "webUrl": "https://test.com/doc.pdf",
                    "file": {"mimeType": "application/pdf"},
                    "@microsoft.graph.downloadUrl": "https://download.url/file",
                }

                with patch.object(
                    connector, "_download_file_content", new_callable=AsyncMock
                ) as mock_download:
                    mock_download.return_value = "PDF content"

                    doc = await connector._process_file(
                        mock_item, "Documents", "document.pdf"
                    )
                    return doc

        doc = run_async(run_test())
        assert doc.content_type == "pdf"
