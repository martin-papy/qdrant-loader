"""Job type constants for worker queue operations.

Consolidates all ingestion job types to prevent typo drift and enable
type-safe job handling across the codebase.
"""

from enum import StrEnum


class JobType(StrEnum):
    """Enumeration of all supported job types in the worker queue.

    Usage:
        - Batch jobs: BULK_INGEST, INCREMENTAL_PULL, CLUSTER_RECOMPUTE
        - Single-document operations: SINGLE_UPSERT, SINGLE_DELETE
    """

    # Batch operations (scheduler + admin trigger)
    BULK_INGEST = "BULK_INGEST"
    INCREMENTAL_PULL = "INCREMENTAL_PULL"
    CLUSTER_RECOMPUTE = "CLUSTER_RECOMPUTE"

    # Single-document operations (webhooks)
    SINGLE_UPSERT = "SINGLE_UPSERT"
    SINGLE_DELETE = "SINGLE_DELETE"

    def __str__(self) -> str:
        """Return the string value of the enum member."""
        return self.value
