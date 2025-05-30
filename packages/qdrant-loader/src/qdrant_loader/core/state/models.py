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
    Text,
    Float,
)
from sqlalchemy import DateTime as SQLDateTime
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
    source = Column(String, nullable=False)
    last_successful_ingestion = Column(UTCDateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    document_count = Column(Integer, default=0)
    error_message = Column(String)
    created_at = Column(UTCDateTime(timezone=True), nullable=False)
    updated_at = Column(UTCDateTime(timezone=True), nullable=False)

    # File conversion metrics
    converted_files_count = Column(Integer, default=0)
    conversion_failures_count = Column(Integer, default=0)
    attachments_processed_count = Column(Integer, default=0)
    total_conversion_time = Column(Float, default=0.0)

    __table_args__ = (UniqueConstraint("source_type", "source", name="uix_source"),)


class DocumentStateRecord(Base):
    """Tracks the state of individual documents."""

    __tablename__ = "document_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(UTCDateTime(timezone=True), nullable=False)
    updated_at = Column(UTCDateTime(timezone=True), nullable=False)

    # File conversion metadata
    is_converted = Column(Boolean, default=False)
    conversion_method = Column(
        String, nullable=True
    )  # 'markitdown', 'markitdown_fallback', etc.
    original_file_type = Column(
        String, nullable=True
    )  # Original file extension/MIME type
    original_filename = Column(String, nullable=True)  # Original filename
    file_size = Column(Integer, nullable=True)  # File size in bytes
    conversion_failed = Column(Boolean, default=False)
    conversion_error = Column(Text, nullable=True)  # Error message if conversion failed
    conversion_time = Column(
        Float, nullable=True
    )  # Time taken for conversion in seconds

    # Attachment metadata
    is_attachment = Column(Boolean, default=False)
    parent_document_id = Column(
        String, nullable=True
    )  # ID of parent document for attachments
    attachment_id = Column(String, nullable=True)  # Unique attachment identifier
    attachment_filename = Column(String, nullable=True)  # Original attachment filename
    attachment_mime_type = Column(String, nullable=True)  # MIME type of attachment
    attachment_download_url = Column(String, nullable=True)  # Original download URL
    attachment_author = Column(String, nullable=True)  # Author of attachment
    attachment_created_at = Column(
        UTCDateTime(timezone=True), nullable=True
    )  # Attachment creation date

    __table_args__ = (
        UniqueConstraint("source_type", "source", "document_id", name="uix_document"),
        Index("ix_document_url", "url"),
        Index("ix_document_converted", "is_converted"),
        Index("ix_document_attachment", "is_attachment"),
        Index("ix_document_parent", "parent_document_id"),
        Index("ix_document_conversion_method", "conversion_method"),
    )
