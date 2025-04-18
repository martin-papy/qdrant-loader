import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.jira.config import JiraProjectConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.models import DocumentStateRecord
from qdrant_loader.core.state.state_change_detector import StateChangeDetector


@pytest.fixture
def mock_state_manager():
    manager = Mock()
    # Configure async method mocks
    manager.get_document_states = AsyncMock(return_value=[])
    manager.get_document_by_key = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def jira_change_detector(mock_state_manager):
    return StateChangeDetector(
        state_manager=mock_state_manager,
        source_config=JiraProjectConfig(
            source_type="jira",
            source_name="test",
            base_url=HttpUrl("https://example.com"),
            project_key="TEST",
            requests_per_minute=60,
            page_size=50,
            process_attachments=True,
            track_last_sync=True,
            token="test_token",
            email="test@example.com",
        ),
    )


@pytest.mark.asyncio
async def test_detect_changes_no_previous_state(jira_change_detector, mock_state_manager):
    # Arrange
    documents = [
        Document(
            id="TEST-1",
            content="Test content 1",
            source="https://example.com",
            source_type="jira",
            metadata={
                "key": "TEST-1",
                "last_modified": "2024-01-01T00:00:00Z",
                "status": "Done",
            },
        ),
        Document(
            id="TEST-2",
            content="Test content 2",
            source="https://example.com",
            source_type="jira",
            metadata={
                "key": "TEST-2",
                "last_modified": "2024-01-01T00:00:00Z",
                "status": "In Progress",
            },
        ),
    ]
    mock_state_manager.get_document_states.return_value = []

    # Act
    result = await jira_change_detector.detect_changes(documents)

    # Assert
    assert result["new"] == documents
    assert result["updated"] == []
    assert result["deleted"] == []
    mock_state_manager.get_document_states.assert_called_once()


@pytest.mark.asyncio
async def test_detect_changes_with_previous_state(jira_change_detector, mock_state_manager):
    # Arrange
    current_docs = [
        Document(
            id="TEST-1",
            content="Updated content",
            source="https://example.com",
            source_type="jira",
            metadata={
                "key": "TEST-1",
                "last_modified": "2024-01-02T00:00:00Z",
                "status": "Done",
            },
        ),
        Document(
            id="TEST-2",
            content="New content",
            source="https://example.com",
            source_type="jira",
            metadata={
                "key": "TEST-2",
                "last_modified": "2024-01-01T00:00:00Z",
                "status": "In Progress",
            },
        ),
    ]
    previous_state = DocumentStateRecord(
        source_type="jira",
        source_name="test",
        document_id="TEST-1",
        content_hash="hash1",
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_ingested=datetime(2024, 1, 1, tzinfo=timezone.utc),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    mock_state_manager.get_document_states.return_value = [previous_state]

    # Act
    result = await jira_change_detector.detect_changes(current_docs)

    # Assert
    assert len(result["new"]) == 1
    assert result["new"][0].metadata["key"] == "TEST-2"
    assert len(result["updated"]) == 1
    assert result["updated"][0].metadata["key"] == "TEST-1"
    assert result["deleted"] == []


@pytest.mark.asyncio
async def test_detect_changes_with_deleted_document(jira_change_detector, mock_state_manager):
    # Arrange
    # Current documents - only TEST-1 exists
    current_docs = [
        Document(
            id="TEST-1",
            content="Updated content",
            source="https://example.com",
            source_type="jira",
            metadata={
                "key": "TEST-1",
                "last_modified": "2024-01-02T00:00:00Z",
                "status": "Done",
            },
        ),
    ]

    # Previous state - both TEST-1 and TEST-2 exist
    previous_states = [
        DocumentStateRecord(
            source_type="jira",
            source_name="test",
            document_id="TEST-1",  # Consistent with current doc
            content_hash="hash1",
            last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_ingested=datetime(2024, 1, 1, tzinfo=timezone.utc),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        DocumentStateRecord(
            source_type="jira",
            source_name="test",
            document_id="TEST-2",  # Will be marked as deleted
            content_hash="hash2",
            last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_ingested=datetime(2024, 1, 1, tzinfo=timezone.utc),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
    ]
    mock_state_manager.get_document_states.return_value = previous_states

    # Mock for deleted document retrieval
    doc_future = asyncio.Future()
    doc_future.set_result(
        Document(
            id="TEST-2",
            content="Deleted content",
            source="https://example.com",
            source_type="jira",
            metadata={
                "key": "TEST-2",
                "last_modified": "2024-01-01T00:00:00Z",
                "status": "In Progress",
            },
        )
    )
    mock_state_manager.get_document_by_key.return_value = doc_future

    # Act
    result = await jira_change_detector.detect_changes(current_docs)

    # Assert
    assert len(result["new"]) == 0
    assert len(result["updated"]) == 1
    assert result["updated"][0].metadata["key"] == "TEST-1"
    assert len(result["deleted"]) == 1
    assert result["deleted"][0].id == "TEST-2"


@pytest.mark.asyncio
async def test_detect_changes_with_same_content(jira_change_detector, mock_state_manager):
    # Arrange
    current_docs = [
        Document(
            id="TEST-1",
            content="Same content",
            source="https://example.com",
            source_type="jira",
            metadata={
                "key": "TEST-1",
                "last_modified": "2024-01-01T00:00:00Z",
                "status": "Done",
                "content_hash": "hash1",
            },
        ),
    ]
    previous_state = DocumentStateRecord(
        source_type="jira",
        source_name="test",
        document_id="TEST-1",
        content_hash="hash1",
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_ingested=datetime(2024, 1, 1, tzinfo=timezone.utc),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    mock_state_manager.get_document_states.return_value = [previous_state]

    # Act
    result = await jira_change_detector.detect_changes(current_docs)

    # Assert
    assert result["new"] == []
    assert result["updated"] == []
    assert result["deleted"] == []
