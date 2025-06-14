"""File processing and filtering logic for LocalFile connector."""

import fnmatch
import os
from typing import TYPE_CHECKING, Optional

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.core.file_conversion import FileDetector

from .config import LocalFileConfig


class LocalFileFileProcessor:
    """Handles file processing and filtering logic for local files."""

    def __init__(
        self,
        config: LocalFileConfig,
        base_path: str,
        file_detector: Optional["FileDetector"] = None,
    ):
        """Initialize the file processor.

        Args:
            config: Local file configuration
            base_path: Base directory path
            file_detector: Optional file detector for conversion support
        """
        self.config = config
        self.base_path = base_path
        self.file_detector = file_detector
        self.logger = LoggingConfig.get_logger(__name__)

    def should_process_file(self, file_path: str) -> bool:
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

            if not os.path.isfile(file_path):
                self.logger.debug(f"Skipping {file_path}: file does not exist")
                return False
            if not os.access(file_path, os.R_OK):
                self.logger.debug(f"Skipping {file_path}: file is not readable")
                return False

            rel_path = os.path.relpath(file_path, self.base_path)
            file_basename = os.path.basename(rel_path)
            if file_basename.startswith("."):
                self.logger.debug(
                    f"Skipping {rel_path}: invalid filename (starts with dot)"
                )
                return False

            for pattern in self.config.exclude_paths:
                pattern = pattern.lstrip("/")
                if pattern.endswith("/**"):
                    dir_pattern = pattern[:-3]
                    if dir_pattern == os.path.dirname(rel_path) or os.path.dirname(
                        rel_path
                    ).startswith(dir_pattern + "/"):
                        self.logger.debug(
                            f"Skipping {rel_path}: matches exclude directory pattern {pattern}"
                        )
                        return False
                elif pattern.endswith("/"):
                    dir_pattern = pattern[:-1]
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

            file_type_match = False
            file_ext = os.path.splitext(file_basename)[1].lower()
            self.logger.debug(f"Checking file extension: {file_ext}")

            # First check configured file types
            for pattern in self.config.file_types:
                self.logger.debug(f"Checking file type pattern: {pattern}")
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

            file_size = os.path.getsize(file_path)
            if file_size > self.config.max_file_size:
                self.logger.debug(f"Skipping {rel_path}: exceeds max file size")
                return False

            if not self.config.include_paths:
                return True

            rel_dir = os.path.dirname(rel_path)
            for pattern in self.config.include_paths:
                pattern = pattern.lstrip("/")
                if pattern == "" or pattern == "/":
                    if rel_dir == "":
                        return True
                if pattern.endswith("/**/*"):
                    dir_pattern = pattern[:-5]
                    if dir_pattern == "" or dir_pattern == "/":
                        return True
                    if dir_pattern == rel_dir or rel_dir.startswith(dir_pattern + "/"):
                        return True
                elif pattern.endswith("/"):
                    dir_pattern = pattern[:-1]
                    if dir_pattern == "" or dir_pattern == "/":
                        if rel_dir == "":
                            return True
                    if dir_pattern == rel_dir or rel_dir.startswith(dir_pattern + "/"):
                        return True
                elif fnmatch.fnmatch(rel_path, pattern):
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking if file should be processed: {e}")
            return False
