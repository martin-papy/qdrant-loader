"""
Unit tests for the DocumentStateManager.
"""

import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader.core.state.document_state_manager import DocumentStateManager
from qdrant_loader.core.state.state_change_detector import DocumentState


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def document_state_manager(mock_logger):
    """Create a DocumentStateManager instance."""
    return DocumentStateManager(mock_logger)


@pytest.fixture
def sample_document_state():
    """Create a sample DocumentState."""
    return DocumentState(
        uri="https://example.com/doc1",
        content_hash="abc123def456",
        updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
    )


class TestDocumentStateManagerInitialization:
    """Test DocumentStateManager initialization."""

    def test_initialization(self, mock_logger):
        """Test that DocumentStateManager initializes correctly."""
        manager = DocumentStateManager(mock_logger)
        assert manager.logger == mock_logger

    def test_get_connection(self, document_state_manager):
        """Test that _get_connection returns a valid SQLite connection."""
        conn = document_state_manager._get_connection()
        assert isinstance(conn, sqlite3.Connection)

        # Test that it's an in-memory database
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        # Should be empty for a new in-memory database
        tables = cursor.fetchall()
        conn.close()


class TestUpdateDocumentState:
    """Test document state update functionality."""

    def test_update_document_state_success(
        self, document_state_manager, sample_document_state, mock_logger
    ):
        """Test successful document state update."""
        doc_id = "doc_123"

        # Mock the database connection and operations
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            document_state_manager.update_document_state(doc_id, sample_document_state)

            # Verify database operations
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

            # Verify the SQL query and parameters
            call_args = mock_cursor.execute.call_args
            assert "INSERT OR REPLACE INTO document_states" in call_args[0][0]
            assert call_args[0][1] == (
                doc_id,
                sample_document_state.uri,
                sample_document_state.content_hash,
                sample_document_state.updated_at.isoformat(),
            )

            # Verify logging
            assert mock_logger.debug.call_count >= 2  # Initial debug + success debug

    def test_update_document_state_database_locked_retry(
        self, document_state_manager, sample_document_state, mock_logger
    ):
        """Test document state update with database locked error and retry."""
        doc_id = "doc_123"

        # Mock the database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # First call raises database locked error, second succeeds
        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError("database is locked"),
            None,  # Success on retry
        ]

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            with patch("time.sleep") as mock_sleep:
                document_state_manager.update_document_state(
                    doc_id, sample_document_state
                )

                # Verify retry logic
                mock_sleep.assert_called_once_with(1)
                assert mock_cursor.execute.call_count == 2
                mock_logger.warning.assert_called_once()

    def test_update_document_state_operational_error(
        self, document_state_manager, sample_document_state, mock_logger
    ):
        """Test document state update with non-locked operational error."""
        doc_id = "doc_123"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # Raise a non-locked operational error
        error = sqlite3.OperationalError("table does not exist")
        mock_cursor.execute.side_effect = error

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            with pytest.raises(sqlite3.OperationalError):
                document_state_manager.update_document_state(
                    doc_id, sample_document_state
                )

            mock_logger.error.assert_called_once()

    def test_update_document_state_unexpected_error(
        self, document_state_manager, sample_document_state, mock_logger
    ):
        """Test document state update with unexpected error."""
        doc_id = "doc_123"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # Raise an unexpected error
        error = ValueError("Unexpected error")
        mock_cursor.execute.side_effect = error

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            with pytest.raises(ValueError):
                document_state_manager.update_document_state(
                    doc_id, sample_document_state
                )

            mock_logger.error.assert_called_once()


