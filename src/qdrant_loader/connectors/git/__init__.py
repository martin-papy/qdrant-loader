from typing import List, Optional
import os
import tempfile
from pathlib import Path
from git import Repo, GitCommandError
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logger import get_logger
from .metadata_extractor import GitMetadataExtractor
import fnmatch
import git
from datetime import datetime

logger = get_logger(__name__)

class GitOperations:
    """Git operations."""

    def __init__(self):
        """Initialize Git operations."""
        self.repo = None
        self.logger = get_logger(__name__)

    def clone(self, url: str, to_path: str, branch: str, depth: int) -> None:
        """Clone a Git repository.

        Args:
            url (str): Repository URL
            to_path (str): Local path to clone to
            branch (str): Branch to clone
            depth (int): Clone depth (use 0 for full history)
        """
        try:
            clone_args = ['--branch', branch]
            if depth > 0:
                clone_args.extend(['--depth', str(depth)])
            
            self.repo = git.Repo.clone_from(url, to_path, multi_options=clone_args)
            self.logger.info(f"Successfully cloned repository from {url} to {to_path}")
        except git.exc.GitCommandError as e:
            self.logger.error(f"Failed to clone repository: {e}")
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

class GitPythonAdapter(GitOperations):
    """Adapter for GitPython library"""
    def __init__(self, repo: Optional[Repo] = None):
        self.repo = repo

    def clone(self, url: str, to_path: str, branch: str, depth: int) -> None:
        """Clone a Git repository.

        Args:
            url (str): Repository URL
            to_path (str): Local path to clone to
            branch (str): Branch to clone
            depth (int): Clone depth (use 0 for full history)
        """
        try:
            clone_args = ['--branch', branch]
            if depth > 0:
                clone_args.extend(['--depth', str(depth)])
            
            self.repo = git.Repo.clone_from(url, to_path, multi_options=clone_args)
            self.logger.info(f"Successfully cloned repository from {url} to {to_path}")
        except git.exc.GitCommandError as e:
            self.logger.error(f"Failed to clone repository: {e}")
            raise

    def get_file_content(self, file_path: str) -> str:
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        return Path(file_path).read_text()

    def get_last_commit_date(self) -> str:
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        return self.repo.head.commit.committed_datetime.isoformat()

    def list_files(self, path: str) -> List[str]:
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        # Use git ls-tree to get all tracked files
        files = self.repo.git.ls_tree('-r', '--name-only', 'HEAD').split('\n')
        # Convert to absolute paths
        return [str(Path(self.repo.working_dir) / f) for f in files if f]

class GitConnector:
    """Connector for Git repositories."""
    
    def __init__(self, config: GitRepoConfig, git_ops: Optional[GitOperations] = None):
        """Initialize the Git connector."""
        self.config = config
        self.git_ops = git_ops or GitOperations()
        self.temp_dir = None
        self.logger = logger
        self.metadata_extractor = GitMetadataExtractor()

    def __enter__(self):
        """Set up the Git repository."""
        self.temp_dir = tempfile.mkdtemp()
        self.git_ops.clone(self.config.url, self.temp_dir, self.config.branch, self.config.depth)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def _should_process_file(self, file_path: str) -> bool:
        """Check if a file should be processed based on configuration."""
        try:
            # Get relative path from repo root
            rel_path = os.path.relpath(file_path, self.temp_dir)
            
            # Skip .git directory
            if rel_path.startswith('.git'):
                self.logger.debug(f"Skipping .git file: {rel_path}")
                return False

            # Check file size
            if os.path.getsize(file_path) > self.config.max_file_size:
                self.logger.debug(f"File too large: {rel_path}")
                return False

            # Check file type
            if not any(fnmatch.fnmatch(os.path.basename(rel_path), pattern) for pattern in self.config.file_types):
                self.logger.debug(f"File type not matched: {rel_path}")
                return False

            # Check include paths (if any are specified)
            if self.config.include_paths and self.config.include_paths != ["**/*"]:
                matched = False
                for pattern in self.config.include_paths:
                    if fnmatch.fnmatch(rel_path, pattern):
                        matched = True
                        break
                if not matched:
                    self.logger.debug(f"File not in include paths: {rel_path}")
                    return False

            # Check exclude paths
            if self.config.exclude_paths:
                for pattern in self.config.exclude_paths:
                    if fnmatch.fnmatch(rel_path, pattern):
                        self.logger.debug(f"File in exclude paths: {rel_path}")
                        return False

            return True
        except Exception as e:
            self.logger.error(f"Error checking file {file_path}: {e}")
            return False

    def _process_file(self, file_path: str) -> Document:
        """Process a single file and return a Document."""
        try:
            # Get relative path from repo root
            rel_path = os.path.relpath(file_path, self.temp_dir)
            self.logger.info(f"Processing file: {rel_path}")

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract metadata
            metadata = self.metadata_extractor.extract_all_metadata(file_path, content)

            # Create document
            return Document(
                content=content,
                metadata=metadata,
                source=metadata.get('repository_url', ''),
                source_type='git'
            )
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            raise

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