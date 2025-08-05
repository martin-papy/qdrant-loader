"""Tests for the StateChangeDetector class."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.exceptions import InvalidDocumentStateError
from qdrant_loader.core.state.state_change_detector import DocumentState, StateChangeDetector
from qdrant_loader.core.state.state_manager import DocumentStateRecord, StateManager


class TestDocumentState:
    """Test cases for DocumentState model."""

    def test_valid_document_state(self):
        """Test creating a valid DocumentState."""
        state = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="abc123",
            updated_at=datetime.now(timezone.utc)
        )
        
        assert state.uri == "git:repo:http://example.com/doc"
        assert state.content_hash == "abc123"
        assert isinstance(state.updated_at, datetime)

    def test_document_state_validation_error(self):
        """Test DocumentState validation with invalid data."""
        with pytest.raises(ValidationError):
            DocumentState(
                # Missing required field should fail validation
                content_hash="abc123",
                updated_at=datetime.now(timezone.utc)
            )

    def test_document_state_extra_fields_forbidden(self):
        """Test that extra fields are forbidden in DocumentState."""
        with pytest.raises(ValidationError):
            DocumentState(
                uri="git:repo:http://example.com/doc",
                content_hash="abc123",
                updated_at=datetime.now(timezone.utc),
                extra_field="not_allowed"  # Should be forbidden
            )

    def test_document_state_equality(self):
        """Test DocumentState equality comparison."""
        timestamp = datetime.now(timezone.utc)
        
        state1 = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="abc123",
            updated_at=timestamp
        )
        
        state2 = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="abc123",
            updated_at=timestamp
        )
        
        assert state1 == state2


class TestStateChangeDetector:
    """Test cases for StateChangeDetector."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create a mock state manager."""
        return MagicMock(spec=StateManager)

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                id="doc1",
                content="Content 1",
                url="http://example.com/doc1",
                content_type="md",
                source_type="git",
                source="repo1",
                title="Document 1",
                content_hash="hash1",
                updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                metadata={"source": "git"},
            ),
            Document(
                id="doc2",
                content="Content 2",
                url="http://example.com/doc2",
                content_type="md",
                source_type="git",
                source="repo1",
                title="Document 2",
                content_hash="hash2",
                updated_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
                metadata={"source": "git"},
            ),
        ]

    @pytest.fixture
    def filtered_config(self):
        """Create a filtered config for testing."""
        config = MagicMock(spec=SourcesConfig)
        config.git = {"repo1": MagicMock()}
        config.confluence = None
        config.jira = None
        config.publicdocs = None
        config.localfile = None
        return config

    def test_initialization(self, mock_state_manager):
        """Test StateChangeDetector initialization."""
        detector = StateChangeDetector(mock_state_manager)
        
        assert detector.state_manager == mock_state_manager
        assert not detector._initialized
        assert detector.logger is not None

    @pytest.mark.asyncio
    async def test_context_manager_entry_exit(self, mock_state_manager):
        """Test async context manager functionality."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Test entry
        async with detector as ctx:
            assert ctx is detector
            assert detector._initialized
        
        # Test that initialized state persists after context
        assert detector._initialized

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self, mock_state_manager):
        """Test async context manager with exception handling."""
        detector = StateChangeDetector(mock_state_manager)
        
        with patch.object(detector, 'logger') as mock_logger:
            try:
                async with detector:
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            # Verify error logging
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            assert "Error in StateChangeDetector context" in error_call

    @pytest.mark.asyncio
    async def test_detect_changes_not_initialized(self, mock_state_manager, sample_documents, filtered_config):
        """Test detect_changes raises error when not initialized."""
        detector = StateChangeDetector(mock_state_manager)
        
        with pytest.raises(RuntimeError, match="StateChangeDetector not initialized"):
            await detector.detect_changes(sample_documents, filtered_config)

    @pytest.mark.asyncio
    async def test_detect_changes_new_documents(self, mock_state_manager, sample_documents, filtered_config):
        """Test detecting new documents."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Mock state manager to return no previous states
        mock_state_manager.get_document_state_records.return_value = []
        
        async with detector:
            with patch.object(detector, 'logger') as mock_logger:
                result = await detector.detect_changes(sample_documents, filtered_config)
        
        # All documents should be new
        assert len(result["new"]) == 2
        assert len(result["updated"]) == 0
        assert len(result["deleted"]) == 0
        assert result["new"] == sample_documents
        
        # Verify logging
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_detect_changes_updated_documents(self, mock_state_manager, sample_documents, filtered_config):
        """Test detecting updated documents."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Create previous state with different hash
        previous_record = DocumentStateRecord(
            url="http://example.com/doc1",
            source="repo1",
            source_type="git",
            document_id="doc1",
            content_hash="old_hash1",  # Different hash
            updated_at=datetime(2022, 12, 31, tzinfo=timezone.utc),  # Earlier date
        )
        
        mock_state_manager.get_document_state_records.return_value = [previous_record]
        
        async with detector:
            result = await detector.detect_changes(sample_documents, filtered_config)
        
        # First document should be updated, second should be new
        assert len(result["new"]) == 1
        assert len(result["updated"]) == 1
        assert len(result["deleted"]) == 0
        assert result["updated"][0] == sample_documents[0]
        assert result["new"][0] == sample_documents[1]

    @pytest.mark.asyncio
    async def test_detect_changes_deleted_documents(self, mock_state_manager, sample_documents, filtered_config):
        """Test detecting deleted documents."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Create previous state for a document not in current documents
        previous_record = DocumentStateRecord(
            url="http://example.com/deleted_doc",
            source="repo1",
            source_type="git",
            document_id="deleted_doc",
            content_hash="deleted_hash",
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        
        mock_state_manager.get_document_state_records.return_value = [previous_record]
        
        async with detector:
            result = await detector.detect_changes(sample_documents, filtered_config)
        
        # Should have deleted document
        assert len(result["new"]) == 2  # Both current docs are new
        assert len(result["updated"]) == 0
        assert len(result["deleted"]) == 1
        
        deleted_doc = result["deleted"][0]
        assert deleted_doc.title == "Deleted Document"
        assert deleted_doc.content == ""
        assert deleted_doc.url == "http://example.com/deleted_doc"

    @pytest.mark.asyncio
    async def test_detect_changes_no_changes(self, mock_state_manager, sample_documents, filtered_config):
        """Test when no changes are detected."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Get the actual content hashes from the sample documents
        doc1_hash = sample_documents[0].content_hash
        doc2_hash = sample_documents[1].content_hash
        
        # Create previous states that match current documents exactly
        previous_records = [
            DocumentStateRecord(
                url="http://example.com/doc1",
                source="repo1",
                source_type="git",
                document_id="doc1",
                content_hash=doc1_hash,  # Use actual hash
                updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            ),
            DocumentStateRecord(
                url="http://example.com/doc2",
                source="repo1",
                source_type="git",
                document_id="doc2",
                content_hash=doc2_hash,  # Use actual hash
                updated_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
            ),
        ]
        
        mock_state_manager.get_document_state_records.return_value = previous_records
        
        async with detector:
            result = await detector.detect_changes(sample_documents, filtered_config)
        
        # No changes should be detected
        assert len(result["new"]) == 0
        assert len(result["updated"]) == 0
        assert len(result["deleted"]) == 0

    def test_get_document_state(self, mock_state_manager, sample_documents):
        """Test _get_document_state method."""
        detector = StateChangeDetector(mock_state_manager)
        
        state = detector._get_document_state(sample_documents[0])
        
        assert isinstance(state, DocumentState)
        assert state.uri == "git:repo1:http%3A%2F%2Fexample.com%2Fdoc1"
        # Content hash is auto-generated, so just verify it exists
        assert state.content_hash is not None
        assert len(state.content_hash) > 0
        assert state.updated_at == sample_documents[0].updated_at

    def test_get_document_state_error(self, mock_state_manager):
        """Test _get_document_state with invalid document."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Create invalid document (missing required fields)
        invalid_doc = MagicMock()
        invalid_doc.content_hash = "hash"
        invalid_doc.updated_at = datetime.now(timezone.utc)
        # Missing url, source, source_type, id
        
        with pytest.raises(InvalidDocumentStateError):
            detector._get_document_state(invalid_doc)

    def test_is_document_updated_content_hash_changed(self, mock_state_manager):
        """Test _is_document_updated with changed content hash."""
        detector = StateChangeDetector(mock_state_manager)
        
        current_state = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="new_hash",
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        previous_state = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="old_hash",
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        assert detector._is_document_updated(current_state, previous_state)

    def test_is_document_updated_timestamp_changed(self, mock_state_manager):
        """Test _is_document_updated with changed timestamp."""
        detector = StateChangeDetector(mock_state_manager)
        
        current_state = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="same_hash",
            updated_at=datetime(2023, 1, 2, tzinfo=timezone.utc)
        )
        
        previous_state = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="same_hash",
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        assert detector._is_document_updated(current_state, previous_state)

    def test_is_document_updated_no_changes(self, mock_state_manager):
        """Test _is_document_updated with no changes."""
        detector = StateChangeDetector(mock_state_manager)
        
        timestamp = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        current_state = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="same_hash",
            updated_at=timestamp
        )
        
        previous_state = DocumentState(
            uri="git:repo:http://example.com/doc",
            content_hash="same_hash",
            updated_at=timestamp
        )
        
        assert not detector._is_document_updated(current_state, previous_state)

    def test_create_deleted_document(self, mock_state_manager):
        """Test _create_deleted_document method."""
        detector = StateChangeDetector(mock_state_manager)
        
        state = DocumentState(
            uri="git:repo1:http%3A//example.com/deleted",
            content_hash="deleted_hash",
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        deleted_doc = detector._create_deleted_document(state)
        
        assert deleted_doc.title == "Deleted Document"
        assert deleted_doc.content == ""
        assert deleted_doc.url == "http://example.com/deleted"
        assert deleted_doc.source == "repo1"
        assert deleted_doc.source_type == "git"
        assert deleted_doc.metadata["uri"] == state.uri

    def test_normalize_url(self, mock_state_manager):
        """Test _normalize_url method."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Test URL normalization (quote encodes all special characters)
        assert detector._normalize_url("http://example.com/") == "http%3A%2F%2Fexample.com"
        assert detector._normalize_url("http://example.com/path") == "http%3A%2F%2Fexample.com%2Fpath"
        assert detector._normalize_url("http://example.com/path/") == "http%3A%2F%2Fexample.com%2Fpath"

    def test_generate_uri_from_document(self, mock_state_manager, sample_documents):
        """Test _generate_uri_from_document method."""
        detector = StateChangeDetector(mock_state_manager)
        
        uri = detector._generate_uri_from_document(sample_documents[0])
        
        assert uri == "git:repo1:http%3A%2F%2Fexample.com%2Fdoc1"

    def test_generate_uri(self, mock_state_manager):
        """Test _generate_uri method."""
        detector = StateChangeDetector(mock_state_manager)
        
        uri = detector._generate_uri(
            "http://example.com/doc",
            "repo1",
            "git",
            "doc_id"
        )
        
        assert uri == "git:repo1:http%3A%2F%2Fexample.com%2Fdoc"

    @pytest.mark.asyncio
    async def test_get_previous_states_multiple_sources(self, mock_state_manager):
        """Test _get_previous_states with multiple source types."""
        detector = StateChangeDetector(mock_state_manager)
        
        # Create config with multiple source types
        config = MagicMock(spec=SourcesConfig)
        config.git = {"repo1": MagicMock()}
        config.confluence = {"space1": MagicMock()}
        config.jira = None
        config.publicdocs = None
        config.localfile = None
        
        # Mock different records for each source type
        git_record = DocumentStateRecord(
            url="http://git.com/doc",
            source="repo1",
            source_type="git",
            document_id="git_doc",
            content_hash="git_hash",
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        
        confluence_record = DocumentStateRecord(
            url="http://confluence.com/doc",
            source="space1",
            source_type="confluence",
            document_id="conf_doc",
            content_hash="conf_hash",
            updated_at=datetime(2023, 1, 2, tzinfo=timezone.utc),
        )
        
        mock_state_manager.get_document_state_records.side_effect = [
            [git_record],  # For git source
            [confluence_record],  # For confluence source
        ]
        
        async with detector:
            states = await detector._get_previous_states(config)
        
        assert len(states) == 2
        assert states[0].uri == "git:repo1:http%3A%2F%2Fgit.com%2Fdoc"
        assert states[1].uri == "confluence:space1:http%3A%2F%2Fconfluence.com%2Fdoc"

    @pytest.mark.asyncio
    async def test_get_previous_states_empty_config(self, mock_state_manager):
        """Test _get_previous_states with empty config."""
        detector = StateChangeDetector(mock_state_manager)
        
        config = MagicMock(spec=SourcesConfig)
        config.git = None
        config.confluence = None
        config.jira = None
        config.publicdocs = None
        config.localfile = None
        
        async with detector:
            states = await detector._get_previous_states(config)
        
        assert states == []
        mock_state_manager.get_document_state_records.assert_not_called()

    @pytest.mark.asyncio
    async def test_detect_changes_empty_documents(self, mock_state_manager, filtered_config):
        """Test detect_changes with empty document list."""
        detector = StateChangeDetector(mock_state_manager)
        
        mock_state_manager.get_document_state_records.return_value = []
        
        async with detector:
            with patch.object(detector, 'logger') as mock_logger:
                result = await detector.detect_changes([], filtered_config)
        
        # Should return empty results
        assert len(result["new"]) == 0
        assert len(result["updated"]) == 0
        assert len(result["deleted"]) == 0
        
        # Should still log
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_detect_changes_logging(self, mock_state_manager, sample_documents, filtered_config):
        """Test that detect_changes logs appropriate information."""
        detector = StateChangeDetector(mock_state_manager)
        
        mock_state_manager.get_document_state_records.return_value = []
        
        async with detector:
            with patch.object(detector, 'logger') as mock_logger:
                await detector.detect_changes(sample_documents, filtered_config)
        
        # Verify logging calls
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        
        assert any("Starting change detection" in msg for msg in info_calls)
        assert any("Change detection completed" in msg for msg in info_calls)