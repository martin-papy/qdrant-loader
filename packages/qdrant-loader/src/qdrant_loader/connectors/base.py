import warnings
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import FileConversionConfig


class ConnectorConfigurationError(Exception):
    """Raised when a connector's configuration is invalid or access is denied.

    This is a *fatal* error: the pipeline should stop rather than silently
    continuing with 0 documents.
    """


class BaseConnector(ABC):
    """Base class for all connectors."""

    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, _exc_tb):
        """Async context manager exit."""
        self._initialized = False

    def set_file_conversion_config(
        self, file_conversion_config: FileConversionConfig
    ) -> None:
        """Set file conversion configuration.

        This default implementation stores the configuration for potential
        use by subclasses that choose to honor it.

        Args:
            file_conversion_config: Global file conversion configuration
        """
        # Store on the instance so connectors that opt-in can access it.
        self._file_conversion_config = file_conversion_config

    async def stream_documents(
        self, since: datetime | None = None
    ) -> AsyncIterator[Document]:
        """Stream documents from the source (WS-1 connector contract).

        This default implementation bridges legacy connectors by calling
        :meth:`get_documents` and yielding documents from the returned list.

        Args:
            since: Optional datetime to fetch documents updated after this time.

        Yields:
            Document objects from the source.
        """
        if (
            type(self).get_documents is BaseConnector.get_documents
            and type(self).stream_documents is BaseConnector.stream_documents
        ):
            raise NotImplementedError(
                f"{type(self).__name__} does not implement stream_documents or get_documents"
            )

        documents = await self.get_documents()
        for document in documents:
            yield document

    @abstractmethod
    async def get_documents(self) -> list[Document]:
        """Get documents from the source (DEPRECATED - use stream_documents)."""
        warnings.warn(
            "BaseConnector.get_documents is deprecated. Implement stream_documents() "
            "or use connector.stream_documents() to avoid materializing the full "
            "document list in memory.",
            DeprecationWarning,
            stacklevel=2,
        )
        documents: list[Document] = []
        async for document in self.stream_documents():
            documents.append(document)
        return documents

    async def fetch_by_id(self, entity_id: str) -> Document | None:
        """Fetch a single entity by ID (WS-1 connector contract).

        Connectors that support single-event ingestion must override this method.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support fetch_by_id")

    async def list_entity_ids(self) -> AsyncIterator[str]:
        """Stream all entity IDs for reconciliation (WS-1 connector contract).

        Yields:
            Entity IDs from the source.
        """
        # Make this an async generator so callers can use `async for` and
        # receive a NotImplementedError during iteration rather than at call-time.
        if False:  # pragma: no cover - makes this function an async generator
            yield ""
        raise NotImplementedError(
            f"{type(self).__name__} does not support list_entity_ids"
        )
