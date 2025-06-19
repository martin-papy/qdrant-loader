"""Tests for GraphitiTemporalIntegration module.

This module tests the Graphiti temporal integration functionality including
episodic processing, temporal edge invalidation, and document versioning.
"""

import pytest
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from graphiti_core.nodes import EpisodeType

from qdrant_loader.core.graphiti_temporal_integration import (
    GraphitiTemporalIntegration,
    GraphitiTemporalOperation,
    GraphitiTemporalOperationType,
)
from qdrant_loader.core.types import EntityType
from qdrant_loader.core.managers import MappingType
from qdrant_loader.core.sync import EnhancedSyncOperation
from qdrant_loader.core.sync.types import SyncOperationType


class TestGraphitiTemporalOperationType:
    """Test GraphitiTemporalOperationType enum."""

    def test_operation_type_values(self):
        """Test that all operation types have correct values."""
        assert GraphitiTemporalOperationType.CREATE_EPISODE.value == "create_episode"
        assert GraphitiTemporalOperationType.UPDATE_EPISODE.value == "update_episode"
        assert (
            GraphitiTemporalOperationType.INVALIDATE_EDGES.value == "invalidate_edges"
        )
        assert GraphitiTemporalOperationType.VERSION_EPISODE.value == "version_episode"
        assert GraphitiTemporalOperationType.TEMPORAL_QUERY.value == "temporal_query"

    def test_operation_type_members(self):
        """Test that all expected members exist."""
        expected_members = {
            "CREATE_EPISODE",
            "UPDATE_EPISODE",
            "INVALIDATE_EDGES",
            "VERSION_EPISODE",
            "TEMPORAL_QUERY",
        }
        actual_members = {member.name for member in GraphitiTemporalOperationType}
        assert actual_members == expected_members


class TestGraphitiTemporalOperation:
    """Test GraphitiTemporalOperation dataclass."""

    def test_operation_creation_defaults(self):
        """Test operation creation with default values."""
        operation = GraphitiTemporalOperation()

        assert operation.operation_id is not None
        assert len(operation.operation_id) > 0
        assert operation.operation_type == GraphitiTemporalOperationType.CREATE_EPISODE
        assert isinstance(operation.timestamp, datetime)
        assert operation.episode_name is None
        assert operation.episode_content is None
        assert operation.episode_type == EpisodeType.text
        assert operation.episode_uuid is None
        assert operation.reference_time is None
        assert operation.document_uuid is None
        assert operation.document_version == 1
        assert operation.previous_version is None
        assert operation.version_metadata == {}
        assert operation.edges_to_invalidate == []
        assert operation.invalidation_reason is None
        assert operation.invalidation_timestamp is None
        assert operation.query_time is None
        assert operation.time_range_start is None
        assert operation.time_range_end is None
        assert operation.metadata == {}

    def test_operation_creation_custom_values(self):
        """Test operation creation with custom values."""
        custom_timestamp = datetime.now(UTC)
        custom_reference_time = datetime.now(UTC) - timedelta(hours=1)
        custom_metadata = {"key": "value"}
        custom_version_metadata = {"version_key": "version_value"}
        custom_edges = ["edge1", "edge2"]

        operation = GraphitiTemporalOperation(
            operation_id="custom_id",
            operation_type=GraphitiTemporalOperationType.VERSION_EPISODE,
            timestamp=custom_timestamp,
            episode_name="Test Episode",
            episode_content="Test content",
            episode_type=EpisodeType.text,
            episode_uuid="episode_uuid",
            reference_time=custom_reference_time,
            document_uuid="doc_uuid",
            document_version=2,
            previous_version=1,
            version_metadata=custom_version_metadata,
            edges_to_invalidate=custom_edges,
            invalidation_reason="test_reason",
            invalidation_timestamp=custom_timestamp,
            query_time=custom_timestamp,
            time_range_start=custom_timestamp,
            time_range_end=custom_timestamp,
            metadata=custom_metadata,
        )

        assert operation.operation_id == "custom_id"
        assert operation.operation_type == GraphitiTemporalOperationType.VERSION_EPISODE
        assert operation.timestamp == custom_timestamp
        assert operation.episode_name == "Test Episode"
        assert operation.episode_content == "Test content"
        assert operation.episode_type == EpisodeType.text
        assert operation.episode_uuid == "episode_uuid"
        assert operation.reference_time == custom_reference_time
        assert operation.document_uuid == "doc_uuid"
        assert operation.document_version == 2
        assert operation.previous_version == 1
        assert operation.version_metadata == custom_version_metadata
        assert operation.edges_to_invalidate == custom_edges
        assert operation.invalidation_reason == "test_reason"
        assert operation.invalidation_timestamp == custom_timestamp
        assert operation.query_time == custom_timestamp
        assert operation.time_range_start == custom_timestamp
        assert operation.time_range_end == custom_timestamp
        assert operation.metadata == custom_metadata

    def test_operation_uuid_generation(self):
        """Test that each operation gets a unique UUID."""
        operation1 = GraphitiTemporalOperation()
        operation2 = GraphitiTemporalOperation()

        assert operation1.operation_id != operation2.operation_id
        assert uuid.UUID(operation1.operation_id)  # Valid UUID format
        assert uuid.UUID(operation2.operation_id)  # Valid UUID format


