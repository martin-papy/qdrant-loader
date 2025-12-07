"""File processing and filtering logic for SharePoint connector.

This module provides file filtering functionality based on:
- File extensions (file_types)
- Path patterns (include_paths, exclude_paths)
- File size limits (max_file_size)

Pattern reference: Git connector's FileProcessor
"""

import fnmatch
from typing import TYPE_CHECKING, Optional

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.connectors.sharepoint.config import SharePointConfig
    from qdrant_loader.core.file_conversion import FileDetector

logger = LoggingConfig.get_logger(__name__)


class SharePointFileProcessor:
    """Handles file processing and filtering logic for SharePoint files.

    Unlike Git connector which works with local files, SharePoint connector
    works with file metadata from the Graph API. This processor filters
    files based on their properties before downloading.
    """

    def __init__(
        self,
        config: "SharePointConfig",
        file_detector: Optional["FileDetector"] = None,
    ):
        """Initialize the file processor.

        Args:
            config: SharePoint configuration
            file_detector: Optional file detector for conversion support
        """
        self.config = config
        self.file_detector = file_detector

    def should_process_file(self, file_info: dict) -> bool:
        """Check if a file should be processed based on configuration.

        Args:
            file_info: File metadata from SharePoint Graph API containing:
                - name: File name
                - size: File size in bytes
                - path: File path relative to document library root

        Returns:
            True if the file should be processed, False otherwise
        """
        try:
            name = file_info.get("name", "")
            size = file_info.get("size", 0) or 0
            path = file_info.get("path", "")

            # Normalize path separators
            path = path.replace("\\", "/")

            logger.debug(
                "Checking if file should be processed",
                file_name=name,
                file_path=path,
                file_size=size,
            )

            # Skip files with invalid names
            if not name or name.startswith("."):
                logger.debug(f"Skipping {name}: invalid filename")
                return False

            # Check exclude patterns first
            if self._matches_exclude_pattern(path):
                logger.debug(f"Skipping {path}: matches exclude pattern")
                return False

            # Check file type/extension
            if not self._matches_file_type(name, path):
                logger.debug(f"Skipping {path}: does not match file type filter")
                return False

            # Check file size
            if size > self.config.max_file_size:
                logger.debug(
                    f"Skipping {path}: exceeds max size ({size} > {self.config.max_file_size})"
                )
                return False

            # Check include patterns (if specified)
            if self.config.include_paths and not self._matches_include_pattern(path):
                logger.debug(f"Skipping {path}: not in include paths")
                return False

            logger.debug(f"Processing file: {path}")
            return True

        except Exception as e:
            logger.error(f"Error checking if file should be processed: {e}")
            return False

    def _matches_exclude_pattern(self, path: str) -> bool:
        """Check if path matches any exclude pattern.

        Args:
            path: File path relative to document library root

        Returns:
            True if path matches an exclude pattern
        """
        if not self.config.exclude_paths:
            return False

        for pattern in self.config.exclude_paths:
            pattern = pattern.lstrip("/")

            # Directory pattern with /**
            if pattern.endswith("/**"):
                dir_pattern = pattern[:-3]
                dir_name = path.rsplit("/", 1)[0] if "/" in path else ""
                if dir_name == dir_pattern or dir_name.startswith(dir_pattern + "/"):
                    return True

            # Directory pattern with trailing /
            elif pattern.endswith("/"):
                dir_pattern = pattern[:-1]
                dir_name = path.rsplit("/", 1)[0] if "/" in path else ""
                if dir_name == dir_pattern or dir_name.startswith(dir_pattern + "/"):
                    return True

            # Glob pattern match
            elif fnmatch.fnmatch(path, pattern):
                return True

        return False

    def _matches_file_type(self, name: str, path: str) -> bool:
        """Check if file matches configured file types.

        Args:
            name: File name
            path: File path

        Returns:
            True if file matches file type filter or no filter is configured
        """
        # If no file types configured, process all files
        if not self.config.file_types:
            return True

        # Get file extension without dot
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

        # Check if extension matches configured file types
        if ext in self.config.file_types:
            return True

        # Check if file conversion is enabled and file can be converted
        if self.config.enable_file_conversion and self.file_detector:
            # For SharePoint, we check by filename since we don't have local path
            if self.file_detector.is_supported_for_conversion(name):
                return True

        return False

    def _matches_include_pattern(self, path: str) -> bool:
        """Check if path matches any include pattern.

        Args:
            path: File path relative to document library root

        Returns:
            True if path matches an include pattern
        """
        if not self.config.include_paths:
            return True  # No include paths = include all

        dir_name = path.rsplit("/", 1)[0] if "/" in path else ""

        for pattern in self.config.include_paths:
            pattern = pattern.lstrip("/")

            # Empty or root pattern
            if pattern == "" or pattern == "/":
                if dir_name == "":
                    return True
                continue

            # Directory pattern with /**/*
            if pattern.endswith("/**/*"):
                dir_pattern = pattern[:-5]
                if dir_pattern == "" or dir_pattern == "/":
                    return True  # Root pattern = include everything
                if dir_pattern == dir_name or dir_name.startswith(dir_pattern + "/"):
                    return True

            # Directory pattern with trailing /
            elif pattern.endswith("/"):
                dir_pattern = pattern[:-1]
                if dir_pattern == "" or dir_pattern == "/":
                    if dir_name == "":
                        return True
                    continue
                if dir_pattern == dir_name or dir_name.startswith(dir_pattern + "/"):
                    return True

            # Glob pattern match
            elif fnmatch.fnmatch(path, pattern):
                return True

        return False

    def get_file_extension(self, name: str) -> str:
        """Get normalized file extension from filename.

        Args:
            name: File name

        Returns:
            Lowercase extension without dot, or empty string
        """
        if "." not in name:
            return ""
        return name.rsplit(".", 1)[-1].lower()
