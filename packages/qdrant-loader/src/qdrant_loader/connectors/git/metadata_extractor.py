import os
import re
from typing import Any

import chardet
import git

from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class GitMetadataExtractor:
    """Extract metadata from Git repository files."""

    def __init__(self, config: GitRepoConfig):
        """Initialize the Git metadata extractor.

        Args:
            config (GitRepoConfig): Configuration for the Git repository.
        """
        self.config = config
        self.logger = LoggingConfig.get_logger(__name__)

    def extract_all_metadata(self, file_path: str, content: str) -> dict[str, Any]:
        """Extract all metadata for a file.

        Args:
            file_path: Path to the file.
            content: Content of the file.

        Returns:
            dict[str, Any]: Dictionary containing all metadata.
        """
        self.logger.debug(f"Starting metadata extraction for file: {file_path!s}")

        file_metadata = self._extract_file_metadata(file_path, content)
        repo_metadata = self._extract_repo_metadata(file_path)
        git_metadata = self._extract_git_metadata(file_path)

        # Only extract structure metadata for markdown files
        structure_metadata = {}
        if file_path.lower().endswith(".md"):
            self.logger.debug(f"Processing markdown file: {file_path!s}")
            structure_metadata = self._extract_structure_metadata(content)

        metadata = {
            **file_metadata,
            **repo_metadata,
            **git_metadata,
            **structure_metadata,
        }

        self.logger.debug(f"Completed metadata extraction for {file_path!s}.")
        self.logger.debug(f"Metadata: {metadata!s}")
        return metadata

    def _extract_file_metadata(self, file_path: str, content: str) -> dict[str, Any]:
        """Extract metadata about the file itself."""
        # Get relative path from repository root
        rel_path = os.path.relpath(file_path, self.config.temp_dir)
        file_type = os.path.splitext(rel_path)[1]
        file_name = os.path.basename(rel_path)
        file_encoding = self._detect_encoding(content)
        line_count = len(content.splitlines())
        word_count = len(content.split())
        file_size = len(content.encode(file_encoding))

        return {
            "file_type": file_type,
            "file_name": file_name,
            "file_directory": os.path.dirname("/" + file_path),
            "file_encoding": file_encoding,
            "line_count": line_count,
            "word_count": word_count,
            "file_size": file_size,
            "has_code_blocks": self._has_code_blocks(content),
            "has_images": self._has_images(content),
            "has_links": self._has_links(content),
        }

    def _extract_repo_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract repository metadata from the given file path.

        Args:
            file_path (str): Path to the file.

        Returns:
            dict[str, Any]: Dictionary containing repository metadata.
        """
        try:
            # Get repository URL from config
            repo_url = str(self.config.base_url)
            if not repo_url:
                return {}

            # Extract repository name and owner from normalized URL
            normalized_url = repo_url[:-4] if repo_url.endswith(".git") else repo_url
            repo_parts = normalized_url.split("/")
            if len(repo_parts) >= 2:
                repo_owner = repo_parts[-2]
                repo_name = repo_parts[-1]
            else:
                repo_owner = ""
                repo_name = normalized_url

            # Initialize metadata with default values
            metadata = {
                "repository_name": repo_name,
                "repository_owner": repo_owner,
                "repository_url": repo_url,
                "repository_description": "",
                "repository_language": "",
            }

            try:
                repo = git.Repo(self.config.temp_dir)
                if repo and not repo.bare:
                    config = repo.config_reader()
                    # Try to get description from github section first
                    if config.has_section("github"):
                        metadata["repository_description"] = str(
                            config.get_value("github", "description", "")
                        )
                        metadata["repository_language"] = str(
                            config.get_value("github", "language", "")
                        )
                    # Fall back to core section if needed
                    if not metadata["repository_description"] and config.has_section(
                        "core"
                    ):
                        metadata["repository_description"] = str(
                            config.get_value("core", "description", "")
                        )
                    self.logger.debug(f"Repository metadata extracted: {metadata!s}")
            except Exception as e:
                self.logger.error(f"Failed to read Git config: {e}")

            return metadata
        except Exception as e:
            self.logger.error(f"Failed to extract repository metadata: {str(e)!s}")
            return {}

    def _extract_git_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract Git-specific metadata."""
        try:
            repo = git.Repo(self.config.temp_dir)
            metadata = {}

            try:
                # Get the relative path from the repository root
                rel_path = os.path.relpath(file_path, repo.working_dir)

                # Try to get commits for the file
                commits = list(repo.iter_commits(paths=rel_path, max_count=1))
                if commits:
                    last_commit = commits[0]
                    metadata.update(
                        {
                            "last_commit_date": last_commit.committed_datetime.isoformat(),
                            "last_commit_author": last_commit.author.name,
                            "last_commit_message": last_commit.message.strip(),
                        }
                    )
                else:
                    # If no commits found for the file, try getting the latest commit
                    commits = list(repo.iter_commits(max_count=1))
                    if commits:
                        last_commit = commits[0]
                        metadata.update(
                            {
                                "last_commit_date": last_commit.committed_datetime.isoformat(),
                                "last_commit_author": last_commit.author.name,
                                "last_commit_message": last_commit.message.strip(),
                            }
                        )
                    else:
                        # If still no commits found, use repository's HEAD commit
                        head_commit = repo.head.commit
                        metadata.update(
                            {
                                "last_commit_date": head_commit.committed_datetime.isoformat(),
                                "last_commit_author": head_commit.author.name,
                                "last_commit_message": head_commit.message.strip(),
                            }
                        )
            except Exception as e:
                self.logger.debug(f"Failed to get commits: {e}")
                # Try one last time with HEAD commit
                try:
                    head_commit = repo.head.commit
                    metadata.update(
                        {
                            "last_commit_date": head_commit.committed_datetime.isoformat(),
                            "last_commit_author": head_commit.author.name,
                            "last_commit_message": head_commit.message.strip(),
                        }
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to get HEAD commit: {e}")

            return metadata
        except Exception as e:
            self.logger.warning(f"Failed to extract Git metadata: {str(e)!s}")
            return {}

    def _extract_structure_metadata(self, content: str) -> dict[str, Any]:
        """Extract metadata about the document structure."""
        self.logger.debug("Starting structure metadata extraction")
        self.logger.debug(f"Content to process:\n{content!s}")

        has_toc = False
        heading_levels = []
        sections_count = 0

        # Check if content is markdown by looking for markdown headers
        # Look for markdown headers that:
        # 1. Start with 1-6 # characters at the start of a line or after a newline
        # 2. Are followed by whitespace and text
        # 3. Continue until the next newline or end of content
        headings = re.findall(
            r"(?:^|\n)\s*(#{1,6})\s+(.+?)(?:\n|$)", content, re.MULTILINE
        )
        self.logger.debug(f"Found {len(headings)!s} headers in content")

        if headings:
            self.logger.debug(f"Headers found: {headings!s}")
            has_toc = "## Table of Contents" in content or "## Contents" in content
            heading_levels = [len(h[0]) for h in headings]
            sections_count = len(heading_levels)
            self.logger.debug(
                f"Has TOC: {has_toc!s}, Heading levels: {heading_levels!s}, Sections count: {sections_count!s}"
            )
        else:
            self.logger.warning("No headers found in content")
            # Log the first few lines of content for debugging
            first_lines = "\n".join(content.splitlines()[:5])
            self.logger.debug(f"First few lines of content:\n{first_lines!s}")
            # Try alternative header detection
            alt_headings = re.findall(r"^#{1,6}\s+.+$", content, re.MULTILINE)
            if alt_headings:
                self.logger.debug(
                    f"Found {len(alt_headings)!s} headers using alternative pattern"
                )
                self.logger.debug(f"Alternative headers found: {alt_headings!s}")
                has_toc = "## Table of Contents" in content or "## Contents" in content
                heading_levels = []
                for h in alt_headings:
                    match = re.match(r"^(#{1,6})", h)
                    if match:
                        heading_levels.append(len(match.group(1)))
                sections_count = len(heading_levels)
                self.logger.debug(
                    f"Has TOC: {has_toc!s}, Heading levels: {heading_levels!s}, Sections count: {sections_count!s}"
                )

        metadata = {
            "has_toc": has_toc,
            "heading_levels": heading_levels,
            "sections_count": sections_count,
        }

        self.logger.debug(f"Structure metadata extraction completed: {metadata!s}")
        return metadata

    def _get_repo_description(self, repo: git.Repo, file_path: str) -> str:
        """Get repository description from Git config or README."""
        try:
            # Try to get description from Git config
            config = repo.config_reader()
            try:
                if config.has_section('remote "origin"'):
                    description = str(
                        config.get_value('remote "origin"', "description", default="")
                    )
                    if (
                        description
                        and isinstance(description, str)
                        and description.strip()
                        and "Unnamed repository;" not in description
                    ):
                        return description.strip()
            except Exception as e:
                self.logger.debug(f"Failed to read Git config: {e}")

            # Try to find description in README files
            readme_files = ["README.md", "README.txt", "README", "README.rst"]
            repo_root = repo.working_dir
            for readme_file in readme_files:
                readme_path = os.path.join(repo_root, readme_file)
                if os.path.exists(readme_path) and os.path.isfile(readme_path):
                    try:
                        with open(readme_path, encoding="utf-8") as f:
                            content = f.read()
                            paragraphs = []
                            current_paragraph = []
                            in_title = True
                            for line in content.splitlines():
                                line = line.strip()
                                # Skip badges and links at the start
                                if in_title and (
                                    line.startswith("[![") or line.startswith("[")
                                ):
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
                                if line.lower() in [
                                    "## installation",
                                    "## usage",
                                    "## contributing",
                                    "## license",
                                ]:
                                    break
                                in_title = False
                                current_paragraph.append(line)

                            if current_paragraph:
                                paragraphs.append(" ".join(current_paragraph))

                            # Find first meaningful paragraph
                            for paragraph in paragraphs:
                                if (
                                    len(paragraph) >= 50
                                ):  # Minimum length for a meaningful description
                                    # Clean up markdown links
                                    paragraph = re.sub(
                                        r"\[([^\]]+)\]\([^)]+\)", r"\1", paragraph
                                    )
                                    # Clean up HTML tags
                                    paragraph = re.sub(r"<[^>]+>", "", paragraph)
                                    # Limit length and break at sentence boundary
                                    if len(paragraph) > 200:
                                        sentences = re.split(
                                            r"(?<=[.!?])\s+", paragraph
                                        )
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
                        self.logger.debug(f"Failed to read README {readme_file}: {e}")
                        continue

        except Exception as e:
            self.logger.debug(f"Failed to get repository description: {e}")

        return "No description available"

    def _detect_encoding(self, content: str) -> str:
        """Detect file encoding."""
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
            ".conf": "Configuration",
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

    def _get_heading_levels(self, content: str) -> list[int]:
        """Get list of heading levels in the content."""
        headings = re.findall(r"^(#+)\s", content, re.MULTILINE)
        return [len(h) for h in headings]
