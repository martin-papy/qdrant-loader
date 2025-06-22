"""
Tests for state management extensions - file conversion and attachment metadata tracking.
"""

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from pydantic import AnyUrl
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.state_manager import StateManager


@pytest.fixture
def mock_config():
    """Create mock state management configuration with in-memory database."""
    config = MagicMock(spec=StateManagementConfig)
    config.database_path = ":memory:"
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
    """Test file conversion state tracking functionality."""

    @pytest.mark.asyncio
    async def test_document_with_conversion_metadata(self, state_manager):
        """Test document state tracking with conversion metadata."""
        # Create document with conversion metadata
        document = Document(
            title="Test PDF Document",
            content="Converted content",
            content_type="text/plain",
            source_type="test_source_type",
            source="test_source",
            url="http://test.com/document.pdf",
            metadata={
                "conversion_method": "markitdown",
                "original_file_type": "pdf",
                "original_filename": "document.pdf",
                "conversion_time": 2.5,
            },
        )

        await state_manager.update_document_state(document)

        # Verify conversion metadata is stored
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/document.pdf"),
        )
        records = await state_manager.get_document_state_records(source_config)
        assert len(records) == 1
        record = records[0]
        assert record.is_converted is True
        assert record.conversion_method == "markitdown"
        assert record.original_file_type == "pdf"
        assert record.original_filename == "document.pdf"
        assert record.conversion_time == 2.5

    @pytest.mark.asyncio
    async def test_document_with_conversion_failure(self, state_manager):
        """Test document state tracking with conversion failure."""
        # Create document with conversion failure metadata
        document = Document(
            title="Failed PDF Document",
            content="",
            content_type="text/plain",
            source_type="test_source_type",
            source="test_source",
            url="http://test.com/document.pdf",
            metadata={
                "conversion_method": "markitdown_fallback",
                "original_file_type": "pdf",
                "conversion_failed": True,
                "conversion_error": "Unable to extract text from PDF",
            },
        )

        await state_manager.update_document_state(document)

        # Verify failure is tracked
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/document.pdf"),
        )
        records = await state_manager.get_document_state_records(source_config)
        assert len(records) == 1
        record = records[0]
        assert record.is_converted is True
        assert record.conversion_failed is True
        assert record.conversion_error == "Unable to extract text from PDF"

    @pytest.mark.asyncio
    async def test_document_without_conversion(self, state_manager):
        """Test document state tracking without conversion."""
        # Create document without conversion metadata
        document = Document(
            title="Plain Text Document",
            content="Direct text content",
            content_type="text/plain",
            source_type="test_source_type",
            source="test_source",
            url="http://test.com/document.txt",
            metadata={},
        )

        await state_manager.update_document_state(document)

        # Verify document is tracked normally
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/document.txt"),
        )
        records = await state_manager.get_document_state_records(source_config)
        assert len(records) == 1
        record = records[0]
        assert record.is_converted is False
        assert record.conversion_method is None


@pytest.mark.asyncio
class TestAttachmentStateTracking:
    """Test attachment state tracking functionality."""

    @pytest.mark.asyncio
    async def test_attachment_document_metadata(self, state_manager):
        """Test document state tracking with attachment metadata."""
        # Create document with attachment metadata
        document = Document(
            title="Attachment Document",
            content="Attachment content",
            content_type="application/pdf",
            source_type="test_source_type",
            source="test_source",
            url="http://test.com/attachment.pdf",
            metadata={
                "is_attachment": True,
                "parent_document_id": "msg_123",
                "attachment_filename": "report.pdf",
                "attachment_mime_type": "application/pdf",
            },
        )

        await state_manager.update_document_state(document)

        # Verify attachment metadata is stored
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/attachment.pdf"),
        )
        records = await state_manager.get_document_state_records(source_config)
        assert len(records) == 1
        record = records[0]
        assert record.is_attachment is True
        assert record.parent_document_id == "msg_123"
        assert record.attachment_filename == "report.pdf"
        assert record.attachment_mime_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_multiple_attachments_for_parent(self, state_manager):
        """Test tracking multiple attachments for the same parent message."""
        parent_id = "msg_123"

        # Create multiple attachment documents
        attachments = [
            Document(
                title=f"Attachment {i}",
                content=f"Attachment {i} content",
                content_type="application/pdf",
                source_type="test_source_type",
                source="test_source",
                url=f"http://test.com/attachment_{i}.pdf",
                metadata={
                    "is_attachment": True,
                    "parent_document_id": parent_id,
                    "attachment_filename": f"file_{i}.pdf",
                },
            )
            for i in range(3)
        ]

        for attachment in attachments:
            await state_manager.update_document_state(attachment)

        # Verify all attachments are tracked
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/attachment_0.pdf"),
        )
        records = await state_manager.get_document_state_records(source_config)
        assert len(records) == 3

        # All should reference the same parent
        for record in records:
            assert record.is_attachment is True
            assert record.parent_document_id == parent_id


