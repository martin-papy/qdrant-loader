"""
Unit tests for state models.
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.qdrant_loader.core.state.models import Base, IngestionHistory, DocumentState

@pytest.fixture
def db_engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(db_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()

def test_ingestion_history_creation(db_session):
    """Test creating an ingestion history record."""
    now = datetime.now(UTC)
    history = IngestionHistory(
        source_type="test",
        source_name="test-source",
        last_successful_ingestion=now,
        status="completed",
        document_count=1,
        error_message=None,
        created_at=now,
        updated_at=now
    )
    db_session.add(history)
    db_session.commit()
    assert history.id is not None

def test_document_state_creation(db_session):
    """Test creating a DocumentState record."""
    now = datetime.now(UTC)
    state = DocumentState(
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now,
        is_deleted=False,
        created_at=now,
        updated_at=now
    )

    db_session.add(state)
    db_session.commit()
    assert state.id is not None

def test_document_state_unique_constraint(db_session):
    """Test the unique constraint on document states."""
    now = datetime.now(UTC)
    state1 = DocumentState(
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now,
        is_deleted=False,
        created_at=now,
        updated_at=now
    )

    state2 = DocumentState(
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',  # Same document_id as state1
        last_updated=now,
        last_ingested=now,
        is_deleted=False,
        created_at=now,
        updated_at=now
    )

    db_session.add(state1)
    db_session.commit()

    db_session.add(state2)
    with pytest.raises(Exception):  # Should raise due to unique constraint
        db_session.commit()

def test_document_state_mark_deleted(db_session):
    """Test marking a document as deleted."""
    now = datetime.now(UTC)
    state = DocumentState(
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now,
        is_deleted=False,
        created_at=now,
        updated_at=now
    )

    db_session.add(state)
    db_session.commit()

    state.is_deleted = True
    state.updated_at = datetime.now(UTC)
    db_session.commit()

    updated = db_session.query(DocumentState).filter_by(id=state.id).first()
    assert updated.is_deleted is True 