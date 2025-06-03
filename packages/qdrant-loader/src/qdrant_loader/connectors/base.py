from abc import ABC, abstractmethod

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import FileConversionConfig


class BaseConnector(ABC):
    """Base class for all connectors."""

    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._initialized = False

    def set_file_conversion_config(
        self, file_conversion_config: FileConversionConfig
    ) -> None:
        """Set file conversion configuration.

        This is a default implementation that does nothing.
        Subclasses that support file conversion should override this method.

        Args:
            file_conversion_config: Global file conversion configuration
        """
        pass

    @abstractmethod
    async def get_documents(self) -> list[Document]:
        """Get documents from the source."""
