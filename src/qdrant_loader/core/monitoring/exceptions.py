"""
Custom exceptions for performance monitoring.
"""


class OperationError(Exception):
    """Base class for operation-related errors."""
    pass


class OperationTimeoutError(OperationError):
    """Raised when an operation times out."""
    pass


class OperationStateError(OperationError):
    """Raised when operation state is invalid."""
    pass 