"""
Unit tests for the attachment downloader service.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader.core.attachment_downloader import (
    AttachmentDownloader,
    AttachmentMetadata,
)
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion.conversion_config import FileConversionConfig


@pytest.fixture
def mock_session():
    """Create a mock HTTP session."""
    session = MagicMock()
    return session


@pytest.fixture
def file_conversion_config():
    """Create file conversion configuration."""
    return FileConversionConfig(
        max_file_size=50 * 1024 * 1024,  # 50MB
        conversion_timeout=300,
    )


@pytest.fixture
def attachment_downloader(mock_session, file_conversion_config):
    """Create attachment downloader instance."""
    return AttachmentDownloader(
        session=mock_session,
        file_conversion_config=file_conversion_config,
        enable_file_conversion=True,
    )


class TestAttachmentMetadata:
    """Test the AttachmentMetadata class."""

    def test_attachment_metadata_creation(self):
        """Test creating attachment metadata."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/download/document.pdf",
            parent_document_id="doc_456",
            author="john.doe@example.com",
            created_at="2024-01-15T10:30:00Z",
        )

        assert metadata.id == "att_123"
        assert metadata.filename == "document.pdf"
        assert metadata.mime_type == "application/pdf"
        assert metadata.size == 1024000
        assert metadata.download_url == "https://example.com/download/document.pdf"
        assert metadata.parent_document_id == "doc_456"
        assert metadata.author == "john.doe@example.com"
        assert metadata.created_at == "2024-01-15T10:30:00Z"

    def test_attachment_metadata_optional_fields(self):
        """Test attachment metadata with optional fields."""
        metadata = AttachmentMetadata(
            id="att_456",
            filename="image.png",
            size=512000,
            mime_type="image/png",
            download_url="https://example.com/image.png",
            parent_document_id="doc_789",
        )

        assert metadata.id == "att_456"
        assert metadata.filename == "image.png"
        assert metadata.size == 512000
        assert metadata.author is None
        assert metadata.created_at is None


class TestAttachmentDownloaderInitialization:
    """Test attachment downloader initialization."""

    def test_initialization_with_file_conversion_enabled(
        self, mock_session, file_conversion_config
    ):
        """Test initialization with file conversion enabled."""
        downloader = AttachmentDownloader(
            session=mock_session,
            file_conversion_config=file_conversion_config,
            enable_file_conversion=True,
        )

        assert downloader.session == mock_session
        assert downloader.enable_file_conversion is True
        assert downloader.file_converter is not None
        assert downloader.file_detector is not None

    def test_initialization_with_file_conversion_disabled(self, mock_session):
        """Test initialization with file conversion disabled."""
        downloader = AttachmentDownloader(
            session=mock_session, enable_file_conversion=False
        )

        assert downloader.session == mock_session
        assert downloader.enable_file_conversion is False
        assert downloader.file_converter is None
        assert downloader.file_detector is None

    def test_initialization_with_custom_max_size(
        self, mock_session, file_conversion_config
    ):
        """Test initialization with custom max attachment size."""
        custom_size = 10 * 1024 * 1024  # 10MB
        downloader = AttachmentDownloader(
            session=mock_session,
            file_conversion_config=file_conversion_config,
            enable_file_conversion=True,
            max_attachment_size=custom_size,
        )

        assert downloader.max_attachment_size == custom_size


