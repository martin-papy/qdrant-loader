"""Custom exceptions for file conversion operations."""

from typing import Optional


class FileConversionError(Exception):
    """Base exception for file conversion errors."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
    ):
        """Initialize the exception.

        Args:
            message: Error message
            file_path: Path to the file that failed conversion
            file_type: Type of file that failed conversion
        """
        super().__init__(message)
        self.file_path = file_path
        self.file_type = file_type


class UnsupportedFileTypeError(FileConversionError):
    """Exception raised when file type is not supported for conversion."""

    def __init__(self, file_type: str, file_path: Optional[str] = None):
        """Initialize the exception.

        Args:
            file_type: The unsupported file type
            file_path: Path to the unsupported file
        """
        message = f"File type '{file_type}' is not supported for conversion"
        super().__init__(message, file_path, file_type)


class FileSizeExceededError(FileConversionError):
    """Exception raised when file size exceeds the maximum allowed size."""

    def __init__(self, file_size: int, max_size: int, file_path: Optional[str] = None):
        """Initialize the exception.

        Args:
            file_size: Actual file size in bytes
            max_size: Maximum allowed file size in bytes
            file_path: Path to the oversized file
        """
        message = (
            f"File size {file_size} bytes exceeds maximum allowed size {max_size} bytes"
        )
        super().__init__(message, file_path)
        self.file_size = file_size
        self.max_size = max_size


class ConversionTimeoutError(FileConversionError):
    """Exception raised when file conversion times out."""

    def __init__(self, timeout: int, file_path: Optional[str] = None):
        """Initialize the exception.

        Args:
            timeout: Timeout duration in seconds
            file_path: Path to the file that timed out
        """
        message = f"File conversion timed out after {timeout} seconds"
        super().__init__(message, file_path)
        self.timeout = timeout


class MarkItDownError(FileConversionError):
    """Exception raised when MarkItDown library fails."""

    def __init__(
        self,
        original_error: Exception,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
    ):
        """Initialize the exception.

        Args:
            original_error: The original exception from MarkItDown
            file_path: Path to the file that failed conversion
            file_type: Type of file that failed conversion
        """
        message = f"MarkItDown conversion failed: {str(original_error)}"
        super().__init__(message, file_path, file_type)
        self.original_error = original_error


class FileAccessError(FileConversionError):
    """Exception raised when file cannot be accessed or read."""

    def __init__(self, file_path: str, original_error: Optional[Exception] = None):
        """Initialize the exception.

        Args:
            file_path: Path to the inaccessible file
            original_error: The original exception that caused the access error
        """
        message = f"Cannot access file: {file_path}"
        if original_error:
            message += f" - {str(original_error)}"
        super().__init__(message, file_path)
        self.original_error = original_error
