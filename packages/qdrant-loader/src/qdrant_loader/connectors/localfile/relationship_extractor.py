"""
LocalFile Relationship Extractor

Extracts metadata and relationships from local files including author information,
timestamps, cross-references, and file-specific metadata.
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from qdrant_loader.connectors.metadata.base import (
    BaseMetadataExtractor,
    MetadataExtractionConfig,
)

logger = logging.getLogger(__name__)


class LocalFileRelationshipExtractor(BaseMetadataExtractor):
    """
    Extracts relationships and metadata from local files.

    Handles:
    - Author metadata from file system attributes and content analysis
    - Timestamp metadata from file system and content
    - Directory/file hierarchical relationships
    - Cross-references within files (links, imports, includes)
    - File-specific metadata (size, type, encoding, etc.)
    """

    def __init__(self, config: MetadataExtractionConfig, base_path: str):
        """Initialize the LocalFile relationship extractor.

        Args:
            config: Metadata extraction configuration
            base_path: Base path for the local files
        """
        super().__init__(config)
        self.base_path = base_path

    def _extract_author_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]] | None:
        """Extract author information from file system and content.

        Args:
            content: File content
            context: Contains file_path and other file metadata

        Returns:
            List of author metadata dictionaries
        """
        authors = []
        file_path = context.get("file_path", "")

        try:
            # Extract from file system owner (if available)
            if file_path and os.path.exists(file_path):
                try:
                    stat_info = os.stat(file_path)
                    # On Unix systems, we can get owner info
                    import pwd

                    owner_info = pwd.getpwuid(stat_info.st_uid)
                    if owner_info:
                        authors.append(
                            {
                                "name": owner_info.pw_name,
                                "role": "file_owner",
                                "confidence_score": 0.8,
                            }
                        )
                except (ImportError, KeyError, OSError):
                    # pwd module not available on Windows or other issues
                    pass

            # Extract from content patterns (for various file types)
            content_authors = self._extract_authors_from_content(content, file_path)
            authors.extend(content_authors)

        except Exception as e:
            self.logger.warning(
                f"Error extracting authors from local file {file_path}: {e}"
            )

        return authors if authors else None

    def _extract_timestamp_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Extract timestamp information from file system and content.

        Args:
            content: File content
            context: Contains file_path and other file metadata

        Returns:
            Dictionary containing timestamp metadata
        """
        timestamps = {}
        file_path = context.get("file_path", "")

        try:
            # Extract from file system
            if file_path and os.path.exists(file_path):
                stat_info = os.stat(file_path)

                # Creation time (if available)
                if hasattr(stat_info, "st_birthtime"):  # macOS
                    timestamps["created"] = {
                        "timestamp": datetime.fromtimestamp(
                            stat_info.st_birthtime
                        ).isoformat(),
                        "confidence_score": 0.9,
                    }

                # Modification time
                timestamps["modified"] = {
                    "timestamp": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    "confidence_score": 0.9,
                }

                # Access time
                timestamps["accessed"] = {
                    "timestamp": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                    "confidence_score": 0.7,
                }

            # Extract from content (for files with embedded timestamps)
            content_timestamps = self._extract_timestamps_from_content(
                content, file_path
            )
            timestamps.update(content_timestamps)

        except Exception as e:
            self.logger.warning(
                f"Error extracting timestamps from local file {file_path}: {e}"
            )

        return timestamps if timestamps else None

    def _extract_relationship_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]] | None:
        """Extract hierarchical and structural relationships.

        Args:
            content: File content
            context: Contains file_path and other file metadata

        Returns:
            List of relationship metadata dictionaries
        """
        relationships = []
        file_path = context.get("file_path", "")

        try:
            # Directory hierarchy relationships
            if file_path:
                path_obj = Path(file_path)

                # Parent directory relationship
                if path_obj.parent and str(path_obj.parent) != str(path_obj):
                    relationships.append(
                        {
                            "source_id": str(path_obj),
                            "target_id": str(path_obj.parent),
                            "type": "child_of",
                            "confidence_score": 1.0,
                        }
                    )

                # Sibling file relationships (same directory)
                try:
                    siblings = [
                        f
                        for f in path_obj.parent.iterdir()
                        if f.is_file() and f != path_obj
                    ]
                    for sibling in siblings[
                        :10
                    ]:  # Limit to avoid too many relationships
                        relationships.append(
                            {
                                "source_id": str(path_obj),
                                "target_id": str(sibling),
                                "type": "sibling_of",
                                "confidence_score": 0.6,
                            }
                        )
                except OSError:
                    pass

            # Content-based relationships
            content_relationships = self._extract_relationships_from_content(
                content, file_path
            )
            relationships.extend(content_relationships)

        except Exception as e:
            self.logger.warning(
                f"Error extracting relationships from local file {file_path}: {e}"
            )

        return relationships if relationships else None

    def _extract_cross_reference_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]] | None:
        """Extract cross-references and links within the content.

        Args:
            content: File content
            context: Contains file_path and other file metadata

        Returns:
            List of cross-reference metadata dictionaries
        """
        cross_refs = []
        file_path = context.get("file_path", "")

        try:
            # Extract various types of references based on file type
            file_ext = Path(file_path).suffix.lower() if file_path else ""

            # URLs
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
            urls = re.findall(url_pattern, content)
            for url in urls[:20]:  # Limit to avoid too many refs
                cross_refs.append(
                    {
                        "target": url,
                        "type": "url",
                        "reference_text": url,
                        "confidence_score": 0.9,
                    }
                )

            # File references (relative paths)
            file_refs = self._extract_file_references(content, file_ext)
            cross_refs.extend(file_refs)

            # Code imports/includes
            if file_ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h"]:
                import_refs = self._extract_import_references(content, file_ext)
                cross_refs.extend(import_refs)

            # Markdown/documentation links
            if file_ext in [".md", ".txt", ".rst"]:
                doc_refs = self._extract_documentation_references(content)
                cross_refs.extend(doc_refs)

        except Exception as e:
            self.logger.warning(
                f"Error extracting cross-references from local file {file_path}: {e}"
            )

        return cross_refs if cross_refs else None

    def _extract_source_specific_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Extract file-specific metadata.

        Args:
            content: File content
            context: Contains file_path and other file metadata

        Returns:
            Dictionary with file-specific metadata
        """
        metadata = {}
        file_path = context.get("file_path", "")

        try:
            if file_path and os.path.exists(file_path):
                path_obj = Path(file_path)
                stat_info = os.stat(file_path)

                # Basic file information
                metadata.update(
                    {
                        "file_name": path_obj.name,
                        "file_extension": path_obj.suffix,
                        "file_size_bytes": stat_info.st_size,
                        "directory_path": str(path_obj.parent),
                        "absolute_path": str(path_obj.absolute()),
                        "is_hidden": path_obj.name.startswith("."),
                        "permissions": oct(stat_info.st_mode)[-3:],
                    }
                )

                # Content analysis
                if content:
                    metadata.update(
                        {
                            "content_length": len(content),
                            "line_count": content.count("\n") + 1 if content else 0,
                            "encoding": self._detect_encoding(file_path),
                            "language": self._detect_language(path_obj.suffix, content),
                        }
                    )

                # File type specific metadata
                if path_obj.suffix.lower() in [".py", ".js", ".ts", ".java"]:
                    metadata["file_type"] = "source_code"
                    metadata.update(
                        self._extract_code_metadata(content, path_obj.suffix)
                    )
                elif path_obj.suffix.lower() in [".md", ".txt", ".rst"]:
                    metadata["file_type"] = "documentation"
                    metadata.update(self._extract_doc_metadata(content))
                elif path_obj.suffix.lower() in [".json", ".yaml", ".yml", ".xml"]:
                    metadata["file_type"] = "configuration"
                elif path_obj.suffix.lower() in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".bmp",
                ]:
                    metadata["file_type"] = "image"
                else:
                    metadata["file_type"] = "other"

        except Exception as e:
            self.logger.warning(
                f"Error extracting source-specific metadata from local file {file_path}: {e}"
            )

        return metadata if metadata else None

    def extract_metadata(self, file_path: str, content: str) -> Dict[str, Any]:
        """Main entry point for metadata extraction from LocalFile connector.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            Dictionary containing all extracted metadata under 'enhanced_metadata' key
        """
        context = {
            "file_path": file_path,
            "content": content,
            "base_path": self.base_path,
        }

        # Use the base class method to extract metadata
        metadata = super().extract_metadata(content, context)

        # Return it under the enhanced_metadata key as expected by the connector
        return {"enhanced_metadata": metadata} if metadata else {}

    # Helper methods for content analysis
    def _extract_authors_from_content(
        self, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """Extract author information from file content."""
        authors = []

        # Look for common author patterns
        patterns = [
            r"@author\s+([^\n\r]+)",  # @author tag
            r"Author:\s*([^\n\r]+)",  # Author: field
            r"Created by:\s*([^\n\r]+)",  # Created by: field
            r"#\s*Author:\s*([^\n\r]+)",  # # Author: comment
            r"//\s*Author:\s*([^\n\r]+)",  # // Author: comment
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                author_name = match.strip()
                if author_name and len(author_name) > 2:
                    authors.append(
                        {
                            "name": author_name,
                            "role": "content_author",
                            "confidence_score": 0.7,
                        }
                    )

        return authors

    def _extract_timestamps_from_content(
        self, content: str, file_path: str
    ) -> Dict[str, Any]:
        """Extract timestamp information from file content."""
        timestamps = {}

        # Look for common timestamp patterns
        patterns = [
            (r"Created:\s*(\d{4}-\d{2}-\d{2})", "created"),
            (r"Modified:\s*(\d{4}-\d{2}-\d{2})", "modified"),
            (r"Date:\s*(\d{4}-\d{2}-\d{2})", "created"),
            (r"Last updated:\s*(\d{4}-\d{2}-\d{2})", "modified"),
        ]

        for pattern, timestamp_type in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    timestamp = datetime.strptime(match, "%Y-%m-%d")
                    timestamps[f"content_{timestamp_type}"] = {
                        "timestamp": timestamp.isoformat(),
                        "confidence_score": 0.6,
                    }
                except ValueError:
                    continue

        return timestamps

    def _extract_relationships_from_content(
        self, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """Extract content-based relationships."""
        relationships = []

        if not file_path:
            return relationships

        current_file = Path(file_path)

        # Look for file dependencies/includes
        if current_file.suffix.lower() == ".py":
            # Python imports
            import_patterns = [
                r"from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import",
                r"import\s+([a-zA-Z_][a-zA-Z0-9_.]*)",
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    relationships.append(
                        {
                            "source_id": str(current_file),
                            "target_id": match,
                            "type": "imports",
                            "confidence_score": 0.8,
                        }
                    )

        return relationships

    def _extract_file_references(
        self, content: str, file_ext: str
    ) -> List[Dict[str, Any]]:
        """Extract file path references from content."""
        cross_refs = []

        # Common file reference patterns
        patterns = [
            r"\.\/[a-zA-Z0-9_\-\/\.]+",  # Relative paths starting with ./
            r"\/[a-zA-Z0-9_\-\/\.]+\.[a-zA-Z0-9]+",  # Absolute paths
            r"[a-zA-Z0-9_\-\/\.]+\.[a-zA-Z0-9]+",  # File names with extensions
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches[:10]:  # Limit references
                if len(match) > 3 and "." in match:  # Basic validation
                    cross_refs.append(
                        {
                            "target": match,
                            "type": "file_reference",
                            "reference_text": match,
                            "confidence_score": 0.6,
                        }
                    )

        return cross_refs

    def _extract_import_references(
        self, content: str, file_ext: str
    ) -> List[Dict[str, Any]]:
        """Extract import/include references for code files."""
        cross_refs = []

        if file_ext == ".py":
            # Python imports
            patterns = [
                (r"from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import", "python_import"),
                (r"import\s+([a-zA-Z_][a-zA-Z0-9_.]*)", "python_import"),
            ]
        elif file_ext in [".js", ".ts"]:
            # JavaScript/TypeScript imports
            patterns = [
                (r'import.*from\s+[\'"]([^\'"]+)[\'"]', "js_import"),
                (r'require\([\'"]([^\'"]+)[\'"]\)', "js_require"),
            ]
        elif file_ext in [".c", ".cpp", ".h"]:
            # C/C++ includes
            patterns = [
                (r"#include\s+<([^>]+)>", "c_include"),
                (r'#include\s+"([^"]+)"', "c_include"),
            ]
        else:
            patterns = []

        for pattern, ref_type in patterns:
            matches = re.findall(pattern, content)
            for match in matches[:15]:  # Limit imports
                cross_refs.append(
                    {
                        "target": match,
                        "type": ref_type,
                        "reference_text": match,
                        "confidence_score": 0.8,
                    }
                )

        return cross_refs

    def _extract_documentation_references(self, content: str) -> List[Dict[str, Any]]:
        """Extract references from documentation files."""
        cross_refs = []

        # Markdown link pattern
        md_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
        for link_text, link_url in md_links[:20]:  # Limit links
            cross_refs.append(
                {
                    "target": link_url,
                    "type": "markdown_link",
                    "reference_text": f"[{link_text}]({link_url})",
                    "confidence_score": 0.9,
                }
            )

        return cross_refs

    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding."""
        try:
            import chardet

            with open(file_path, "rb") as f:
                raw_data = f.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                return result.get("encoding") or "utf-8"
        except (ImportError, Exception):
            return "utf-8"

    def _detect_language(self, file_ext: str, content: str) -> str:
        """Detect programming language or file type."""
        ext_mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c_header",
            ".md": "markdown",
            ".txt": "text",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
        }
        return ext_mapping.get(file_ext.lower(), "unknown")

    def _extract_code_metadata(self, content: str, file_ext: str) -> Dict[str, Any]:
        """Extract metadata specific to source code files."""
        metadata = {}

        if not content:
            return metadata

        # Count functions, classes, etc.
        if file_ext == ".py":
            metadata["function_count"] = len(
                re.findall(r"^\s*def\s+\w+", content, re.MULTILINE)
            )
            metadata["class_count"] = len(
                re.findall(r"^\s*class\s+\w+", content, re.MULTILINE)
            )
            metadata["import_count"] = len(
                re.findall(r"^\s*(import|from)\s+", content, re.MULTILINE)
            )
        elif file_ext in [".js", ".ts"]:
            metadata["function_count"] = len(
                re.findall(r"function\s+\w+|=>\s*{|\w+\s*:\s*function", content)
            )
            metadata["class_count"] = len(re.findall(r"class\s+\w+", content))

        # Comment density
        total_lines = content.count("\n") + 1
        if file_ext == ".py":
            comment_lines = len(re.findall(r"^\s*#", content, re.MULTILINE))
        elif file_ext in [".js", ".ts", ".java", ".cpp", ".c"]:
            comment_lines = len(re.findall(r"^\s*//", content, re.MULTILINE))
        else:
            comment_lines = 0

        metadata["comment_density"] = (
            comment_lines / total_lines if total_lines > 0 else 0
        )

        return metadata

    def _extract_doc_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata specific to documentation files."""
        metadata = {}

        if not content:
            return metadata

        # Count headings (markdown)
        metadata["heading_count"] = len(re.findall(r"^#+\s", content, re.MULTILINE))

        # Count links
        metadata["link_count"] = len(re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content))

        # Count code blocks
        metadata["code_block_count"] = len(re.findall(r"```", content)) // 2

        # Word count (approximate)
        words = re.findall(r"\b\w+\b", content)
        metadata["word_count"] = len(words)

        return metadata