class TestShouldDownloadAttachment:
    """Test attachment download decision logic."""

    def test_should_download_small_attachment(self, attachment_downloader):
        """Test that small attachments should be downloaded."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,  # 1MB
            mime_type="application/pdf",
            download_url="https://example.com/document.pdf",
            parent_document_id="doc_456",
        )

        assert attachment_downloader.should_download_attachment(metadata) is True

    def test_should_not_download_large_attachment(self, attachment_downloader):
        """Test that large attachments should not be downloaded."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="huge_file.pdf",
            size=100 * 1024 * 1024,  # 100MB (exceeds default 50MB limit)
            mime_type="application/pdf",
            download_url="https://example.com/huge_file.pdf",
            parent_document_id="doc_456",
        )

        assert attachment_downloader.should_download_attachment(metadata) is False

    def test_should_download_supported_mime_type(self, attachment_downloader):
        """Test that supported MIME types should be downloaded."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="spreadsheet.xlsx",
            size=2048000,  # 2MB
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_url="https://example.com/spreadsheet.xlsx",
            parent_document_id="doc_456",
        )

        assert attachment_downloader.should_download_attachment(metadata) is True


class TestAttachmentDownload:
    """Test attachment download functionality."""

    @pytest.mark.asyncio
    async def test_download_attachment_success(self, attachment_downloader):
        """Test successful attachment download."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/document.pdf",
            parent_document_id="doc_456",
        )

        # Mock successful response
        mock_response = MagicMock()
        mock_response.headers = {
            "content-length": "1024000",
            "content-type": "application/pdf",
        }
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [
            b"PDF content chunk 1",
            b"PDF content chunk 2",
        ]
        attachment_downloader.session.get.return_value = mock_response

        # Mock temporary file creation and file operations
        with (
            patch("tempfile.NamedTemporaryFile") as mock_temp_file_class,
            patch("os.path.getsize") as mock_getsize,
        ):

            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test_attachment.pdf"
            mock_temp_file.write = MagicMock()
            mock_temp_file.close = MagicMock()
            mock_temp_file_class.return_value = mock_temp_file

            # Mock file size to be non-zero
            mock_getsize.return_value = 1024000

            temp_file_path = await attachment_downloader.download_attachment(metadata)

            assert temp_file_path == "/tmp/test_attachment.pdf"
            attachment_downloader.session.get.assert_called_once()
            # Verify that content was written to the file
            assert mock_temp_file.write.call_count >= 1

    @pytest.mark.asyncio
    async def test_download_attachment_http_error(self, attachment_downloader):
        """Test attachment download with HTTP error."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/document.pdf",
            parent_document_id="doc_456",
        )

        # Mock HTTP error
        attachment_downloader.session.get.side_effect = Exception("HTTP 404 Not Found")

        temp_file_path = await attachment_downloader.download_attachment(metadata)

        assert temp_file_path is None

    @pytest.mark.asyncio
    async def test_download_attachment_size_mismatch(self, attachment_downloader):
        """Test attachment download with size mismatch."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/document.pdf",
            parent_document_id="doc_456",
        )

        # Mock response with different content length
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "2048000"}  # Different from metadata
        attachment_downloader.session.get.return_value = mock_response

        temp_file_path = await attachment_downloader.download_attachment(metadata)

        assert temp_file_path is None

    @pytest.mark.asyncio
    async def test_download_attachment_html_response(self, attachment_downloader):
        """Test attachment download that returns HTML (auth error)."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/document.pdf",
            parent_document_id="doc_456",
        )

        # Mock HTML response (indicates auth error)
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        attachment_downloader.session.get.return_value = mock_response

        temp_file_path = await attachment_downloader.download_attachment(metadata)

        assert temp_file_path is None


class TestProcessAttachment:
    """Test attachment processing functionality."""

    def test_process_attachment_with_conversion(self, attachment_downloader):
        """Test processing attachment with file conversion."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/document.pdf",
            parent_document_id="doc_456",
        )

        parent_document = Document(
            title="Parent Document",
            content="Parent content",
            content_type="html",
            source_type="confluence",
            source="test_space",
            url="https://example.com/parent",
            metadata={},
        )

        temp_file_path = "/tmp/test_attachment.pdf"

        # Mock file converter
        with patch.object(
            attachment_downloader.file_converter, "convert_file"
        ) as mock_convert:
            mock_convert.return_value = (
                "# Converted PDF Content\n\nThis is the converted markdown."
            )

            document = attachment_downloader.process_attachment(
                metadata, temp_file_path, parent_document
            )

            assert document is not None
            assert (
                document.title == "Attachment: document.pdf"
            )  # Actual format includes "Attachment: "
            assert "# Converted PDF Content" in document.content
            assert document.content_type == "md"
            assert document.metadata["is_attachment"] is True
            assert (
                document.metadata["parent_document_id"] == metadata.parent_document_id
            )

    def test_process_attachment_conversion_failure(self, attachment_downloader):
        """Test processing attachment with conversion failure."""
        metadata = AttachmentMetadata(
            id="att_123",
            filename="corrupted.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/corrupted.pdf",
            parent_document_id="doc_456",
        )

        parent_document = Document(
            title="Parent Document",
            content="Parent content",
            content_type="html",
            source_type="confluence",
            source="test_space",
            url="https://example.com/parent",
            metadata={},
        )

        temp_file_path = "/tmp/corrupted.pdf"

        # Mock file converter to raise FileConversionError (not generic Exception)
        from qdrant_loader.core.file_conversion.exceptions import FileConversionError

        with (
            patch.object(
                attachment_downloader.file_converter, "convert_file"
            ) as mock_convert,
            patch.object(
                attachment_downloader.file_converter, "create_fallback_document"
            ) as mock_fallback,
        ):

            mock_convert.side_effect = FileConversionError("Conversion failed")
            mock_fallback.return_value = (
                "# corrupted.pdf\n\nFailed to convert: Conversion failed"
            )

            document = attachment_downloader.process_attachment(
                metadata, temp_file_path, parent_document
            )

            assert document is not None
            assert "Failed to convert" in document.content
            assert document.metadata["conversion_failed"] is True

    def test_process_attachment_no_conversion(self, mock_session):
        """Test processing attachment without file conversion."""
        downloader = AttachmentDownloader(
            session=mock_session, enable_file_conversion=False
        )

        metadata = AttachmentMetadata(
            id="att_123",
            filename="document.pdf",
            size=1024000,
            mime_type="application/pdf",
            download_url="https://example.com/document.pdf",
            parent_document_id="doc_456",
        )

        parent_document = Document(
            title="Parent Document",
            content="Parent content",
            content_type="html",
            source_type="jira",
            source="test_project",
            url="https://example.com/parent",
            metadata={},
        )

        temp_file_path = "/tmp/document.pdf"

        document = downloader.process_attachment(
            metadata, temp_file_path, parent_document
        )

        assert document is not None
        assert (
            "This attachment could not be converted to text" in document.content
        )  # Actual message
        # conversion_method is only added when needs_conversion is True, so it won't exist when file conversion is disabled
        assert "conversion_method" not in document.metadata


