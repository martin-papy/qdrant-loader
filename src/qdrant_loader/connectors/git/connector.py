"""Git repository connector implementation."""

import os
import shutil
import tempfile

import structlog

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.git.file_processor import FileProcessor
from qdrant_loader.connectors.git.metadata_extractor import GitMetadataExtractor
from qdrant_loader.connectors.git.operations import GitOperations
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class GitConnector(BaseConnector):
    """Git repository connector."""

    def __init__(self, config: GitRepoConfig):
        """Initialize the Git connector.

        Args:
            config: Configuration for the Git repository
        """
        super().__init__(config)
        self.config = config
        self.temp_dir = None  # Will be set in __enter__
        self.metadata_extractor = GitMetadataExtractor(config=self.config)
        self.git_ops = GitOperations()
        self.file_processor = None  # Will be initialized in __enter__
        self.logger = structlog.get_logger(__name__)
        self.logger.info("Initializing GitConnector")
        self.logger.debug("GitConnector Configuration", config=config.model_dump())
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp()
            self.config.temp_dir = self.temp_dir  # Update config with the actual temp dir
            self.logger.debug("Created temporary directory", temp_dir=self.temp_dir)

            # Initialize file processor
            self.file_processor = FileProcessor(config=self.config, temp_dir=self.temp_dir)

            # Get auth token from config
            auth_token = None
            if self.config.token:
                auth_token = self.config.token
                self.logger.debug("Using authentication token", token_length=len(auth_token))

            # Clone repository
            self.logger.debug(
                "Attempting to clone repository",
                url=self.config.base_url,
                branch=self.config.branch,
                depth=self.config.depth,
                temp_dir=self.temp_dir,
            )

            try:
                self.git_ops.clone(
                    url=str(self.config.base_url),
                    to_path=self.temp_dir,
                    branch=self.config.branch,
                    depth=self.config.depth,
                    auth_token=auth_token,
                )
            except Exception as clone_error:
                self.logger.error(
                    "Failed to clone repository",
                    error=str(clone_error),
                    error_type=type(clone_error).__name__,
                    url=self.config.base_url,
                    branch=self.config.branch,
                    temp_dir=self.temp_dir,
                )
                raise

            # Verify repository initialization
            if not self.git_ops.repo:
                self.logger.error("Repository not initialized after clone", temp_dir=self.temp_dir)
                raise ValueError("Repository not initialized")

            # Verify repository is valid
            try:
                self.git_ops.repo.git.status()
                self.logger.debug("Repository is valid and accessible", temp_dir=self.temp_dir)
            except Exception as status_error:
                self.logger.error(
                    "Failed to verify repository status",
                    error=str(status_error),
                    error_type=type(status_error).__name__,
                    temp_dir=self.temp_dir,
                )
                raise

            self._initialized = True
            return self
        except ValueError as e:
            # Preserve ValueError type
            self.logger.error("Failed to set up Git repository", error=str(e))
            raise ValueError(str(e)) from e  # Re-raise with the same message
        except Exception as e:
            self.logger.error(
                "Failed to set up Git repository",
                error=str(e),
                error_type=type(e).__name__,
                temp_dir=self.temp_dir,
            )
            # Clean up if something goes wrong
            if self.temp_dir:
                self._cleanup()
            raise RuntimeError(f"Failed to set up Git repository: {e}") from e

    def __enter__(self):
        """Synchronous context manager entry."""
        if not self._initialized:
            self._initialized = True
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp()
            self.config.temp_dir = self.temp_dir  # Update config with the actual temp dir
            self.logger.debug("Created temporary directory", temp_dir=self.temp_dir)

            # Initialize file processor
            self.file_processor = FileProcessor(config=self.config, temp_dir=self.temp_dir)

            # Get auth token from config
            auth_token = None
            if self.config.token:
                auth_token = self.config.token
                self.logger.debug("Using authentication token", token_length=len(auth_token))

            # Clone repository
            self.logger.debug(
                "Attempting to clone repository",
                url=self.config.base_url,
                branch=self.config.branch,
                depth=self.config.depth,
                temp_dir=self.temp_dir,
            )

            try:
                self.git_ops.clone(
                    url=str(self.config.base_url),
                    to_path=self.temp_dir,
                    branch=self.config.branch,
                    depth=self.config.depth,
                    auth_token=auth_token,
                )
            except Exception as clone_error:
                self.logger.error(
                    "Failed to clone repository",
                    error=str(clone_error),
                    error_type=type(clone_error).__name__,
                    url=self.config.base_url,
                    branch=self.config.branch,
                    temp_dir=self.temp_dir,
                )
                raise

            # Verify repository initialization
            if not self.git_ops.repo:
                self.logger.error("Repository not initialized after clone", temp_dir=self.temp_dir)
                raise ValueError("Repository not initialized")

            # Verify repository is valid
            try:
                self.git_ops.repo.git.status()
                self.logger.debug("Repository is valid and accessible", temp_dir=self.temp_dir)
            except Exception as status_error:
                self.logger.error(
                    "Failed to verify repository status",
                    error=str(status_error),
                    error_type=type(status_error).__name__,
                    temp_dir=self.temp_dir,
                )
                raise
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._cleanup()
        self._initialized = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        self._cleanup()

    def _cleanup(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.info("Cleaned up temporary directory")
            except Exception as e:
                self.logger.error(f"Failed to clean up temporary directory: {e}")

    def _process_file(self, file_path: str) -> Document:
        """Process a single file.

        Args:
            file_path: Path to the file

        Returns:
            Document instance with file content and metadata

        Raises:
            Exception: If file processing fails
        """
        try:
            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self.temp_dir)

            # Read file content
            content = self.git_ops.get_file_content(file_path)

            first_commit_date = self.git_ops.get_first_commit_date(file_path)

            # Get last commit date
            last_commit_date = self.git_ops.get_last_commit_date(file_path)

            # Extract metadata
            metadata = self.metadata_extractor.extract_all_metadata(
                file_path=rel_path, content=content
            )

            # Add Git-specific metadata
            metadata.update(
                {
                    "repository_url": self.config.base_url,
                    "branch": self.config.branch,
                    "last_commit_date": last_commit_date.isoformat() if last_commit_date else None,
                }
            )
            # Get relative path from repository root
            rel_path = os.path.relpath(file_path, self.temp_dir)
            self.logger.debug(f"Processed Git file: /{rel_path!s}")

            # Create document
            git_document = Document(
                title=os.path.basename(file_path),
                content=content,
                metadata=metadata,
                source_type=SourceType.GIT,
                source=self.config.source,
                url=f"{str(self.config.base_url).replace('.git', '')}/blob/{self.config.branch}/{rel_path}",
                is_deleted=False,
                created_at=first_commit_date,
                updated_at=last_commit_date,
            )

            return git_document
        except Exception as e:
            self.logger.error("Failed to process file", file_path=file_path, error=str(e))
            raise

    async def get_documents(self) -> list[Document]:
        """Get all documents from the repository.

        Returns:
            List of documents

        Raises:
            Exception: If document retrieval fails
        """
        try:
            self._ensure_initialized()
            try:
                files = self.git_ops.list_files()  # This will raise ValueError if not initialized
            except ValueError as e:
                self.logger.error("Failed to list files", error=str(e))
                raise ValueError("Repository not initialized") from e

            documents = []

            for file_path in files:
                if not self.file_processor.should_process_file(file_path):  # type: ignore
                    continue

                try:
                    document = self._process_file(file_path)
                    documents.append(document)

                except Exception as e:
                    self.logger.error("Failed to process file", file_path=file_path, error=str(e))
                    continue

            # Return all documents that need to be processed
            return documents

        except ValueError as e:
            # Re-raise ValueError to maintain the error type
            self.logger.error("Failed to get documents", error=str(e))
            raise
        except Exception as e:
            self.logger.error("Failed to get documents", error=str(e))
            raise

    def _ensure_initialized(self):
        """Ensure the repository is initialized before performing operations."""
        if not self._initialized:
            self.logger.error("Repository not initialized. Use the connector as a context manager.")
            raise ValueError("Repository not initialized")
