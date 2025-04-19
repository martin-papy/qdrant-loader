"""Tests for Git change detector."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.git.config import GitRepoConfig
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
def git_change_detector(mock_state_manager):
    return StateChangeDetector(
        state_manager=mock_state_manager,
        source_config=GitRepoConfig(
            source_type="git",
            source="test",
            base_url=HttpUrl("https://github.com/example/repo.git"),
            branch="main",
            depth=1,
            file_types=["*.md", "*.txt"],
            include_paths=["docs/**/*"],
            exclude_paths=["tests/**/*"],
            max_file_size=1024 * 1024,  # 1MB
            token="test-token",
            temp_dir="/tmp/test",
        ),
    )


@pytest.mark.asyncio
async def test_detect_changes_new_documents(git_change_detector, mock_state_manager):
    # Arrange
    documents = [
        Document(
            id="file1.md",
            content="Test content 1",
            source="https://github.com/example/repo.git",
            source_type="git",
            metadata={
                "path": "docs/file1.md",
                "last_modified": "2024-01-01T00:00:00Z",
                "content_hash": "hash1",
            },
        ),
        Document(
            id="file2.md",
            content="Test content 2",
            source="https://github.com/example/repo.git",
            source_type="git",
            metadata={
                "path": "docs/file2.md",
                "last_modified": "2024-01-01T00:00:00Z",
                "content_hash": "hash2",
            },
        ),
    ]
    mock_state_manager.get_document_states.return_value = []

    # Act
    result = await git_change_detector.detect_changes(documents)

    # Assert
    assert result["new"] == documents
    assert result["updated"] == []
    assert result["deleted"] == []
    mock_state_manager.get_document_states.assert_called_once()


@pytest.mark.asyncio
async def test_detect_changes_updated_documents(git_change_detector, mock_state_manager):
    # Arrange
    current_docs = [
        Document(
            id="file1.md",
            content="Updated content",
            source="https://github.com/example/repo.git",
            source_type="git",
            metadata={
                "path": "docs/file1.md",
                "last_modified": "2024-01-02T00:00:00Z",
                "content_hash": "hash1_updated",
            },
        ),
        Document(
            id="file2.md",
            content="New content",
            source="https://github.com/example/repo.git",
            source_type="git",
            metadata={
                "path": "docs/file2.md",
                "last_modified": "2024-01-01T00:00:00Z",
                "content_hash": "hash2",
            },
        ),
    ]
    previous_state = DocumentStateRecord(
        source_type="git",
        source="test",
        document_id="file1.md",
        content_hash="hash1",
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_ingested=datetime(2024, 1, 1, tzinfo=timezone.utc),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    mock_state_manager.get_document_states.return_value = [previous_state]

    # Act
    result = await git_change_detector.detect_changes(current_docs)

    # Assert
    assert len(result["new"]) == 1
    assert result["new"][0].id == "file2.md"
    assert len(result["updated"]) == 1
    assert result["updated"][0].id == "file1.md"
    assert result["deleted"] == []


@pytest.mark.asyncio
async def test_detect_changes_deleted_documents(git_change_detector, mock_state_manager):
    # Arrange
    # Current documents - only file1.md exists
    current_docs = [
        Document(
            id="file1.md",
            content="Updated content",
            source="https://github.com/example/repo.git",
            source_type="git",
            metadata={
                "path": "docs/file1.md",
                "last_modified": "2024-01-02T00:00:00Z",
                "content_hash": "hash1_updated",
            },
        ),
    ]

    # Previous state - both file1.md and file2.md exist
    previous_states = [
        DocumentStateRecord(
            source_type="git",
            source="test",
            document_id="file1.md",
            content_hash="hash1",
            last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_ingested=datetime(2024, 1, 1, tzinfo=timezone.utc),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        DocumentStateRecord(
            source_type="git",
            source="test",
            document_id="file2.md",
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
            id="file2.md",
            content="Deleted content",
            source="https://github.com/example/repo.git",
            source_type="git",
            metadata={
                "path": "docs/file2.md",
                "last_modified": "2024-01-01T00:00:00Z",
                "content_hash": "hash2",
            },
        )
    )
    mock_state_manager.get_document_by_key.return_value = doc_future

    # Act
    result = await git_change_detector.detect_changes(current_docs)

    # Assert
    assert len(result["new"]) == 0
    assert len(result["updated"]) == 1
    assert result["updated"][0].id == "file1.md"
    assert len(result["deleted"]) == 1
    assert result["deleted"][0].id == "file2.md"


@pytest.mark.asyncio
async def test_detect_changes_no_changes(git_change_detector, mock_state_manager):
    # Arrange
    current_docs = [
        Document(
            id="file1.md",
            content="Test content",
            source="https://github.com/example/repo.git",
            source_type="git",
            metadata={
                "path": "docs/file1.md",
                "last_modified": "2024-01-01T00:00:00Z",
                "content_hash": "hash1",
            },
        ),
    ]
    previous_state = DocumentStateRecord(
        source_type="git",
        source="test",
        document_id="file1.md",
        content_hash="hash1",
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_ingested=datetime(2024, 1, 1, tzinfo=timezone.utc),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    mock_state_manager.get_document_states.return_value = [previous_state]

    # Act
    result = await git_change_detector.detect_changes(current_docs)

    # Assert
    assert result["new"] == []
    assert result["updated"] == []
    assert result["deleted"] == []