class TestGetDocumentState:
    """Test document state retrieval functionality."""

    def test_get_document_state_found(
        self, document_state_manager, sample_document_state, mock_logger
    ):
        """Test successful document state retrieval when document exists."""
        doc_id = "doc_123"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # Mock database result
        mock_cursor.fetchone.return_value = (
            sample_document_state.uri,
            sample_document_state.content_hash,
            sample_document_state.updated_at.isoformat(),
        )

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            result = document_state_manager.get_document_state(doc_id)

            # Verify database operations
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called_once()
            mock_cursor.fetchone.assert_called_once()

            # Verify the SQL query
            call_args = mock_cursor.execute.call_args
            assert (
                "SELECT uri, content_hash, updated_at FROM document_states WHERE doc_id = ?"
                in call_args[0][0]
            )
            assert call_args[0][1] == (doc_id,)

            # Verify the returned state
            assert result is not None
            assert isinstance(result, DocumentState)
            assert result.uri == sample_document_state.uri
            assert result.content_hash == sample_document_state.content_hash
            assert result.updated_at == sample_document_state.updated_at

            # Verify logging
            mock_logger.debug.assert_called()

    def test_get_document_state_not_found(self, document_state_manager, mock_logger):
        """Test document state retrieval when document doesn't exist."""
        doc_id = "nonexistent_doc"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # Mock no result found
        mock_cursor.fetchone.return_value = None

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            result = document_state_manager.get_document_state(doc_id)

            # Verify database operations
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called_once()
            mock_cursor.fetchone.assert_called_once()

            # Verify no result
            assert result is None

            # Verify logging
            mock_logger.debug.assert_called()

    def test_get_document_state_database_locked_retry(
        self, document_state_manager, sample_document_state, mock_logger
    ):
        """Test document state retrieval with database locked error and retry."""
        doc_id = "doc_123"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # First call raises database locked error, second succeeds
        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError("database is locked"),
            None,  # Success on retry
        ]
        mock_cursor.fetchone.return_value = (
            sample_document_state.uri,
            sample_document_state.content_hash,
            sample_document_state.updated_at.isoformat(),
        )

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            with patch("time.sleep") as mock_sleep:
                result = document_state_manager.get_document_state(doc_id)

                # Verify retry logic
                mock_sleep.assert_called_once_with(1)
                assert mock_cursor.execute.call_count == 2
                mock_logger.warning.assert_called_once()

                # Verify successful result after retry
                assert result is not None
                assert result.uri == sample_document_state.uri

    def test_get_document_state_operational_error(
        self, document_state_manager, mock_logger
    ):
        """Test document state retrieval with non-locked operational error."""
        doc_id = "doc_123"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # Raise a non-locked operational error
        error = sqlite3.OperationalError("table does not exist")
        mock_cursor.execute.side_effect = error

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            with pytest.raises(sqlite3.OperationalError):
                document_state_manager.get_document_state(doc_id)

            mock_logger.error.assert_called_once()

    def test_get_document_state_unexpected_error(
        self, document_state_manager, mock_logger
    ):
        """Test document state retrieval with unexpected error."""
        doc_id = "doc_123"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # Raise an unexpected error
        error = ValueError("Unexpected error")
        mock_cursor.execute.side_effect = error

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            with pytest.raises(ValueError):
                document_state_manager.get_document_state(doc_id)

            mock_logger.error.assert_called_once()


class TestIntegration:
    """Test integration scenarios."""

    def test_update_and_get_document_state_integration(
        self, document_state_manager, sample_document_state, mock_logger
    ):
        """Test updating and then retrieving document state."""
        doc_id = "doc_integration_test"

        # Mock successful database operations for both update and get
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        # Mock fetchone to return the data we just inserted
        mock_cursor.fetchone.return_value = (
            sample_document_state.uri,
            sample_document_state.content_hash,
            sample_document_state.updated_at.isoformat(),
        )

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            # Update document state
            document_state_manager.update_document_state(doc_id, sample_document_state)

            # Get document state
            retrieved_state = document_state_manager.get_document_state(doc_id)

            # Verify the retrieved state matches what we stored
            assert retrieved_state is not None
            assert retrieved_state.uri == sample_document_state.uri
            assert retrieved_state.content_hash == sample_document_state.content_hash
            assert retrieved_state.updated_at == sample_document_state.updated_at

    def test_multiple_document_states(self, document_state_manager, mock_logger):
        """Test handling multiple document states."""
        documents = [
            (
                "doc_1",
                DocumentState(
                    uri="https://example.com/doc1",
                    content_hash="hash1",
                    updated_at=datetime(2024, 1, 1, tzinfo=UTC),
                ),
            ),
            (
                "doc_2",
                DocumentState(
                    uri="https://example.com/doc2",
                    content_hash="hash2",
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                ),
            ),
            (
                "doc_3",
                DocumentState(
                    uri="https://example.com/doc3",
                    content_hash="hash3",
                    updated_at=datetime(2024, 1, 3, tzinfo=UTC),
                ),
            ),
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)

        with patch.object(
            document_state_manager, "_get_connection", return_value=mock_conn
        ):
            # Update all document states
            for doc_id, state in documents:
                document_state_manager.update_document_state(doc_id, state)

            # Verify all updates were called
            assert mock_cursor.execute.call_count == len(documents)
            assert mock_conn.commit.call_count == len(documents)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
