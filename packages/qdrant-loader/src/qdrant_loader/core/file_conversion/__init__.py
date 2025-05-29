"""File conversion module for qdrant-loader."""

from .conversion_config import (
    ConnectorFileConversionConfig,
    FileConversionConfig,
    MarkItDownConfig,
)
from .exceptions import (
    ConversionTimeoutError,
    FileAccessError,
    FileConversionError,
    FileSizeExceededError,
    MarkItDownError,
    UnsupportedFileTypeError,
)
from .file_converter import FileConverter
from .file_detector import FileDetector

__all__ = [
    # Configuration
    "FileConversionConfig",
    "MarkItDownConfig",
    "ConnectorFileConversionConfig",
    # Core services
    "FileConverter",
    "FileDetector",
    # Exceptions
    "FileConversionError",
    "UnsupportedFileTypeError",
    "FileSizeExceededError",
    "ConversionTimeoutError",
    "MarkItDownError",
    "FileAccessError",
]
