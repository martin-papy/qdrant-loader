"""Streamlined Version Manager for QDrant Loader.

This module provides the main VersionManager class that orchestrates
all versioning operations using the modular versioning components.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from neo4j import AsyncDriver

from ...utils.logging import LoggingConfig
from ..managers import IDMappingManager, Neo4jManager, QdrantManager
from . import (
    VersionCleanup,
    VersionConfig,
    VersionDiff,
    VersionMetadata,
    VersionOperation,
    VersionOperations,
    VersionSnapshot,
    VersionStatistics,
    VersionStorage,
    VersionType,
)


class VersionManager:
    """Main version manager that orchestrates all versioning operations."""

    def __init__(
        self,
        id_mapping_manager: IDMappingManager,
        neo4j_manager: Neo4jManager,
        qdrant_manager: QdrantManager,
        neo4j_driver: AsyncDriver,
        config: VersionConfig | None = None,
    ):
        """Initialize the version manager.

        Args:
            id_mapping_manager: ID mapping manager
            neo4j_manager: Neo4j manager
            qdrant_manager: Qdrant manager
            neo4j_driver: Neo4j async driver
            config: Optional version configuration
        """
        self.id_mapping_manager = id_mapping_manager
        self.neo4j_manager = neo4j_manager
        self.qdrant_manager = qdrant_manager
        self.neo4j_driver = neo4j_driver

        # Use provided config or create default
        self.config = config or VersionConfig()

        # Initialize components
        self.storage = VersionStorage(neo4j_driver, self.config)
        self.operations = VersionOperations(
            self.storage,
            id_mapping_manager,
            neo4j_manager,
            qdrant_manager,
            self.config,
        )
        self.cleanup = VersionCleanup(self.storage, self.config)

        self.logger = LoggingConfig.get_logger(__name__)
        self._cleanup_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize the version manager."""
        try:
            # Create necessary indexes
            await self.storage.create_indexes()

            # Start cleanup scheduler if enabled
            if self.config.enable_auto_cleanup:
                self._cleanup_task = asyncio.create_task(
                    self.cleanup.schedule_cleanup()
                )

            self.logger.info("Version manager initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize version manager: {e}")
            raise

    # Version Operations
    async def create_version(
        self,
        entity_id: str,
        version_type: VersionType,
        content: dict[str, Any],
        operation: VersionOperation = VersionOperation.CREATE,
        parent_version_id: str | None = None,
        supersedes: str | None = None,
        created_by: str | None = None,
        tags: list[str] | None = None,
        is_milestone: bool = False,
    ) -> VersionMetadata | None:
        """Create a new version."""
        return await self.operations.create_version(
            entity_id=entity_id,
            version_type=version_type,
            content=content,
            operation=operation,
            parent_version_id=parent_version_id,
            supersedes=supersedes,
            created_by=created_by,
            tags=tags,
            is_milestone=is_milestone,
        )

    async def get_version(self, version_id: str) -> VersionMetadata | None:
        """Get version by ID."""
        return await self.operations.get_version(version_id)

    async def get_latest_version(
        self, entity_id: str, version_type: VersionType
    ) -> VersionMetadata | None:
        """Get the latest version for an entity."""
        return await self.operations.get_latest_version(entity_id, version_type)

    async def get_entity_versions(
        self,
        entity_id: str,
        version_type: VersionType | None = None,
        limit: int | None = None,
    ) -> list[VersionMetadata]:
        """Get all versions for an entity."""
        return await self.storage.get_entity_versions(entity_id, version_type, limit)

    async def get_version_history(
        self,
        entity_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[VersionMetadata]:
        """Get version history for an entity within a time range."""
        return await self.storage.get_version_history(entity_id, start_time, end_time)

    async def compare_versions(
        self, from_version_id: str, to_version_id: str
    ) -> VersionDiff | None:
        """Compare two versions and generate a diff."""
        return await self.operations.compare_versions(from_version_id, to_version_id)

    async def rollback_to_version(
        self, entity_id: str, version_id: str, created_by: str | None = None
    ) -> bool:
        """Rollback an entity to a specific version."""
        return await self.operations.rollback_to_version(
            entity_id, version_id, created_by
        )

    # Snapshot Operations
    async def create_snapshot(
        self,
        description: str = "",
        entity_ids: list[str] | None = None,
        created_by: str | None = None,
        tags: list[str] | None = None,
    ) -> VersionSnapshot | None:
        """Create a point-in-time snapshot."""
        return await self.operations.create_snapshot(
            description=description,
            entity_ids=entity_ids,
            created_by=created_by,
            tags=tags,
        )

    async def get_snapshot(self, snapshot_id: str) -> VersionSnapshot | None:
        """Get a version snapshot by ID."""
        return await self.storage.get_version_snapshot(snapshot_id)

    # Cleanup Operations
    async def run_cleanup(self) -> dict[str, int]:
        """Run comprehensive cleanup operations."""
        return await self.cleanup.run_cleanup()

    async def cleanup_old_versions(self, retention_days: int | None = None) -> int:
        """Clean up old versions."""
        return await self.cleanup.cleanup_old_versions(retention_days)

    async def get_cleanup_recommendations(self) -> dict[str, Any]:
        """Get cleanup recommendations."""
        return await self.cleanup.get_cleanup_recommendations()

    async def validate_version_integrity(self) -> dict[str, list[str]]:
        """Validate version data integrity."""
        return await self.cleanup.validate_version_integrity()

    # Statistics and Monitoring
    async def get_version_statistics(self) -> VersionStatistics:
        """Get version usage statistics."""
        return await self.storage.get_version_statistics()

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the version manager."""
        try:
            stats = await self.get_version_statistics()

            health_status = {
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "version_count": stats.total_versions,
                "entity_count": stats.total_entities,
                "storage_size_bytes": stats.storage_size_bytes,
                "cache_size": stats.cache_size,
                "cleanup_enabled": self.config.enable_auto_cleanup,
                "compression_enabled": self.config.enable_compression,
            }

            # Check for potential issues
            warnings = []
            if stats.total_versions > 10000:
                warnings.append("High version count - consider cleanup")
            if stats.storage_size_bytes > 1024 * 1024 * 1024:  # 1GB
                warnings.append("Large storage size - consider archival")

            if warnings:
                health_status["warnings"] = warnings

            return health_status

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            }

    # Configuration Management
    def update_config(self, config: VersionConfig) -> None:
        """Update version configuration."""
        self.config = config
        self.storage.config = config
        self.cleanup.config = config
        self.operations.config = config

        self.logger.info("Version manager configuration updated")

    def get_config(self) -> VersionConfig:
        """Get current version configuration."""
        return self.config

    # Lifecycle Management
    async def close(self) -> None:
        """Close the version manager and cleanup resources."""
        try:
            # Cancel cleanup task if running
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("Version manager closed successfully")

        except Exception as e:
            self.logger.error(f"Error closing version manager: {e}")

    # Context Manager Support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
