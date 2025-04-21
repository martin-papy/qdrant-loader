"""Base classes for connectors and change detectors."""

from datetime import datetime
from urllib.parse import quote, unquote

from pydantic import BaseModel, ConfigDict

from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.exceptions import InvalidDocumentStateError
from qdrant_loader.core.state.state_manager import StateManager, DocumentStateRecord
from qdrant_loader.utils.logging import LoggingConfig


class DocumentState(BaseModel):
    """Standardized document state representation.

    This class provides a consistent way to represent document states across
    all sources. It includes the essential fields needed for change detection.
    """

    uri: str  # Universal identifier in format: {source_type}:{source}:{url}:{document_id}
    content_hash: str  # Hash of document content
    updated_at: datetime  # Last update timestamp

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StateChangeDetector:
    """Base class for all change detectors.

    This class provides standardized change detection functionality that can be
    used by all sources. Subclasses only need to implement source-specific
    methods for content hashing and URI generation.
    """

    def __init__(
        self,
        state_manager: StateManager,
    ):
        """Initialize the change detector."""
        self.logger = LoggingConfig.get_logger(f"qdrant_loader.{self.__class__.__name__}")
        self._initialized = False
        self.state_manager = state_manager
        self.logger.debug(
            "Initialized %s",
            self.__class__.__name__,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""

    async def detect_changes(
        self, documents: list[Document], filtered_config: SourcesConfig
    ) -> dict[str, list[Document]]:
        """Detect changes in documents."""
        if not self._initialized:
            raise RuntimeError(
                "StateChangeDetector not initialized. Use the detector as an async context manager."
            )

        self._log_change_detection_start(len(documents))

        # Get current states
        current_states = [self._get_document_state(doc) for doc in documents]

        # Get previous states
        previous_states = await self._get_previous_states(filtered_config)

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
                content_hash=document.content_hash,
                updated_at=document.updated_at,
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
        self.logger.debug(
            "Checking if document has been updated",
            current_state=current_state.updated_at,
            previous_state=previous_state.updated_at,
            hash_diff=current_state.content_hash != previous_state.content_hash,
        )
        return (
            current_state.content_hash != previous_state.content_hash
            or current_state.updated_at > previous_state.updated_at
        )

    def _create_deleted_document(self, document_state: DocumentState) -> Document:
        """Create a minimal document for a deleted item.

        Args:
            state: The last known state of the document

        Returns:
            A minimal Document object for deletion
        """
        source_type, source, url = document_state.uri.split(":")
        url = unquote(url)
        self.logger.critical(
            "Creating deleted document",
            uri=document_state.uri,
            source_type=source_type,
            source=source,
            url=url,
        )
        return Document(
            content="",
            source=source,
            source_type=source_type,
            url=url,
            title="Deleted Document",
            metadata={
                "uri": document_state.uri,
                "title": "Deleted Document",
                "updated_at": document_state.updated_at.isoformat(),
                "content_hash": document_state.content_hash,
            },
        )

    def _log_change_detection_start(self, document_count: int):
        """Log the start of change detection.

        Args:
            document_count: Number of documents to process
            last_ingestion_time: Time of last successful ingestion
        """
        self.logger.info("Starting change detection", document_count=document_count)

    def _log_change_detection_complete(self, changes: dict[str, list[Document]]):
        """Log the completion of change detection.

        Args:
            changes: Dictionary of detected changes
        """
        self.logger.info(
            "Change detection completed",
            new_count=len(changes["new"]),
            updated_count=len(changes["updated"]),
            deleted_count=len(changes["deleted"]),
        )

    async def _get_previous_states(self, filtered_config: SourcesConfig) -> list[DocumentState]:
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

        previous_states_records: list[DocumentStateRecord] = []

        # Process each config individually
        if filtered_config.git:
            for config in filtered_config.git.values():
                previous_states_records.extend(
                    await self.state_manager.get_document_state_records(config)
                )

        if filtered_config.confluence:
            for config in filtered_config.confluence.values():
                previous_states_records.extend(
                    await self.state_manager.get_document_state_records(config)
                )

        # Process Jira projects
        if filtered_config.jira:
            for config in filtered_config.jira.values():
                previous_states_records.extend(
                    await self.state_manager.get_document_state_records(config)
                )

        # Process public documentation
        if filtered_config.publicdocs:
            for config in filtered_config.publicdocs.values():
                previous_states_records.extend(
                    await self.state_manager.get_document_state_records(config)
                )

        previous_states = [
            DocumentState(
                uri=self._generate_uri(state_record.url, state_record.source, state_record.source_type, state_record.document_id),  # type: ignore
                content_hash=state_record.content_hash,  # type: ignore
                updated_at=state_record.updated_at,  # type: ignore
            )
            for state_record in previous_states_records
        ]
        return previous_states

    def _normalize_url(self, url: str) -> str:
        """Normalize a base URL by ensuring consistent trailing slashes.

        Args:
            base_url: The base URL to normalize

        Returns:
            The normalized base URL
        """
        # Remove trailing slashes and quote the URL
        url = url.rstrip("/")
        return quote(url, safe="")

    def _generate_uri_from_document(self, document: Document) -> str:
        """Generate a URI from a document.

        Args:
            document: The document to generate URI for

        Returns:
            A URI string in format: {source_type}:{source}:{base_url}
        """
        return self._generate_uri(document.url, document.source, document.source_type, document.id)

    def _generate_uri(self, url: str, source: str, source_type: str, document_id: str) -> str:
        """Generate a URI from a URL, source, and source type.

        Args:
            url: The URL to generate URI for
            source: The source to generate URI for
            source_type: The source type to generate URI for
            document_id: The document ID
        """
        # Use the same format as Document.generate_id
        uri = f"{source_type}:{source}:{self._normalize_url(url)}"
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
            for document_state, doc in zip(current_states, documents)
            if document_state.uri in previous_states_dict
            and self._is_document_updated(document_state, previous_states_dict[document_state.uri])
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
