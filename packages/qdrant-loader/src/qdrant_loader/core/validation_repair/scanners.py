"""
Validation scanners for detecting inconsistencies between QDrant and Neo4j.

This module contains all the scanner methods that check for various types
of validation issues across the synchronized databases.
"""

import logging
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any

from ..managers import IDMappingManager, Neo4jManager, QdrantManager, MappingStatus
from ..types import EntityType
from .models import (
    ValidationIssue,
    ValidationCategory,
    ValidationSeverity,
    RepairAction,
)

logger = logging.getLogger(__name__)


class ValidationScanners:
    """Collection of validation scanner methods."""

    def __init__(
        self,
        id_mapping_manager: IDMappingManager,
        neo4j_manager: Neo4jManager,
        qdrant_manager: QdrantManager,
    ):
        self.id_mapping_manager = id_mapping_manager
        self.neo4j_manager = neo4j_manager
        self.qdrant_manager = qdrant_manager

    async def scan_missing_mappings(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for entities that exist in one database but lack mappings."""
        issues = []

        try:
            # Check QDrant points without mappings
            qdrant_issues = await self._scan_qdrant_missing_mappings(max_entities)
            issues.extend(qdrant_issues)

            # Check Neo4j nodes without mappings
            neo4j_issues = await self._scan_neo4j_missing_mappings(max_entities)
            issues.extend(neo4j_issues)

        except Exception as e:
            logger.error(f"Error scanning missing mappings: {e}")

        return issues

    async def _scan_qdrant_missing_mappings(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for QDrant points without corresponding mappings."""
        issues = []

        try:
            # Get all points from QDrant
            client = self.qdrant_manager._ensure_client_connected()
            collection_info = client.get_collection(self.qdrant_manager.collection_name)

            # Scroll through points
            scroll_result = client.scroll(
                collection_name=self.qdrant_manager.collection_name,
                limit=max_entities or 10000,
                with_payload=True,
            )

            for point in scroll_result[0]:
                point_id = str(point.id)

                # Check if mapping exists
                mapping = await self.id_mapping_manager.get_mapping_by_qdrant_id(
                    point_id
                )

                if not mapping:
                    issue = ValidationIssue(
                        category=ValidationCategory.MISSING_MAPPING,
                        severity=ValidationSeverity.WARNING,
                        title="Missing QDrant Mapping",
                        description=f"QDrant point {point_id} has no corresponding mapping",
                        qdrant_point_id=point_id,
                        suggested_actions=[RepairAction.CREATE_MAPPING],
                        auto_repairable=True,
                        repair_priority=6,
                        metadata={
                            "point_payload": point.payload,
                            "vector_size": len(point.vector) if point.vector else 0,
                        },
                    )
                    issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning QDrant missing mappings: {e}")

        return issues

    async def _scan_neo4j_missing_mappings(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for Neo4j nodes without corresponding mappings."""
        issues = []

        try:
            # Query for nodes that might need mappings (exclude system nodes)
            query = """
            MATCH (n)
            WHERE NOT n:IDMapping 
              AND NOT n:_GraphitiBatch
              AND NOT n:_GraphitiEpisode
            RETURN id(n) as node_id, labels(n) as labels, 
                   n.uuid as uuid, n.name as name
            LIMIT $limit
            """

            results = self.neo4j_manager.execute_read_query(
                query, {"limit": max_entities or 10000}
            )

            for result in results:
                node_id = str(result["node_id"])
                node_uuid = result.get("uuid")

                # Check if mapping exists by ID or UUID
                mapping = await self.id_mapping_manager.get_mapping_by_neo4j_id(node_id)
                if not mapping and node_uuid:
                    mapping = await self.id_mapping_manager.get_mapping_by_neo4j_uuid(
                        node_uuid
                    )

                if not mapping:
                    issue = ValidationIssue(
                        category=ValidationCategory.MISSING_MAPPING,
                        severity=ValidationSeverity.WARNING,
                        title="Missing Neo4j Mapping",
                        description=f"Neo4j node {node_id} has no corresponding mapping",
                        neo4j_node_id=node_id,
                        suggested_actions=[RepairAction.CREATE_MAPPING],
                        auto_repairable=True,
                        repair_priority=6,
                        metadata={
                            "node_labels": result["labels"],
                            "node_uuid": node_uuid,
                            "node_name": result.get("name"),
                        },
                    )
                    issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning Neo4j missing mappings: {e}")

        return issues

    async def scan_orphaned_records(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for orphaned records where mapped entities no longer exist."""
        issues = []

        try:
            # Get all mappings
            mappings = await self.id_mapping_manager.get_mappings_by_entity_type(
                EntityType.CONCEPT,  # This will get all types due to implementation
                limit=max_entities or 10000,
            )

            for mapping in mappings:
                # Validate existence of mapped entities
                await self.id_mapping_manager._validate_mapping_existence(mapping)

                if mapping.is_orphaned():
                    severity = (
                        ValidationSeverity.ERROR
                        if mapping.status == MappingStatus.ACTIVE
                        else ValidationSeverity.WARNING
                    )

                    issue = ValidationIssue(
                        category=ValidationCategory.ORPHANED_RECORD,
                        severity=severity,
                        title="Orphaned Mapping",
                        description=f"Mapping {mapping.mapping_id} references non-existent entities",
                        mapping_id=mapping.mapping_id,
                        qdrant_point_id=mapping.qdrant_point_id,
                        neo4j_node_id=mapping.neo4j_node_id,
                        suggested_actions=[RepairAction.DELETE_ORPHANED],
                        auto_repairable=True,
                        repair_priority=7,
                        metadata={
                            "qdrant_exists": mapping.qdrant_exists,
                            "neo4j_exists": mapping.neo4j_exists,
                            "entity_type": mapping.entity_type.value,
                            "mapping_type": mapping.mapping_type.value,
                        },
                    )
                    issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning orphaned records: {e}")

        return issues

    async def scan_data_mismatches(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for data mismatches between QDrant and Neo4j."""
        issues = []

        try:
            # Get active mappings
            mappings = await self.id_mapping_manager.get_mappings_by_entity_type(
                EntityType.CONCEPT,
                status=MappingStatus.ACTIVE,
                limit=max_entities or 1000,
            )

            for mapping in mappings:
                if not mapping.qdrant_point_id or not (
                    mapping.neo4j_node_id or mapping.neo4j_node_uuid
                ):
                    continue

                try:
                    # Get QDrant point data
                    client = self.qdrant_manager._ensure_client_connected()
                    qdrant_points = client.retrieve(
                        collection_name=self.qdrant_manager.collection_name,
                        ids=[mapping.qdrant_point_id],
                        with_payload=True,
                    )

                    if not qdrant_points:
                        continue

                    qdrant_point = qdrant_points[0]

                    # Get Neo4j node data
                    if mapping.neo4j_node_id:
                        neo4j_query = "MATCH (n) WHERE id(n) = $node_id RETURN n"
                        neo4j_params = {"node_id": int(mapping.neo4j_node_id)}
                    else:
                        neo4j_query = "MATCH (n {uuid: $node_uuid}) RETURN n"
                        neo4j_params = {"node_uuid": mapping.neo4j_node_uuid}

                    neo4j_results = self.neo4j_manager.execute_read_query(
                        neo4j_query, neo4j_params
                    )

                    if not neo4j_results:
                        continue

                    neo4j_node = neo4j_results[0]["n"]

                    # Compare data
                    mismatches = self._compare_entity_data(
                        qdrant_point, neo4j_node, mapping
                    )

                    for mismatch in mismatches:
                        issue = ValidationIssue(
                            category=ValidationCategory.DATA_MISMATCH,
                            severity=ValidationSeverity.WARNING,
                            title=f"Data Mismatch: {mismatch['field']}",
                            description=f"Field '{mismatch['field']}' differs between QDrant and Neo4j",
                            mapping_id=mapping.mapping_id,
                            qdrant_point_id=mapping.qdrant_point_id,
                            neo4j_node_id=mapping.neo4j_node_id,
                            expected_value=mismatch["neo4j_value"],
                            actual_value=mismatch["qdrant_value"],
                            suggested_actions=[RepairAction.SYNC_ENTITIES],
                            auto_repairable=True,
                            repair_priority=5,
                            metadata=mismatch,
                        )
                        issues.append(issue)

                except Exception as e:
                    logger.warning(
                        f"Error comparing data for mapping {mapping.mapping_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error scanning data mismatches: {e}")

        return issues

    async def scan_version_inconsistencies(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for version inconsistencies between databases."""
        issues = []

        try:
            # Get mappings with version information
            mappings = await self.id_mapping_manager.get_mappings_by_entity_type(
                EntityType.CONCEPT,
                status=MappingStatus.ACTIVE,
                limit=max_entities or 1000,
            )

            for mapping in mappings:
                if not mapping.qdrant_point_id or not (
                    mapping.neo4j_node_id or mapping.neo4j_node_uuid
                ):
                    continue

                try:
                    # Check version consistency
                    version_issue = await self._check_version_consistency(mapping)
                    if version_issue:
                        issues.append(version_issue)

                except Exception as e:
                    logger.warning(
                        f"Error checking version for mapping {mapping.mapping_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error scanning version inconsistencies: {e}")

        return issues

    async def scan_sync_failures(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for mappings with sync failures."""
        issues = []

        try:
            # Get mappings with sync failures
            query = """
            MATCH (m:IDMapping)
            WHERE m.status = $sync_failed_status
            RETURN m
            LIMIT $limit
            """

            results = self.neo4j_manager.execute_read_query(
                query,
                {
                    "sync_failed_status": MappingStatus.SYNC_FAILED.value,
                    "limit": max_entities or 1000,
                },
            )

            for result in results:
                mapping_data = result["m"]
                mapping = self.id_mapping_manager._neo4j_result_to_mapping(mapping_data)

                issue = ValidationIssue(
                    category=ValidationCategory.SYNC_FAILURE,
                    severity=ValidationSeverity.ERROR,
                    title="Sync Failure",
                    description=f"Mapping {mapping.mapping_id} has failed synchronization",
                    mapping_id=mapping.mapping_id,
                    qdrant_point_id=mapping.qdrant_point_id,
                    neo4j_node_id=mapping.neo4j_node_id,
                    suggested_actions=[RepairAction.SYNC_ENTITIES],
                    auto_repairable=True,
                    repair_priority=8,
                    metadata={
                        "sync_errors": mapping.sync_errors,
                        "last_sync_time": (
                            mapping.last_sync_time.isoformat()
                            if mapping.last_sync_time
                            else None
                        ),
                        "sync_version": mapping.sync_version,
                    },
                )
                issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning sync failures: {e}")

        return issues

    async def scan_constraint_violations(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for constraint violations in the databases."""
        issues = []

        try:
            # Check Neo4j constraints
            neo4j_issues = await self._check_neo4j_constraints()
            issues.extend(neo4j_issues)

            # Check QDrant constraints (collection health, etc.)
            qdrant_issues = await self._check_qdrant_constraints()
            issues.extend(qdrant_issues)

        except Exception as e:
            logger.error(f"Error scanning constraint violations: {e}")

        return issues

    async def scan_performance_issues(
        self, max_entities: Optional[int] = None
    ) -> List[ValidationIssue]:
        """Scan for performance-related issues."""
        issues = []

        try:
            # Check for large batch operations
            performance_metrics = await self._collect_performance_metrics()

            # Check query performance
            if performance_metrics.get("avg_query_time_ms", 0) > 1000:
                issue = ValidationIssue(
                    category=ValidationCategory.PERFORMANCE_ISSUE,
                    severity=ValidationSeverity.WARNING,
                    title="Slow Query Performance",
                    description="Average query time exceeds recommended threshold",
                    suggested_actions=[RepairAction.REBUILD_INDEX],
                    auto_repairable=False,
                    repair_priority=3,
                    metadata=performance_metrics,
                )
                issues.append(issue)

            # Check memory usage
            if performance_metrics.get("memory_usage_percent", 0) > 80:
                issue = ValidationIssue(
                    category=ValidationCategory.PERFORMANCE_ISSUE,
                    severity=ValidationSeverity.WARNING,
                    title="High Memory Usage",
                    description="System memory usage is above 80%",
                    suggested_actions=[RepairAction.MANUAL_INTERVENTION],
                    auto_repairable=False,
                    repair_priority=4,
                    metadata=performance_metrics,
                )
                issues.append(issue)

        except Exception as e:
            logger.error(f"Error scanning performance issues: {e}")

        return issues

    # Helper methods

    def _compare_entity_data(
        self, qdrant_point, neo4j_node, mapping
    ) -> List[Dict[str, Any]]:
        """Compare data between QDrant point and Neo4j node."""
        mismatches = []

        try:
            # Compare common fields
            qdrant_payload = qdrant_point.payload or {}
            neo4j_props = dict(neo4j_node)

            # Check name/title fields
            qdrant_name = qdrant_payload.get("name") or qdrant_payload.get("title")
            neo4j_name = neo4j_props.get("name") or neo4j_props.get("title")

            if qdrant_name and neo4j_name and qdrant_name != neo4j_name:
                mismatches.append(
                    {
                        "field": "name",
                        "qdrant_value": qdrant_name,
                        "neo4j_value": neo4j_name,
                        "severity": "medium",
                    }
                )

            # Check UUID fields
            qdrant_uuid = qdrant_payload.get("uuid")
            neo4j_uuid = neo4j_props.get("uuid")

            if qdrant_uuid and neo4j_uuid and qdrant_uuid != neo4j_uuid:
                mismatches.append(
                    {
                        "field": "uuid",
                        "qdrant_value": qdrant_uuid,
                        "neo4j_value": neo4j_uuid,
                        "severity": "high",
                    }
                )

            # Check timestamps
            qdrant_updated = qdrant_payload.get("updated_at")
            neo4j_updated = neo4j_props.get("updated_at")

            if qdrant_updated and neo4j_updated:
                try:
                    qdrant_dt = datetime.fromisoformat(
                        qdrant_updated.replace("Z", "+00:00")
                    )
                    neo4j_dt = datetime.fromisoformat(
                        neo4j_updated.replace("Z", "+00:00")
                    )

                    # Allow small time differences (1 second)
                    if abs((qdrant_dt - neo4j_dt).total_seconds()) > 1:
                        mismatches.append(
                            {
                                "field": "updated_at",
                                "qdrant_value": qdrant_updated,
                                "neo4j_value": neo4j_updated,
                                "severity": "low",
                            }
                        )
                except Exception:
                    pass  # Skip timestamp comparison if parsing fails

        except Exception as e:
            logger.warning(f"Error comparing entity data: {e}")

        return mismatches

    async def _check_version_consistency(self, mapping) -> Optional[ValidationIssue]:
        """Check version consistency for a mapping."""
        try:
            # Get version information from both databases
            qdrant_version = None
            neo4j_version = None

            if mapping.qdrant_point_id:
                qdrant_version = await self._get_qdrant_version(mapping.qdrant_point_id)

            node_identifier = mapping.neo4j_node_id or mapping.neo4j_node_uuid
            if node_identifier:
                neo4j_version = await self._get_neo4j_version(node_identifier)

            if qdrant_version and neo4j_version and qdrant_version != neo4j_version:
                return ValidationIssue(
                    category=ValidationCategory.VERSION_INCONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    title="Version Mismatch",
                    description=f"Version mismatch between QDrant ({qdrant_version}) and Neo4j ({neo4j_version})",
                    mapping_id=mapping.mapping_id,
                    qdrant_point_id=mapping.qdrant_point_id,
                    neo4j_node_id=mapping.neo4j_node_id,
                    expected_value=neo4j_version,
                    actual_value=qdrant_version,
                    suggested_actions=[RepairAction.SYNC_ENTITIES],
                    auto_repairable=True,
                    repair_priority=4,
                    metadata={
                        "qdrant_version": qdrant_version,
                        "neo4j_version": neo4j_version,
                    },
                )

        except Exception as e:
            logger.warning(f"Error checking version consistency: {e}")

        return None

    async def _get_qdrant_version(self, point_id: str) -> Optional[str]:
        """Get version information from QDrant point."""
        try:
            client = self.qdrant_manager._ensure_client_connected()
            points = client.retrieve(
                collection_name=self.qdrant_manager.collection_name,
                ids=[point_id],
                with_payload=True,
            )

            if points and points[0].payload:
                return points[0].payload.get("version")

        except Exception as e:
            logger.warning(f"Error getting QDrant version: {e}")

        return None

    async def _get_neo4j_version(self, node_identifier: str) -> Optional[str]:
        """Get version information from Neo4j node."""
        try:
            if node_identifier.isdigit():
                query = "MATCH (n) WHERE id(n) = $node_id RETURN n.version as version"
                params = {"node_id": int(node_identifier)}
            else:
                query = "MATCH (n {uuid: $node_uuid}) RETURN n.version as version"
                params = {"node_uuid": node_identifier}

            results = self.neo4j_manager.execute_read_query(query, params)
            if results:
                return results[0].get("version")

        except Exception as e:
            logger.warning(f"Error getting Neo4j version: {e}")

        return None

    async def _check_neo4j_constraints(self) -> List[ValidationIssue]:
        """Check Neo4j database constraints."""
        issues = []

        try:
            # Check for constraint violations
            constraint_query = "SHOW CONSTRAINTS"
            try:
                constraints = self.neo4j_manager.execute_read_query(
                    constraint_query, {}
                )
                # Add specific constraint validation logic here
            except Exception:
                # Fallback for older Neo4j versions
                pass

        except Exception as e:
            logger.warning(f"Error checking Neo4j constraints: {e}")

        return issues

    async def _check_qdrant_constraints(self) -> List[ValidationIssue]:
        """Check QDrant database constraints."""
        issues = []

        try:
            client = self.qdrant_manager._ensure_client_connected()

            # Check collection health
            collection_info = client.get_collection(self.qdrant_manager.collection_name)

            if collection_info.status != "green":
                issue = ValidationIssue(
                    category=ValidationCategory.CONSTRAINT_VIOLATION,
                    severity=ValidationSeverity.ERROR,
                    title="QDrant Collection Health Issue",
                    description=f"Collection status is {collection_info.status}",
                    suggested_actions=[RepairAction.MANUAL_INTERVENTION],
                    auto_repairable=False,
                    repair_priority=9,
                    metadata={"collection_status": collection_info.status},
                )
                issues.append(issue)

        except Exception as e:
            logger.warning(f"Error checking QDrant constraints: {e}")

        return issues

    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics from both databases."""
        metrics = {}

        try:
            # Neo4j metrics
            neo4j_metrics = await self._collect_neo4j_metrics()
            metrics.update(neo4j_metrics)

            # QDrant metrics
            qdrant_metrics = await self._collect_qdrant_metrics()
            metrics.update(qdrant_metrics)

        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")

        return metrics

    async def _collect_neo4j_metrics(self) -> Dict[str, Any]:
        """Collect Neo4j-specific performance metrics."""
        metrics = {}

        try:
            # Query execution time
            start_time = datetime.now(UTC)
            self.neo4j_manager.execute_read_query("RETURN 1", {})
            end_time = datetime.now(UTC)
            metrics["neo4j_query_time_ms"] = (
                end_time - start_time
            ).total_seconds() * 1000

            # Database size
            size_query = """
            CALL apoc.meta.stats() YIELD nodeCount, relCount
            RETURN nodeCount, relCount
            """
            try:
                size_results = self.neo4j_manager.execute_read_query(size_query, {})
                if size_results:
                    metrics["neo4j_node_count"] = size_results[0].get("nodeCount", 0)
                    metrics["neo4j_relationship_count"] = size_results[0].get(
                        "relCount", 0
                    )
            except Exception:
                # Fallback if APOC is not available
                count_query = "MATCH (n) RETURN count(n) as nodeCount"
                count_results = self.neo4j_manager.execute_read_query(count_query, {})
                if count_results:
                    metrics["neo4j_node_count"] = count_results[0]["nodeCount"]

        except Exception as e:
            logger.warning(f"Error collecting Neo4j metrics: {e}")

        return metrics

    async def _collect_qdrant_metrics(self) -> Dict[str, Any]:
        """Collect QDrant-specific performance metrics."""
        metrics = {}

        try:
            client = self.qdrant_manager._ensure_client_connected()

            # Collection info
            collection_info = client.get_collection(self.qdrant_manager.collection_name)
            metrics["qdrant_points_count"] = collection_info.points_count
            metrics["qdrant_vectors_count"] = collection_info.vectors_count

            # Query performance test
            start_time = datetime.now(UTC)
            client.scroll(collection_name=self.qdrant_manager.collection_name, limit=1)
            end_time = datetime.now(UTC)
            metrics["qdrant_query_time_ms"] = (
                end_time - start_time
            ).total_seconds() * 1000

        except Exception as e:
            logger.warning(f"Error collecting QDrant metrics: {e}")

        return metrics
