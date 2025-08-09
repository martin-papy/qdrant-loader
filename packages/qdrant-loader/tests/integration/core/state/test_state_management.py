"""
Tests for state management extensions - file conversion and attachment metadata tracking.
"""

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.state_manager import StateManager


@pytest.fixture
def mock_config():
    """Create mock state management configuration."""
    config = MagicMock(spec=StateManagementConfig)
    config.database_path = "sqlite:///:memory:"
    config.connection_pool = {"size": 5, "timeout": 30}
    return config


@pytest_asyncio.fixture
async def state_manager(mock_config):
    """Create and initialize a state manager for testing."""
    manager = StateManager(mock_config)
    await manager.initialize()
    yield manager
    await manager.dispose()


@pytest.mark.asyncio
class TestFileConversionStateTracking:
    """Test file conversion metadata tracking in state management."""

    async def test_document_with_conversion_metadata(self, state_manager):
        """Test that conversion metadata is properly stored and retrieved."""
        # Create a document with conversion metadata
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

        # Retrieve and verify
        retrieved_record = await state_manager.get_document_state_record(
            document.source_type, document.source, document.id
        )
        assert retrieved_record is not None
        assert retrieved_record.is_converted is True
        assert retrieved_record.conversion_method == "markitdown"

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
class TestAttachmentStateTracking:
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

    async def test_multiple_attachments_for_parent(self, state_manager):
        """Test multiple attachments for a single parent document."""
        # Create parent document
        parent_doc = Document(
            title="JIRA Issue",
            content="# Bug Report\n\nThis issue has multiple attachments.",
            content_type="html",
            source_type="jira",
            source="test_project",
            url="https://company.atlassian.net/browse/TEST-123",
            metadata={},
        )
        await state_manager.update_document_state(parent_doc)

        # Create multiple attachments
        attachments_data = [
            {
                "title": "Screenshot",
                "filename": "bug_screenshot.png",
                "mime_type": "image/png",
                "attachment_id": "att_001",
            },
            {
                "title": "Log File",
                "filename": "error.log",
                "mime_type": "text/plain",
                "attachment_id": "att_002",
            },
            {
                "title": "Test Data",
                "filename": "test_data.csv",
                "mime_type": "text/csv",
                "attachment_id": "att_003",
            },
        ]

        for _i, att_data in enumerate(attachments_data):
            attachment_doc = Document(
                title=att_data["title"],
                content=f"# {att_data['title']}\n\nProcessed attachment content.",
                content_type="md",
                source_type="jira",
                source="test_project",
                url=f"https://company.atlassian.net/secure/attachment/{att_data['attachment_id']}/{att_data['filename']}",
                metadata={
                    "is_attachment": True,
                    "parent_document_id": parent_doc.id,
                    "attachment_id": att_data["attachment_id"],
                    "attachment_filename": att_data["filename"],
                    "attachment_mime_type": att_data["mime_type"],
                    "conversion_method": (
                        "markitdown" if att_data["mime_type"] != "text/plain" else None
                    ),
                },
            )
            await state_manager.update_document_state(attachment_doc)

        # Verify all attachments are linked to parent
        attachments = await state_manager.get_attachment_documents(parent_doc.id)
        assert len(attachments) == 3

        attachment_ids = {att.attachment_id for att in attachments}
        expected_ids = {"att_001", "att_002", "att_003"}
        assert attachment_ids == expected_ids


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
class TestStateManagementIntegration:
    """Test integration of all Phase 5 state management features."""

    async def test_complete_workflow_with_conversions_and_attachments(
        self, state_manager
    ):
        """Test a complete workflow with file conversions and attachments."""
        # Create a parent document (Confluence page)
        parent_doc = Document(
            title="Project Documentation",
            content="# Project Documentation\n\nThis page contains important project files.",
            content_type="html",
            source_type="confluence",
            source="project_space",
            url="https://company.atlassian.net/wiki/spaces/PROJ/pages/456789",
            metadata={},
        )
        await state_manager.update_document_state(parent_doc)

        # Create converted file attachments
        attachment_1 = Document(
            title="Requirements Document",
            content="# Requirements Document\n\n## Functional Requirements\n\n1. Feature A\n2. Feature B",
            content_type="md",
            source_type="confluence",
            source="project_space",
            url="https://company.atlassian.net/wiki/download/attachments/456789/requirements.docx",
            metadata={
                "conversion_method": "markitdown",
                "original_file_type": "docx",
                "original_filename": "requirements.docx",
                "file_size": 1536000,
                "conversion_failed": False,
                "conversion_time": 2.8,
                "is_attachment": True,
                "parent_document_id": parent_doc.id,
                "attachment_id": "att_req_001",
                "attachment_filename": "Project Requirements.docx",
                "attachment_mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "attachment_author": "project.manager@company.com",
                "attachment_created_at": "2024-01-10T09:00:00Z",
            },
        )
        await state_manager.update_document_state(attachment_1)

        # Create failed conversion attachment
        attachment_2 = Document(
            title="Encrypted Presentation",
            content="# Encrypted Presentation\n\nFile type: pptx\nSize: 5242880 bytes\nConversion failed: Password protected file",
            content_type="md",
            source_type="confluence",
            source="project_space",
            url="https://company.atlassian.net/wiki/download/attachments/456789/presentation.pptx",
            metadata={
                "conversion_method": "markitdown_fallback",
                "original_file_type": "pptx",
                "original_filename": "presentation.pptx",
                "file_size": 5242880,
                "conversion_failed": True,
                "conversion_error": "Password protected file",
                "conversion_time": 0.2,
                "is_attachment": True,
                "parent_document_id": parent_doc.id,
                "attachment_id": "att_ppt_002",
                "attachment_filename": "Project Presentation.pptx",
                "attachment_mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "attachment_author": "designer@company.com",
                "attachment_created_at": "2024-01-12T14:30:00Z",
            },
        )
        await state_manager.update_document_state(attachment_2)

        # Update conversion metrics
        await state_manager.update_conversion_metrics(
            source_type="confluence",
            source="project_space",
            converted_files_count=1,
            conversion_failures_count=1,
            attachments_processed_count=2,
            total_conversion_time=3.0,
        )

        # Verify parent-child relationships
        attachments = await state_manager.get_attachment_documents(parent_doc.id)
        assert len(attachments) == 2

        successful_attachment = next(
            att for att in attachments if not att.conversion_failed
        )
        failed_attachment = next(att for att in attachments if att.conversion_failed)

        assert successful_attachment.conversion_method == "markitdown"
        assert successful_attachment.original_file_type == "docx"
        assert failed_attachment.conversion_method == "markitdown_fallback"
        assert failed_attachment.conversion_error == "Password protected file"

        # Verify conversion metrics
        metrics = await state_manager.get_conversion_metrics(
            "confluence", "project_space"
        )
        assert metrics["converted_files_count"] == 1
        assert metrics["conversion_failures_count"] == 1
        assert metrics["attachments_processed_count"] == 2
        assert metrics["total_conversion_time"] == 3.0

        # Verify converted documents query
        converted_docs = await state_manager.get_converted_documents(
            "confluence", "project_space"
        )
        assert len(converted_docs) == 2  # Both attachments have conversion metadata

        successful_conversions = await state_manager.get_converted_documents(
            "confluence", "project_space", conversion_method="markitdown"
        )
        assert len(successful_conversions) == 1
        assert successful_conversions[0].document_id == attachment_1.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
