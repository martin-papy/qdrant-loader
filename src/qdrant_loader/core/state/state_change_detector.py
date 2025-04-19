"""Base classes for connectors and change detectors."""

from datetime import datetime
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.exceptions import InvalidDocumentStateError
from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.utils.logging import LoggingConfig


class DocumentState(BaseModel):
    """Standardized document state representation.

    This class provides a consistent way to represent document states across
    all sources. It includes the essential fields needed for change detection.
    """

    uri: str  # Universal identifier in format: {source_type}:{source}:{base_url}:{document_id}
    content_hash: str  # Hash of document content
    last_updated: datetime  # Last update timestamp

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StateChangeDetector:
    """Base class for all change detectors.

    This class provides standardized change detection functionality that can be
    used by all sources. Subclasses only need to implement source-specific
    methods for content hashing and URI generation.
    """

    def __init__(
        self,
        source_config: SourceConfig,
        state_manager: StateManager,
    ):
        """Initialize the change detector.

        Args:
            source_config: Configuration for the source
            state_manager: State manager for tracking document states
        """
        self.source_config = source_config
        self.state_manager = state_manager
        self.logger = LoggingConfig.get_logger(self.__class__.__name__)
        self._initialized = False
        self.logger.debug(
            "Initialized %s",
            self.__class__.__name__,
            source=str(getattr(self.source_config, "base_url", "")),
        )

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            await self.state_manager.initialize()
            self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    def _compute_content_hash(self, document: Document) -> str:
        """Compute a hash of the document's content.

        Args:
            document: The document to hash

        Returns:
            A string representing the content hash
        """
        # Use the content hash from metadata if available
        content_hash = document.metadata.get("content_hash")
        if content_hash:
            return str(content_hash)

        # Fallback to hashing the document's string representation
        return str(hash(str(document)))

    def _get_document_state(self, document: Document) -> DocumentState:
        """Get the standardized state of a document.

        Args:
            document: The document to get state for

        Returns:
            A DocumentState object with standardized fields

        Raises:
            InvalidDocumentStateError: If the document state is invalid
        """
        try:
            return DocumentState(
                uri=self._generate_uri_from_document(document),
                content_hash=self._compute_content_hash(document),
                last_updated=datetime.fromisoformat(document.metadata.get("last_modified", "")),
            )
        except Exception as e:
            raise InvalidDocumentStateError(f"Failed to get document state: {e}") from e

    def _is_document_updated(
        self,
        current_state: DocumentState,
        previous_state: DocumentState,
    ) -> bool:
        """Check if a document has been updated.

        Args:
            current_state: Current document state
            previous_state: Previous document state

        Returns:
            True if the document has been updated, False otherwise
        """
        return (
            current_state.content_hash != previous_state.content_hash
            or current_state.last_updated > previous_state.last_updated
        )

    def _create_deleted_document(self, state: DocumentState) -> Document:
        """Create a minimal document for a deleted item.

        Args:
            state: The last known state of the document

        Returns:
            A minimal Document object for deletion
        """
        source_type, source, base_url, document_id = state.uri.split(":")
        base_url = quote(base_url, safe="")
        return Document(
            id=document_id,
            content="",
            source=source,
            source_type=source_type,
            metadata={
                "uri": state.uri,
                "title": "Deleted Document",
                "last_modified": state.last_updated.isoformat(),
                "content_hash": state.content_hash,
            },
        )

    def _log_change_detection_start(
        self, document_count: int, last_ingestion_time: datetime | None
    ):
        """Log the start of change detection.

        Args:
            document_count: Number of documents to process
            last_ingestion_time: Time of last successful ingestion
        """
        self.logger.info(
            "Starting change detection",
            source_type=self.source_config.source_type,
            source=str(self.source_config.source),
            base_url=str(self.source_config.base_url),
            document_count=document_count,
            last_ingestion_time=last_ingestion_time,
        )

    def _log_change_detection_complete(self, changes: dict[str, list[Document]]):
        """Log the completion of change detection.

        Args:
            changes: Dictionary of detected changes
        """
        self.logger.info(
            "Change detection completed",
            source_type=self.source_config.source_type,
            source=self.source_config.source,
            base_url=str(self.source_config.base_url),
            new_count=len(changes["new"]),
            updated_count=len(changes["updated"]),
            deleted_count=len(changes["deleted"]),
        )

    async def _get_previous_states(
        self,
        last_ingestion_time: datetime | None = None,
    ) -> list[DocumentState]:
        """Get previous document states from the state manager.

        Args:
            last_ingestion_time: Time of last successful ingestion

        Returns:
            List of previous document states
        """
        if not self._initialized:
            raise RuntimeError(
                "StateChangeDetector not initialized. Use the detector as an async context manager."
            )
        states = await self.state_manager.get_document_states(
            source_type=self.source_config.source_type,
            source=self.source_config.source,
            since=last_ingestion_time,
        )
        return [self._state_to_document_state(state) for state in states]

    def _normalize_base_url(self, base_url: str) -> str:
        """Normalize a base URL by ensuring consistent trailing slashes.

        Args:
            base_url: The base URL to normalize

        Returns:
            The normalized base URL
        """
        # Remove trailing slashes and quote the URL
        base_url = base_url.rstrip("/")
        return quote(base_url, safe="")

    def _state_to_document_state(self, state: Any) -> DocumentState:
        """Convert a state manager state to a DocumentState.

        Args:
            state: The state from the state manager

        Returns:
            A DocumentState object
        """
        if isinstance(state, DocumentState):
            return state

        base_url = self._normalize_base_url(str(self.source_config.base_url))
        source = self.source_config.source
        source_type = self.source_config.source_type
        uri = f"{source_type}:{source}:{base_url}:{state.document_id}"
        return DocumentState(
            uri=uri,
            content_hash=str(state.content_hash),
            last_updated=(
                state.last_updated
                if isinstance(state.last_updated, datetime)
                else datetime.fromisoformat(str(state.last_updated))
            ),
        )

    def _generate_uri_from_document(self, document: Document) -> str:
        """Generate a URI from a document.

        Args:
            document: The document to generate URI for

        Returns:
            A URI string in format: {source_type}:{source}:{base_url}:{documentId}
        """
        base_url = self._normalize_base_url(str(self.source_config.base_url))
        source = self.source_config.source
        source_type = self.source_config.source_type

        uri = f"{source_type}:{source}:{base_url}:{document.id}"

        return uri

    async def _find_new_documents(
        self,
        current_states: list[DocumentState],
        previous_states: list[DocumentState],
        documents: list[Document],
    ) -> list[Document]:
        """Find new documents by comparing current and previous states."""
        if not self._initialized:
            raise RuntimeError(
                "StateChangeDetector not initialized. Use the detector as an async context manager."
            )
        previous_uris = {state.uri for state in previous_states}
        return [
            doc for state, doc in zip(current_states, documents) if state.uri not in previous_uris
        ]

    async def _find_updated_documents(
        self,
        current_states: list[DocumentState],
        previous_states: list[DocumentState],
        documents: list[Document],
    ) -> list[Document]:
        """Find updated documents by comparing current and previous states."""
        if not self._initialized:
            raise RuntimeError(
                "StateChangeDetector not initialized. Use the detector as an async context manager."
            )
        previous_states_dict = {state.uri: state for state in previous_states}
        return [
            doc
            for state, doc in zip(current_states, documents)
            if state.uri in previous_states_dict
            and self._is_document_updated(state, previous_states_dict[state.uri])
        ]

    async def _find_deleted_documents(
        self,
        current_states: list[DocumentState],
        previous_states: list[DocumentState],
    ) -> list[Document]:
        """Find deleted documents by comparing current and previous states.

        Args:
            current_states: List of current document states
            previous_states: List of previous document states

        Returns:
            List of deleted documents
        """
        if not self._initialized:
            raise RuntimeError(
                "StateChangeDetector not initialized. Use the detector as an async context manager."
            )
        current_uris = {state.uri for state in current_states}
        deleted_states = [state for state in previous_states if state.uri not in current_uris]

        return [self._create_deleted_document(state) for state in deleted_states]

    async def detect_changes(
        self,
        documents: list[Document],
        last_ingestion_time: datetime | None = None,
    ) -> dict[str, list[Document]]:
        """Detect changes in documents."""
        if not self._initialized:
            raise RuntimeError(
                "StateChangeDetector not initialized. Use the detector as an async context manager."
            )
        self._log_change_detection_start(len(documents), last_ingestion_time)

        # Get current states
        current_states = [self._get_document_state(doc) for doc in documents]

        # Get previous states
        previous_states = await self._get_previous_states(last_ingestion_time)

        # Compare states
        changes = {
            "new": await self._find_new_documents(current_states, previous_states, documents),
            "updated": await self._find_updated_documents(
                current_states, previous_states, documents
            ),
            "deleted": await self._find_deleted_documents(current_states, previous_states),
        }

        self._log_change_detection_complete(changes)
        return changes
