"""Git repository connector implementation."""

import os
import tempfile
import shutil
import fnmatch
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from langchain.schema import Document
from pydantic.v1 import BaseModel  # Use v1 explicitly since langchain still uses it

from pathlib import Path
from git import Repo, GitCommandError
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logger import get_logger
from .metadata_extractor import GitMetadataExtractor
from .config import GitRepoConfig
import git
import time

logger = get_logger(__name__)

class GitOperations:
    """Git operations wrapper."""

    def __init__(self, logger: logging.Logger = None):
        """Initialize Git operations.

        Args:
            logger (logging.Logger, optional): Logger instance. Defaults to None.
        """
        self.repo = None
        self.logger = logger or logging.getLogger(__name__)

    def clone(self, url: str, to_path: str, branch: str, depth: int, max_retries: int = 3, retry_delay: int = 2, auth_token: Optional[str] = None) -> None:
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
            self.logger.info(f"Using local repository at {url}")
            
            # Ensure the source is a valid Git repository
            if not os.path.exists(os.path.join(url, '.git')):
                raise ValueError(f"Path {url} is not a valid Git repository")
            
            # Copy the repository
            shutil.copytree(url, to_path, dirs_exist_ok=True)
            self.repo = git.Repo(to_path)
            return

        for attempt in range(max_retries):
            try:
                clone_args = ['--branch', branch]
                if depth > 0:
                    clone_args.extend(['--depth', str(depth)])

                # Store original value and disable credential prompts
                original_prompt = os.environ.get('GIT_TERMINAL_PROMPT')
                os.environ['GIT_TERMINAL_PROMPT'] = '0'

                try:
                    # If auth token is provided, modify the URL to include it
                    clone_url = url
                    if auth_token and url.startswith('https://'):
                        # Insert token into URL: https://token@github.com/...
                        clone_url = url.replace('https://', f'https://{auth_token}@')

                    self.repo = git.Repo.clone_from(clone_url, to_path, multi_options=clone_args)
                    self.logger.info(f"Successfully cloned repository from {url} to {to_path}")
                finally:
                    # Restore original value
                    if original_prompt is not None:
                        os.environ['GIT_TERMINAL_PROMPT'] = original_prompt
                    else:
                        del os.environ['GIT_TERMINAL_PROMPT']
                return
            except git.exc.GitCommandError as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Clone attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"All clone attempts failed: {e}")
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
            except git.exc.GitCommandError as e:
                if "exists on disk, but not in" in str(e):
                    # File exists on disk but not in the repository
                    raise FileNotFoundError(f"File {rel_path} exists on disk but not in the repository")
                elif "does not exist" in str(e):
                    # File does not exist in the repository
                    raise FileNotFoundError(f"File {rel_path} does not exist in the repository")
                else:
                    # Other git command errors
                    raise
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def get_last_commit_date(self, file_path: str) -> Optional[datetime]:
        """Get the last commit date for a file.

        Args:
            file_path (str): Path to the file

        Returns:
            Optional[datetime]: Last commit date or None if not found
        """
        try:
            if not self.repo:
                raise ValueError("Repository not initialized")
            
            # Get the relative path from the repository root
            rel_path = os.path.relpath(file_path, self.repo.working_dir)
            
            # Get the last commit for the file
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=1))
            if commits:
                last_commit = commits[0]
                return last_commit.committed_datetime
            return None
        except Exception as e:
            self.logger.error(f"Failed to get last commit date for {file_path}: {e}")
            return None

    def list_files(self) -> List[str]:
        """List all files in the repository.

        Returns:
            List[str]: List of file paths
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
            self.logger.error(f"Failed to list files: {e}")
            raise

class GitPythonAdapter:
    """Adapter for GitPython operations."""

    def __init__(self, repo: Optional[git.Repo] = None) -> None:
        """Initialize the adapter.

        Args:
            repo (Optional[git.Repo]): Git repository instance
        """
        self.repo = repo
        self.logger = get_logger(__name__)

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
                clone_args = ['--branch', branch]
                if depth > 0:
                    clone_args.extend(['--depth', str(depth)])

                # Store original value and disable credential prompts
                original_prompt = os.environ.get('GIT_TERMINAL_PROMPT')
                os.environ['GIT_TERMINAL_PROMPT'] = '0'
                try:
                    self.repo = git.Repo.clone_from(url, to_path, multi_options=clone_args)
                    self.logger.info(f"Successfully cloned repository from {url} to {to_path}")
                finally:
                    # Restore original value
                    if original_prompt is not None:
                        os.environ['GIT_TERMINAL_PROMPT'] = original_prompt
                    else:
                        del os.environ['GIT_TERMINAL_PROMPT']
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Clone attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to clone repository after {max_retries} attempts: {e}")
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

    def get_last_commit_date(self, file_path: str) -> Optional[datetime]:
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

    def list_files(self, path: str = ".") -> List[str]:
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

class GitConnector:
    """Git repository connector."""

    def __init__(self, config: GitRepoConfig):
        """Initialize the Git connector.
        
        Args:
            config: Configuration for the Git repository
        """
        self.config = config
        self.temp_dir = None  # Will be set in __enter__
        self.metadata_extractor = GitMetadataExtractor(config=self.config)
        self.git_ops = GitOperations()
        self.logger = get_logger(__name__)

    def __enter__(self):
        """Set up the Git repository.

        Returns:
            GitConnector: The connector instance
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp()
            self.config.temp_dir = self.temp_dir  # Update config with the actual temp dir
            self.logger.info(f"Created temporary directory: {self.temp_dir}")

            # Get auth token from config
            auth_token = None
            if self.config.auth and self.config.auth.token:
                auth_token = self.config.auth.token
            elif self.config.token:
                auth_token = self.config.token

            # Clone repository
            self.git_ops.clone(
                url=self.config.url,
                to_path=self.temp_dir,
                branch=self.config.branch,
                depth=self.config.depth,
                auth_token=auth_token
            )

            return self
        except Exception as e:
            # Clean up if something goes wrong
            if self.temp_dir:
                self._cleanup()
            raise RuntimeError(f"Failed to set up Git repository: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        self._cleanup()

    def _cleanup(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                self.logger.error(f"Failed to clean up temporary directory: {e}")

    def _should_process_file(self, file_path: str) -> bool:
        """Check if a file should be processed based on configuration.

        Args:
            file_path (str): Path to the file

        Returns:
            bool: True if the file should be processed, False otherwise
        """
        try:
            self.logger.debug(f"Checking if file should be processed: {file_path}")
            
            # Check if file exists and is readable
            if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
                self.logger.debug(f"Skipping {file_path}: file does not exist or is not readable")
                return False

            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self.temp_dir)
            self.logger.debug(f"Relative path: {rel_path}")

            # Skip files that are just extensions without names (e.g. ".md")
            file_basename = os.path.basename(rel_path)
            if file_basename.startswith("."):
                self.logger.debug(f"Skipping {rel_path}: invalid filename (starts with dot)")
                return False

            # Check if file matches any exclude patterns first
            for pattern in self.config.exclude_paths:
                pattern = pattern.lstrip("/")
                self.logger.debug(f"Checking exclude pattern: {pattern}")
                if pattern.endswith("/**"):
                    dir_pattern = pattern[:-3]  # Remove /** suffix
                    if dir_pattern == os.path.dirname(rel_path) or os.path.dirname(rel_path).startswith(dir_pattern + "/"):
                        self.logger.debug(f"Skipping {rel_path}: matches exclude directory pattern {pattern}")
                        return False
                elif pattern.endswith("/"):
                    dir_pattern = pattern[:-1]  # Remove trailing slash
                    if os.path.dirname(rel_path) == dir_pattern or os.path.dirname(rel_path).startswith(dir_pattern + "/"):
                        self.logger.debug(f"Skipping {rel_path}: matches exclude directory pattern {pattern}")
                        return False
                elif fnmatch.fnmatch(rel_path, pattern):
                    self.logger.debug(f"Skipping {rel_path}: matches exclude pattern {pattern}")
                    return False

            # Check if file matches any file type patterns (case-insensitive)
            file_type_match = False
            file_ext = os.path.splitext(file_basename)[1].lower()  # Get extension with dot
            for pattern in self.config.file_types:
                self.logger.debug(f"Checking file type pattern: {pattern}")
                # Extract extension from pattern (e.g., "*.md" -> ".md")
                pattern_ext = os.path.splitext(pattern)[1].lower()
                if pattern_ext and file_ext == pattern_ext:
                    file_type_match = True
                    self.logger.debug(f"File {rel_path} matches file type pattern {pattern}")
                    break

            if not file_type_match:
                self.logger.debug(f"Skipping {rel_path}: does not match any file type patterns")
                return False

            # Check file size
            file_size = os.path.getsize(file_path)
            self.logger.debug(f"File size: {file_size} bytes (max: {self.config.max_file_size})")
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
                    continue
                if pattern.endswith("/**/*"):
                    dir_pattern = pattern[:-5]  # Remove /**/* suffix
                    if dir_pattern == "" or dir_pattern == "/":
                        self.logger.debug(f"Including {rel_path}: matches root /**/* pattern")
                        return True  # Root pattern with /**/* means include everything
                    if dir_pattern == rel_dir or rel_dir.startswith(dir_pattern + "/"):
                        self.logger.debug(f"Including {rel_path}: matches directory pattern {pattern}")
                        return True
                elif pattern.endswith("/"):
                    dir_pattern = pattern[:-1]  # Remove trailing slash
                    if dir_pattern == "" or dir_pattern == "/":
                        # Root pattern with / means include only files in root directory
                        if rel_dir == "":
                            self.logger.debug(f"Including {rel_path}: matches root pattern")
                            return True
                        continue
                    if dir_pattern == rel_dir or rel_dir.startswith(dir_pattern + "/"):
                        self.logger.debug(f"Including {rel_path}: matches directory pattern {pattern}")
                        return True
                elif fnmatch.fnmatch(rel_path, pattern):
                    self.logger.debug(f"Including {rel_path}: matches exact pattern {pattern}")
                    return True

            # If we have include patterns but none matched, exclude the file
            self.logger.debug(f"Skipping {rel_path}: not in include paths")
            return False

        except Exception as e:
            self.logger.error(f"Error checking if file should be processed: {e}")
            return False

    def _process_file(self, file_path: str) -> Document:
        """Process a single file.

        Args:
            file_path (str): Path to the file

        Returns:
            Document: Document instance with file content and metadata
        """
        try:
            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self.temp_dir)

            # Read file content
            content = self.git_ops.get_file_content(file_path)

            # Get last commit date
            last_commit_date = self.git_ops.get_last_commit_date(file_path)

            # Extract metadata
            metadata = self.metadata_extractor.extract_all_metadata(
                file_path=rel_path,
                content=content
            )

            # Add Git-specific metadata
            metadata.update({
                'repository_url': self.config.url,
                'branch': self.config.branch,
                'last_commit_date': last_commit_date.isoformat() if last_commit_date else None
            })

            # Create document
            return Document(
                content=content,
                metadata=metadata,
                source=self.config.url,
                source_type="git",
                url=f"{self.config.url}/blob/{self.config.branch}/{rel_path}",
                last_updated=last_commit_date
            )

        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {e}")
            raise

    def get_documents(self) -> List[Document]:
        """Get all documents from the repository.

        Returns:
            List[Document]: List of documents
        """
        documents = []

        try:
            # List all files
            files = self.git_ops.list_files()

            # Process each file
            for file_path in files:
                if self._should_process_file(file_path):
                    try:
                        document = self._process_file(file_path)
                        documents.append(document)
                        self.logger.info(f"Successfully processed file: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Failed to process file {file_path}: {e}")
                        continue

            return documents

        except Exception as e:
            self.logger.error(f"Failed to get documents: {e}")
            raise 