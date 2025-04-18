"""
Unit tests for state manager.
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine

from qdrant_loader.core.state.models import Base, IngestionHistory, DocumentStateRecord
from qdrant_loader.core.state.state_manager import StateManager


@pytest.fixture
def state_manager(test_global_config):
    """Create test state manager."""
    return StateManager(test_global_config.state_management)


def test_ingestion_history_creation(state_manager):
    """Test creating an ingestion history record."""
    with state_manager.Session() as session:
        now = datetime.now(UTC)
        history = IngestionHistory(
            source_type="test",
            source_name="test-source",
            last_successful_ingestion=now,
            status="completed",
            document_count=1,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        session.add(history)
        session.commit()
        assert history.id is not None


def test_document_state_creation(state_manager):
    """Test creating a document state record."""
    with state_manager.Session() as session:
        now = datetime.now(UTC)
        doc_state = DocumentStateRecord(
            source_type="test",
            source_name="test-source",
            document_id="doc-1",
            last_updated=now,
            last_ingested=now,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(doc_state)
        session.commit()
        assert doc_state.id is not None


def test_get_document_state(state_manager):
    """Test retrieving a document state."""
    with state_manager.Session() as session:
        now = datetime.now(UTC)
        doc_state = DocumentStateRecord(
            source_type="test",
            source_name="test-source",
            document_id="doc-1",
            last_updated=now,
            last_ingested=now,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(doc_state)
        session.commit()

        retrieved = session.query(DocumentStateRecord).filter_by(id=doc_state.id).first()
        assert retrieved is not None
        assert retrieved.source_type == "test"
        assert retrieved.document_id == "doc-1"


def test_update_document_state(state_manager):
    """Test updating a document state."""
    with state_manager.Session() as session:
        now = datetime.now(UTC)
        doc_state = DocumentStateRecord(
            source_type="test",
            source_name="test-source",
            document_id="doc-1",
            last_updated=now,
            last_ingested=now,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(doc_state)
        session.commit()

        doc_state.is_deleted = True  # type: ignore
        session.commit()

        updated = session.query(DocumentStateRecord).filter_by(id=doc_state.id).first()
        assert updated.is_deleted is True
