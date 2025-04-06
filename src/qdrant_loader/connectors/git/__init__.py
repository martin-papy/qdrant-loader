from typing import List, Optional
import os
import tempfile
from pathlib import Path
from git import Repo, GitCommandError
from qdrant_loader.config import GitRepoConfig, GitAuthConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logger import get_logger
from .metadata_extractor import GitMetadataExtractor

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
    
    def __init__(self, config: GitRepoConfig, auth_config: Optional[GitAuthConfig] = None):
        self.config = config
        self.auth_config = auth_config
        self.temp_dir = None
        self.git_ops = None

    def __enter__(self):
        """Context manager entry."""
        self.temp_dir = tempfile.mkdtemp()
        self.git_ops = GitPythonAdapter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")

    def _clone_repository(self) -> None:
        """Clone the repository to a temporary directory."""
        if not self.temp_dir or not self.git_ops:
            raise RuntimeError("GitConnector must be used as a context manager")

        try:
            # Set up authentication if provided
            if self.auth_config and self.auth_config.token_env:
                os.environ["GIT_ASKPASS"] = "echo"
                os.environ["GIT_USERNAME"] = "token"
                os.environ["GIT_PASSWORD"] = os.getenv(self.auth_config.token_env, "")

            self.git_ops.clone(
                url=self.config.url,
                to_path=self.temp_dir,
                branch=self.config.branch,
                depth=self.config.depth
            )
            logger.info(f"Successfully cloned repository: {self.config.url}")
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise

    def _should_process_file(self, file_path: str) -> bool:
        """Check if a file should be processed based on configuration."""
        rel_path = str(Path(file_path).relative_to(self.temp_dir))
        
        # Check file size
        if self.config.max_file_size:
            file_size = os.path.getsize(file_path)
            if file_size > self.config.max_file_size:
                logger.debug(f"Skipping large file: {rel_path} ({file_size} bytes)")
                return False
        
        # Check file type
        if self.config.file_types:
            file_ext = os.path.splitext(rel_path)[1]
            logger.debug(f"Checking file type for {rel_path} (ext: {file_ext})")
            for ft in self.config.file_types:
                logger.debug(f"  Comparing with {ft} -> {ft.replace('*', '')}")
            if not any(ft.replace('*', '') == file_ext for ft in self.config.file_types):
                logger.debug(f"Skipping file type: {rel_path} (ext: {file_ext})")
                return False
        
        # Check include paths
        if self.config.include_paths:
            logger.debug(f"Checking include paths for {rel_path}")
            from fnmatch import fnmatch
            matches = False
            for p in self.config.include_paths:
                logger.debug(f"  Checking against pattern {p} -> {fnmatch(rel_path, p)}")
                if fnmatch(rel_path, p):
                    matches = True
                    break
            if not matches:
                logger.debug(f"File not in include paths: {rel_path}")
                return False
        
        # Check exclude paths
        if self.config.exclude_paths:
            logger.debug(f"Checking exclude paths for {rel_path}")
            from fnmatch import fnmatch
            for p in self.config.exclude_paths:
                logger.debug(f"  Checking against pattern {p} -> {fnmatch(rel_path, p)}")
                if fnmatch(rel_path, p):
                    logger.debug(f"File in exclude paths: {rel_path}")
                    return False
        
        logger.debug(f"File passed all filters: {rel_path}")
        return True

    def _process_file(self, file_path: str) -> Optional[Document]:
        """Process a single file into a document with enhanced metadata."""
        try:
            # Initialize metadata extractor
            extractor = GitMetadataExtractor(self.git_ops.repo, file_path)
            
            # Extract all metadata
            metadata = extractor.extract_all_metadata()
            
            # Get file content
            content = self.git_ops.get_file_content(file_path)
            
            # Create document with enhanced metadata
            return Document(
                content=content,
                metadata=metadata,
                source=self.config.url,
                source_type="git"
            )
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return None

    def get_documents(self) -> List[Document]:
        """Get documents from the Git repository."""
        if not self.temp_dir or not self.git_ops:
            raise RuntimeError("GitConnector must be used as a context manager")

        try:
            # Clone repository
            self._clone_repository()
            
            # Get all files matching the configuration
            files = self.git_ops.list_files(self.temp_dir)
            logger.debug(f"Found {len(files)} files in repository")
            for file in files:
                logger.debug(f"Found file: {file}")
            
            # Process files into documents
            documents = []
            for file_path in files:
                rel_path = str(Path(file_path).relative_to(self.temp_dir))
                logger.debug(f"Processing file: {rel_path}")
                if self._should_process_file(file_path):
                    logger.debug(f"File passed filters: {rel_path}")
                    doc = self._process_file(file_path)
                    if doc:
                        documents.append(doc)
                else:
                    logger.debug(f"File filtered out: {rel_path}")
            
            logger.info(f"Processed {len(documents)} documents from repository")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing Git repository: {e}")
            raise 