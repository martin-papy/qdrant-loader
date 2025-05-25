"""Base classes for connectors and change detectors."""

from datetime import datetime
from urllib.parse import quote, unquote

from pydantic import BaseModel, ConfigDict

from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.exceptions import InvalidDocumentStateError
from qdrant_loader.core.state.state_manager import DocumentStateRecord, StateManager
from qdrant_loader.utils.logging import LoggingConfig


class DocumentState(BaseModel):
    """Standardized document state representation.

    This class provides a consistent way to represent document states across
    all sources. It includes the essential fields needed for change detection.
    """

    uri: str  # Universal identifier in format: {source_type}:{source}:{url}
    content_hash: str  # Hash of document content
    updated_at: datetime  # Last update timestamp

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class StateChangeDetector:
    """Optimized change detector for document state management.

    This class provides efficient change detection functionality across
    all sources with minimal overhead and simplified logic.
    """

    def __init__(self, state_manager: StateManager):
        """Initialize the change detector."""
        self.logger = LoggingConfig.get_logger(
            f"qdrant_loader.{self.__class__.__name__}"
        )
        self._initialized = False
        self.state_manager = state_manager

    async def __aenter__(self):
        """Async context manager entry."""
        self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type:
            self.logger.error(
                "Error in StateChangeDetector context",
                error_type=exc_type.__name__,
                error=str(exc_val),
            )

    async def detect_changes(
        self, documents: list[Document], filtered_config: SourcesConfig
    ) -> dict[str, list[Document]]:
        """Detect changes in documents efficiently."""
        if not self._initialized:
            raise RuntimeError(
                "StateChangeDetector not initialized. Use as async context manager."
            )

        self.logger.info("Starting change detection", document_count=len(documents))

        # Get current and previous states
        current_states = [self._get_document_state(doc) for doc in documents]
        previous_states = await self._get_previous_states(filtered_config)

        # Create lookup sets/dicts for efficient comparison
        previous_uris: set[str] = {state.uri for state in previous_states}
        previous_states_dict: dict[str, DocumentState] = {
            state.uri: state for state in previous_states
        }
        current_uris: set[str] = {state.uri for state in current_states}

        # Find changes efficiently
        new_docs = [
            doc
            for state, doc in zip(current_states, documents, strict=False)
            if state.uri not in previous_uris
        ]

        updated_docs = [
            doc
            for state, doc in zip(current_states, documents, strict=False)
            if state.uri in previous_states_dict
            and self._is_document_updated(state, previous_states_dict[state.uri])
        ]

        deleted_docs = [
            self._create_deleted_document(state)
            for state in previous_states
            if state.uri not in current_uris
        ]

        changes = {
            "new": new_docs,
            "updated": updated_docs,
            "deleted": deleted_docs,
        }

        self.logger.info(
            "Change detection completed",
            new_count=len(new_docs),
            updated_count=len(updated_docs),
            deleted_count=len(deleted_docs),
        )

        return changes

    def _get_document_state(self, document: Document) -> DocumentState:
        """Get the standardized state of a document."""
        try:
            return DocumentState(
                uri=self._generate_uri_from_document(document),
                content_hash=document.content_hash,
                updated_at=document.updated_at,
            )
        except Exception as e:
            raise InvalidDocumentStateError(f"Failed to get document state: {e}") from e

    def _is_document_updated(
        self, current_state: DocumentState, previous_state: DocumentState
    ) -> bool:
        """Check if a document has been updated."""
        return (
            current_state.content_hash != previous_state.content_hash
            or current_state.updated_at > previous_state.updated_at
        )

    def _create_deleted_document(self, document_state: DocumentState) -> Document:
        """Create a minimal document for a deleted item."""
        source_type, source, url = document_state.uri.split(":", 2)
        url = unquote(url)

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

    async def _get_previous_states(
        self, filtered_config: SourcesConfig
    ) -> list[DocumentState]:
        """Get previous document states from the state manager efficiently."""
        previous_states_records: list[DocumentStateRecord] = []

        # Define source type mappings for cleaner iteration
        source_mappings = [
            ("git", filtered_config.git),
            ("confluence", filtered_config.confluence),
            ("jira", filtered_config.jira),
            ("publicdocs", filtered_config.publicdocs),
            ("localfile", filtered_config.localfile),
        ]

        # Process each source type
        for _source_name, source_configs in source_mappings:
            if source_configs:
                for config in source_configs.values():
                    records = await self.state_manager.get_document_state_records(
                        config
                    )
                    previous_states_records.extend(records)

        # Convert records to states efficiently
        return [
            DocumentState(
                uri=self._generate_uri(
                    record.url, record.source, record.source_type, record.document_id  # type: ignore
                ),
                content_hash=record.content_hash,  # type: ignore
                updated_at=record.updated_at,  # type: ignore
            )
            for record in previous_states_records
        ]

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL for consistent hashing."""
        return quote(url.rstrip("/"), safe="")

    def _generate_uri_from_document(self, document: Document) -> str:
        """Generate a URI from a document."""
        return self._generate_uri(
            document.url, document.source, document.source_type, document.id
        )

    def _generate_uri(
        self, url: str, source: str, source_type: str, document_id: str
    ) -> str:
        """Generate a URI from document components."""
        return f"{source_type}:{source}:{self._normalize_url(url)}"
