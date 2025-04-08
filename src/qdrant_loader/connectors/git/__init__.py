import os
import tempfile
import shutil
import fnmatch
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from langchain.schema import Document
from pydantic.v1 import BaseModel  # Use v1 explicitly since langchain still uses it

from ...config import GitRepoConfig

from pathlib import Path
from git import Repo, GitCommandError
from qdrant_loader.config import GitAuthConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logger import get_logger
from .metadata_extractor import GitMetadataExtractor
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
        # If url is a local path, copy the repository instead of cloning
        if os.path.exists(url):
            self.logger.info(f"Using local repository at {url}")
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
        """Get the content of a file in the repository.

        Args:
            file_path (str): Path to the file

        Returns:
            str: File content
        """
        try:
            if self.repo is None:
                raise ValueError("Repository not initialized")
            return self.repo.git.show(f"HEAD:{file_path}")
        except Exception as e:
            self.logger.error(f"Failed to get file content: {str(e)}")
            raise

    def get_last_commit_date(self, file_path: str) -> datetime:
        """Get the last commit date for a file.

        Args:
            file_path (str): Path to the file

        Returns:
            datetime: Last commit date
        """
        try:
            if self.repo is None:
                raise ValueError("Repository not initialized")
            log = self.repo.git.log("-1", "--format=%ai", file_path)
            return datetime.fromisoformat(log.strip())
        except Exception as e:
            self.logger.error(f"Failed to get last commit date: {str(e)}")
            raise

    def list_files(self, path: str = ".") -> List[str]:
        """List files in the repository.

        Args:
            path (str): Path to list files from

        Returns:
            List[str]: List of file paths
        """
        try:
            if self.repo is None:
                raise ValueError("Repository not initialized")
            return [line.split()[-1] for line in self.repo.git.ls_tree("-r", "--name-only", "HEAD", path).splitlines()]
        except Exception as e:
            self.logger.error(f"Failed to list files: {str(e)}")
            raise

