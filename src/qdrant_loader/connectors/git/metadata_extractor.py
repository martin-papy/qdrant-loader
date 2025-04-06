import chardet
import re
from pathlib import Path
from typing import Dict, Any, List
from git import Repo
import structlog
from qdrant_loader.utils.logger import get_logger
import os
import git
import logging

logger = get_logger(__name__)

class GitMetadataExtractor:
    """Extract metadata from Git repository files."""

    def __init__(self):
        """Initialize the Git metadata extractor."""
        self.logger = logging.getLogger(__name__)

    def extract_all_metadata(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract all metadata for a file.

        Args:
            file_path: Path to the file.
            content: Content of the file.

        Returns:
            Dict[str, Any]: Dictionary containing all metadata.
        """
        file_metadata = self._extract_file_metadata(file_path, content)
        repo_metadata = self._extract_repo_metadata(file_path)
        git_metadata = self._extract_git_metadata(file_path)
        structure_metadata = self._extract_structure_metadata(content)

        return {
            **file_metadata,
            **repo_metadata,
            **git_metadata,
            **structure_metadata
        }

    def _extract_file_metadata(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract metadata about the file itself."""
        file_type = os.path.splitext(file_path)[1]
        file_name = os.path.basename(file_path)
        file_directory = os.path.dirname(file_path)
        file_encoding = self._detect_encoding(content)
        line_count = len(content.splitlines())
        word_count = len(content.split())

        return {
            "file_type": file_type,
            "file_name": file_name,
            "file_directory": file_directory,
            "file_encoding": file_encoding,
            "line_count": line_count,
            "word_count": word_count,
            "has_code_blocks": self._has_code_blocks(content),
            "has_images": self._has_images(content),
            "has_links": self._has_links(content)
        }

    def _extract_repo_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata about the repository."""
        repo = git.Repo(os.path.dirname(file_path), search_parent_directories=True)
        repo_url = repo.remotes.origin.url
        repo_name = os.path.splitext(os.path.basename(repo_url))[0]
        repo_owner = os.path.basename(os.path.dirname(repo_url))
        repo_description = self._get_repo_description(repo, file_path)
        repo_language = self._detect_language(file_path)

        return {
            "repository_url": repo_url,
            "repository_name": repo_name,
            "repository_owner": repo_owner,
            "repository_description": repo_description,
            "repository_language": repo_language
        }

    def _extract_git_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract Git-specific metadata."""
        repo = git.Repo(os.path.dirname(file_path), search_parent_directories=True)
        commits = list(repo.iter_commits(paths=file_path, max_count=1))
        if commits:
            last_commit = commits[0]
            last_commit_date = last_commit.committed_datetime.isoformat()
            last_commit_author = last_commit.author.name
            last_commit_message = last_commit.message.strip()
        else:
            last_commit_date = None
            last_commit_author = None
            last_commit_message = None

        return {
            "last_commit_date": last_commit_date,
            "last_commit_author": last_commit_author,
            "last_commit_message": last_commit_message
        }

    def _extract_structure_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata about the document structure."""
        has_toc = "## Table of Contents" in content or "## Contents" in content
        heading_levels = self._get_heading_levels(content)
        sections_count = len(heading_levels)

        return {
            "has_toc": has_toc,
            "heading_levels": heading_levels,
            "sections_count": sections_count
        }

    def _get_repo_description(self, repo: git.Repo, file_path: str) -> str:
        """Get repository description from Git config or README."""
        # Try to get description from Git config
        description = repo.description
        if description and description.strip() and "Unnamed repository;" not in description:
            return description.strip()

        # Try to find description in README files
        readme_files = ["README.md", "README.txt", "README", "README.rst"]
        repo_root = repo.working_dir
        for readme_file in readme_files:
            readme_path = os.path.join(repo_root, readme_file)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        paragraphs = []
                        current_paragraph = []
                        in_title = True
                        for line in content.splitlines():
                            line = line.strip()
                            # Skip badges and links at the start
                            if in_title and (line.startswith("[![") or line.startswith("[")):
                                continue
                            # Skip empty lines
                            if not line:
                                if current_paragraph:
                                    paragraphs.append(" ".join(current_paragraph))
                                    current_paragraph = []
                                continue
                            # Skip titles
                            if line.startswith("#") or line.startswith("==="):
                                in_title = True
                                continue
                            # Skip common sections
                            if line.lower() in ["## installation", "## usage", "## contributing", "## license"]:
                                break
                            in_title = False
                            current_paragraph.append(line)

                        if current_paragraph:
                            paragraphs.append(" ".join(current_paragraph))

                        # Find first meaningful paragraph
                        for paragraph in paragraphs:
                            if len(paragraph) >= 50:  # Minimum length for a meaningful description
                                # Clean up markdown links
                                paragraph = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", paragraph)
                                # Clean up HTML tags
                                paragraph = re.sub(r"<[^>]+>", "", paragraph)
                                # Limit length and break at sentence boundary
                                if len(paragraph) > 200:
                                    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                                    description = ""
                                    for sentence in sentences:
                                        if len(description + sentence) > 200:
                                            break
                                        description += sentence + " "
                                    description = description.strip() + "..."
                                else:
                                    description = paragraph
                                return description
                except Exception as e:
                    self.logger.error({"event": "Failed to read README", "error": str(e)})

        return "No description available"

    def _detect_encoding(self, content: str) -> str:
        """Detect file encoding."""
        if not content:
            return "utf-8"

        try:
            result = chardet.detect(content.encode())
            if result["encoding"] and result["encoding"].lower() != "ascii" and result["confidence"] > 0.8:
                return result["encoding"].lower()
        except Exception as e:
            self.logger.error({"event": "Failed to detect encoding", "error": str(e)})

        return "utf-8"

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".scala": "Scala",
            ".kt": "Kotlin",
            ".swift": "Swift",
            ".m": "Objective-C",
            ".h": "C/C++ Header",
            ".sh": "Shell",
            ".bat": "Batch",
            ".ps1": "PowerShell",
            ".md": "Markdown",
            ".rst": "reStructuredText",
            ".txt": "Text",
            ".json": "JSON",
            ".xml": "XML",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".ini": "INI",
            ".cfg": "Configuration",
            ".conf": "Configuration"
        }
        return language_map.get(ext, "Unknown")

    def _has_code_blocks(self, content: str) -> bool:
        """Check if content contains code blocks."""
        return bool(re.search(r"```[a-zA-Z]*\n[\s\S]*?\n```", content))

    def _has_images(self, content: str) -> bool:
        """Check if content contains image references."""
        return bool(re.search(r"!\[.*?\]\(.*?\)", content))

    def _has_links(self, content: str) -> bool:
        """Check if content contains links."""
        return bool(re.search(r"\[.*?\]\(.*?\)", content))

    def _get_heading_levels(self, content: str) -> List[int]:
        """Get list of heading levels in the content."""
        headings = re.findall(r"^(#+)\s", content, re.MULTILINE)
        return [len(h) for h in headings] 