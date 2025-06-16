"""Graphiti Temporal Integration for Enhanced Sync Event System.

This module provides integration between Graphiti's temporal processing capabilities
and the enhanced sync event system, leveraging episodic processing and temporal
edge invalidation for document versioning and relationship management.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from graphiti_core.nodes import EpisodeType

from ..utils.logging import LoggingConfig
from .managers import GraphitiManager, IDMappingManager, TemporalManager
from .sync import EnhancedSyncOperation
from .sync.types import SyncOperationType

logger = LoggingConfig.get_logger(__name__)


class GraphitiTemporalOperationType(Enum):
    """Types of Graphiti temporal operations."""

    CREATE_EPISODE = "create_episode"
    UPDATE_EPISODE = "update_episode"
    INVALIDATE_EDGES = "invalidate_edges"
    VERSION_EPISODE = "version_episode"
    TEMPORAL_QUERY = "temporal_query"


@dataclass
class GraphitiTemporalOperation:
    """Container for Graphiti temporal operations."""

    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: GraphitiTemporalOperationType = (
        GraphitiTemporalOperationType.CREATE_EPISODE
    )
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Episode information
    episode_name: str | None = None
    episode_content: str | None = None
    episode_type: EpisodeType = EpisodeType.text
    episode_uuid: str | None = None
    reference_time: datetime | None = None

    # Versioning information
    document_uuid: str | None = None
    document_version: int = 1
    previous_version: int | None = None
    version_metadata: dict[str, Any] = field(default_factory=dict)

    # Edge invalidation information
    edges_to_invalidate: list[str] = field(default_factory=list)
    invalidation_reason: str | None = None
    invalidation_timestamp: datetime | None = None

    # Temporal query information
    query_time: datetime | None = None
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphitiTemporalIntegration:
    """Integration layer for Graphiti temporal features with enhanced sync system."""

    def __init__(
        self,
        graphiti_manager: GraphitiManager,
        temporal_manager: TemporalManager,
        id_mapping_manager: IDMappingManager,
        enable_episodic_versioning: bool = True,
        enable_temporal_edge_invalidation: bool = True,
        episode_retention_days: int = 365,
    ):
        """Initialize the Graphiti temporal integration.

        Args:
            graphiti_manager: Graphiti manager instance
            temporal_manager: Temporal manager instance
            id_mapping_manager: ID mapping manager instance
            enable_episodic_versioning: Whether to enable episodic versioning
            enable_temporal_edge_invalidation: Whether to enable temporal edge invalidation
            episode_retention_days: Number of days to retain episodes
        """
        self.graphiti_manager = graphiti_manager
        self.temporal_manager = temporal_manager
        self.id_mapping_manager = id_mapping_manager
        self.enable_episodic_versioning = enable_episodic_versioning
        self.enable_temporal_edge_invalidation = enable_temporal_edge_invalidation
        self.episode_retention_days = episode_retention_days

        # Operation tracking
        self._active_operations: dict[str, GraphitiTemporalOperation] = {}
        self._episode_version_map: dict[str, list[str]] = (
            {}
        )  # document_uuid -> episode_uuids
        self._edge_invalidation_log: list[dict[str, Any]] = []

        logger.info("GraphitiTemporalIntegration initialized")

    async def process_sync_operation(
        self, sync_operation: EnhancedSyncOperation
    ) -> list[GraphitiTemporalOperation]:
        """Process an enhanced sync operation using Graphiti temporal features.

        Args:
            sync_operation: The sync operation to process

        Returns:
            List of Graphiti temporal operations created
        """
        temporal_operations = []

        try:
            if sync_operation.operation_type == SyncOperationType.CREATE_DOCUMENT:
                temporal_operations.extend(
                    await self._handle_create_document_temporal(sync_operation)
                )
            elif sync_operation.operation_type == SyncOperationType.UPDATE_DOCUMENT:
                temporal_operations.extend(
                    await self._handle_update_document_temporal(sync_operation)
                )
            elif sync_operation.operation_type == SyncOperationType.DELETE_DOCUMENT:
                temporal_operations.extend(
                    await self._handle_delete_document_temporal(sync_operation)
                )
            elif sync_operation.operation_type == SyncOperationType.VERSION_UPDATE:
                temporal_operations.extend(
                    await self._handle_version_update_temporal(sync_operation)
                )

            logger.debug(
                f"Processed sync operation {sync_operation.operation_id}, "
                f"created {len(temporal_operations)} temporal operations"
            )

        except Exception as e:
            logger.error(
                f"Failed to process sync operation {sync_operation.operation_id}: {e}"
            )
            raise

        return temporal_operations

    async def _handle_create_document_temporal(
        self, sync_operation: EnhancedSyncOperation
    ) -> list[GraphitiTemporalOperation]:
        """Handle CREATE document operation with episodic processing."""
        operations = []

        if not self.enable_episodic_versioning:
            return operations

        # Create episode for the new document
        episode_operation = GraphitiTemporalOperation(
            operation_type=GraphitiTemporalOperationType.CREATE_EPISODE,
            episode_name=f"Document Creation: {sync_operation.entity_id}",
            episode_content=self._extract_content_from_operation(sync_operation),
            episode_type=EpisodeType.text,
            document_uuid=sync_operation.entity_uuid or sync_operation.entity_id,
            document_version=sync_operation.document_version,
            reference_time=sync_operation.timestamp,
            metadata={
                "sync_operation_id": sync_operation.operation_id,
                "operation_type": sync_operation.operation_type.value,
                "entity_type": sync_operation.entity_type.value,
            },
        )

        # Execute the episode creation
        episode_uuid = await self._execute_episode_operation(episode_operation)
        episode_operation.episode_uuid = episode_uuid

        # Track episode for versioning
        document_uuid = sync_operation.entity_uuid or sync_operation.entity_id
        if document_uuid:
            if document_uuid not in self._episode_version_map:
                self._episode_version_map[document_uuid] = []
            self._episode_version_map[document_uuid].append(episode_uuid)

        operations.append(episode_operation)
        return operations

    async def _handle_update_document_temporal(
        self, sync_operation: EnhancedSyncOperation
    ) -> list[GraphitiTemporalOperation]:
        """Handle UPDATE document operation with versioning and edge invalidation."""
        operations = []

        document_uuid = sync_operation.entity_uuid or sync_operation.entity_id
        if not document_uuid:
            logger.warning("No document UUID available for update operation")
            return operations

        # Create new version episode
        if self.enable_episodic_versioning:
            version_operation = GraphitiTemporalOperation(
                operation_type=GraphitiTemporalOperationType.VERSION_EPISODE,
                episode_name=f"Document Update v{sync_operation.document_version}: {document_uuid}",
                episode_content=self._extract_content_from_operation(sync_operation),
                episode_type=EpisodeType.text,
                document_uuid=document_uuid,
                document_version=sync_operation.document_version,
                previous_version=sync_operation.previous_version,
                reference_time=sync_operation.timestamp,
                version_metadata={
                    "update_reason": "document_update",
                    "content_hash": sync_operation.content_hash,
                    "previous_version": sync_operation.previous_version,
                },
                metadata={
                    "sync_operation_id": sync_operation.operation_id,
                    "operation_type": sync_operation.operation_type.value,
                },
            )

            # Execute the versioned episode creation
            episode_uuid = await self._execute_episode_operation(version_operation)
            version_operation.episode_uuid = episode_uuid

            # Track episode version
            if document_uuid:
                if document_uuid not in self._episode_version_map:
                    self._episode_version_map[document_uuid] = []
                self._episode_version_map[document_uuid].append(episode_uuid)

            operations.append(version_operation)

        # Handle temporal edge invalidation
        if self.enable_temporal_edge_invalidation:
            invalidation_operation = await self._create_edge_invalidation_operation(
                sync_operation, document_uuid
            )
            if invalidation_operation:
                await self._execute_edge_invalidation(invalidation_operation)
                operations.append(invalidation_operation)

        return operations

    async def _handle_delete_document_temporal(
        self, sync_operation: EnhancedSyncOperation
    ) -> list[GraphitiTemporalOperation]:
        """Handle DELETE document operation with temporal preservation."""
        operations = []

        document_uuid = sync_operation.entity_uuid or sync_operation.entity_id
        if not document_uuid:
            return operations

        # Create deletion episode to preserve history
        if self.enable_episodic_versioning:
            deletion_operation = GraphitiTemporalOperation(
                operation_type=GraphitiTemporalOperationType.UPDATE_EPISODE,
                episode_name=f"Document Deletion: {document_uuid}",
                episode_content=f"Document {document_uuid} was deleted at {sync_operation.timestamp.isoformat()}",
                episode_type=EpisodeType.text,
                document_uuid=document_uuid,
                reference_time=sync_operation.timestamp,
                metadata={
                    "sync_operation_id": sync_operation.operation_id,
                    "operation_type": sync_operation.operation_type.value,
                    "deletion_reason": "document_deleted",
                },
            )

            episode_uuid = await self._execute_episode_operation(deletion_operation)
            deletion_operation.episode_uuid = episode_uuid
            operations.append(deletion_operation)

        # Invalidate all edges related to the document
        if self.enable_temporal_edge_invalidation:
            invalidation_operation = await self._create_comprehensive_edge_invalidation(
                sync_operation, document_uuid
            )
            if invalidation_operation:
                await self._execute_edge_invalidation(invalidation_operation)
                operations.append(invalidation_operation)

        return operations

    async def _handle_version_update_temporal(
        self, sync_operation: EnhancedSyncOperation
    ) -> list[GraphitiTemporalOperation]:
        """Handle VERSION update operation with episodic versioning."""
        operations = []

        if not self.enable_episodic_versioning:
            return operations

        document_uuid = sync_operation.entity_uuid or sync_operation.entity_id
        if not document_uuid:
            return operations

        # Create version update episode
        version_operation = GraphitiTemporalOperation(
            operation_type=GraphitiTemporalOperationType.VERSION_EPISODE,
            episode_name=f"Version Update v{sync_operation.document_version}: {document_uuid}",
            episode_content=self._extract_content_from_operation(sync_operation),
            episode_type=EpisodeType.text,
            document_uuid=document_uuid,
            document_version=sync_operation.document_version,
            previous_version=sync_operation.previous_version,
            reference_time=sync_operation.timestamp,
            version_metadata={
                "update_reason": "version_update",
                "version_increment": 1,
            },
            metadata={
                "sync_operation_id": sync_operation.operation_id,
                "operation_type": sync_operation.operation_type.value,
            },
        )

        episode_uuid = await self._execute_episode_operation(version_operation)
        version_operation.episode_uuid = episode_uuid

        # Track episode version
        if document_uuid:
            if document_uuid not in self._episode_version_map:
                self._episode_version_map[document_uuid] = []
            self._episode_version_map[document_uuid].append(episode_uuid)

        operations.append(version_operation)
        return operations

    async def _execute_episode_operation(
        self, operation: GraphitiTemporalOperation
    ) -> str:
        """Execute an episode operation using Graphiti."""
        try:
            episode_uuid = await self.graphiti_manager.add_episode(
                name=operation.episode_name or f"Episode {operation.operation_id}",
                content=operation.episode_content or "",
                episode_type=operation.episode_type,
                source_description="Enhanced Sync Event System",
                reference_time=operation.reference_time or operation.timestamp,
                **operation.metadata,
            )

            logger.debug(
                f"Created episode {episode_uuid} for operation {operation.operation_id}"
            )
            return episode_uuid

        except Exception as e:
            logger.error(
                f"Failed to execute episode operation {operation.operation_id}: {e}"
            )
            raise

    async def _create_edge_invalidation_operation(
        self, sync_operation: EnhancedSyncOperation, document_uuid: str
    ) -> GraphitiTemporalOperation | None:
        """Create an edge invalidation operation for document updates."""
        try:
            # Find edges related to the document that need invalidation
            edges_to_invalidate = await self._find_edges_for_invalidation(document_uuid)

            if not edges_to_invalidate:
                return None

            invalidation_operation = GraphitiTemporalOperation(
                operation_type=GraphitiTemporalOperationType.INVALIDATE_EDGES,
                document_uuid=document_uuid,
                edges_to_invalidate=edges_to_invalidate,
                invalidation_reason="document_update",
                invalidation_timestamp=sync_operation.timestamp,
                metadata={
                    "sync_operation_id": sync_operation.operation_id,
                    "document_version": sync_operation.document_version,
                    "previous_version": sync_operation.previous_version,
                },
            )

            return invalidation_operation

        except Exception as e:
            logger.error(f"Failed to create edge invalidation operation: {e}")
            return None

    async def _create_comprehensive_edge_invalidation(
        self, sync_operation: EnhancedSyncOperation, document_uuid: str
    ) -> GraphitiTemporalOperation | None:
        """Create comprehensive edge invalidation for document deletion."""
        try:
            # Find all edges related to the document
            all_edges = await self._find_all_document_edges(document_uuid)

            if not all_edges:
                return None

            invalidation_operation = GraphitiTemporalOperation(
                operation_type=GraphitiTemporalOperationType.INVALIDATE_EDGES,
                document_uuid=document_uuid,
                edges_to_invalidate=all_edges,
                invalidation_reason="document_deletion",
                invalidation_timestamp=sync_operation.timestamp,
                metadata={
                    "sync_operation_id": sync_operation.operation_id,
                    "deletion_type": "comprehensive",
                },
            )

            return invalidation_operation

        except Exception as e:
            logger.error(f"Failed to create comprehensive edge invalidation: {e}")
            return None

    async def _execute_edge_invalidation(
        self, operation: GraphitiTemporalOperation
    ) -> None:
        """Execute edge invalidation using Graphiti's temporal features."""
        try:
            # Log the invalidation for tracking
            invalidation_record = {
                "operation_id": operation.operation_id,
                "document_uuid": operation.document_uuid,
                "edges_invalidated": operation.edges_to_invalidate,
                "reason": operation.invalidation_reason,
                "timestamp": (
                    operation.invalidation_timestamp or datetime.now(UTC)
                ).isoformat(),
                "metadata": operation.metadata,
            }

            self._edge_invalidation_log.append(invalidation_record)

            # Note: Graphiti handles temporal edge invalidation internally
            # through its episodic processing. When we create new episodes
            # with updated information, Graphiti automatically manages
            # the temporal validity of relationships.

            logger.info(
                f"Logged edge invalidation for document {operation.document_uuid}, "
                f"affecting {len(operation.edges_to_invalidate)} edges"
            )

        except Exception as e:
            logger.error(f"Failed to execute edge invalidation: {e}")
            raise

    async def _find_edges_for_invalidation(self, document_uuid: str) -> list[str]:
        """Find edges that need invalidation for a document update."""
        try:
            # Use Graphiti search to find relationships involving the document
            search_results = await self.graphiti_manager.search(
                query=f"document:{document_uuid}",
                limit=100,
            )

            # Extract edge UUIDs from search results
            edge_uuids = []
            for result in search_results:
                if hasattr(result, "uuid") and hasattr(result, "relationships"):
                    # Extract relationship UUIDs
                    for rel in getattr(result, "relationships", []):
                        if hasattr(rel, "uuid"):
                            edge_uuids.append(rel.uuid)

            return edge_uuids

        except Exception as e:
            logger.error(f"Failed to find edges for invalidation: {e}")
            return []

    async def _find_all_document_edges(self, document_uuid: str) -> list[str]:
        """Find all edges related to a document for comprehensive invalidation."""
        try:
            # Use broader search to find all relationships
            search_results = await self.graphiti_manager.search(
                query=f"uuid:{document_uuid} OR source:{document_uuid} OR target:{document_uuid}",
                limit=200,
            )

            edge_uuids = []
            for result in search_results:
                if hasattr(result, "uuid"):
                    edge_uuids.append(result.uuid)

            return edge_uuids

        except Exception as e:
            logger.error(f"Failed to find all document edges: {e}")
            return []

    def _extract_content_from_operation(
        self, sync_operation: EnhancedSyncOperation
    ) -> str:
        """Extract content from sync operation for episode creation."""
        operation_data = sync_operation.operation_data

        if isinstance(operation_data, dict):
            # Extract text content if available
            content = operation_data.get("content", "")
            if not content:
                content = operation_data.get("text", "")
            if not content:
                content = operation_data.get("body", "")
            if not content:
                # Fallback to JSON representation
                import json

                content = json.dumps(operation_data, indent=2)
        else:
            content = str(operation_data)

        return (
            content
            or f"Operation {sync_operation.operation_type.value} for {sync_operation.entity_id}"
        )

    async def query_temporal_episodes(
        self,
        document_uuid: str,
        query_time: datetime | None = None,
        time_range_start: datetime | None = None,
        time_range_end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Query episodes for a document within a temporal range."""
        try:
            episodes = self._episode_version_map.get(document_uuid, [])

            if not episodes:
                return []

            # Use Graphiti search to get episode details
            episode_details = []
            for episode_uuid in episodes:
                try:
                    search_results = await self.graphiti_manager.search(
                        query=f"episode:{episode_uuid}",
                        limit=1,
                    )

                    if search_results:
                        episode_details.append(
                            {
                                "episode_uuid": episode_uuid,
                                "document_uuid": document_uuid,
                                "details": search_results[0],
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to retrieve episode {episode_uuid}: {e}")

            return episode_details

        except Exception as e:
            logger.error(f"Failed to query temporal episodes: {e}")
            return []

    async def get_document_version_history(
        self, document_uuid: str
    ) -> list[dict[str, Any]]:
        """Get the complete version history for a document."""
        try:
            episodes = await self.query_temporal_episodes(document_uuid)

            # Sort by creation time and add version information
            version_history = []
            for i, episode in enumerate(episodes):
                version_info = {
                    "version": i + 1,
                    "episode_uuid": episode["episode_uuid"],
                    "document_uuid": document_uuid,
                    "created_at": episode.get("details", {}).get("created_at"),
                    "episode_details": episode["details"],
                }
                version_history.append(version_info)

            return sorted(version_history, key=lambda x: x.get("created_at", ""))

        except Exception as e:
            logger.error(f"Failed to get document version history: {e}")
            return []

    async def get_edge_invalidation_log(
        self,
        document_uuid: str | None = None,
        time_range_start: datetime | None = None,
        time_range_end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get the edge invalidation log with optional filtering."""
        try:
            filtered_log = self._edge_invalidation_log

            if document_uuid:
                filtered_log = [
                    record
                    for record in filtered_log
                    if record.get("document_uuid") == document_uuid
                ]

            if time_range_start or time_range_end:

                def in_time_range(record):
                    timestamp_str = record.get("timestamp", "")
                    try:
                        timestamp = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00")
                        )
                        if time_range_start and timestamp < time_range_start:
                            return False
                        if time_range_end and timestamp > time_range_end:
                            return False
                        return True
                    except Exception:
                        return False

                filtered_log = [
                    record for record in filtered_log if in_time_range(record)
                ]

            return filtered_log

        except Exception as e:
            logger.error(f"Failed to get edge invalidation log: {e}")
            return []

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the Graphiti temporal integration."""
        try:
            return {
                "healthy": True,
                "graphiti_manager_initialized": self.graphiti_manager.is_initialized,
                "episodic_versioning_enabled": self.enable_episodic_versioning,
                "temporal_edge_invalidation_enabled": self.enable_temporal_edge_invalidation,
                "active_operations": len(self._active_operations),
                "tracked_documents": len(self._episode_version_map),
                "edge_invalidations_logged": len(self._edge_invalidation_log),
                "episode_retention_days": self.episode_retention_days,
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
            }