class TestGraphitiTemporalIntegration:
    """Test GraphitiTemporalIntegration main class."""

    @pytest.fixture
    def mock_managers(self):
        """Create mock managers for testing."""
        graphiti_manager = MagicMock()
        graphiti_manager.is_initialized = True
        graphiti_manager.add_episode = AsyncMock(return_value="episode_uuid_123")
        graphiti_manager.search = AsyncMock(return_value=[])

        temporal_manager = MagicMock()
        id_mapping_manager = MagicMock()

        return graphiti_manager, temporal_manager, id_mapping_manager

    @pytest.fixture
    def integration(self, mock_managers):
        """Create GraphitiTemporalIntegration instance for testing."""
        graphiti_manager, temporal_manager, id_mapping_manager = mock_managers
        return GraphitiTemporalIntegration(
            graphiti_manager=graphiti_manager,
            temporal_manager=temporal_manager,
            id_mapping_manager=id_mapping_manager,
        )

    def test_initialization(self, mock_managers):
        """Test GraphitiTemporalIntegration initialization."""
        graphiti_manager, temporal_manager, id_mapping_manager = mock_managers

        integration = GraphitiTemporalIntegration(
            graphiti_manager=graphiti_manager,
            temporal_manager=temporal_manager,
            id_mapping_manager=id_mapping_manager,
        )

        assert integration.graphiti_manager == graphiti_manager
        assert integration.temporal_manager == temporal_manager
        assert integration.id_mapping_manager == id_mapping_manager
        assert integration.enable_episodic_versioning is True
        assert integration.enable_temporal_edge_invalidation is True
        assert integration.episode_retention_days == 365
        assert integration._active_operations == {}
        assert integration._episode_version_map == {}
        assert integration._edge_invalidation_log == []

    def test_initialization_custom_params(self, mock_managers):
        """Test initialization with custom parameters."""
        graphiti_manager, temporal_manager, id_mapping_manager = mock_managers

        integration = GraphitiTemporalIntegration(
            graphiti_manager=graphiti_manager,
            temporal_manager=temporal_manager,
            id_mapping_manager=id_mapping_manager,
            enable_episodic_versioning=False,
            enable_temporal_edge_invalidation=False,
            episode_retention_days=30,
        )

        assert integration.enable_episodic_versioning is False
        assert integration.enable_temporal_edge_invalidation is False
        assert integration.episode_retention_days == 30

    @pytest.mark.asyncio
    async def test_process_sync_operation_create_document(self, integration):
        """Test processing CREATE_DOCUMENT sync operation."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            entity_uuid="uuid_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            operation_data={"content": "Test document content"},
            timestamp=datetime.now(UTC),
        )

        operations = await integration.process_sync_operation(sync_operation)

        assert len(operations) == 1
        operation = operations[0]
        assert operation.operation_type == GraphitiTemporalOperationType.CREATE_EPISODE
        assert operation.document_uuid == "uuid_123"
        assert operation.episode_uuid == "episode_uuid_123"
        assert "uuid_123" in integration._episode_version_map
        assert len(integration._episode_version_map["uuid_123"]) == 1

    @pytest.mark.asyncio
    async def test_process_sync_operation_update_document(self, integration):
        """Test processing UPDATE_DOCUMENT sync operation."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id="doc_123",
            entity_uuid="uuid_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            operation_data={"content": "Updated content"},
            document_version=2,
            previous_version=1,
            timestamp=datetime.now(UTC),
        )

        # Mock edge finding to return some edges
        integration.graphiti_manager.search.return_value = [
            MagicMock(uuid="edge1", relationships=[MagicMock(uuid="rel1")])
        ]

        operations = await integration.process_sync_operation(sync_operation)

        assert len(operations) == 2  # Version operation + invalidation operation
        version_op = next(
            op
            for op in operations
            if op.operation_type == GraphitiTemporalOperationType.VERSION_EPISODE
        )
        invalidation_op = next(
            op
            for op in operations
            if op.operation_type == GraphitiTemporalOperationType.INVALIDATE_EDGES
        )

        assert version_op.document_version == 2
        assert version_op.previous_version == 1
        assert len(invalidation_op.edges_to_invalidate) > 0

    @pytest.mark.asyncio
    async def test_process_sync_operation_delete_document(self, integration):
        """Test processing DELETE_DOCUMENT sync operation."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            entity_id="doc_123",
            entity_uuid="uuid_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            timestamp=datetime.now(UTC),
        )

        # Mock edge finding for comprehensive invalidation
        integration.graphiti_manager.search.return_value = [
            MagicMock(uuid="edge1"),
            MagicMock(uuid="edge2"),
        ]

        operations = await integration.process_sync_operation(sync_operation)

        assert len(operations) == 2  # Deletion episode + comprehensive invalidation
        deletion_op = next(
            op
            for op in operations
            if op.operation_type == GraphitiTemporalOperationType.UPDATE_EPISODE
        )
        invalidation_op = next(
            op
            for op in operations
            if op.operation_type == GraphitiTemporalOperationType.INVALIDATE_EDGES
        )

        assert "Document Deletion" in deletion_op.episode_name
        assert invalidation_op.invalidation_reason == "document_deletion"

    @pytest.mark.asyncio
    async def test_process_sync_operation_version_update(self, integration):
        """Test processing VERSION_UPDATE sync operation."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.VERSION_UPDATE,
            entity_id="doc_123",
            entity_uuid="uuid_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            operation_data={"content": "Version update content"},
            document_version=3,
            previous_version=2,
            timestamp=datetime.now(UTC),
        )

        operations = await integration.process_sync_operation(sync_operation)

        assert len(operations) == 1
        operation = operations[0]
        assert operation.operation_type == GraphitiTemporalOperationType.VERSION_EPISODE
        assert operation.document_version == 3
        assert operation.previous_version == 2

    @pytest.mark.asyncio
    async def test_process_sync_operation_unsupported_type(self, integration):
        """Test processing unsupported sync operation type."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_ENTITY,  # Not handled by temporal integration
            entity_id="entity_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.ENTITY,
            timestamp=datetime.now(UTC),
        )

        operations = await integration.process_sync_operation(sync_operation)

        assert len(operations) == 0

    @pytest.mark.asyncio
    async def test_process_sync_operation_exception_handling(self, integration):
        """Test exception handling in process_sync_operation."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            timestamp=datetime.now(UTC),
        )

        # Make add_episode raise an exception
        integration.graphiti_manager.add_episode.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            await integration.process_sync_operation(sync_operation)

    @pytest.mark.asyncio
    async def test_execute_episode_operation(self, integration):
        """Test executing episode operation."""
        operation = GraphitiTemporalOperation(
            episode_name="Test Episode",
            episode_content="Test content",
            episode_type=EpisodeType.text,
            reference_time=datetime.now(UTC),
            metadata={"test": "metadata"},
        )

        episode_uuid = await integration._execute_episode_operation(operation)

        assert episode_uuid == "episode_uuid_123"
        integration.graphiti_manager.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_episode_operation_exception(self, integration):
        """Test exception handling in execute_episode_operation."""
        operation = GraphitiTemporalOperation()
        integration.graphiti_manager.add_episode.side_effect = Exception(
            "Episode error"
        )

        with pytest.raises(Exception, match="Episode error"):
            await integration._execute_episode_operation(operation)

    @pytest.mark.asyncio
    async def test_create_edge_invalidation_operation(self, integration):
        """Test creating edge invalidation operation."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id="doc_123",
            timestamp=datetime.now(UTC),
            document_version=2,
            previous_version=1,
        )

        # Mock finding edges
        mock_result = MagicMock()
        mock_result.uuid = "result_uuid"
        mock_rel = MagicMock()
        mock_rel.uuid = "rel_uuid"
        mock_result.relationships = [mock_rel]
        integration.graphiti_manager.search.return_value = [mock_result]

        operation = await integration._create_edge_invalidation_operation(
            sync_operation, "doc_uuid"
        )

        assert operation is not None
        assert (
            operation.operation_type == GraphitiTemporalOperationType.INVALIDATE_EDGES
        )
        assert operation.document_uuid == "doc_uuid"
        assert "rel_uuid" in operation.edges_to_invalidate
        assert operation.invalidation_reason == "document_update"

    @pytest.mark.asyncio
    async def test_create_edge_invalidation_operation_no_edges(self, integration):
        """Test creating edge invalidation operation when no edges found."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id="doc_123",
            timestamp=datetime.now(UTC),
        )

        integration.graphiti_manager.search.return_value = []

        operation = await integration._create_edge_invalidation_operation(
            sync_operation, "doc_uuid"
        )

        assert operation is None

    @pytest.mark.asyncio
    async def test_create_comprehensive_edge_invalidation(self, integration):
        """Test creating comprehensive edge invalidation."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            entity_id="doc_123",
            timestamp=datetime.now(UTC),
        )

        # Mock finding all edges
        mock_edges = [MagicMock(uuid=f"edge_{i}") for i in range(3)]
        integration.graphiti_manager.search.return_value = mock_edges

        operation = await integration._create_comprehensive_edge_invalidation(
            sync_operation, "doc_uuid"
        )

        assert operation is not None
        assert (
            operation.operation_type == GraphitiTemporalOperationType.INVALIDATE_EDGES
        )
        assert operation.document_uuid == "doc_uuid"
        assert len(operation.edges_to_invalidate) == 3
        assert operation.invalidation_reason == "document_deletion"

    @pytest.mark.asyncio
    async def test_execute_edge_invalidation(self, integration):
        """Test executing edge invalidation."""
        operation = GraphitiTemporalOperation(
            operation_type=GraphitiTemporalOperationType.INVALIDATE_EDGES,
            document_uuid="doc_uuid",
            edges_to_invalidate=["edge1", "edge2"],
            invalidation_reason="test_reason",
            invalidation_timestamp=datetime.now(UTC),
            metadata={"test": "data"},
        )

        await integration._execute_edge_invalidation(operation)

        assert len(integration._edge_invalidation_log) == 1
        log_entry = integration._edge_invalidation_log[0]
        assert log_entry["document_uuid"] == "doc_uuid"
        assert log_entry["edges_invalidated"] == ["edge1", "edge2"]
        assert log_entry["reason"] == "test_reason"

    @pytest.mark.asyncio
    async def test_find_edges_for_invalidation(self, integration):
        """Test finding edges for invalidation."""
        # Mock search results with relationships
        mock_result = MagicMock()
        mock_result.uuid = "result_uuid"
        mock_rel1 = MagicMock()
        mock_rel1.uuid = "rel1_uuid"
        mock_rel2 = MagicMock()
        mock_rel2.uuid = "rel2_uuid"
        mock_result.relationships = [mock_rel1, mock_rel2]
        integration.graphiti_manager.search.return_value = [mock_result]

        edges = await integration._find_edges_for_invalidation("doc_uuid")

        assert "rel1_uuid" in edges
        assert "rel2_uuid" in edges
        integration.graphiti_manager.search.assert_called_once_with(
            query="document:doc_uuid", limit=100
        )

    @pytest.mark.asyncio
    async def test_find_all_document_edges(self, integration):
        """Test finding all document edges."""
        mock_edges = [MagicMock(uuid=f"edge_{i}") for i in range(5)]
        integration.graphiti_manager.search.return_value = mock_edges

        edges = await integration._find_all_document_edges("doc_uuid")

        assert len(edges) == 5
        assert all(f"edge_{i}" in edges for i in range(5))
        integration.graphiti_manager.search.assert_called_once_with(
            query="uuid:doc_uuid OR source:doc_uuid OR target:doc_uuid", limit=200
        )

    def test_extract_content_from_operation_dict_content(self, integration):
        """Test extracting content from operation with dict data containing content."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            operation_data={"content": "Test content", "other": "data"},
        )

        content = integration._extract_content_from_operation(sync_operation)
        assert content == "Test content"

    def test_extract_content_from_operation_dict_text(self, integration):
        """Test extracting content from operation with dict data containing text."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            operation_data={"text": "Test text", "other": "data"},
        )

        content = integration._extract_content_from_operation(sync_operation)
        assert content == "Test text"

    def test_extract_content_from_operation_dict_body(self, integration):
        """Test extracting content from operation with dict data containing body."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            operation_data={"body": "Test body", "other": "data"},
        )

        content = integration._extract_content_from_operation(sync_operation)
        assert content == "Test body"

    def test_extract_content_from_operation_dict_fallback(self, integration):
        """Test extracting content from operation with dict data fallback to JSON."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            operation_data={"other": "data", "number": 123},
        )

        content = integration._extract_content_from_operation(sync_operation)
        assert '"other": "data"' in content
        assert '"number": 123' in content

    def test_extract_content_from_operation_string(self, integration):
        """Test extracting content from operation with string data."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            operation_data={"content": "Simple string content"},
        )

        content = integration._extract_content_from_operation(sync_operation)
        assert content == "Simple string content"

    def test_extract_content_from_operation_none(self, integration):
        """Test extracting content from operation with None data."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            operation_data={},
        )

        content = integration._extract_content_from_operation(sync_operation)
        assert "Operation create_document for doc_123" in content or content == "{}"

    @pytest.mark.asyncio
    async def test_query_temporal_episodes(self, integration):
        """Test querying temporal episodes."""
        # Set up episode version map
        integration._episode_version_map["doc_uuid"] = ["episode1", "episode2"]

        # Mock search results
        mock_results = [{"episode_data": "test"}]
        integration.graphiti_manager.search.return_value = mock_results

        episodes = await integration.query_temporal_episodes("doc_uuid")

        assert len(episodes) == 2
        for episode in episodes:
            assert episode["document_uuid"] == "doc_uuid"
            assert "episode_uuid" in episode
            assert episode["details"] == {"episode_data": "test"}

    @pytest.mark.asyncio
    async def test_query_temporal_episodes_no_episodes(self, integration):
        """Test querying temporal episodes when none exist."""
        episodes = await integration.query_temporal_episodes("nonexistent_doc")
        assert episodes == []

    @pytest.mark.asyncio
    async def test_query_temporal_episodes_search_failure(self, integration):
        """Test querying temporal episodes with search failure."""
        integration._episode_version_map["doc_uuid"] = ["episode1"]
        integration.graphiti_manager.search.side_effect = Exception("Search error")

        episodes = await integration.query_temporal_episodes("doc_uuid")
        assert episodes == []

    @pytest.mark.asyncio
    async def test_get_document_version_history(self, integration):
        """Test getting document version history."""
        # Mock query_temporal_episodes
        mock_episodes = [
            {
                "episode_uuid": "episode1",
                "document_uuid": "doc_uuid",
                "details": {"created_at": "2023-01-01T00:00:00Z"},
            },
            {
                "episode_uuid": "episode2",
                "document_uuid": "doc_uuid",
                "details": {"created_at": "2023-01-02T00:00:00Z"},
            },
        ]

        with patch.object(
            integration, "query_temporal_episodes", return_value=mock_episodes
        ):
            history = await integration.get_document_version_history("doc_uuid")

        assert len(history) == 2
        assert history[0]["version"] == 1
        assert history[1]["version"] == 2
        assert history[0]["episode_uuid"] == "episode1"
        assert history[1]["episode_uuid"] == "episode2"

    @pytest.mark.asyncio
    async def test_get_edge_invalidation_log_no_filter(self, integration):
        """Test getting edge invalidation log without filters."""
        # Add some test log entries
        test_entries = [
            {
                "operation_id": "op1",
                "document_uuid": "doc1",
                "timestamp": "2023-01-01T00:00:00Z",
            },
            {
                "operation_id": "op2",
                "document_uuid": "doc2",
                "timestamp": "2023-01-02T00:00:00Z",
            },
        ]
        integration._edge_invalidation_log = test_entries

        log = await integration.get_edge_invalidation_log()
        assert log == test_entries

    @pytest.mark.asyncio
    async def test_get_edge_invalidation_log_document_filter(self, integration):
        """Test getting edge invalidation log with document filter."""
        test_entries = [
            {"document_uuid": "doc1", "operation_id": "op1"},
            {"document_uuid": "doc2", "operation_id": "op2"},
            {"document_uuid": "doc1", "operation_id": "op3"},
        ]
        integration._edge_invalidation_log = test_entries

        log = await integration.get_edge_invalidation_log(document_uuid="doc1")
        assert len(log) == 2
        assert all(entry["document_uuid"] == "doc1" for entry in log)

    @pytest.mark.asyncio
    async def test_get_edge_invalidation_log_time_filter(self, integration):
        """Test getting edge invalidation log with time range filter."""
        test_entries = [
            {"timestamp": "2023-01-01T00:00:00Z", "operation_id": "op1"},
            {"timestamp": "2023-01-02T00:00:00Z", "operation_id": "op2"},
            {"timestamp": "2023-01-03T00:00:00Z", "operation_id": "op3"},
        ]
        integration._edge_invalidation_log = test_entries

        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        end_time = datetime(2023, 1, 2, 12, 0, 0, tzinfo=UTC)

        log = await integration.get_edge_invalidation_log(
            time_range_start=start_time, time_range_end=end_time
        )
        assert len(log) == 1
        assert log[0]["operation_id"] == "op2"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, integration):
        """Test health check when system is healthy."""
        # Add some test data
        integration._active_operations["op1"] = GraphitiTemporalOperation()
        integration._episode_version_map["doc1"] = ["episode1"]
        integration._edge_invalidation_log.append({"test": "entry"})

        health = await integration.health_check()

        assert health["healthy"] is True
        assert health["graphiti_manager_initialized"] is True
        assert health["episodic_versioning_enabled"] is True
        assert health["temporal_edge_invalidation_enabled"] is True
        assert health["active_operations"] == 1
        assert health["tracked_documents"] == 1
        assert health["edge_invalidations_logged"] == 1
        assert health["episode_retention_days"] == 365

    @pytest.mark.asyncio
    async def test_disabled_episodic_versioning(self, mock_managers):
        """Test behavior when episodic versioning is disabled."""
        graphiti_manager, temporal_manager, id_mapping_manager = mock_managers
        integration = GraphitiTemporalIntegration(
            graphiti_manager=graphiti_manager,
            temporal_manager=temporal_manager,
            id_mapping_manager=id_mapping_manager,
            enable_episodic_versioning=False,
        )

        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="doc_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            timestamp=datetime.now(UTC),
        )

        operations = await integration.process_sync_operation(sync_operation)
        assert len(operations) == 0

    @pytest.mark.asyncio
    async def test_disabled_temporal_edge_invalidation(self, mock_managers):
        """Test behavior when temporal edge invalidation is disabled."""
        graphiti_manager, temporal_manager, id_mapping_manager = mock_managers
        integration = GraphitiTemporalIntegration(
            graphiti_manager=graphiti_manager,
            temporal_manager=temporal_manager,
            id_mapping_manager=id_mapping_manager,
            enable_temporal_edge_invalidation=False,
        )

        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id="doc_123",
            entity_uuid="uuid_123",
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            timestamp=datetime.now(UTC),
        )

        operations = await integration.process_sync_operation(sync_operation)
        # Should only have version operation, no invalidation operation
        assert len(operations) == 1
        assert (
            operations[0].operation_type
            == GraphitiTemporalOperationType.VERSION_EPISODE
        )

    @pytest.mark.asyncio
    async def test_missing_document_uuid_handling(self, integration):
        """Test handling of operations with missing document UUID."""
        sync_operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id="doc_123",
            entity_uuid=None,  # No UUID
            entity_type=EntityType.CONCEPT,
            mapping_type=MappingType.DOCUMENT,
            timestamp=datetime.now(UTC),
        )

        operations = await integration.process_sync_operation(sync_operation)
        # Should still process with entity_id as fallback
        assert len(operations) >= 1
