"""Main file conversion service using MarkItDown."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion.conversion_config import FileConversionConfig
from qdrant_loader.core.file_conversion.exceptions import (
    ConversionTimeoutError,
    FileAccessError,
    FileSizeExceededError,
    MarkItDownError,
    UnsupportedFileTypeError,
)
from qdrant_loader.core.file_conversion.file_detector import FileDetector
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class FileConverter:
    """Service for converting files to Markdown using MarkItDown."""

    def __init__(self, config: FileConversionConfig):
        """Initialize the file converter."""
        self.config = config
        self.file_detector = FileDetector()
        self.logger = LoggingConfig.get_logger(__name__)
        self._markitdown = None

    def _get_markitdown(self):
        """Get MarkItDown instance with lazy loading."""
        if self._markitdown is None:
            try:
                from markitdown import MarkItDown  # type: ignore

                self._markitdown = MarkItDown()
                self.logger.debug("MarkItDown initialized successfully")
            except ImportError as e:
                raise MarkItDownError(
                    Exception("MarkItDown library not available")
                ) from e
        return self._markitdown

    def convert_file(self, file_path: str) -> str:
        """Convert a file to Markdown format."""
        self.logger.info("Starting file conversion", file_path=file_path)

        try:
            self._validate_file(file_path)
            markitdown = self._get_markitdown()
            result = markitdown.convert(file_path)

            if hasattr(result, "text_content"):
                markdown_content = result.text_content
            else:
                markdown_content = str(result)

            self.logger.info(
                "File conversion completed",
                file_path=file_path,
                content_length=len(markdown_content),
            )
            return markdown_content

        except Exception as e:
            self.logger.error(
                "File conversion failed", file_path=file_path, error=str(e)
            )
            raise MarkItDownError(e, file_path) from e

    def _validate_file(self, file_path: str) -> None:
        """Validate file for conversion."""
        if not os.path.exists(file_path):
            raise FileAccessError(f"File does not exist: {file_path}")

        if not os.access(file_path, os.R_OK):
            raise FileAccessError(f"File is not readable: {file_path}")

        file_size = os.path.getsize(file_path)
        if not self.config.is_file_size_allowed(file_size):
            raise FileSizeExceededError(file_size, self.config.max_file_size, file_path)

        if not self.file_detector.is_supported_for_conversion(file_path):
            file_info = self.file_detector.get_file_type_info(file_path)
            raise UnsupportedFileTypeError(
                file_info.get("normalized_type", "unknown"), file_path
            )

    def create_fallback_document(self, file_path: str, error: Exception) -> str:
        """Create a fallback Markdown document when conversion fails."""
        filename = Path(file_path).name
        file_info = self.file_detector.get_file_type_info(file_path)

        return f"""# {filename}

**File Information:**
- **Type**: {file_info.get("normalized_type", "unknown")}
- **Size**: {file_info.get("file_size", 0):,} bytes
- **Path**: {file_path}

**Conversion Status**: ❌ Failed
**Error**: {str(error)}

*This document was created as a fallback when the original file could not be converted.*
"""
