import os
import re
from typing import Any

import chardet

from qdrant_loader.utils.logging import LoggingConfig


class LocalFileMetadataExtractor:
    """Extract metadata from local files."""

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.logger = LoggingConfig.get_logger(__name__)

    def extract_all_metadata(self, file_path: str, content: str) -> dict[str, Any]:
        self.logger.debug(f"Starting metadata extraction for file: {file_path!s}")
        file_metadata = self._extract_file_metadata(file_path, content)
        structure_metadata = {}
        if file_path.lower().endswith(".md"):
            structure_metadata = self._extract_structure_metadata(content)
        metadata = {**file_metadata, **structure_metadata}
        self.logger.debug(f"Completed metadata extraction for {file_path!s}.")
        self.logger.debug(f"Metadata: {metadata!s}")
        return metadata

    def _extract_file_metadata(self, file_path: str, content: str) -> dict[str, Any]:
        rel_path = os.path.relpath(file_path, self.base_path)
        file_type = os.path.splitext(rel_path)[1]
        file_name = os.path.basename(rel_path)
        file_encoding = self._detect_encoding(content)
        line_count = len(content.splitlines())
        word_count = len(content.split())
        file_size = len(content.encode(file_encoding))
        return {
            "file_type": file_type,
            "file_name": file_name,
            "file_directory": os.path.dirname("/" + rel_path),
            "file_encoding": file_encoding,
            "line_count": line_count,
            "word_count": word_count,
            "file_size": file_size,
        }

    def _extract_structure_metadata(self, content: str) -> dict[str, Any]:
        headings = re.findall(
            r"(?:^|\n)\s*(#{1,6})\s+(.+?)(?:\n|$)", content, re.MULTILINE
        )
        has_toc = "## Table of Contents" in content or "## Contents" in content
        heading_levels = [len(h[0]) for h in headings]
        sections_count = len(heading_levels)
        return {
            "has_toc": has_toc,
            "heading_levels": heading_levels,
            "sections_count": sections_count,
        }

    def _detect_encoding(self, content: str) -> str:
        if not content:
            return "utf-8"
        try:
            result = chardet.detect(content.encode())
            if (
                result["encoding"]
                and result["encoding"].lower() != "ascii"
                and result["confidence"] > 0.8
            ):
                return result["encoding"].lower()
        except Exception as e:
            self.logger.error({"event": "Failed to detect encoding", "error": str(e)})
        return "utf-8"
