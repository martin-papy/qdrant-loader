"""Adapter for GitPython operations."""

import os
import time
from datetime import datetime

import git

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class GitPythonAdapter:
    """Adapter for GitPython operations."""

    def __init__(self, repo: git.Repo | None = None) -> None:
        """Initialize the adapter.

        Args:
            repo: Git repository instance
        """
        self.repo = repo
        self.logger = LoggingConfig.get_logger(__name__)

    def clone(self, url: str, to_path: str, branch: str, depth: int) -> None:
        """Clone a Git repository.

        Args:
            url (str): Repository URL
            to_path (str): Local path to clone to
            branch (str): Branch to clone
            depth (int): Clone depth (use 0 for full history)
        """
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                clone_args = ["--branch", branch]
                if depth > 0:
                    clone_args.extend(["--depth", str(depth)])

                # Store original value and disable credential prompts
                original_prompt = os.environ.get("GIT_TERMINAL_PROMPT")
                os.environ["GIT_TERMINAL_PROMPT"] = "0"
                try:
                    self.repo = git.Repo.clone_from(
                        url, to_path, multi_options=clone_args
                    )
                    self.logger.info(
                        f"Successfully cloned repository from {url} to {to_path}"
                    )
                finally:
                    # Restore original value
                    if original_prompt is not None:
                        os.environ["GIT_TERMINAL_PROMPT"] = original_prompt
                    else:
                        del os.environ["GIT_TERMINAL_PROMPT"]
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(
                        f"Clone attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds..."
                    )
                    time.sleep(retry_delay)
                else:
                    self.logger.error(
                        f"Failed to clone repository after {max_retries} attempts: {e}"
                    )
                    raise

    def get_file_content(self, file_path: str) -> str:
        """Get file content.

        Args:
            file_path (str): Path to the file

        Returns:
            str: File content
        """
        try:
            if not self.repo:
                raise ValueError("Repository not initialized")
            return self.repo.git.show(f"HEAD:{file_path}")
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def get_last_commit_date(self, file_path: str) -> datetime | None:
        """Get the last commit date for a file.

        Args:
            file_path (str): Path to the file

        Returns:
            Optional[datetime]: Last commit date or None if not found
        """
        try:
            repo = git.Repo(os.path.dirname(file_path), search_parent_directories=True)
            commits = list(repo.iter_commits(paths=file_path, max_count=1))
            if commits:
                last_commit = commits[0]
                return last_commit.committed_datetime
            return None
        except Exception as e:
            self.logger.error(f"Failed to get last commit date for {file_path}: {e}")
            return None

    def list_files(self, path: str = ".") -> list[str]:
        """List all files in the repository.

        Args:
            path (str, optional): Path to list files from. Defaults to ".".

        Returns:
            List[str]: List of file paths
        """
        try:
            if not self.repo:
                raise ValueError("Repository not initialized")

            # Use git ls-tree to list all files
            output = self.repo.git.ls_tree("-r", "--name-only", "HEAD", path)
            return output.splitlines() if output else []
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            raise
