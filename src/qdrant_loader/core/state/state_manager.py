"""
State management service for tracking document ingestion state.
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import and_, create_engine, event, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from .exceptions import (
    ConcurrentUpdateError,
    DatabaseError,
    StateNotFoundError,
    StateValidationError,
)
from .models import Base, DocumentState, IngestionHistory
from qdrant_loader.config.state import StateManagementConfig

logger = logging.getLogger(__name__)

def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragma for timezone support."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class StateManager:
    """Manages state for document ingestion."""
    
    def __init__(self, config: StateManagementConfig):
        """Initialize the state manager with configuration."""
        db_url = config.database_path
        if not db_url.startswith('sqlite:///'):
            db_url = f'sqlite:///{db_url}'
        
        # Create sync engine for migrations and sync operations
        engine_args = {}
        if not db_url == 'sqlite:///:memory:':  # Don't use pool settings for in-memory SQLite
            engine_args.update({
                'pool_size': config.connection_pool['size'],
                'pool_timeout': config.connection_pool['timeout']
            })
            
        self.engine = create_engine(db_url, **engine_args)
        if 'sqlite' in db_url:
            event.listen(self.engine, 'connect', _set_sqlite_pragma)
        
        # Create async engine for async operations
        self.async_engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_url.replace('sqlite:///', '')}",
            **engine_args
        )
        
        # Create session factories
        self.Session = sessionmaker(bind=self.engine)
        self.AsyncSession = async_sessionmaker(bind=self.async_engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
    def update_and_get_last_ingestion(self, source_type: str, source_name: str) -> datetime:
        """Update and get the last successful ingestion time for a source."""
        with self.Session() as session:
            now = datetime.now(UTC)
            ingestion = session.query(IngestionHistory).filter_by(
                source_type=source_type,
                source_name=source_name
            ).first()

            if ingestion:
                ingestion.last_successful_ingestion = now
                ingestion.updated_at = now
            else:
                ingestion = IngestionHistory(
                    source_type=source_type,
                    source_name=source_name,
                    last_successful_ingestion=now,
                    status="success",
                    created_at=now,
                    updated_at=now
                )
                session.add(ingestion)

            session.commit()
            return ingestion.last_successful_ingestion

    def update_and_get_document_state(
        self,
        source_type: str,
        source_name: str,
        document_id: str,
        last_updated: datetime
    ) -> DocumentState:
        """Update and get the state of a document."""
        with self.Session() as session:
            now = datetime.now(UTC)
            
            state = session.query(DocumentState).filter_by(
                source_type=source_type,
                source_name=source_name,
                document_id=document_id
            ).first()

            if state:
                state.last_updated = last_updated
                state.last_ingested = now
                state.updated_at = now
            else:
                state = DocumentState(
                    source_type=source_type,
                    source_name=source_name,
                    document_id=document_id,
                    last_updated=last_updated,
                    last_ingested=now,
                    created_at=now,
                    updated_at=now
                )
                session.add(state)

            session.commit()
            session.refresh(state)
            return state

    def mark_document_deleted(
        self,
        source_type: str,
        source_name: str,
        document_id: str
    ) -> None:
        """Mark a document as deleted."""
        with self.Session() as session:
            now = datetime.now(UTC)
            state = session.query(DocumentState).filter_by(
                source_type=source_type,
                source_name=source_name,
                document_id=document_id
            ).first()

            if state:
                state.is_deleted = True
                state.last_updated = now
                state.updated_at = now
                session.commit()

    def get_document_states(
        self,
        source_type: str,
        source_name: str,
        since: Optional[datetime] = None
    ) -> List[DocumentState]:
        """Get all document states for a source, optionally filtered by last update time."""
        with self.Session() as session:
            query = session.query(DocumentState).filter_by(
                source_type=source_type,
                source_name=source_name
            )
            
            if since:
                query = query.filter(DocumentState.last_updated >= since)
            
            return query.all()

    async def get_last_ingestion(self, source_type: str, source_name: str) -> Optional[IngestionHistory]:
        """Get the last ingestion record for a source."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(IngestionHistory)
                .filter(
                    IngestionHistory.source_type == source_type,
                    IngestionHistory.source_name == source_name
                )
                .order_by(IngestionHistory.timestamp.desc())
            )
            return result.scalar_one_or_none()

    async def update_ingestion(self, source_type: str, source_name: str, status: str, count: int) -> IngestionHistory:
        """Update ingestion history for a source."""
        async with self.AsyncSession() as session:
            history = IngestionHistory(
                source_type=source_type,
                source_name=source_name,
                status=status,
                document_count=count,
                timestamp=datetime.now(UTC)
            )
            session.add(history)
            await session.commit()
            return history

    async def get_document_state(self, source_type: str, source_name: str, document_id: str) -> Optional[DocumentState]:
        """Get the state of a document."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(DocumentState)
                .filter(
                    DocumentState.source_type == source_type,
                    DocumentState.source_name == source_name,
                    DocumentState.document_id == document_id
                )
            )
            return result.scalar_one_or_none()

    async def update_document_state(self, state: DocumentState) -> DocumentState:
        """Update the state of a document."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(DocumentState)
                .filter(
                    DocumentState.source_type == state.source_type,
                    DocumentState.source_name == state.source_name,
                    DocumentState.document_id == state.document_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.last_updated = state.last_updated
                existing.last_ingested = state.last_ingested
                existing.is_deleted = state.is_deleted
                existing.updated_at = datetime.now(UTC)
                state = existing
            else:
                # Create new record
                state.created_at = datetime.now(UTC)
                state.updated_at = datetime.now(UTC)
                session.add(state)

            await session.commit()
            return state

    async def mark_document_deleted(self, source_type: str, source_name: str, document_id: str) -> DocumentState:
        """Mark a document as deleted."""
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(DocumentState)
                .filter(
                    DocumentState.source_type == source_type,
                    DocumentState.source_name == source_name,
                    DocumentState.document_id == document_id
                )
            )
            state = result.scalar_one_or_none()

            if not state:
                raise StateNotFoundError(f"Document state not found for {source_type}/{source_name}/{document_id}")

            state.is_deleted = True
            state.updated_at = datetime.now(UTC)
            await session.commit()
            return state 