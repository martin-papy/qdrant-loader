"""
Unit tests for Phase 5 state management extensions - file conversion and attachment metadata tracking.
"""

import pytest
import pytest_asyncio
from datetime import datetime, UTC
import tempfile
import os

from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.core.document import Document
from qdrant_loader.config.state import StateManagementConfig


@pytest.fixture
def mock_config():
    """Create mock state management configuration."""
    # Create a temporary file for the database
    temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_fd)  # Close the file descriptor, we just need the path

    config = StateManagementConfig(
        database_path=temp_path, connection_pool={"size": 5, "timeout": 30}
    )
    return config


@pytest_asyncio.fixture
async def state_manager(mock_config):
    """Create and initialize a state manager for testing."""
    manager = StateManager(mock_config)
    await manager.initialize()
    yield manager
    await manager.dispose()


@pytest.mark.asyncio
class TestFileConversionMetadataTracking:
    """Test file conversion metadata tracking in state management."""

    async def test_document_with_conversion_metadata(self, state_manager):
        """Test that conversion metadata is properly stored and retrieved."""
        document = Document(
            title="Test PDF Document",
            content="# Test PDF Document\n\nThis is converted content.",
            content_type="md",
            source_type="git",
            source="test_repo",
            url="https://github.com/test/repo/test.pdf",
            metadata={
                "conversion_method": "markitdown",
                "original_file_type": "pdf",
                "original_filename": "test.pdf",
                "file_size": 1024000,
                "conversion_failed": False,
                "conversion_time": 2.5,
            },
        )

        # Update document state
        state_record = await state_manager.update_document_state(document)

        # Verify conversion metadata is stored
        assert state_record.is_converted is True
        assert state_record.conversion_method == "markitdown"
        assert state_record.original_file_type == "pdf"
        assert state_record.original_filename == "test.pdf"
        assert state_record.file_size == 1024000
        assert state_record.conversion_failed is False
        assert state_record.conversion_time == 2.5

    async def test_document_with_conversion_failure(self, state_manager):
        """Test that conversion failure metadata is properly stored."""
        document = Document(
            title="Failed Conversion",
            content="# Failed Conversion\n\nFallback content.",
            content_type="md",
            source_type="localfile",
            source="test_files",
            url="/path/to/corrupted.docx",
            metadata={
                "conversion_method": "markitdown_fallback",
                "original_file_type": "docx",
                "original_filename": "corrupted.docx",
                "file_size": 512000,
                "conversion_failed": True,
                "conversion_error": "File is corrupted or password protected",
                "conversion_time": 0.1,
            },
        )

        state_record = await state_manager.update_document_state(document)

        assert state_record.is_converted is True
        assert state_record.conversion_method == "markitdown_fallback"
        assert state_record.conversion_failed is True
        assert (
            state_record.conversion_error == "File is corrupted or password protected"
        )

    async def test_document_without_conversion(self, state_manager):
        """Test that documents without conversion have proper default values."""
        document = Document(
            title="Regular Markdown",
            content="# Regular Markdown\n\nNo conversion needed.",
            content_type="md",
            source_type="git",
            source="test_repo",
            url="https://github.com/test/repo/README.md",
            metadata={},
        )

        state_record = await state_manager.update_document_state(document)

        assert state_record.is_converted is False
        assert state_record.conversion_method is None
        assert state_record.original_file_type is None
        assert state_record.conversion_failed is False


