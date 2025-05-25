from abc import ABC, abstractmethod

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.document import Document


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

    @abstractmethod
    async def get_documents(self) -> list[Document]:
        """Get documents from the source."""