class GitConnector:
    """Connector for Git repositories."""
    
    def __init__(self, config: GitRepoConfig, git_ops: Optional[GitOperations] = None):
        """Initialize the Git connector."""
        self.config = config
        self.git_ops = git_ops or GitOperations()
        self.temp_dir = None
        self.logger = logger
        self.metadata_extractor = GitMetadataExtractor(config)

    def __enter__(self):
        """Enter the context manager."""
        try:
            self.temp_dir = tempfile.mkdtemp()
            self.logger.info(f"Created temporary directory: {self.temp_dir}")
            
            # Get authentication token if configured
            token = None
            if self.config.auth.type != "none":
                token = self.config.auth.get_token()
                if not token:
                    self._cleanup()
                    raise ValueError("Authentication token not found in environment variable")
            
            # Modify URL for authenticated access if token is present
            url = self.config.url
            if token and url.startswith("https://"):
                # For GitHub/GitLab/Bitbucket, insert token into URL
                if self.config.auth.type in ["github", "gitlab"]:
                    url = url.replace("https://", f"https://{token}@")
                elif self.config.auth.type == "bitbucket":
                    url = url.replace("https://", f"https://x-token-auth:{token}@")
            
            try:
                self.git_ops.clone(
                    url=url,
                    to_path=self.temp_dir,
                    branch=self.config.branch,
                    depth=self.config.depth
                )
            except Exception as e:
                self._cleanup()
                raise
            return self
        except Exception as e:
            self.logger.error(f"Failed to initialize Git connector: {str(e)}")
            self._cleanup()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        self._cleanup()

    def _cleanup(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.logger.error(f"Failed to clean up temporary directory {self.temp_dir}: {str(e)}")
            self.temp_dir = None

    def _should_process_file(self, file_path: str) -> bool:
        """Check if a file should be processed based on its path and type.

        Args:
            file_path (str): Path to the file to check.

        Returns:
            bool: True if the file should be processed, False otherwise.
        """
        # Skip if file doesn't exist or isn't a regular file
        if not os.path.isfile(file_path):
            return False

        # Get relative path from repo root for path matching
        rel_path = os.path.relpath(file_path, self.temp_dir)

        # Skip .git directory
        if rel_path.startswith('.git/'):
            return False

        # Get the file name and extension
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_name)

        # Skip if no extension
        if not ext:
            return False

        # Skip if file name starts with a dot (hidden file)
        if file_name.startswith('.'):
            return False

        # Check if file matches any of the allowed patterns
        if self.config.file_types:
            matches_pattern = False
            for pattern in self.config.file_types:
                # Ensure pattern starts with * to match any file name
                if not pattern.startswith('*'):
                    pattern = '*' + pattern
                if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                    matches_pattern = True
                    break
            if not matches_pattern:
                return False

        # Check file size
        if self.config.max_file_size:
            file_size = os.path.getsize(file_path)
            if file_size > self.config.max_file_size:
                return False

        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            return False

        # Check include paths
        if self.config.include_paths:
            include_matched = False
            for pattern in self.config.include_paths:
                # Handle root directory files
                if pattern == '' or pattern == '/':
                    if os.path.dirname(rel_path) == '':  # Only match files directly in root
                        include_matched = True
                        break
                    continue
                # Ensure pattern ends with / for directory matching
                if not pattern.endswith('/'):
                    pattern = pattern + '/'
                # Check if the file is in an included directory
                if rel_path.startswith(pattern):
                    include_matched = True
                    break
            if not include_matched:
                return False

        # Check exclude paths
        if self.config.exclude_paths:
            for pattern in self.config.exclude_paths:
                # Handle root directory files
                if pattern == '' or pattern == '/':
                    return False
                # Ensure pattern ends with / for directory matching
                if not pattern.endswith('/'):
                    pattern = pattern + '/'
                # Check if the file is in an excluded directory
                if rel_path.startswith(pattern):
                    return False

        return True

    def _process_file(self, file_path: str) -> Document:
        """Process a single file and return a single document.

        Args:
            file_path (str): Path to the file to process.

        Returns:
            Document: Single document with the file content and metadata.
        """
        if not self._should_process_file(file_path):
            return None

        try:
            # Get file statistics
            file_stats = os.stat(file_path)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract metadata
            metadata = {
                'file_path': os.path.relpath(file_path, self.temp_dir),
                'file_name': os.path.basename(file_path),
                'file_type': os.path.splitext(file_path)[1].lower().lstrip('.'),
                'file_size': file_stats.st_size,
                'last_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'repository_url': self.config.url
            }

            # Create document with content and metadata
            document = Document(
                content=content,
                source=self.config.url,  # Use repository URL as source
                source_type="git",  # Set source type to git
                metadata=metadata
            )

            return document  # Return single Document instance

        except UnicodeDecodeError:
            logger.warning(f"Could not decode file {file_path} as UTF-8, skipping")
            return None
        except IOError as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None

    def get_documents(self) -> List[Document]:
        """Get all documents from the repository."""
        documents = []
        try:
            # Walk through repository
            for root, _, files in os.walk(self.temp_dir):
                self.logger.info(f"Found {len(files)} files in repository")
                for file in files:
                    file_path = os.path.join(root, file)
                    self.logger.debug(f"Found file: {file_path}")
                    
                    # Check if file should be processed
                    if self._should_process_file(file_path):
                        try:
                            doc = self._process_file(file_path)
                            if doc:
                                documents.append(doc)
                        except Exception as e:
                            self.logger.error(f"Failed to process file {file_path}: {e}")
                    else:
                        self.logger.debug(f"File filtered out: {file}")

            self.logger.info(f"Processed {len(documents)} documents from repository")
            return documents
        except Exception as e:
            self.logger.error(f"Error getting documents: {e}")
            raise 