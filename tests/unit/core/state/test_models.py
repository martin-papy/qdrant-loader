"""
Unit tests for state management models.
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.qdrant_loader.core.state.models import Base, IngestionHistory, DocumentState

@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_ingestion_history_creation(db_session):
    """Test creating an IngestionHistory record."""
    history = IngestionHistory(
        source_type='git',
        source_name='test-repo',
        last_successful_ingestion=datetime.now(UTC),
        status='success',
        document_count=10
    )
    
    db_session.add(history)
    db_session.commit()
    
    # Verify the record was created
    saved_history = db_session.query(IngestionHistory).first()
    assert saved_history is not None
    assert saved_history.source_type == 'git'
    assert saved_history.source_name == 'test-repo'
    assert saved_history.status == 'success'
    assert saved_history.document_count == 10
    assert saved_history.error_message is None
    assert saved_history.created_at is not None
    assert saved_history.updated_at is not None

def test_document_state_creation(db_session):
    """Test creating a DocumentState record."""
    now = datetime.now(UTC)
    state = DocumentState(
        id='test-doc-1',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now
    )
    
    db_session.add(state)
    db_session.commit()
    
    # Verify the record was created
    saved_state = db_session.query(DocumentState).first()
    assert saved_state is not None
    assert saved_state.id == 'test-doc-1'
    assert saved_state.source_type == 'git'
    assert saved_state.source_name == 'test-repo'
    assert saved_state.document_id == 'doc-1'
    assert saved_state.last_updated == now
    assert saved_state.last_ingested == now
    assert saved_state.is_deleted is False
    assert saved_state.created_at is not None
    assert saved_state.updated_at is not None

def test_document_state_unique_constraint(db_session):
    """Test the unique constraint on document states."""
    now = datetime.now(UTC)
    state1 = DocumentState(
        id='test-doc-1',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now
    )
    
    state2 = DocumentState(
        id='test-doc-2',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',  # Same document_id as state1
        last_updated=now,
        last_ingested=now
    )
    
    db_session.add(state1)
    db_session.commit()
    
    # Adding state2 should raise an integrity error
    with pytest.raises(Exception):
        db_session.add(state2)
        db_session.commit()

def test_document_state_mark_deleted(db_session):
    """Test marking a document as deleted."""
    now = datetime.now(UTC)
    state = DocumentState(
        id='test-doc-1',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now
    )
    
    db_session.add(state)
    db_session.commit()
    
    # Mark as deleted
    state.is_deleted = True
    db_session.commit()
    
    # Verify the update
    saved_state = db_session.query(DocumentState).first()
    assert saved_state.is_deleted is True
    assert saved_state.updated_at > now  # updated_at should be updated 