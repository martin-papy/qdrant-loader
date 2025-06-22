"""Base Exceptions for QDrant Loader.

This module defines the base exception classes used throughout the QDrant Loader
application to provide consistent error handling and reporting.
"""


class QDrantLoaderError(Exception):
    """Base exception for all QDrant Loader errors.
    
    This is the base class for all custom exceptions in the QDrant Loader
    application. It provides a consistent interface for error handling.
    """
    
    def __init__(self, message: str, *args, **kwargs):
        """Initialize the exception with a message.
        
        Args:
            message: The error message describing what went wrong.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(message, *args)
        self.message = message
        self.context = kwargs
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.context:
            context_str = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            return f"{self.message} ({context_str})"
        return self.message


class ConfigurationError(QDrantLoaderError):
    """Exception raised for configuration-related errors."""
    pass


class ValidationError(QDrantLoaderError):
    """Exception raised for validation errors."""
    pass


class ConnectionError(QDrantLoaderError):
    """Exception raised for connection-related errors."""
    pass


class ProcessingError(QDrantLoaderError):
    """Exception raised for data processing errors."""
    pass 