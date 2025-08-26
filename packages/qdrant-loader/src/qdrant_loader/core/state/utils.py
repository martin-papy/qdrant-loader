"""
Utilities for StateManager: database URL construction and common query builders.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select

from qdrant_loader.core.state.exceptions import DatabaseError
from qdrant_loader.core.state.models import DocumentStateRecord, IngestionHistory


def ensure_parent_directory(db_path: Path) -> None:
    """Ensure the parent directory of the database file exists and is writable."""
    parent_dir = db_path.parent
    if not parent_dir.exists():
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # pragma: no cover - safety net
            raise DatabaseError(
                f"Cannot create database directory {parent_dir}: {e}"
            ) from e
    if not os.access(parent_dir, os.W_OK):
        raise DatabaseError(f"No write permission for database directory: {parent_dir}")


def generate_sqlite_aiosqlite_url(database_path: str) -> str:
    """Generate an aiosqlite URL from a configured database path string.

    Supports special values like ":memory:" and already-prefixed sqlite URLs.
    Ensures parent directory exists for file-backed databases.
    """
    if database_path in (":memory:", "sqlite:///:memory:", "sqlite://:memory:"):
        return "sqlite+aiosqlite:///:memory:"

    if database_path.startswith("sqlite://"):
        # Convert to aiosqlite dialect
        return database_path.replace("sqlite://", "sqlite+aiosqlite://")

    # Treat as filesystem path
    db_path = Path(database_path)
    if not db_path.is_absolute():
        db_path = db_path.resolve()

    ensure_parent_directory(db_path)

    # Normalize to POSIX path for SQLAlchemy URL
    db_url_path = db_path.as_posix()
    # Absolute and relative are handled similarly here (three slashes)
    return f"sqlite+aiosqlite:///{db_url_path}"


def build_ingestion_history_select(
    source_type: str,
    source: str,
    project_id: str | None = None,
    order_by_last_successful_desc: bool = False,
):
    """Create a select() for IngestionHistory with optional project filter and ordering."""
    query = select(IngestionHistory).filter(
        IngestionHistory.source_type == source_type, IngestionHistory.source == source
    )
    if project_id is not None:
        query = query.filter(IngestionHistory.project_id == project_id)
    if order_by_last_successful_desc:
        query = query.order_by(IngestionHistory.last_successful_ingestion.desc())
    return query


def build_document_state_select(
    source_type: str,
    source: str,
    document_id: str | None = None,
    project_id: str | None = None,
):
    """Create a select() for DocumentStateRecord with optional project/doc filters."""
    conditions = [
        DocumentStateRecord.source_type == source_type,
        DocumentStateRecord.source == source,
    ]
    if document_id is not None:
        conditions.append(DocumentStateRecord.document_id == document_id)
    query = select(DocumentStateRecord).filter(*conditions)
    if project_id is not None:
        query = query.filter(DocumentStateRecord.project_id == project_id)
    return query
