"""
Custom exceptions for state management.
"""


class StateError(Exception):
    """Base exception for state management errors."""


class DatabaseError(StateError):
    """Exception raised for database-related errors."""


class MigrationError(StateError):
    """Exception raised for database migration errors."""


class StateNotFoundError(StateError):
    """Exception raised when a requested state is not found."""


class StateValidationError(StateError):
    """Exception raised when state validation fails."""


class ConcurrentUpdateError(StateError):
    """Exception raised when concurrent updates are detected."""


class ChangeDetectionError(StateError):
    """Base exception for change detection errors."""


class InvalidDocumentStateError(ChangeDetectionError):
    """Raised when a document state is invalid."""


class MissingMetadataError(ChangeDetectionError):
    """Raised when required metadata is missing."""