@pytest.mark.asyncio
class TestConversionMetricsTracking:
    """Test conversion metrics tracking functionality."""

    @pytest.mark.asyncio
    async def test_update_conversion_metrics(self, state_manager):
        """Test updating conversion metrics."""
        document = Document(
            title="Test Document",
            content="Test content",
            content_type="text/plain",
            source_type="test_source_type",
            source="test_source",
            url="http://test.com/document",
            metadata={"conversion_metrics": {"pages": 5, "words": 100}},
        )

        await state_manager.update_document_state(document)

        # Verify the document was stored
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/document"),
        )
        records = await state_manager.get_document_state_records(source_config)
        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_accumulate_conversion_metrics(self, state_manager):
        """Test accumulating conversion metrics across documents."""
        # Create documents with metrics
        documents = [
            Document(
                title=f"Document {i}",
                content=f"Content {i}",
                content_type="text/plain",
                source_type="test_source_type",
                source="test_source",
                url=f"http://test.com/document_{i}",
                metadata={
                    "conversion_metrics": {"pages": i + 1, "words": (i + 1) * 10}
                },
            )
            for i in range(3)
        ]

        for doc in documents:
            await state_manager.update_document_state(doc)

        # Verify all documents are stored
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/document_0"),
        )
        records = await state_manager.get_document_state_records(source_config)
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_get_converted_documents(self, state_manager):
        """Test getting documents that have been converted."""
        # Create mix of converted and non-converted documents
        documents = [
            Document(
                title="Converted Document",
                content="Converted content",
                content_type="text/plain",
                source_type="test_source_type",
                source="test_source",
                url="http://test.com/converted.pdf",
                metadata={
                    "conversion_method": "markitdown",
                    "original_file_type": "pdf",
                },
            ),
            Document(
                title="Direct Document",
                content="Direct content",
                content_type="text/plain",
                source_type="test_source_type",
                source="test_source",
                url="http://test.com/direct.txt",
                metadata={},
            ),
        ]

        for doc in documents:
            await state_manager.update_document_state(doc)

        # Get all records and filter converted ones
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/converted.pdf"),
        )
        records = await state_manager.get_document_state_records(source_config)
        converted_records = [record for record in records if record.is_converted]

        assert len(converted_records) == 1
        assert converted_records[0].conversion_method == "markitdown"


@pytest.mark.asyncio
class TestStateManagementIntegration:
    """Test complete state management integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_conversions_and_attachments(
        self, state_manager
    ):
        """Test complete workflow with file conversions and attachment handling."""
        # Create a mix of documents: regular, converted, and attachments
        documents = [
            # Regular document
            Document(
                title="Regular Document",
                content="Regular content",
                content_type="text/plain",
                source_type="test_source_type",
                source="test_source",
                url="http://test.com/regular.txt",
                metadata={},
            ),
            # Converted document
            Document(
                title="Converted Document",
                content="Converted content from PDF",
                content_type="text/plain",
                source_type="test_source_type",
                source="test_source",
                url="http://test.com/converted.pdf",
                metadata={
                    "conversion_method": "markitdown",
                    "original_file_type": "pdf",
                    "conversion_time": 3.0,
                },
            ),
            # Attachment document
            Document(
                title="Attachment Document",
                content="Attachment content",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                source_type="test_source_type",
                source="test_source",
                url="http://test.com/attachment.docx",
                metadata={
                    "is_attachment": True,
                    "parent_document_id": "msg_456",
                    "attachment_filename": "document.docx",
                    "attachment_mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "conversion_method": "markitdown",
                    "original_file_type": "docx",
                },
            ),
        ]

        # Process all documents
        for doc in documents:
            await state_manager.update_document_state(doc)

        # Verify all documents are tracked
        source_config = SourceConfig(
            source_type="test_source_type",
            source="test_source",
            base_url=AnyUrl("http://test.com/regular.txt"),
        )
        all_records = await state_manager.get_document_state_records(source_config)
        assert len(all_records) == 3

        # Regular document
        regular_record = next(r for r in all_records if "regular.txt" in r.url)
        assert regular_record.is_converted is False
        assert regular_record.is_attachment is False

        # Converted document
        converted_record = next(r for r in all_records if "converted.pdf" in r.url)
        assert converted_record.is_converted is True
        assert converted_record.conversion_method == "markitdown"
        assert converted_record.original_file_type == "pdf"

        # Attachment document with conversion
        attachment_record = next(r for r in all_records if "attachment.docx" in r.url)
        assert attachment_record.is_attachment is True
        assert attachment_record.is_converted is True
        assert attachment_record.parent_document_id == "msg_456"
        assert attachment_record.conversion_method == "markitdown"

        # Test filtering capabilities
        converted_docs = [record for record in all_records if record.is_converted]
        assert len(converted_docs) == 2  # converted_doc and attachment_doc

        attachment_docs = [record for record in all_records if record.is_attachment]
        assert len(attachment_docs) == 1  # attachment_doc only


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
