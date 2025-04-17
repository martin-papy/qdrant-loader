"""
SQLAlchemy models for state management database.
"""

from datetime import UTC

from sqlalchemy import (
    Boolean,
    Column,
    Index,
    Integer,
    String,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy import (
    DateTime as SQLDateTime,
)
from sqlalchemy.orm import declarative_base

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class UTCDateTime(TypeDecorator):
    """Automatically handle timezone information for datetime columns."""

    impl = SQLDateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not value.tzinfo:
                value = value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if not value.tzinfo:
                value = value.replace(tzinfo=UTC)
        return value


Base = declarative_base()


class IngestionHistory(Base):
    """Tracks ingestion history for each source."""

    __tablename__ = "ingestion_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String, nullable=False)
    source_name = Column(String, nullable=False)
    last_successful_ingestion = Column(UTCDateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    document_count = Column(Integer, default=0)
    error_message = Column(String)
    created_at = Column(UTCDateTime(timezone=True), nullable=False)
    updated_at = Column(UTCDateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("source_type", "source_name", name="uix_source"),)


class DocumentState(Base):
    """Tracks the state of individual documents."""

    __tablename__ = "document_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String, nullable=False)
    source_name = Column(String, nullable=False)
    document_id = Column(String, nullable=False)
    last_updated = Column(UTCDateTime(timezone=True), nullable=False)
    last_ingested = Column(UTCDateTime(timezone=True), nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(UTCDateTime(timezone=True), nullable=False)
    updated_at = Column(UTCDateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("source_type", "source_name", "document_id", name="uix_document"),
        Index("idx_document_states_source", "source_type", "source_name"),
        Index("idx_document_states_last_updated", "last_updated"),
    )
