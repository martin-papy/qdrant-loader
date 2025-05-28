"""
State management module for tracking document ingestion state.

This module provides functionality for tracking the state of document ingestion,
including last successful ingestion times, document states, and change detection.
"""

from .exceptions import (
    DatabaseError,
    InvalidDocumentStateError,
    MigrationError,
    MissingMetadataError,
    StateError,
)
from .models import DocumentStateRecord, IngestionHistory
from .state_manager import StateManager

__all__ = [
    "DatabaseError",
    "DocumentStateRecord",
    "IngestionHistory",
    "InvalidDocumentStateError",
    "MigrationError",
    "MissingMetadataError",
    "StateError",
    "StateManager",
]
