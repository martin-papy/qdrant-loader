"""File processing and filtering logic for LocalFile connector."""

import fnmatch
import os

import structlog

from .config import LocalFileConfig


class LocalFileFileProcessor:
    """Handles file processing and filtering logic for local files."""

    def __init__(self, config: LocalFileConfig, base_path: str):
        self.config = config
        self.base_path = base_path
        self.logger = structlog.get_logger(__name__)

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
            for pattern in self.config.file_types:
                pattern_ext = os.path.splitext(pattern)[1].lower()
                if pattern_ext and file_ext == pattern_ext:
                    file_type_match = True
                    break
            if not file_type_match:
                self.logger.debug(
                    f"Skipping {rel_path}: does not match any file type patterns"
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
