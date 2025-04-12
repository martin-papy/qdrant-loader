"""
State management service for tracking document ingestion state.
"""

import os
import logging
from datetime import datetime, UTC
from typing import Optional, List
from pathlib import Path
from sqlalchemy import create_engine, select, update, and_, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, IngestionHistory, DocumentState
from .exceptions import (
    DatabaseError,
    StateNotFoundError,
    StateValidationError,
    ConcurrentUpdateError
)

logger = logging.getLogger(__name__)

def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragma for timezone support."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class StateManager:
    """Manages the state of document ingestion."""
    
    def __init__(self, db_url: str):
        """
        Initialize the state manager.
        
        Args:
            db_url: URL to the database
        """
        self.engine = create_engine(db_url)
        
        if 'sqlite' in db_url:
            event.listen(self.engine, 'connect', _set_sqlite_pragma)
            
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
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