"""Unit tests for the state manager."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sqlite3
import os
import tempfile

import pytest
import pytest_asyncio
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import IngestionStatus, StateManagementConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.exceptions import DatabaseError, StateError
from qdrant_loader.core.state.models import Base, DocumentStateRecord, IngestionHistory
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


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return Document(
        id="test-doc-1",
        title="Test Document",
        content="Test content",
        source_type="test",
        source="test-source",
        url="http://test.com/doc1",
        metadata={},
    )


@pytest.mark.asyncio
async def test_initialization(mock_config):
    """Test state manager initialization."""
    manager = StateManager(mock_config)
    await manager.initialize()
    assert manager._initialized is True
    assert manager._engine is not None
    assert manager._session_factory is not None
    await manager.dispose()


@pytest.mark.asyncio
async def test_initialization_error():
    """Test initialization error handling."""
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the database file first
        db_path = os.path.join(temp_dir, "db.sqlite")

        # Create an empty file
        with open(db_path, "w") as f:
            pass

        # Make the database file read-only
        os.chmod(db_path, 0o444)

        # Try to initialize a manager with the read-only database
        config = MagicMock(spec=StateManagementConfig)
        config.database_path = db_path
        config.connection_pool = {"size": 5, "timeout": 30}
        manager = StateManager(config)

        with pytest.raises((DatabaseError, sqlite3.OperationalError)):
            await manager.initialize()  # This should fail because the database is read-only

        # Clean up by making the file writable again so it can be deleted
        os.chmod(db_path, 0o644)


@pytest.mark.asyncio
async def test_update_last_ingestion(state_manager):
    """Test updating last ingestion time."""
    source_type = "test"
    source = "test-source"

    await state_manager.update_last_ingestion(
        source_type=source_type, source=source, status=IngestionStatus.SUCCESS, document_count=10
    )

    history = await state_manager.get_last_ingestion(source_type, source)
    assert history is not None
    assert history.source_type == source_type
    assert history.source == source
    assert history.status == IngestionStatus.SUCCESS
    assert history.document_count == 10


@pytest.mark.asyncio
async def test_update_last_ingestion_error(state_manager):
    """Test error handling when updating last ingestion."""
    with patch.object(state_manager, "_session_factory", side_effect=Exception("Test error")):
        with pytest.raises(Exception):
            await state_manager.update_last_ingestion(
                source_type="test",
                source="test-source",
                status=IngestionStatus.FAILED,
                error_message="Test error",
            )


@pytest.mark.asyncio
async def test_update_document_state(state_manager, sample_document):
    """Test updating document state."""
    # First update
    record = await state_manager.update_document_state(sample_document)
    assert record.document_id == sample_document.id
    assert record.content_hash == sample_document.content_hash
    assert record.is_deleted is False

    # Update with changes
    updated_document = Document(
        id=sample_document.id,
        title="Updated Title",
        content="Updated content",
        source_type=sample_document.source_type,
        source=sample_document.source,
        url=sample_document.url,
        metadata=sample_document.metadata,
    )
    updated_record = await state_manager.update_document_state(updated_document)
    assert updated_record.title == "Updated Title"
    assert updated_record.content_hash != record.content_hash


@pytest.mark.asyncio
async def test_mark_document_deleted(state_manager, sample_document):
    """Test marking a document as deleted."""
    # First create the document state
    await state_manager.update_document_state(sample_document)

    # Mark as deleted
    await state_manager.mark_document_deleted(
        source_type=sample_document.source_type,
        source=sample_document.source,
        document_id=sample_document.id,
    )

    # Verify deletion
    record = await state_manager.get_document_state_record(
        source_type=sample_document.source_type,
        source=sample_document.source,
        document_id=sample_document.id,
    )
    assert record is not None
    assert record.is_deleted is True


@pytest.mark.asyncio
async def test_get_document_state_records(state_manager, sample_document):
    """Test retrieving document state records."""
    # Create multiple documents
    documents = [
        sample_document,
        Document(
            id="test-doc-2",
            title="Test Document 2",
            content="Test content 2",
            source_type="test",
            source="test-source",
            url="http://test.com/doc2",
            metadata={},
        ),
    ]

    # Update states
    for doc in documents:
        await state_manager.update_document_state(doc)

    # Get records
    source_config = SourceConfig(
        source_type="test", source="test-source", base_url=HttpUrl("http://test.com")
    )
    records = await state_manager.get_document_state_records(source_config)

    assert len(records) == 2
    assert all(record.source_type == "test" for record in records)
    assert all(record.source == "test-source" for record in records)


@pytest.mark.asyncio
async def test_get_document_state_records_since(state_manager, sample_document):
    """Test retrieving document state records with since filter."""
    # Create initial document
    await state_manager.update_document_state(sample_document)

    # Wait a moment
    await asyncio.sleep(0.1)
    since = datetime.now(UTC)

    # Create another document after the since time
    new_doc = Document(
        id="test-doc-2",
        title="New Document",
        content="New content",
        source_type="test",
        source="test-source",
        url="http://test.com/doc2",
        metadata={},
    )
    new_record = await state_manager.update_document_state(new_doc)

    # Get records since the timestamp
    source_config = SourceConfig(
        source_type="test", source="test-source", base_url=HttpUrl("http://test.com")
    )
    records = await state_manager.get_document_state_records(source_config, since=since)

    assert len(records) == 1
    assert records[0].document_id == new_record.document_id


@pytest.mark.asyncio
async def test_context_manager(mock_config):
    """Test state manager as context manager."""
    manager = StateManager(mock_config)
    await manager.initialize()
    async with manager:
        assert manager._initialized is True
    assert manager._initialized is False