@pytest.mark.asyncio
class TestAttachmentMetadataTracking:
    """Test attachment metadata tracking in state management."""

    async def test_attachment_document_metadata(self, state_manager):
        """Test that attachment metadata is properly stored and retrieved."""
        # Create parent document first
        parent_doc = Document(
            title="Confluence Page",
            content="# Confluence Page\n\nThis page has attachments.",
            content_type="html",
            source_type="confluence",
            source="test_space",
            url="https://company.atlassian.net/wiki/spaces/TEST/pages/123456",
            metadata={},
        )
        await state_manager.update_document_state(parent_doc)

        # Create attachment document
        attachment_doc = Document(
            title="Important Spreadsheet",
            content="# Important Spreadsheet\n\n| Column 1 | Column 2 |\n|----------|----------|\n| Data 1   | Data 2   |",
            content_type="md",
            source_type="confluence",
            source="test_space",
            url="https://company.atlassian.net/wiki/download/attachments/123456/spreadsheet.xlsx",
            metadata={
                "conversion_method": "markitdown",
                "original_file_type": "xlsx",
                "original_filename": "spreadsheet.xlsx",
                "file_size": 2048000,
                "conversion_failed": False,
                "conversion_time": 3.2,
                "is_attachment": True,
                "parent_document_id": parent_doc.id,
                "attachment_id": "att_789",
                "attachment_filename": "Important Spreadsheet.xlsx",
                "attachment_mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "attachment_download_url": "https://company.atlassian.net/wiki/download/attachments/123456/spreadsheet.xlsx",
                "attachment_author": "john.doe@company.com",
                "attachment_created_at": "2024-01-15T10:30:00Z",
            },
        )

        state_record = await state_manager.update_document_state(attachment_doc)

        # Verify attachment metadata
        assert state_record.is_attachment is True
        assert state_record.parent_document_id == parent_doc.id
        assert state_record.attachment_id == "att_789"
        assert state_record.attachment_filename == "Important Spreadsheet.xlsx"
        assert (
            state_record.attachment_mime_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert (
            state_record.attachment_download_url
            == "https://company.atlassian.net/wiki/download/attachments/123456/spreadsheet.xlsx"
        )
        assert state_record.attachment_author == "john.doe@company.com"
        assert state_record.attachment_created_at is not None

        # Test querying attachments by parent
        attachments = await state_manager.get_attachment_documents(parent_doc.id)
        assert len(attachments) == 1
        assert attachments[0].document_id == attachment_doc.id
        assert attachments[0].is_attachment is True


@pytest.mark.asyncio
class TestConversionMetricsTracking:
    """Test conversion metrics tracking in state management."""

    async def test_update_conversion_metrics(self, state_manager):
        """Test updating conversion metrics for a source."""
        source_type = "confluence"
        source = "test_space"

        # Update metrics
        await state_manager.update_conversion_metrics(
            source_type=source_type,
            source=source,
            converted_files_count=5,
            conversion_failures_count=1,
            attachments_processed_count=3,
            total_conversion_time=12.5,
        )

        # Retrieve and verify metrics
        metrics = await state_manager.get_conversion_metrics(source_type, source)
        assert metrics["converted_files_count"] == 5
        assert metrics["conversion_failures_count"] == 1
        assert metrics["attachments_processed_count"] == 3
        assert metrics["total_conversion_time"] == 12.5

    async def test_accumulate_conversion_metrics(self, state_manager):
        """Test that conversion metrics accumulate correctly."""
        source_type = "git"
        source = "test_repo"

        # First batch
        await state_manager.update_conversion_metrics(
            source_type=source_type,
            source=source,
            converted_files_count=3,
            conversion_failures_count=1,
            total_conversion_time=8.0,
        )

        # Second batch
        await state_manager.update_conversion_metrics(
            source_type=source_type,
            source=source,
            converted_files_count=2,
            conversion_failures_count=0,
            attachments_processed_count=1,
            total_conversion_time=4.5,
        )

        # Verify accumulated metrics
        metrics = await state_manager.get_conversion_metrics(source_type, source)
        assert metrics["converted_files_count"] == 5
        assert metrics["conversion_failures_count"] == 1
        assert metrics["attachments_processed_count"] == 1
        assert metrics["total_conversion_time"] == 12.5

    async def test_get_converted_documents(self, state_manager):
        """Test querying converted documents by source and method."""
        source_type = "localfile"
        source = "test_files"

        # Create documents with different conversion methods
        documents_data = [
            {"method": "markitdown", "file_type": "pdf", "filename": "doc1.pdf"},
            {"method": "markitdown", "file_type": "docx", "filename": "doc2.docx"},
            {
                "method": "markitdown_fallback",
                "file_type": "xlsx",
                "filename": "doc3.xlsx",
            },
            {"method": None, "file_type": "md", "filename": "doc4.md"},  # No conversion
        ]

        for i, doc_data in enumerate(documents_data):
            metadata = {}
            if doc_data["method"]:
                metadata.update(
                    {
                        "conversion_method": doc_data["method"],
                        "original_file_type": doc_data["file_type"],
                        "original_filename": doc_data["filename"],
                    }
                )

            document = Document(
                title=f"Test Document {i+1}",
                content=f"# Test Document {i+1}\n\nContent here.",
                content_type="md",
                source_type=source_type,
                source=source,
                url=f"/path/to/{doc_data['filename']}",
                metadata=metadata,
            )
            await state_manager.update_document_state(document)

        # Query all converted documents
        all_converted = await state_manager.get_converted_documents(source_type, source)
        assert len(all_converted) == 3  # Excludes the non-converted document

        # Query by specific conversion method
        markitdown_docs = await state_manager.get_converted_documents(
            source_type, source, conversion_method="markitdown"
        )
        assert len(markitdown_docs) == 2

        fallback_docs = await state_manager.get_converted_documents(
            source_type, source, conversion_method="markitdown_fallback"
        )
        assert len(fallback_docs) == 1


@pytest.mark.asyncio
class TestTimezoneHandling:
    """Test timezone handling for attachment creation dates."""

    async def test_parse_attachment_created_at_with_timezone(self, state_manager):
        """Test parsing attachment creation date with timezone."""
        document = Document(
            title="Attachment",
            content="Content",
            content_type="md",
            source_type="confluence",
            source="test_space",
            url="https://example.com/attachment",
            metadata={
                "is_attachment": True,
                "attachment_created_at": "2024-01-15T10:30:00+02:00",
            },
        )

        state_record = await state_manager.update_document_state(document)

        # Verify the datetime was parsed and set
        assert state_record.attachment_created_at is not None

    async def test_parse_attachment_created_at_invalid_format(self, state_manager):
        """Test handling of invalid attachment creation date format."""
        document = Document(
            title="Attachment",
            content="Content",
            content_type="md",
            source_type="confluence",
            source="test_space",
            url="https://example.com/attachment",
            metadata={
                "is_attachment": True,
                "attachment_created_at": "invalid-date-format",
            },
        )

        # Should not raise an exception
        state_record = await state_manager.update_document_state(document)

        # Should set to None for invalid format
        assert state_record.attachment_created_at is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
