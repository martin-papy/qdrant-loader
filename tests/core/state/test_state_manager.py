from datetime import datetime, UTC
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.core.state.models import Base, IngestionHistory, DocumentState

@pytest.fixture
def state_manager():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return StateManager('sqlite:///:memory:')

def test_last_ingestion_creation(state_manager):
    source_type = "test"
    source_name = "test_source"
    
    last_ingestion = state_manager.update_and_get_last_ingestion(source_type, source_name)
    assert isinstance(last_ingestion, datetime)
    assert last_ingestion.tzinfo is not None
    
    with state_manager.Session() as session:
        history = session.query(IngestionHistory).first()
        assert history is not None
        assert history.source_type == source_type
        assert history.source_name == source_name
        assert history.last_successful_ingestion == last_ingestion

def test_document_state_creation(state_manager):
    source_type = "test"
    source_name = "test_source"
    document_id = "doc1"
    last_updated = datetime.now(UTC)
    
    state = state_manager.update_and_get_document_state(
        source_type, source_name, document_id, last_updated
    )
    assert isinstance(state, DocumentState)
    assert state.last_updated.tzinfo is not None
    assert state.last_ingested.tzinfo is not None
    
    with state_manager.Session() as session:
        db_state = session.query(DocumentState).first()
        assert db_state is not None
        assert db_state.source_type == source_type
        assert db_state.source_name == source_name
        assert db_state.document_id == document_id
        assert db_state.last_updated == last_updated
        assert db_state.last_ingested == state.last_ingested

def test_document_state_mark_deleted(state_manager):
    source_type = "test"
    source_name = "test_source"
    document_id = "doc1"
    last_updated = datetime.now(UTC)
    
    # First create a document state
    state = state_manager.update_and_get_document_state(
        source_type, source_name, document_id, last_updated
    )
    
    # Then mark it as deleted
    state_manager.mark_document_deleted(source_type, source_name, document_id)
    
    with state_manager.Session() as session:
        db_state = session.query(DocumentState).first()
        assert db_state.is_deleted is True
        assert db_state.last_updated.tzinfo is not None

def test_get_document_states(state_manager):
    source_type = "test"
    source_name = "test_source"
    last_updated = datetime.now(UTC)
    
    # Create multiple document states
    for i in range(3):
        state_manager.update_and_get_document_state(
            source_type, source_name, f"doc{i}", last_updated
        )
    
    # Get all states
    states = state_manager.get_document_states(source_type, source_name)
    assert len(states) == 3
    
    # Get states since a specific time
    since = datetime.now(UTC)
    states = state_manager.get_document_states(source_type, source_name, since)
    assert len(states) == 0 