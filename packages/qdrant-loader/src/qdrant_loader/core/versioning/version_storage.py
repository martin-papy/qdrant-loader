"""Version storage operations for Neo4j database.

This module handles all database interactions for version management,
including storing, retrieving, and querying version data.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from neo4j import AsyncDriver

from ...utils.logging import LoggingConfig
from .version_types import (
    VersionConfig,
    VersionMetadata,
    VersionSnapshot,
    VersionStatistics,
    VersionType,
)


class VersionStorage:
    """Handles version storage operations in Neo4j."""

    def __init__(self, driver: AsyncDriver, config: VersionConfig):
        """Initialize version storage.

        Args:
            driver: Neo4j async driver
            config: Version configuration
        """
        self.driver = driver
        self.config = config
        self.logger = LoggingConfig.get_logger(__name__)

    async def store_version_metadata(self, metadata: VersionMetadata) -> bool:
        """Store version metadata in Neo4j.

        Args:
            metadata: Version metadata to store

        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            MERGE (v:Version {version_id: $version_id})
            SET v += $properties
            WITH v
            OPTIONAL MATCH (parent:Version {version_id: $parent_version_id})
            OPTIONAL MATCH (supersedes:Version {version_id: $supersedes})
            FOREACH (p IN CASE WHEN parent IS NOT NULL THEN [parent] ELSE [] END |
                MERGE (p)-[:PARENT_OF]->(v)
            )
            FOREACH (s IN CASE WHEN supersedes IS NOT NULL THEN [supersedes] ELSE [] END |
                MERGE (v)-[:SUPERSEDES]->(s)
                SET s.status = 'superseded'
            )
            RETURN v.version_id as version_id
            """

            properties = metadata.to_dict()

            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    {
                        "version_id": metadata.version_id,
                        "parent_version_id": metadata.parent_version_id,
                        "supersedes": metadata.supersedes,
                        "properties": properties,
                    },
                )

                record = await result.single()
                if record:
                    self.logger.info(f"Stored version metadata: {metadata.version_id}")
                    return True

        except Exception as e:
            self.logger.error(f"Failed to store version metadata: {e}")

        return False

    async def get_version_metadata(self, version_id: str) -> VersionMetadata | None:
        """Retrieve version metadata by ID.

        Args:
            version_id: Version ID to retrieve

        Returns:
            Version metadata if found, None otherwise
        """
        try:
            query = """
            MATCH (v:Version {version_id: $version_id})
            RETURN v
            """

            async with self.driver.session() as session:
                result = await session.run(query, {"version_id": version_id})
                record = await result.single()

                if record:
                    version_data = dict(record["v"])
                    return VersionMetadata.from_dict(version_data)

        except Exception as e:
            self.logger.error(f"Failed to get version metadata: {e}")

        return None

    async def get_entity_versions(
        self,
        entity_id: str,
        version_type: VersionType | None = None,
        limit: int | None = None,
    ) -> list[VersionMetadata]:
        """Get all versions for an entity.

        Args:
            entity_id: Entity ID
            version_type: Optional version type filter
            limit: Optional limit on number of versions

        Returns:
            List of version metadata
        """
        try:
            query = """
            MATCH (v:Version {entity_id: $entity_id})
            """

            params: dict[str, Any] = {"entity_id": entity_id}

            if version_type:
                query += " WHERE v.version_type = $version_type"
                params["version_type"] = version_type.value

            query += " RETURN v ORDER BY v.version_number DESC"

            if limit:
                query += " LIMIT $limit"
                params["limit"] = limit

            async with self.driver.session() as session:
                result = await session.run(query, params)
                records = await result.data()

                return [
                    VersionMetadata.from_dict(dict(record["v"])) for record in records
                ]

        except Exception as e:
            self.logger.error(f"Failed to get entity versions: {e}")

        return []

    async def get_version_history(
        self,
        entity_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[VersionMetadata]:
        """Get version history for an entity within a time range.

        Args:
            entity_id: Entity ID
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of version metadata in chronological order
        """
        try:
            query = """
            MATCH (v:Version {entity_id: $entity_id})
            WHERE 1=1
            """

            params: dict[str, Any] = {"entity_id": entity_id}

            if start_time:
                query += " AND datetime(v.created_at) >= datetime($start_time)"
                params["start_time"] = start_time.isoformat()

            if end_time:
                query += " AND datetime(v.created_at) <= datetime($end_time)"
                params["end_time"] = end_time.isoformat()

            query += " RETURN v ORDER BY v.created_at ASC"

            async with self.driver.session() as session:
                result = await session.run(query, params)
                records = await result.data()

                return [
                    VersionMetadata.from_dict(dict(record["v"])) for record in records
                ]

        except Exception as e:
            self.logger.error(f"Failed to get version history: {e}")

        return []

    async def store_version_snapshot(self, snapshot: VersionSnapshot) -> bool:
        """Store a version snapshot.

        Args:
            snapshot: Version snapshot to store

        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            CREATE (s:VersionSnapshot {
                snapshot_id: $snapshot_id,
                timestamp: $timestamp,
                description: $description,
                created_by: $created_by,
                entity_count: $entity_count,
                relationship_count: $relationship_count,
                mapping_count: $mapping_count,
                entities: $entities,
                relationships: $relationships,
                mappings: $mappings,
                tags: $tags
            })
            RETURN s.snapshot_id as snapshot_id
            """

            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    {
                        "snapshot_id": snapshot.snapshot_id,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "description": snapshot.description,
                        "created_by": snapshot.created_by,
                        "entity_count": snapshot.entity_count,
                        "relationship_count": snapshot.relationship_count,
                        "mapping_count": snapshot.mapping_count,
                        "entities": json.dumps(snapshot.entities),
                        "relationships": json.dumps(snapshot.relationships),
                        "mappings": json.dumps(snapshot.mappings),
                        "tags": list(snapshot.tags),
                    },
                )

                record = await result.single()
                if record:
                    self.logger.info(f"Stored version snapshot: {snapshot.snapshot_id}")
                    return True

        except Exception as e:
            self.logger.error(f"Failed to store version snapshot: {e}")

        return False

    async def get_version_snapshot(self, snapshot_id: str) -> VersionSnapshot | None:
        """Retrieve a version snapshot by ID.

        Args:
            snapshot_id: Snapshot ID to retrieve

        Returns:
            Version snapshot if found, None otherwise
        """
        try:
            query = """
            MATCH (s:VersionSnapshot {snapshot_id: $snapshot_id})
            RETURN s
            """

            async with self.driver.session() as session:
                result = await session.run(query, {"snapshot_id": snapshot_id})
                record = await result.single()

                if record:
                    data = dict(record["s"])

                    snapshot = VersionSnapshot(
                        snapshot_id=data["snapshot_id"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        description=data.get("description", ""),
                        created_by=data.get("created_by"),
                        entity_count=data.get("entity_count", 0),
                        relationship_count=data.get("relationship_count", 0),
                        mapping_count=data.get("mapping_count", 0),
                        entities=json.loads(data.get("entities", "{}")),
                        relationships=json.loads(data.get("relationships", "{}")),
                        mappings=json.loads(data.get("mappings", "{}")),
                        tags=set(data.get("tags", [])),
                    )

                    return snapshot

        except Exception as e:
            self.logger.error(f"Failed to get version snapshot: {e}")

        return None

    async def delete_version(self, version_id: str) -> bool:
        """Delete a version and its relationships.

        Args:
            version_id: Version ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            MATCH (v:Version {version_id: $version_id})
            DETACH DELETE v
            RETURN count(v) as deleted_count
            """

            async with self.driver.session() as session:
                result = await session.run(query, {"version_id": version_id})
                record = await result.single()

                if record and record["deleted_count"] > 0:
                    self.logger.info(f"Deleted version: {version_id}")
                    return True

        except Exception as e:
            self.logger.error(f"Failed to delete version: {e}")

        return False

    async def cleanup_old_versions(self, retention_days: int | None = None) -> int:
        """Clean up old versions based on retention policy.

        Args:
            retention_days: Optional override for retention days

        Returns:
            Number of versions cleaned up
        """
        try:
            retention = retention_days or self.config.retention_days
            cutoff_date = datetime.now(UTC) - timedelta(days=retention)

            query = """
            MATCH (v:Version)
            WHERE datetime(v.created_at) < datetime($cutoff_date)
            AND v.status <> 'active'
            AND NOT v.is_milestone
            DETACH DELETE v
            RETURN count(v) as deleted_count
            """

            async with self.driver.session() as session:
                result = await session.run(
                    query, {"cutoff_date": cutoff_date.isoformat()}
                )
                record = await result.single()

                deleted_count = record["deleted_count"] if record else 0

                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} old versions")

                return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old versions: {e}")

        return 0

    async def get_version_statistics(self) -> VersionStatistics:
        """Get version usage statistics.

        Returns:
            Version statistics
        """
        try:
            query = """
            MATCH (v:Version)
            RETURN 
                count(v) as total_versions,
                count(DISTINCT v.entity_id) as total_entities,
                avg(v.version_number) as avg_versions_per_entity,
                max(v.version_number) as max_versions_per_entity,
                min(datetime(v.created_at)) as oldest_version,
                max(datetime(v.created_at)) as newest_version,
                collect(DISTINCT v.version_type) as version_types,
                collect(DISTINCT v.status) as version_statuses
            """

            async with self.driver.session() as session:
                result = await session.run(query)
                record = await result.single()

                if record:
                    # Get type and status counts
                    type_counts = {}
                    status_counts = {}

                    type_query = """
                    MATCH (v:Version)
                    RETURN v.version_type as type, count(v) as count
                    """

                    status_query = """
                    MATCH (v:Version)
                    RETURN v.status as status, count(v) as count
                    """

                    type_result = await session.run(type_query)
                    async for type_record in type_result:
                        type_counts[type_record["type"]] = type_record["count"]

                    status_result = await session.run(status_query)
                    async for status_record in status_result:
                        status_counts[status_record["status"]] = status_record["count"]

                    stats = VersionStatistics(
                        total_versions=record["total_versions"],
                        total_entities=record["total_entities"],
                        average_versions_per_entity=record["avg_versions_per_entity"]
                        or 0.0,
                        max_versions_per_entity=record["max_versions_per_entity"] or 0,
                        oldest_version=record["oldest_version"],
                        newest_version=record["newest_version"],
                        version_types=type_counts,
                        version_statuses=status_counts,
                    )

                    return stats

        except Exception as e:
            self.logger.error(f"Failed to get version statistics: {e}")

        return VersionStatistics()

    async def create_indexes(self) -> bool:
        """Create necessary indexes for version queries.

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.driver.session() as session:
                # Create indexes using literal strings to satisfy Neo4j requirements
                await session.run(
                    "CREATE INDEX version_id_index IF NOT EXISTS FOR (v:Version) ON (v.version_id)"
                )
                await session.run(
                    "CREATE INDEX entity_id_index IF NOT EXISTS FOR (v:Version) ON (v.entity_id)"
                )
                await session.run(
                    "CREATE INDEX version_type_index IF NOT EXISTS FOR (v:Version) ON (v.version_type)"
                )
                await session.run(
                    "CREATE INDEX version_status_index IF NOT EXISTS FOR (v:Version) ON (v.status)"
                )
                await session.run(
                    "CREATE INDEX version_created_at_index IF NOT EXISTS FOR (v:Version) ON (v.created_at)"
                )
                await session.run(
                    "CREATE INDEX snapshot_id_index IF NOT EXISTS FOR (s:VersionSnapshot) ON (s.snapshot_id)"
                )
                await session.run(
                    "CREATE INDEX snapshot_timestamp_index IF NOT EXISTS FOR (s:VersionSnapshot) ON (s.timestamp)"
                )

            self.logger.info("Created version storage indexes")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create indexes: {e}")
            return False