class TestDownloadAndProcessAttachments:
    """Test the main download and process method."""

    @pytest.mark.asyncio
    async def test_download_and_process_attachments_success(
        self, attachment_downloader
    ):
        """Test successful download and processing of multiple attachments."""
        parent_document = Document(
            title="Parent Document",
            content="Parent content",
            content_type="html",
            source_type="confluence",
            source="test_space",
            url="https://example.com/parent",
            metadata={},
        )

        attachments = [
            AttachmentMetadata(
                id="att_001",
                filename="document.pdf",
                size=1024000,
                mime_type="application/pdf",
                download_url="https://example.com/document.pdf",
                parent_document_id="doc_456",
            ),
            AttachmentMetadata(
                id="att_002",
                filename="spreadsheet.xlsx",
                size=2048000,
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                download_url="https://example.com/spreadsheet.xlsx",
                parent_document_id="doc_456",
            ),
        ]

        # Mock successful downloads and processing
        with (
            patch.object(attachment_downloader, "download_attachment") as mock_download,
            patch.object(attachment_downloader, "process_attachment") as mock_process,
            patch.object(attachment_downloader, "cleanup_temp_file") as mock_cleanup,
        ):

            # Mock download returns temp file paths
            mock_download.side_effect = ["/tmp/temp1.pdf", "/tmp/temp2.xlsx"]

            # Mock process returns documents
            mock_process.side_effect = [
                Document(
                    title="document.pdf",
                    content="PDF content",
                    content_type="md",
                    source_type="confluence",
                    source="test_space",
                    url="https://example.com/document.pdf",
                    metadata={},
                ),
                Document(
                    title="spreadsheet.xlsx",
                    content="Excel content",
                    content_type="md",
                    source_type="confluence",
                    source="test_space",
                    url="https://example.com/spreadsheet.xlsx",
                    metadata={},
                ),
            ]

            documents = await attachment_downloader.download_and_process_attachments(
                attachments, parent_document
            )

            assert len(documents) == 2
            assert documents[0].title == "document.pdf"
            assert documents[1].title == "spreadsheet.xlsx"

            # Verify cleanup was called for each temp file
            assert mock_cleanup.call_count == 2

    @pytest.mark.asyncio
    async def test_download_and_process_attachments_with_failures(
        self, attachment_downloader
    ):
        """Test download and processing with some failures."""
        parent_document = Document(
            title="Parent Document",
            content="Parent content",
            content_type="html",
            source_type="jira",
            source="test_project",
            url="https://example.com/parent",
            metadata={},
        )

        attachments = [
            AttachmentMetadata(
                id="att_001",
                filename="good_document.pdf",
                size=1024000,
                mime_type="application/pdf",
                download_url="https://example.com/good_document.pdf",
                parent_document_id="doc_456",
            ),
            AttachmentMetadata(
                id="att_002",
                filename="bad_document.pdf",
                size=1024000,
                mime_type="application/pdf",
                download_url="https://example.com/bad_document.pdf",
                parent_document_id="doc_456",
            ),
        ]

        # Mock one successful download, one failure
        with (
            patch.object(attachment_downloader, "download_attachment") as mock_download,
            patch.object(attachment_downloader, "process_attachment") as mock_process,
            patch.object(attachment_downloader, "cleanup_temp_file") as mock_cleanup,
        ):

            # First download succeeds, second fails
            mock_download.side_effect = ["/tmp/temp1.pdf", None]

            mock_process.return_value = Document(
                title="good_document.pdf",
                content="PDF content",
                content_type="md",
                source_type="jira",
                source="test_project",
                url="https://example.com/good_document.pdf",
                metadata={},
            )

            documents = await attachment_downloader.download_and_process_attachments(
                attachments, parent_document
            )

            # Should only get one document (the successful one)
            assert len(documents) == 1
            assert documents[0].title == "good_document.pdf"

            # Cleanup should only be called once (for the successful download)
            mock_cleanup.assert_called_once_with("/tmp/temp1.pdf")

    @pytest.mark.asyncio
    async def test_download_and_process_empty_attachments(self, attachment_downloader):
        """Test processing empty attachment list."""
        parent_document = Document(
            title="Parent Document",
            content="Parent content",
            content_type="html",
            source_type="confluence",
            source="test_space",
            url="https://example.com/parent",
            metadata={},
        )

        documents = await attachment_downloader.download_and_process_attachments(
            [], parent_document
        )

        assert len(documents) == 0


class TestCleanup:
    """Test cleanup functionality."""

    def test_cleanup_temp_file_exists(self, attachment_downloader):
        """Test cleanup of existing temporary file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test content")

        # Verify file exists
        assert Path(temp_path).exists()

        # Cleanup
        attachment_downloader.cleanup_temp_file(temp_path)

        # Verify file is deleted
        assert not Path(temp_path).exists()

    def test_cleanup_temp_file_not_exists(self, attachment_downloader):
        """Test cleanup of non-existent temporary file."""
        temp_path = "/tmp/nonexistent_file.txt"

        # Should not raise an exception
        attachment_downloader.cleanup_temp_file(temp_path)

    def test_cleanup_temp_file_empty_path(self, attachment_downloader):
        """Test cleanup with empty path."""
        # Should not raise an exception
        attachment_downloader.cleanup_temp_file("")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
