"""
State management module for tracking document ingestion state.

This module provides functionality for tracking the state of document ingestion,
including last successful ingestion times, document states, and change detection.
"""

__version__ = "0.1.0"

from .state_manager import StateManager
from .models import DocumentState, IngestionHistory
from .exceptions import StateError, DatabaseError, MigrationError

__all__ = [
    "StateManager",
    "DocumentState",
    "IngestionHistory",
    "StateError",
    "DatabaseError",
    "MigrationError",
]
