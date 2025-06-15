"""Shared synchronization types to avoid circular imports.

This module contains types that are shared across multiple synchronization
modules to prevent circular import issues.
"""

from enum import Enum


class SyncOperationType(Enum):
    """Types of synchronization operations."""

    CREATE_DOCUMENT = "create_document"
    UPDATE_DOCUMENT = "update_document"
    DELETE_DOCUMENT = "delete_document"
    CREATE_ENTITY = "create_entity"
    UPDATE_ENTITY = "update_entity"
    DELETE_ENTITY = "delete_entity"
    CASCADE_DELETE = "cascade_delete"
    VERSION_UPDATE = "version_update"


class SyncOperationStatus(Enum):
    """Status of synchronization operations."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
