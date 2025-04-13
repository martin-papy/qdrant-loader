"""
Unit tests for state manager.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.qdrant_loader.config import Settings, GlobalConfig, StateManagementConfig
from src.qdrant_loader.core.state.models import Base, IngestionHistory, DocumentState
from src.qdrant_loader.core.state.state_manager import StateManager

@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        OPENAI_API_KEY="test-key",
        QDRANT_URL="https://test-url",
        QDRANT_API_KEY="test-key",
        QDRANT_COLLECTION_NAME="test-collection",
        STATE_DB_PATH=":memory:"
    )

@pytest.fixture
def global_config():
    """Create test global configuration."""
    return GlobalConfig(
        state_management=StateManagementConfig(
            database_path=":memory:",
            table_prefix="test_",
            connection_pool={"size": 1, "timeout": "5s"}
        )
    )

@pytest.fixture
def state_manager(settings, global_config):
    """Create test state manager."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return StateManager(settings, global_config, Session)

def test_ingestion_history_creation(state_manager):
    """Test creating an ingestion history record."""
    with state_manager.session() as session:
        history = IngestionHistory(
            source_type="test",
            source_name="test-source",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status="completed",
            error=None
        )
        session.add(history)
        session.commit()
        assert history.id is not None

def test_document_state_creation(state_manager):
    """Test creating a document state record."""
    with state_manager.session() as session:
        doc_state = DocumentState(
            source_type="test",
            source_name="test-source",
            status="pending",
            error=None,
            metadata={"test": "value"}
        )
        session.add(doc_state)
        session.commit()
        assert doc_state.id is not None

def test_get_document_state(state_manager):
    """Test retrieving a document state."""
    with state_manager.session() as session:
        doc_state = DocumentState(
            source_type="test",
            source_name="test-source",
            status="pending",
            error=None,
            metadata={"test": "value"}
        )
        session.add(doc_state)
        session.commit()
        
        retrieved = session.query(DocumentState).filter_by(id=doc_state.id).first()
        assert retrieved is not None
        assert retrieved.source_type == "test"
        assert retrieved.status == "pending"

def test_update_document_state(state_manager):
    """Test updating a document state."""
    with state_manager.session() as session:
        doc_state = DocumentState(
            source_type="test",
            source_name="test-source",
            status="pending",
            error=None,
            metadata={"test": "value"}
        )
        session.add(doc_state)
        session.commit()
        
        doc_state.status = "completed"
        session.commit()
        
        updated = session.query(DocumentState).filter_by(id=doc_state.id).first()
        assert updated.status == "completed" 