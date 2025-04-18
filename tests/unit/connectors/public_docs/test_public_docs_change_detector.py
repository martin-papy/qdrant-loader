"""Tests for public documentation change detection."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from urllib.parse import quote

import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.public_docs.config import PublicDocsSourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.state_change_detector import DocumentState, StateChangeDetector
from qdrant_loader.core.state.state_manager import StateManager


@pytest.fixture
def source_config():
    """Create a test source configuration."""
    return PublicDocsSourceConfig(
        source_type="public-docs",
        source_name="test",
        base_url=HttpUrl("https://example.com/docs"),
        version="1.0.0",
    )


@pytest.fixture
def state_manager():
    """Create a mock state manager."""
    manager = Mock(spec=StateManager)
    manager.get_document_state = AsyncMock(return_value=None)
    manager.get_document_by_url = AsyncMock(return_value=None)
    manager.get_document_states = AsyncMock(return_value=[])
    return manager


@pytest.fixture
def change_detector(source_config, state_manager):
    """Create a change detector instance."""
    return StateChangeDetector(source_config, state_manager)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        Document(
            id="doc1",
            content="Content 1",
            source="https://example.com/docs",
            source_type="public_docs",
            metadata={
                "url": "https://example.com/docs/page1",
                "title": "Page 1",
                "content_hash": "hash1",
                "last_modified": datetime.now().isoformat(),
            },
        ),
        Document(
            id="doc2",
            content="Content 2",
            source="https://example.com/docs",
            source_type="public_docs",
            metadata={
                "url": "https://example.com/docs/page2",
                "title": "Page 2",
                "content_hash": "hash2",
                "last_modified": datetime.now().isoformat(),
            },
        ),
    ]


@pytest.mark.asyncio
async def test_detect_changes_new_documents(change_detector, sample_documents):
    """Test detecting new documents."""
    changes = await change_detector.detect_changes(sample_documents)

    assert len(changes["new"]) == 2
    assert len(changes["updated"]) == 0
    assert len(changes["deleted"]) == 0
    assert changes["new"] == sample_documents


@pytest.mark.asyncio
async def test_detect_changes_updated_documents(change_detector, sample_documents, state_manager):
    """Test detecting updated documents."""

    # Create previous state for doc1
    base_url = quote("https://example.com/docs", safe="")
    previous_state = DocumentState(
        uri=f"public-docs:test:{base_url}:doc1",
        content_hash="old_hash",
        last_updated=datetime.now() - timedelta(days=1),
    )

    # Mock get_document_states to return the previous state
    state_manager.get_document_states.return_value = [previous_state]

    # Print URIs for debugging
    current_states = [change_detector._get_document_state(doc) for doc in sample_documents]
    print("\nPrevious state URI:", previous_state.uri)
    print("Current state URIs:", [state.uri for state in current_states])

    changes = await change_detector.detect_changes(sample_documents)

    assert len(changes["new"]) == 1  # doc2 is new
    assert len(changes["updated"]) == 1  # doc1 is updated
    assert len(changes["deleted"]) == 0


@pytest.mark.asyncio
async def test_detect_changes_deleted_documents(change_detector, sample_documents, state_manager):
    """Test detecting deleted documents."""
    # Mock last known URLs including the deleted one
    base_url = quote("https://example.com/docs", safe="")
    previous_state = DocumentState(
        uri=f"public-docs:test:{base_url}:deleted",
        content_hash="deleted_hash",
        last_updated=datetime.now() - timedelta(days=1),
    )
    state_manager.get_document_states.return_value = [previous_state]

    # Create the expected deleted document
    expected_deleted_doc = Document(
        content="",
        source=quote(base_url, safe=""),  # Double encode the URL
        source_type="public-docs",
        metadata={
            "uri": f"public-docs:test:{base_url}:deleted",
            "title": "Deleted Document",
            "last_modified": previous_state.last_updated.isoformat(),
            "content_hash": "deleted_hash",
            "source": quote(base_url, safe=""),  # Double encode the URL
            "source_type": "public-docs",
        },
    )

    changes = await change_detector.detect_changes(
        sample_documents,
        last_ingestion_time=datetime.now() - timedelta(days=1),
    )

    assert len(changes["new"]) == 2  # Both current documents are new
    assert len(changes["updated"]) == 0
    assert len(changes["deleted"]) == 1

    # Compare relevant fields instead of the entire Document object
    actual_deleted_doc = changes["deleted"][0]
    assert actual_deleted_doc.content == expected_deleted_doc.content
    assert actual_deleted_doc.source == expected_deleted_doc.source
    assert actual_deleted_doc.source_type == expected_deleted_doc.source_type

    # Compare metadata fields individually, ignoring created_at
    actual_metadata = actual_deleted_doc.metadata
    expected_metadata = expected_deleted_doc.metadata

    # Add created_at to expected metadata to match the actual metadata structure
    expected_metadata = dict(expected_metadata)
    expected_metadata["created_at"] = actual_deleted_doc.metadata["created_at"]

    # Compare the metadata
    assert actual_metadata == expected_metadata


@pytest.mark.asyncio
async def test_detect_changes_no_changes(change_detector, sample_documents, state_manager):
    """Test detecting no changes."""

    # Mock existing document states matching current state
    base_url = quote("https://example.com/docs", safe="")
    previous_states = [
        DocumentState(
            uri=f"public-docs:test:{base_url}:doc1",
            content_hash="hash1",
            last_updated=datetime.fromisoformat(sample_documents[0].metadata["last_modified"]),
        ),
        DocumentState(
            uri=f"public-docs:test:{base_url}:doc2",
            content_hash="hash2",
            last_updated=datetime.fromisoformat(sample_documents[1].metadata["last_modified"]),
        ),
    ]
    state_manager.get_document_states.return_value = previous_states

    changes = await change_detector.detect_changes(sample_documents)

    assert len(changes["new"]) == 0
    assert len(changes["updated"]) == 0
    assert len(changes["deleted"]) == 0
