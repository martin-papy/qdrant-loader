"""File processing and filtering logic for Git connector."""

import fnmatch
import os
from typing import TYPE_CHECKING, Optional

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.connectors.git.config import GitRepoConfig
    from qdrant_loader.core.file_conversion import FileDetector

logger = LoggingConfig.get_logger(__name__)


class FileProcessor:
    """Handles file processing and filtering logic."""

    def __init__(
        self,
        config: "GitRepoConfig",
        temp_dir: str,
        file_detector: Optional["FileDetector"] = None,
    ):
        """Initialize the file processor.

        Args:
            config: Git repository configuration
            temp_dir: Temporary directory path
            file_detector: Optional file detector for conversion support
        """
        self.config = config
        self.temp_dir = temp_dir
        self.file_detector = file_detector
        self.logger = LoggingConfig.get_logger(__name__)

    def should_process_file(self, file_path: str) -> bool:
        """Check if a file should be processed based on configuration.

        Args:
            file_path: Path to the file

        Returns:
            True if the file should be processed, False otherwise
        """
        try:
            self.logger.debug(
                "Checking if file should be processed", file_path=file_path
            )
            self.logger.debug(
                "Current configuration",
                file_types=self.config.file_types,
                include_paths=self.config.include_paths,
                exclude_paths=self.config.exclude_paths,
                max_file_size=self.config.max_file_size,
            )

            # Check if file exists and is readable
            if not os.path.isfile(file_path):
                self.logger.debug(f"Skipping {file_path}: file does not exist")
                return False
            if not os.access(file_path, os.R_OK):
                self.logger.debug(f"Skipping {file_path}: file is not readable")
                return False

            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self.temp_dir)
            self.logger.debug(f"Relative path: {rel_path}")

            # Skip files that are just extensions without names (e.g. ".md")
            file_basename = os.path.basename(rel_path)
            if file_basename.startswith("."):
                self.logger.debug(
                    f"Skipping {rel_path}: invalid filename (starts with dot)"
                )
                return False

            # Check if file matches any exclude patterns first
            for pattern in self.config.exclude_paths:
                pattern = pattern.lstrip("/")
                self.logger.debug(f"Checking exclude pattern: {pattern}")
                if pattern.endswith("/**"):
                    dir_pattern = pattern[:-3]  # Remove /** suffix
                    if dir_pattern == os.path.dirname(rel_path) or os.path.dirname(
                        rel_path
                    ).startswith(dir_pattern + "/"):
                        self.logger.debug(
                            f"Skipping {rel_path}: matches exclude directory pattern {pattern}"
                        )
                        return False
                elif pattern.endswith("/"):
                    dir_pattern = pattern[:-1]  # Remove trailing slash
                    if os.path.dirname(rel_path) == dir_pattern or os.path.dirname(
                        rel_path
                    ).startswith(dir_pattern + "/"):
                        self.logger.debug(
                            f"Skipping {rel_path}: matches exclude directory pattern {pattern}"
                        )
                        return False
                elif fnmatch.fnmatch(rel_path, pattern):
                    self.logger.debug(
                        f"Skipping {rel_path}: matches exclude pattern {pattern}"
                    )
                    return False

            # Check if file matches any file type patterns (case-insensitive)
            file_type_match = False
            file_ext = os.path.splitext(file_basename)[
                1
            ].lower()  # Get extension with dot
            self.logger.debug(f"Checking file extension: {file_ext}")

            # First check configured file types
            for pattern in self.config.file_types:
                self.logger.debug(f"Checking file type pattern: {pattern}")
                # Extract extension from pattern (e.g., "*.md" -> ".md")
                pattern_ext = os.path.splitext(pattern)[1].lower()
                if pattern_ext and file_ext == pattern_ext:
                    file_type_match = True
                    self.logger.debug(
                        f"File {rel_path} matches file type pattern {pattern}"
                    )
                    break

            # If file conversion is enabled and file doesn't match configured types,
            # check if it can be converted
            if (
                not file_type_match
                and self.config.enable_file_conversion
                and self.file_detector
            ):
                if self.file_detector.is_supported_for_conversion(file_path):
                    file_type_match = True
                    self.logger.debug(f"File {rel_path} supported for conversion")

            if not file_type_match:
                self.logger.debug(
                    f"Skipping {rel_path}: does not match any file type patterns and not supported for conversion"
                )
                return False

            # Check file size
            file_size = os.path.getsize(file_path)
            self.logger.debug(
                f"File size: {file_size} bytes (max: {self.config.max_file_size})"
            )
            if file_size > self.config.max_file_size:
                self.logger.debug(f"Skipping {rel_path}: exceeds max file size")
                return False

            # Check if file matches any include patterns
            if not self.config.include_paths:
                # If no include paths specified, include everything
                self.logger.debug("No include paths specified, including all files")
                return True

            # Get the file's directory relative to repo root
            rel_dir = os.path.dirname(rel_path)
            self.logger.debug(f"Checking include patterns for directory: {rel_dir}")

            for pattern in self.config.include_paths:
                pattern = pattern.lstrip("/")
                self.logger.debug(f"Checking include pattern: {pattern}")
                if pattern == "" or pattern == "/":
                    # Root pattern means include only files in root directory
                    if rel_dir == "":
                        self.logger.debug(f"Including {rel_path}: matches root pattern")
                        return True
                if pattern.endswith("/**/*"):
                    dir_pattern = pattern[:-5]  # Remove /**/* suffix
                    if dir_pattern == "" or dir_pattern == "/":
                        self.logger.debug(
                            f"Including {rel_path}: matches root /**/* pattern"
                        )
                        return True  # Root pattern with /**/* means include everything
                    if dir_pattern == rel_dir or rel_dir.startswith(dir_pattern + "/"):
                        self.logger.debug(
                            f"Including {rel_path}: matches directory pattern {pattern}"
                        )
                        return True
                elif pattern.endswith("/"):
                    dir_pattern = pattern[:-1]  # Remove trailing slash
                    if dir_pattern == "" or dir_pattern == "/":
                        # Root pattern with / means include only files in root directory
                        if rel_dir == "":
                            self.logger.debug(
                                f"Including {rel_path}: matches root pattern"
                            )
                            return True
                    if dir_pattern == rel_dir or rel_dir.startswith(dir_pattern + "/"):
                        self.logger.debug(
                            f"Including {rel_path}: matches directory pattern {pattern}"
                        )
                        return True
                elif fnmatch.fnmatch(rel_path, pattern):
                    self.logger.debug(
                        f"Including {rel_path}: matches exact pattern {pattern}"
                    )
                    return True

            # If we have include patterns but none matched, exclude the file
            self.logger.debug(f"Skipping {rel_path}: not in include paths")
            return False

        except Exception as e:
            self.logger.error(f"Error checking if file should be processed: {e}")
            return False
