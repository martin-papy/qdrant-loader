"""File type detection service using MIME type and extension-based detection."""

import mimetypes
import os
from pathlib import Path
from typing import Optional, Tuple

from qdrant_loader.utils.logging import LoggingConfig

from .exceptions import FileAccessError

logger = LoggingConfig.get_logger(__name__)


class FileDetector:
    """Service for detecting file types using MIME type and extension-based detection."""

    # MarkItDown supported file types (based on documentation)
    SUPPORTED_MIME_TYPES = {
        # PDF files
        "application/pdf": "pdf",
        # Microsoft Office documents
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "application/msword": "doc",
        "application/vnd.ms-excel": "xls",
        "application/vnd.ms-powerpoint": "ppt",
        # Images
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
        "image/webp": "webp",
        # Audio files
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/wave": "wav",
        # EPUB files
        "application/epub+zip": "epub",
        # ZIP archives
        "application/zip": "zip",
        "application/x-zip-compressed": "zip",
        # Plain text (for completeness)
        "text/plain": "txt",
        # CSV files
        "text/csv": "csv",
        "application/csv": "csv",
        # XML files
        "application/xml": "xml",
        "text/xml": "xml",
    }

    # File extensions that should be excluded (handled by existing strategies)
    EXCLUDED_EXTENSIONS = {
        ".html",
        ".htm",  # HTML strategy
        ".md",
        ".markdown",  # Markdown strategy
        ".txt",  # Base strategy for plain text
        ".json",  # JSON strategy
    }

    def __init__(self):
        """Initialize the file detector."""
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize mimetypes with additional types
        mimetypes.init()
        self._add_custom_mime_types()

    def _add_custom_mime_types(self):
        """Add custom MIME type mappings for better detection."""
        # Add Office document types that might not be in default mimetypes
        custom_types = {
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".doc": "application/msword",
            ".xls": "application/vnd.ms-excel",
            ".ppt": "application/vnd.ms-powerpoint",
            ".epub": "application/epub+zip",
        }

        for ext, mime_type in custom_types.items():
            mimetypes.add_type(mime_type, ext)

    def detect_file_type(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Detect file type using MIME type detection with extension fallback.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Tuple of (mime_type, file_extension) or (None, None) if detection fails
        """
        try:
            # Get file extension
            file_extension = Path(file_path).suffix.lower()

            # Try MIME type detection using mimetypes
            mime_type = self._detect_mime_type(file_path)

            self.logger.debug(
                "File type detection",
                file_path=file_path,
                detected_mime_type=mime_type,
                file_extension=file_extension,
            )

            return mime_type, file_extension

        except Exception as e:
            self.logger.warning(
                "File type detection failed", file_path=file_path, error=str(e)
            )
            return None, None

    def _detect_mime_type(self, file_path: str) -> Optional[str]:
        """Detect MIME type using mimetypes module.

        Args:
            file_path: Path to the file

        Returns:
            MIME type string or None if detection fails
        """
        try:
            # Check if file exists and is accessible
            if not os.path.exists(file_path):
                raise FileAccessError(f"File does not exist: {file_path}")

            if not os.access(file_path, os.R_OK):
                raise FileAccessError(f"File is not readable: {file_path}")

            # Use mimetypes module for MIME type detection
            mime_type, _ = mimetypes.guess_type(file_path)

            return mime_type

        except Exception as e:
            self.logger.debug(
                "MIME type detection failed, will try extension fallback",
                file_path=file_path,
                error=str(e),
            )
            return None

    def is_supported_for_conversion(self, file_path: str) -> bool:
        """Check if file is supported for conversion.

        Args:
            file_path: Path to the file

        Returns:
            True if file is supported for conversion, False otherwise
        """
        mime_type, file_extension = self.detect_file_type(file_path)

        # Check if extension should be excluded (handled by existing strategies)
        if file_extension in self.EXCLUDED_EXTENSIONS:
            self.logger.debug(
                "File excluded - handled by existing strategy",
                file_path=file_path,
                file_extension=file_extension,
            )
            return False

        # Check if MIME type is supported
        if mime_type and mime_type in self.SUPPORTED_MIME_TYPES:
            self.logger.debug(
                "File supported via MIME type", file_path=file_path, mime_type=mime_type
            )
            return True

        # Check if extension is supported (fallback)
        if file_extension:
            extension_without_dot = file_extension.lstrip(".")
            supported_extensions = set(self.SUPPORTED_MIME_TYPES.values())

            if extension_without_dot in supported_extensions:
                self.logger.debug(
                    "File supported via extension fallback",
                    file_path=file_path,
                    file_extension=file_extension,
                )
                return True

        self.logger.debug(
            "File not supported for conversion",
            file_path=file_path,
            mime_type=mime_type,
            file_extension=file_extension,
        )
        return False

    def get_file_type_info(self, file_path: str) -> dict:
        """Get comprehensive file type information.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file type information
        """
        mime_type, file_extension = self.detect_file_type(file_path)

        # Get file size
        file_size = None
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            pass

        # Determine if supported
        is_supported = self.is_supported_for_conversion(file_path)

        # Get normalized file type
        normalized_type = None
        if mime_type and mime_type in self.SUPPORTED_MIME_TYPES:
            normalized_type = self.SUPPORTED_MIME_TYPES[mime_type]
        elif file_extension:
            extension_without_dot = file_extension.lstrip(".")
            if extension_without_dot in self.SUPPORTED_MIME_TYPES.values():
                normalized_type = extension_without_dot

        return {
            "file_path": file_path,
            "mime_type": mime_type,
            "file_extension": file_extension,
            "file_size": file_size,
            "is_supported": is_supported,
            "normalized_type": normalized_type,
            "is_excluded": file_extension in self.EXCLUDED_EXTENSIONS,
        }

    @classmethod
    def get_supported_extensions(cls) -> set[str]:
        """Get set of supported file extensions.

        Returns:
            Set of supported file extensions (with dots)
        """
        extensions = set()
        for file_type in cls.SUPPORTED_MIME_TYPES.values():
            extensions.add(f".{file_type}")

        # Add some common variations
        extensions.update({".jpeg", ".tif", ".wave"})

        return extensions

    @classmethod
    def get_supported_mime_types(cls) -> set[str]:
        """Get set of supported MIME types.

        Returns:
            Set of supported MIME types
        """
        return set(cls.SUPPORTED_MIME_TYPES.keys())
