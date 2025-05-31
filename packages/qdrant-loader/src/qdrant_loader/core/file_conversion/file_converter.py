"""Main file conversion service using MarkItDown."""

import logging
import os
import signal
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


class TimeoutHandler:
    """Context manager for handling conversion timeouts."""

    def __init__(self, timeout_seconds: int, file_path: str):
        self.timeout_seconds = timeout_seconds
        self.file_path = file_path
        self.old_handler = None

    def _timeout_handler(self, signum, frame):
        """Signal handler for timeout."""
        raise ConversionTimeoutError(self.timeout_seconds, self.file_path)

    def __enter__(self):
        """Set up timeout signal handler."""
        self.old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.timeout_seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up timeout signal handler."""
        signal.alarm(0)  # Cancel the alarm
        if self.old_handler is not None:
            signal.signal(signal.SIGALRM, self.old_handler)


class FileConverter:
    """Service for converting files to Markdown using MarkItDown."""

    def __init__(self, config: FileConversionConfig):
        """Initialize the file converter."""
        self.config = config
        self.file_detector = FileDetector()
        self.logger = LoggingConfig.get_logger(__name__)
        self._markitdown = None

    def _get_markitdown(self):
        """Get MarkItDown instance with lazy loading and LLM configuration."""
        if self._markitdown is None:
            try:
                from markitdown import MarkItDown  # type: ignore

                # Configure MarkItDown with LLM settings if enabled
                if self.config.markitdown.enable_llm_descriptions:
                    self.logger.debug(
                        "Initializing MarkItDown with LLM configuration",
                        llm_model=self.config.markitdown.llm_model,
                        llm_endpoint=self.config.markitdown.llm_endpoint,
                    )

                    # Create LLM client based on endpoint
                    llm_client = self._create_llm_client()

                    self._markitdown = MarkItDown(
                        llm_client=llm_client,
                        llm_model=self.config.markitdown.llm_model,
                    )
                    self.logger.debug("MarkItDown initialized with LLM support")
                else:
                    self._markitdown = MarkItDown()
                    self.logger.debug("MarkItDown initialized without LLM support")

            except ImportError as e:
                raise MarkItDownError(
                    Exception("MarkItDown library not available")
                ) from e
        return self._markitdown

    def _create_llm_client(self):
        """Create LLM client based on configuration."""
        try:
            # Get API key from configuration
            api_key = self.config.markitdown.llm_api_key
            if not api_key:
                self.logger.warning(
                    "No LLM API key configured for MarkItDown LLM integration"
                )
                # Fallback to environment variable for backward compatibility
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv(
                    "LLM_API_KEY", "dummy-key"
                )

            # Check if it's an OpenAI-compatible endpoint
            if "openai" in self.config.markitdown.llm_endpoint.lower():
                from openai import OpenAI  # type: ignore

                return OpenAI(
                    base_url=self.config.markitdown.llm_endpoint,
                    api_key=api_key,
                )
            else:
                # For other endpoints, try to create a generic OpenAI-compatible client
                from openai import OpenAI  # type: ignore

                return OpenAI(
                    base_url=self.config.markitdown.llm_endpoint,
                    api_key=api_key,
                )
        except ImportError as e:
            self.logger.warning(
                "OpenAI library not available for LLM integration", error=str(e)
            )
            raise MarkItDownError(
                Exception("OpenAI library required for LLM integration")
            ) from e

    def convert_file(self, file_path: str) -> str:
        """Convert a file to Markdown format with timeout support."""
        self.logger.info("Starting file conversion", file_path=file_path)

        try:
            self._validate_file(file_path)
            markitdown = self._get_markitdown()

            # Apply timeout wrapper for conversion
            with TimeoutHandler(self.config.conversion_timeout, file_path):
                result = markitdown.convert(file_path)

            if hasattr(result, "text_content"):
                markdown_content = result.text_content
            else:
                markdown_content = str(result)

            self.logger.info(
                "File conversion completed",
                file_path=file_path,
                content_length=len(markdown_content),
                timeout_used=self.config.conversion_timeout,
            )
            return markdown_content

        except ConversionTimeoutError:
            # Re-raise timeout errors as-is
            self.logger.error(
                "File conversion timed out",
                file_path=file_path,
                timeout=self.config.conversion_timeout,
            )
            raise
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
