import sqlite3
import time
from datetime import datetime

from qdrant_loader.core.state.state_change_detector import DocumentState


class DocumentStateManager:
    def __init__(self, logger):
        self.logger = logger

    def _get_connection(self):
        # This method should return a connection to the database
        # For the sake of this example, we'll use an in-memory SQLite database
        return sqlite3.connect(":memory:")

    def update_document_state(self, doc_id: str, state: DocumentState) -> None:
        """Update the state of a document.

        Args:
            doc_id: The ID of the document to update
            state: The new state to set
        """
        self.logger.debug(
            "Updating document state",
            extra={
                "doc_id": doc_id,
                "uri": state.uri,
                "content_hash": state.content_hash,
                "updated_at": state.updated_at.isoformat(),
            },
        )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO document_states (doc_id, uri, content_hash, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        state.uri,
                        state.content_hash,
                        state.updated_at.isoformat(),
                    ),
                )
                conn.commit()
                self.logger.debug(
                    "Document state updated successfully",
                    extra={
                        "doc_id": doc_id,
                        "uri": state.uri,
                        "content_hash": state.content_hash,
                    },
                )
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                self.logger.warning(
                    "Database is locked, retrying in 1 second",
                    extra={"doc_id": doc_id, "error": str(e), "retry_count": 0},
                )
                time.sleep(1)
                self.update_document_state(doc_id, state)
            else:
                self.logger.error(
                    f"Error updating document state: {str(e)}",
                    extra={
                        "doc_id": doc_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error updating document state: {str(e)}",
                extra={
                    "doc_id": doc_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def get_document_state(self, doc_id: str) -> DocumentState | None:
        """Get the current state of a document.

        Args:
            doc_id: The ID of the document to check

        Returns:
            The current state of the document, or None if not found
        """
        self.logger.debug(
            "Getting document state",
            extra={"doc_id": doc_id, "timestamp": datetime.now().isoformat()},
        )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT uri, content_hash, updated_at FROM document_states WHERE doc_id = ?",
                    (doc_id,),
                )
                result = cursor.fetchone()

                if result:
                    state = DocumentState(
                        uri=result[0],
                        content_hash=result[1],
                        updated_at=datetime.fromisoformat(result[2]),
                    )
                    self.logger.debug(
                        "Document state retrieved",
                        extra={
                            "doc_id": doc_id,
                            "uri": state.uri,
                            "content_hash": state.content_hash,
                        },
                    )
                    return state
                else:
                    self.logger.debug(
                        "No state found for document", extra={"doc_id": doc_id}
                    )
                    return None
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                self.logger.warning(
                    "Database is locked, retrying in 1 second",
                    extra={"doc_id": doc_id, "error": str(e), "retry_count": 0},
                )
                time.sleep(1)
                return self.get_document_state(doc_id)
            else:
                self.logger.error(
                    f"Error getting document state: {str(e)}",
                    extra={
                        "doc_id": doc_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error getting document state: {str(e)}",
                extra={
                    "doc_id": doc_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
