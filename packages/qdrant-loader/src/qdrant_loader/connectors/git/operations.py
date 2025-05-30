"""Git operations wrapper."""

import os
import shutil
import time
from datetime import datetime

import git
from git.exc import GitCommandError

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class GitOperations:
    """Git operations wrapper."""

    def __init__(self):
        """Initialize Git operations."""
        self.repo = None
        self.logger = LoggingConfig.get_logger(__name__)
        self.logger.info("Initializing GitOperations")

    def clone(
        self,
        url: str,
        to_path: str,
        branch: str,
        depth: int,
        max_retries: int = 3,
        retry_delay: int = 2,
        auth_token: str | None = None,
    ) -> None:
        """Clone a Git repository.

        Args:
            url (str): Repository URL or local path
            to_path (str): Local path to clone to
            branch (str): Branch to clone
            depth (int): Clone depth (use 0 for full history)
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
            retry_delay (int, optional): Delay between retries in seconds. Defaults to 2.
            auth_token (Optional[str], optional): Authentication token. Defaults to None.
        """
        # Resolve the URL to an absolute path if it's a local path
        if os.path.exists(url):
            url = os.path.abspath(url)
            self.logger.info("Using local repository", url=url)

            # Ensure the source is a valid Git repository
            if not os.path.exists(os.path.join(url, ".git")):
                self.logger.error("Invalid Git repository", path=url)
                raise ValueError(f"Path {url} is not a valid Git repository")

            # Copy the repository
            shutil.copytree(url, to_path, dirs_exist_ok=True)
            self.repo = git.Repo(to_path)
            return

        for attempt in range(max_retries):
            try:
                clone_args = ["--branch", branch]
                if depth > 0:
                    clone_args.extend(["--depth", str(depth)])

                # Store original value and disable credential prompts
                original_prompt = os.environ.get("GIT_TERMINAL_PROMPT")
                os.environ["GIT_TERMINAL_PROMPT"] = "0"
                self.logger.info(
                    f"Cloning repository : {url} | branch: {branch} | depth: {depth}",
                )
                try:
                    # If auth token is provided, modify the URL to include it
                    clone_url = url
                    if auth_token and url.startswith("https://"):
                        # Insert token into URL: https://token@github.com/...
                        clone_url = url.replace("https://", f"https://{auth_token}@")
                        self.logger.debug("Using authenticated URL", url=clone_url)

                    self.logger.debug(
                        "Attempting to clone repository",
                        attempt=attempt + 1,
                        max_attempts=max_retries,
                        url=clone_url,
                        branch=branch,
                        depth=depth,
                        to_path=to_path,
                    )

                    # Verify target directory is empty
                    if os.path.exists(to_path) and os.listdir(to_path):
                        self.logger.warning(
                            "Target directory is not empty",
                            to_path=to_path,
                            contents=os.listdir(to_path),
                        )
                        shutil.rmtree(to_path)
                        os.makedirs(to_path)

                    self.repo = git.Repo.clone_from(
                        clone_url, to_path, multi_options=clone_args
                    )

                    # Verify repository was cloned successfully
                    if not self.repo or not os.path.exists(
                        os.path.join(to_path, ".git")
                    ):
                        raise RuntimeError("Repository was not cloned successfully")

                    self.logger.info("Successfully cloned repository")
                finally:
                    # Restore original value
                    if original_prompt is not None:
                        os.environ["GIT_TERMINAL_PROMPT"] = original_prompt
                    else:
                        del os.environ["GIT_TERMINAL_PROMPT"]
                return
            except GitCommandError as e:
                self.logger.error(
                    "Git clone attempt failed",
                    attempt=attempt + 1,
                    max_attempts=max_retries,
                    error=str(e),
                    error_type=type(e).__name__,
                    stderr=getattr(e, "stderr", None),
                )
                if attempt < max_retries - 1:
                    self.logger.warning(
                        f"Retrying in {retry_delay} seconds...",
                        next_attempt=attempt + 2,
                    )
                    time.sleep(retry_delay)
                else:
                    self.logger.error("All clone attempts failed", error=str(e))
                    raise

    def get_file_content(self, file_path: str) -> str:
        """Get file content.

        Args:
            file_path (str): Path to the file

        Returns:
            str: File content

        Raises:
            ValueError: If repository is not initialized
            FileNotFoundError: If file does not exist in the repository
            Exception: For other errors
        """
        try:
            if not self.repo:
                raise ValueError("Repository not initialized")

            # Get the relative path from the repository root
            rel_path = os.path.relpath(file_path, self.repo.working_dir)

            # Check if file exists in the repository
            try:
                # First try to get the file content using git show
                content = self.repo.git.show(f"HEAD:{rel_path}")
                return content
            except GitCommandError as e:
                if "exists on disk, but not in" in str(e):
                    # File exists on disk but not in the repository
                    raise FileNotFoundError(
                        f"File {rel_path} exists on disk but not in the repository"
                    ) from e
                elif "does not exist" in str(e):
                    # File does not exist in the repository
                    raise FileNotFoundError(
                        f"File {rel_path} does not exist in the repository"
                    ) from e
                else:
                    # Other git command errors
                    raise
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def get_last_commit_date(self, file_path: str) -> datetime | None:
        """Get the last commit date for a file.

        Args:
            file_path: Path to the file

        Returns:
            Last commit date or None if not found
        """
        try:
            if not self.repo:
                raise ValueError("Repository not initialized")

            # Get the relative path from the repository root
            rel_path = os.path.relpath(file_path, self.repo.working_dir)
            self.logger.debug("Getting last commit date", file_path=rel_path)

            # Get the last commit for the file
            try:
                commits = list(self.repo.iter_commits(paths=rel_path, max_count=1))
                if commits:
                    last_commit = commits[0]
                    self.logger.debug(
                        "Found last commit",
                        file_path=rel_path,
                        commit_date=last_commit.committed_datetime,
                        commit_hash=last_commit.hexsha,
                    )
                    return last_commit.committed_datetime
                self.logger.debug("No commits found for file", file_path=rel_path)
                return None
            except GitCommandError as e:
                self.logger.warning(
                    "Failed to get commits for file",
                    file_path=rel_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return None
            except BrokenPipeError as e:
                self.logger.warning(
                    "Git process terminated unexpectedly",
                    file_path=rel_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return None
            except Exception as e:
                self.logger.warning(
                    "Unexpected error getting commits",
                    file_path=rel_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return None

        except Exception as e:
            self.logger.error(
                "Failed to get last commit date",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def get_first_commit_date(self, file_path: str) -> datetime | None:
        """Get the creation date for a file.

        Args:
            file_path: Path to the file

        Returns:
            Creation date or None if not found
        """
        try:
            if not self.repo:
                raise ValueError("Repository not initialized")

            # Get the relative path from the repository root
            rel_path = os.path.relpath(file_path, self.repo.working_dir)
            self.logger.debug("Getting creation date", file_path=rel_path)

            # Get the first commit for the file
            try:
                # Use git log with --reverse to get commits in chronological order
                commits = list(
                    self.repo.iter_commits(paths=rel_path, reverse=True, max_count=1)
                )
                if commits:
                    first_commit = commits[0]
                    self.logger.debug(
                        "Found first commit",
                        file_path=rel_path,
                        commit_date=first_commit.committed_datetime,
                        commit_hash=first_commit.hexsha,
                    )
                    return first_commit.committed_datetime
                self.logger.debug("No commits found for file", file_path=rel_path)
                return None
            except GitCommandError as e:
                self.logger.warning(
                    "Failed to get commits for file",
                    file_path=rel_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return None
            except BrokenPipeError as e:
                self.logger.warning(
                    "Git process terminated unexpectedly",
                    file_path=rel_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return None
            except Exception as e:
                self.logger.warning(
                    "Unexpected error getting commits",
                    file_path=rel_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return None

        except Exception as e:
            self.logger.error(
                "Failed to get creation date",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def list_files(self) -> list[str]:
        """List all files in the repository.

        Returns:
            List of file paths
        """
        try:
            if not self.repo:
                raise ValueError("Repository not initialized")

            # Use git ls-tree to list all files
            output = self.repo.git.ls_tree("-r", "--name-only", "HEAD")
            files = output.splitlines() if output else []

            # Convert relative paths to absolute paths
            return [os.path.join(self.repo.working_dir, f) for f in files]
        except Exception as e:
            self.logger.error("Failed to list files", error=str(e))
            raise
