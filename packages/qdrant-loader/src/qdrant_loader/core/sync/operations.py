"""Sync Operation Types and Data Structures.

This module defines the core data structures and enums for synchronization operations
in the enhanced sync event system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..managers import MappingType
from ..types import EntityType
from .event_system import ChangeEvent, DatabaseType
from .types import SyncOperationStatus, SyncOperationType


@dataclass
class EnhancedSyncOperation:
    """Enhanced synchronization operation with atomic transaction support."""

    # Operation identification
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Operation details
    operation_type: SyncOperationType = SyncOperationType.UPDATE_DOCUMENT
    source_event: ChangeEvent | None = None
    target_databases: set[DatabaseType] = field(default_factory=set)

    # Entity information
    entity_id: str | None = None
    entity_uuid: str | None = None
    entity_type: EntityType = EntityType.CONCEPT
    mapping_type: MappingType = MappingType.DOCUMENT

    # Operation data
    operation_data: dict[str, Any] = field(default_factory=dict)
    previous_data: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Versioning information
    document_version: int = 1
    previous_version: int | None = None
    content_hash: str | None = None

    # Processing status
    status: SyncOperationStatus = SyncOperationStatus.PENDING
    transaction_id: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3

    # Relationships and dependencies
    related_operations: list[str] = field(default_factory=list)
    dependent_operations: list[str] = field(default_factory=list)

    def mark_processing(self, transaction_id: str) -> None:
        """Mark operation as processing with transaction ID."""
        self.status = SyncOperationStatus.PROCESSING
        self.transaction_id = transaction_id

    def mark_completed(self) -> None:
        """Mark operation as completed."""
        self.status = SyncOperationStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        """Mark operation as failed with error message."""
        self.status = SyncOperationStatus.FAILED
        self.error_message = error
        self.retry_count += 1

    def mark_rolled_back(self) -> None:
        """Mark operation as rolled back."""
        self.status = SyncOperationStatus.ROLLED_BACK

    def can_retry(self) -> bool:
        """Check if operation can be retried."""
        return (
            self.retry_count < self.max_retries
            and self.status == SyncOperationStatus.FAILED
        )
