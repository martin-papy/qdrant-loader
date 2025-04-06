from typing import List, Optional
import os
import tempfile
from pathlib import Path
from git import Repo, GitCommandError
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logger import get_logger

logger = get_logger(__name__)

class GitOperations:
    """Abstract interface for Git operations"""
    def clone(self, url: str, to_path: str, branch: str, depth: int) -> None:
        raise NotImplementedError

    def get_file_content(self, file_path: str) -> str:
        raise NotImplementedError

    def get_last_commit_date(self) -> str:
        raise NotImplementedError

    def list_files(self, path: str) -> List[str]:
        raise NotImplementedError

class GitPythonAdapter(GitOperations):
    """Adapter for GitPython library"""
    def __init__(self, repo: Optional[Repo] = None):
        self.repo = repo

    def clone(self, url: str, to_path: str, branch: str, depth: int) -> None:
        try:
            self.repo = Repo.clone_from(
                url,
                to_path,
                branch=branch,
                depth=depth
            )
        except GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise

    def get_file_content(self, file_path: str) -> str:
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        return Path(file_path).read_text()

    def get_last_commit_date(self) -> str:
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        return self.repo.git.log("-1", "--format=%cd", "--date=iso")

    def list_files(self, path: str) -> List[str]:
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        files = []
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files

class GitConnector:
    """Connector for Git repositories"""
    def __init__(self, config: GitRepoConfig, git_ops: Optional[GitOperations] = None):
        self.config = config
        self.temp_dir = None
        self.repo = None
        self.git_ops = git_ops or GitPythonAdapter()

    def _clone_repository(self) -> None:
        """Clone the repository to a temporary directory"""
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp()
        
        try:
            self.git_ops.clone(
                self.config.url,
                self.temp_dir,
                self.config.branch,
                self.config.depth
            )
        except Exception as e:
            logger.error(f"Failed to process Git repository: {e}")
            raise

    def _should_process_file(self, file_path: str) -> bool:
        """Check if a file should be processed based on configuration"""
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.config.max_file_size:
            logger.debug(f"File {file_path} exceeds max size: {file_size} > {self.config.max_file_size}")
            return False

        # Check file type
        file_ext = os.path.splitext(file_path)[1]
        if not any(ft.replace("*", "") == file_ext for ft in self.config.file_types):
            logger.debug(f"File {file_path} with extension {file_ext} does not match any of {self.config.file_types}")
            return False

        # Check include/exclude paths
        rel_path = os.path.relpath(file_path, self.temp_dir)
        if self.config.include_paths:
            # Special case for **/* pattern
            if not any(p == "**/*" or Path(rel_path).match(p) for p in self.config.include_paths):
                logger.debug(f"File {file_path} does not match any include paths: {self.config.include_paths}")
                return False
        if self.config.exclude_paths and any(Path(rel_path).match(p) for p in self.config.exclude_paths):
            logger.debug(f"File {file_path} matches exclude paths: {self.config.exclude_paths}")
            return False

        logger.debug(f"File {file_path} passed all checks")
        return True

    def _process_file(self, file_path: str) -> Document:
        """Process a single file and return a Document"""
        try:
            content = self.git_ops.get_file_content(file_path)
            last_commit_date = self.git_ops.get_last_commit_date()
            
            return Document(
                content=content,
                source=self.config.url,
                source_type="git",
                project=self.config.url.split("/")[-1].replace(".git", ""),
                metadata={
                    "file_path": file_path,
                    "branch": self.config.branch,
                    "file_size": os.path.getsize(file_path),
                    "last_commit_date": last_commit_date
                }
            )
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            raise

    def get_documents(self) -> List[Document]:
        """Get all documents from the repository"""
        self._clone_repository()
        
        documents = []
        for file_path in self.git_ops.list_files(self.temp_dir):
            if self._should_process_file(file_path):
                try:
                    doc = self._process_file(file_path)
                    documents.append(doc)
                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {e}")
                    continue
        
        return documents

    def cleanup(self) -> None:
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
        self.temp_dir = None
        self.repo = None 