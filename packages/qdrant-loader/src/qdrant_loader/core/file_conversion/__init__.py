"""
File conversion module for qdrant-loader.

This module provides file conversion capabilities using MarkItDown,
supporting various file formats including PDF, Office documents, images, and more.
"""

import warnings

# Suppress pydub ffmpeg warning since audio processing is optional for file conversion
warnings.filterwarnings(
    "ignore", message="Couldn't find ffmpeg or avconv", category=RuntimeWarning
)

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
