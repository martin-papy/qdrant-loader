"""Tests for Confluence change detector."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
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
def confluence_change_detector(mock_state_manager):
    return StateChangeDetector(
        state_manager=mock_state_manager,
        source_config=ConfluenceSpaceConfig(
            source_type="confluence",
            source_name="test",
            base_url=HttpUrl("https://confluence.example.com"),
            space_key="TEST",
            token="test-token",
            email="test@example.com",
        ),
    )


@pytest.mark.asyncio
async def test_detect_changes_new_document(confluence_change_detector, mock_state_manager):
    # Arrange
    documents = [
        Document(
            id="123",
            content="Test content",
            source="https://confluence.example.com",
            source_type="confluence",
            metadata={
                "key": "123",
                "url": "https://confluence.example.com/pages/123",
                "title": "Test Page",
                "content_hash": "abc123",
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "version": 1,
            },
        ),
    ]
    mock_state_manager.get_document_states.return_value = []

    # Act
    result = await confluence_change_detector.detect_changes(documents)

    # Assert
    assert result["new"] == documents
    assert result["updated"] == []
    assert result["deleted"] == []
    mock_state_manager.get_document_states.assert_called_once()


@pytest.mark.asyncio
async def test_detect_changes_updated_document(confluence_change_detector, mock_state_manager):
    # Arrange
    current_docs = [
        Document(
            id="123",
            content="Updated content",
            source="https://confluence.example.com",
            source_type="confluence",
            metadata={
                "key": "123",
                "url": "https://confluence.example.com/pages/123",
                "title": "Updated Page",
                "content_hash": "def456",
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "version": 2,
            },
        ),
    ]
    previous_state = DocumentStateRecord(
        source_type="confluence",
        source_name="test",
        document_id="123",
        content_hash="abc123",
        last_updated=datetime.now(timezone.utc),
        last_ingested=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_state_manager.get_document_states.return_value = [previous_state]

    # Act
    result = await confluence_change_detector.detect_changes(current_docs)

    # Assert
    assert len(result["new"]) == 0
    assert len(result["updated"]) == 1
    assert result["updated"][0].metadata["key"] == "123"
    assert result["deleted"] == []


@pytest.mark.asyncio
async def test_detect_changes_deleted_document(confluence_change_detector, mock_state_manager):
    # Arrange
    current_docs = [
        Document(
            id="123",
            content="Updated content",
            source="https://confluence.example.com",
            source_type="confluence",
            metadata={
                "key": "123",
                "url": "https://confluence.example.com/pages/123",
                "title": "Updated Page",
                "content_hash": "def456",
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "version": 2,
            },
        ),
    ]
    previous_states = [
        DocumentStateRecord(
            source_type="confluence",
            source_name="test",
            document_id="123",
            content_hash="abc123",
            last_updated=datetime.now(timezone.utc),
            last_ingested=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        DocumentStateRecord(
            source_type="confluence",
            source_name="test",
            document_id="456",
            content_hash="xyz789",
            last_updated=datetime.now(timezone.utc),
            last_ingested=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    mock_state_manager.get_document_states.return_value = previous_states

    doc_future = asyncio.Future()
    doc_future.set_result(
        Document(
            id="456",
            content="Deleted content",
            source="https://confluence.example.com",
            source_type="confluence",
            metadata={
                "key": "456",
                "url": "https://confluence.example.com/pages/456",
                "title": "Deleted Page",
                "content_hash": "xyz789",
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "version": 1,
            },
        )
    )
    mock_state_manager.get_document_by_key.return_value = doc_future

    # Act
    result = await confluence_change_detector.detect_changes(current_docs)

    # Assert
    assert len(result["new"]) == 0
    assert len(result["updated"]) == 1
    assert result["updated"][0].metadata["key"] == "123"
    assert len(result["deleted"]) == 1
    assert result["deleted"][0].id == "456"


@pytest.mark.asyncio
async def test_detect_changes_no_changes(confluence_change_detector, mock_state_manager):
    # Arrange
    current_docs = [
        Document(
            id="123",
            content="Test content",
            source="https://confluence.example.com",
            source_type="confluence",
            metadata={
                "key": "123",
                "url": "https://confluence.example.com/pages/123",
                "title": "Test Page",
                "content_hash": "abc123",
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "version": 1,
            },
        ),
    ]
    previous_state = DocumentStateRecord(
        source_type="confluence",
        source_name="test",
        document_id="123",
        content_hash="abc123",
        last_updated=datetime.now(timezone.utc),
        last_ingested=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_state_manager.get_document_states.return_value = [previous_state]

    # Act
    result = await confluence_change_detector.detect_changes(current_docs)

    # Assert
    assert result["new"] == []
    assert result["updated"] == []
    assert result["deleted"] == []
