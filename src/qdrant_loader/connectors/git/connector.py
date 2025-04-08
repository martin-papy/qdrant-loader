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

    def clone(self, url: str, to_path: str, branch: str, depth: int, max_retries: int = 3, retry_delay: int = 2) -> None:
        """Clone a Git repository.

        Args:
            url (str): Repository URL or local path
            to_path (str): Local path to clone to
            branch (str): Branch to clone
            depth (int): Clone depth (use 0 for full history)
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
            retry_delay (int, optional): Delay between retries in seconds. Defaults to 2.
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
                    self.repo = git.Repo.clone_from(url, to_path, multi_options=clone_args)
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
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def get_last_commit_date(self, file_path: str) -> datetime:
        """Get last commit date for a file.

        Args:
            file_path (str): Path to the file

        Returns:
            datetime: Last commit date
        """
        try:
            if not self.repo:
                raise RuntimeError("Repository not initialized")
            
            # Get the relative path from the repo root
            rel_path = os.path.relpath(file_path, self.repo.working_dir)
            
            # Get the last commit for the file
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=1))
            if not commits:
                return datetime.now()
            
            return datetime.fromtimestamp(commits[0].committed_date)
        except Exception as e:
            self.logger.error(f"Failed to get last commit date for {file_path}: {e}")
            raise

    def list_files(self) -> List[str]:
        """List all files in the repository.

        Returns:
            List[str]: List of file paths
        """
        try:
            if not self.repo:
                raise RuntimeError("Repository not initialized")
            
            files = []
            for root, _, filenames in os.walk(self.repo.working_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    files.append(file_path)
            
            return files
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
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def get_last_commit_date(self, file_path: str) -> datetime:
        """Get last commit date for a file.

        Args:
            file_path (str): Path to the file

        Returns:
            datetime: Last commit date
        """
        try:
            if not self.repo:
                raise RuntimeError("Repository not initialized")
            
            # Get the relative path from the repo root
            rel_path = os.path.relpath(file_path, self.repo.working_dir)
            
            # Get the last commit for the file
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=1))
            if not commits:
                return datetime.now()
            
            return datetime.fromtimestamp(commits[0].committed_date)
        except Exception as e:
            self.logger.error(f"Failed to get last commit date for {file_path}: {e}")
            raise

    def list_files(self, path: str = ".") -> List[str]:
        """List all files in the repository.

        Args:
            path (str, optional): Path to list files from. Defaults to ".".

        Returns:
            List[str]: List of file paths
        """
        try:
            if not self.repo:
                raise RuntimeError("Repository not initialized")
            
            files = []
            for root, _, filenames in os.walk(os.path.join(self.repo.working_dir, path)):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    files.append(file_path)
            
            return files
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            raise

class GitConnector:
    """Git repository connector."""

    def __init__(self, config: GitRepoConfig, git_ops: Optional[GitOperations] = None):
        """Initialize the connector.

        Args:
            config (GitRepoConfig): Git repository configuration
            git_ops (Optional[GitOperations], optional): Git operations instance. Defaults to None.
        """
        self.config = config
        self.git_ops = git_ops or GitOperations()
        self.temp_dir = None
        self.logger = get_logger(__name__)
        self.metadata_extractor = GitMetadataExtractor()

    def __enter__(self):
        """Set up the Git repository.

        Returns:
            GitConnector: The connector instance
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp()
            self.logger.info(f"Created temporary directory: {self.temp_dir}")

            # Clone repository
            self.git_ops.clone(
                url=self.config.url,
                to_path=self.temp_dir,
                branch=self.config.branch,
                depth=self.config.depth
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
            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self.temp_dir)

            # Check file size
            if os.path.getsize(file_path) > self.config.max_file_size:
                self.logger.debug(f"Skipping {rel_path}: exceeds max file size")
                return False

            # Check if file matches any include patterns
            included = False
            for pattern in self.config.include_paths:
                if pattern == "/":
                    included = True
                    break
                if fnmatch.fnmatch(rel_path, pattern.lstrip("/")):
                    included = True
                    break

            if not included:
                self.logger.debug(f"Skipping {rel_path}: not in include paths")
                return False

            # Check if file matches any exclude patterns
            for pattern in self.config.exclude_paths:
                if fnmatch.fnmatch(rel_path, pattern.lstrip("/")):
                    self.logger.debug(f"Skipping {rel_path}: matches exclude pattern {pattern}")
                    return False

            # Check if file matches any file type patterns
            for pattern in self.config.file_types:
                if fnmatch.fnmatch(rel_path, pattern):
                    return True

            self.logger.debug(f"Skipping {rel_path}: does not match any file type patterns")
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
            metadata = self.metadata_extractor.extract_metadata(
                file_path=rel_path,
                content=content,
                last_commit_date=last_commit_date,
                repo_url=self.config.url,
                branch=self.config.branch
            )

            # Create document
            return Document(
                page_content=content,
                metadata=metadata
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