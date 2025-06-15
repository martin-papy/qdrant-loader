"""
Enums for atomic transaction management.
"""

from enum import Enum


class TransactionState(Enum):
    """States of a distributed transaction."""

    INITIALIZED = "initialized"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    FAILED = "failed"


class OperationType(Enum):
    """Types of database operations."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    UPSERT = "upsert"
    BATCH_CREATE = "batch_create"
    BATCH_UPDATE = "batch_update"
    BATCH_DELETE = "batch_delete"
