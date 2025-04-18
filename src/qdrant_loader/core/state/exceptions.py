"""
Custom exceptions for state management.
"""


class StateError(Exception):
    """Base exception for state management errors."""

    pass


class DatabaseError(StateError):
    """Exception raised for database-related errors."""

    pass


class MigrationError(StateError):
    """Exception raised for database migration errors."""

    pass


class StateNotFoundError(StateError):
    """Exception raised when a requested state is not found."""

    pass


class StateValidationError(StateError):
    """Exception raised when state validation fails."""

    pass


class ConcurrentUpdateError(StateError):
    """Exception raised when concurrent updates are detected."""

    pass


class ChangeDetectionError(StateError):
    """Base exception for change detection errors."""

    pass


class InvalidDocumentStateError(ChangeDetectionError):
    """Raised when a document state is invalid."""

    pass


class MissingMetadataError(ChangeDetectionError):
    """Raised when required metadata is missing."""

    pass
