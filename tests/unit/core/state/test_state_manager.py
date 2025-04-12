"""
Unit tests for StateManager class.
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.qdrant_loader.core.state.state_manager import StateManager
from src.qdrant_loader.core.state.models import DocumentState
from src.qdrant_loader.core.state.exceptions import StateNotFoundError

@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
        yield tmp.name

@pytest.fixture
def state_manager(temp_db):
    """Create a StateManager instance with a temporary database."""
    return StateManager(temp_db)

@pytest.mark.asyncio
async def test_get_last_ingestion_no_history(state_manager):
    """Test getting last ingestion time when no history exists."""
    result = await state_manager.get_last_ingestion('git', 'test-repo')
    assert result is None

@pytest.mark.asyncio
async def test_update_and_get_last_ingestion(state_manager):
    """Test updating and getting last ingestion time."""
    # Update ingestion history
    await state_manager.update_ingestion(
        source_type='git',
        source_name='test-repo',
        status='success',
        count=10
    )
    
    # Get last ingestion time
    result = await state_manager.get_last_ingestion('git', 'test-repo')
    assert result is not None
    assert isinstance(result, datetime)
    assert (datetime.utcnow() - result) < timedelta(seconds=1)

@pytest.mark.asyncio
async def test_get_document_state_not_found(state_manager):
    """Test getting a non-existent document state."""
    result = await state_manager.get_document_state('git', 'test-repo', 'doc-1')
    assert result is None

@pytest.mark.asyncio
async def test_update_and_get_document_state(state_manager):
    """Test updating and getting a document state."""
    now = datetime.utcnow()
    state = DocumentState(
        id='test-doc-1',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now
    )
    
    # Update document state
    await state_manager.update_document_state(state)
    
    # Get document state
    result = await state_manager.get_document_state('git', 'test-repo', 'doc-1')
    assert result is not None
    assert result.id == 'test-doc-1'
    assert result.source_type == 'git'
    assert result.source_name == 'test-repo'
    assert result.document_id == 'doc-1'
    assert result.last_updated == now
    assert result.last_ingested == now
    assert result.is_deleted is False

@pytest.mark.asyncio
async def test_mark_document_deleted_not_found(state_manager):
    """Test marking a non-existent document as deleted."""
    with pytest.raises(StateNotFoundError):
        await state_manager.mark_document_deleted('git', 'test-repo', 'doc-1')

@pytest.mark.asyncio
async def test_mark_document_deleted(state_manager):
    """Test marking a document as deleted."""
    now = datetime.utcnow()
    state = DocumentState(
        id='test-doc-1',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now
    )
    
    # Create document state
    await state_manager.update_document_state(state)
    
    # Mark as deleted
    await state_manager.mark_document_deleted('git', 'test-repo', 'doc-1')
    
    # Verify the update
    result = await state_manager.get_document_state('git', 'test-repo', 'doc-1')
    assert result is not None
    assert result.is_deleted is True
    assert result.updated_at > now

@pytest.mark.asyncio
async def test_concurrent_updates(state_manager):
    """Test handling concurrent updates."""
    now = datetime.utcnow()
    state1 = DocumentState(
        id='test-doc-1',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now,
        last_ingested=now
    )
    
    state2 = DocumentState(
        id='test-doc-1',
        source_type='git',
        source_name='test-repo',
        document_id='doc-1',
        last_updated=now + timedelta(minutes=1),
        last_ingested=now + timedelta(minutes=1)
    )
    
    # First update
    await state_manager.update_document_state(state1)
    
    # Second update should succeed (merge)
    await state_manager.update_document_state(state2)
    
    # Verify the final state
    result = await state_manager.get_document_state('git', 'test-repo', 'doc-1')
    assert result is not None
    assert result.last_updated == now + timedelta(minutes=1)
    assert result.last_ingested == now + timedelta(minutes=1) 