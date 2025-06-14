"""Temporal knowledge management for tracking information validity and resolving conflicts.

This module provides temporal tracking capabilities to manage when information was valid
versus when it was recorded, with conflict resolution for contradictory information.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from ..utils.logging import LoggingConfig
from .graphiti_manager import GraphitiManager
from .types import ExtractedEntity, ExtractedRelationship, TemporalInfo

logger = LoggingConfig.get_logger(__name__)


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving temporal conflicts."""

    LATEST_WINS = "latest_wins"  # Most recent transaction time wins
    HIGHEST_CONFIDENCE = "highest_confidence"  # Highest confidence score wins
    TEMPORAL_INVALIDATION = "temporal_invalidation"  # Use temporal invalidation
    MANUAL_REVIEW = "manual_review"  # Flag for manual review
    MERGE_ATTRIBUTES = "merge_attributes"  # Merge non-conflicting attributes


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""

    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: str = (
        ""  # "entity_overlap", "relationship_overlap", "attribute_conflict"
    )
    entities_involved: list[str] = field(default_factory=list)  # UUIDs
    relationships_involved: list[str] = field(default_factory=list)  # UUIDs
    conflict_description: str = ""
    resolution_strategy: ConflictResolutionStrategy = (
        ConflictResolutionStrategy.TEMPORAL_INVALIDATION
    )
    resolution_timestamp: datetime | None = None
    resolved: bool = False
    resolution_notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalQuery:
    """Container for temporal query parameters."""

    query_time: datetime | None = None  # Point-in-time query
    time_range_start: datetime | None = None  # Range query start
    time_range_end: datetime | None = None  # Range query end
    include_superseded: bool = False  # Include superseded versions
    version_filter: int | None = None  # Specific version filter
    entity_types: list[str] | None = None  # Filter by entity types
    relationship_types: list[str] | None = None  # Filter by relationship types


class TemporalManager:
    """Manager for temporal knowledge tracking and conflict resolution."""

    def __init__(
        self,
        graphiti_manager: GraphitiManager,
        default_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.TEMPORAL_INVALIDATION,
    ):
        """Initialize the temporal manager.

        Args:
            graphiti_manager: Initialized GraphitiManager instance
            default_strategy: Default conflict resolution strategy
        """
        self.graphiti_manager = graphiti_manager
        self.default_strategy = default_strategy

        # In-memory storage for temporal tracking
        # In a production system, this would be persisted to Neo4j
        self._entities: dict[str, list[ExtractedEntity]] = {}  # UUID -> versions
        self._relationships: dict[str, list[ExtractedRelationship]] = (
            {}
        )  # UUID -> versions
        self._conflicts: dict[str, ConflictInfo] = {}  # conflict_id -> conflict info

        # Indexes for efficient querying
        self._entity_name_index: dict[str, set[str]] = {}  # name -> set of UUIDs
        self._relationship_index: dict[tuple[str, str], set[str]] = (
            {}
        )  # (source, target) -> set of UUIDs

        logger.info(
            f"TemporalManager initialized with strategy: {default_strategy.value}"
        )

    async def add_entity(
        self,
        entity: ExtractedEntity,
        reference_time: datetime | None = None,
        resolve_conflicts: bool = True,
    ) -> tuple[str, list[ConflictInfo]]:
        """Add an entity with temporal tracking and conflict resolution.

        Args:
            entity: Entity to add
            reference_time: Reference time for validity (defaults to now)
            resolve_conflicts: Whether to automatically resolve conflicts

        Returns:
            Tuple of (entity_uuid, list_of_conflicts)
        """
        if reference_time:
            entity.temporal_info.valid_from = reference_time

        # Generate UUID if not provided
        if not entity.entity_uuid:
            entity.entity_uuid = str(uuid.uuid4())

        # Check for conflicts
        conflicts = await self._detect_entity_conflicts(entity)

        if conflicts and resolve_conflicts:
            resolved_conflicts = []
            for conflict in conflicts:
                resolved_conflict = await self._resolve_conflict(conflict, entity)
                resolved_conflicts.append(resolved_conflict)
            conflicts = resolved_conflicts

        # Store the entity
        if entity.entity_uuid not in self._entities:
            self._entities[entity.entity_uuid] = []

        self._entities[entity.entity_uuid].append(entity)

        # Update indexes
        if entity.name not in self._entity_name_index:
            self._entity_name_index[entity.name] = set()
        self._entity_name_index[entity.name].add(entity.entity_uuid)

        logger.debug(f"Added entity {entity.name} with UUID {entity.entity_uuid}")

        return entity.entity_uuid, conflicts

    async def add_relationship(
        self,
        relationship: ExtractedRelationship,
        reference_time: datetime | None = None,
        resolve_conflicts: bool = True,
    ) -> tuple[str, list[ConflictInfo]]:
        """Add a relationship with temporal tracking and conflict resolution.

        Args:
            relationship: Relationship to add
            reference_time: Reference time for validity (defaults to now)
            resolve_conflicts: Whether to automatically resolve conflicts

        Returns:
            Tuple of (relationship_uuid, list_of_conflicts)
        """
        if reference_time:
            relationship.temporal_info.valid_from = reference_time

        # Generate UUID if not provided
        if not relationship.relationship_uuid:
            relationship.relationship_uuid = str(uuid.uuid4())

        # Check for conflicts
        conflicts = await self._detect_relationship_conflicts(relationship)

        if conflicts and resolve_conflicts:
            resolved_conflicts = []
            for conflict in conflicts:
                resolved_conflict = await self._resolve_conflict(conflict, relationship)
                resolved_conflicts.append(resolved_conflict)
            conflicts = resolved_conflicts

        # Store the relationship
        if relationship.relationship_uuid not in self._relationships:
            self._relationships[relationship.relationship_uuid] = []

        self._relationships[relationship.relationship_uuid].append(relationship)

        # Update indexes
        rel_key = (relationship.source_entity, relationship.target_entity)
        if rel_key not in self._relationship_index:
            self._relationship_index[rel_key] = set()
        self._relationship_index[rel_key].add(relationship.relationship_uuid)

        logger.debug(
            f"Added relationship {relationship.relationship_type.value} with UUID {relationship.relationship_uuid}"
        )

        return relationship.relationship_uuid, conflicts

    async def _detect_entity_conflicts(
        self, new_entity: ExtractedEntity
    ) -> list[ConflictInfo]:
        """Detect conflicts with existing entities.

        Args:
            new_entity: New entity to check for conflicts

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check for entities with the same name
        if new_entity.name in self._entity_name_index:
            for existing_uuid in self._entity_name_index[new_entity.name]:
                existing_versions = self._entities[existing_uuid]

                for existing_entity in existing_versions:
                    # Skip if not currently valid
                    if not existing_entity.is_currently_valid():
                        continue

                    # Check for temporal overlap
                    if self._has_temporal_overlap(
                        new_entity.temporal_info, existing_entity.temporal_info
                    ):
                        conflict = ConflictInfo(
                            conflict_type="entity_overlap",
                            entities_involved=[
                                existing_uuid,
                                new_entity.entity_uuid or "",
                            ],
                            conflict_description="Temporal overlap for entity f'{new_entity.name}' between versionsf",
                            resolution_strategy=self.default_strategy,
                            metadata={
                                "new_entity": new_entity.to_dict(),
                                "existing_entity": existing_entity.to_dict(),
                                "overlap_type": "temporal",
                            },
                        )
                        conflicts.append(conflict)

                    # Check for attribute conflicts
                    if (
                        existing_entity.entity_type != new_entity.entity_type
                        or abs(existing_entity.confidence - new_entity.confidence) > 0.3
                    ):
                        conflict = ConflictInfo(
                            conflict_type="attribute_conflict",
                            entities_involved=[
                                existing_uuid,
                                new_entity.entity_uuid or "",
                            ],
                            conflict_description="Attribute conflict for entity f'{new_entity.name}'f",
                            resolution_strategy=self.default_strategy,
                            metadata={
                                "new_entity": new_entity.to_dict(),
                                "existing_entity": existing_entity.to_dict(),
                                "conflict_attributes": ["entity_type", "confidence"],
                            },
                        )
                        conflicts.append(conflict)

        return conflicts

    async def _detect_relationship_conflicts(
        self, new_relationship: ExtractedRelationship
    ) -> list[ConflictInfo]:
        """Detect conflicts with existing relationships.

        Args:
            new_relationship: New relationship to check for conflicts

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check for relationships with the same source and target
        rel_key = (new_relationship.source_entity, new_relationship.target_entity)
        if rel_key in self._relationship_index:
            for existing_uuid in self._relationship_index[rel_key]:
                existing_versions = self._relationships[existing_uuid]

                for existing_relationship in existing_versions:
                    # Skip if not currently valid
                    if not existing_relationship.is_currently_valid():
                        continue

                    # Check for temporal overlap with same relationship type
                    if (
                        existing_relationship.relationship_type
                        == new_relationship.relationship_type
                        and self._has_temporal_overlap(
                            new_relationship.temporal_info,
                            existing_relationship.temporal_info,
                        )
                    ):
                        conflict = ConflictInfo(
                            conflict_type="relationship_overlap",
                            relationships_involved=[
                                existing_uuid,
                                new_relationship.relationship_uuid or "",
                            ],
                            conflict_description=f"Temporal overlap for relationship {new_relationship.relationship_type.value}",
                            resolution_strategy=self.default_strategy,
                            metadata={
                                "new_relationship": new_relationship.to_dict(),
                                "existing_relationship": existing_relationship.to_dict(),
                                "overlap_type": "temporal",
                            },
                        )
                        conflicts.append(conflict)

        return conflicts

    def _has_temporal_overlap(
        self, temporal1: TemporalInfo, temporal2: TemporalInfo
    ) -> bool:
        """Check if two temporal infos have overlapping valid time periods.

        Args:
            temporal1: First temporal info
            temporal2: Second temporal info

        Returns:
            True if there's temporal overlap, False otherwise
        """
        # Get end times (use current time if None)
        end1 = temporal1.valid_to or datetime.now(UTC)
        end2 = temporal2.valid_to or datetime.now(UTC)

        # Check for overlap: start1 < end2 and start2 < end1
        return temporal1.valid_from < end2 and temporal2.valid_from < end1

    async def _resolve_conflict(
        self,
        conflict: ConflictInfo,
        new_item: Any,  # ExtractedEntity or ExtractedRelationship
    ) -> ConflictInfo:
        """Resolve a detected conflict using the specified strategy.

        Args:
            conflict: Conflict to resolve
            new_item: New entity or relationship causing the conflict

        Returns:
            Updated conflict info with resolution details
        """
        logger.info(
            f"Resolving conflict {conflict.conflict_id} using strategy {conflict.resolution_strategy.value}"
        )

        try:
            if (
                conflict.resolution_strategy
                == ConflictResolutionStrategy.TEMPORAL_INVALIDATION
            ):
                await self._resolve_with_temporal_invalidation(conflict, new_item)
            elif conflict.resolution_strategy == ConflictResolutionStrategy.LATEST_WINS:
                await self._resolve_with_latest_wins(conflict, new_item)
            elif (
                conflict.resolution_strategy
                == ConflictResolutionStrategy.HIGHEST_CONFIDENCE
            ):
                await self._resolve_with_highest_confidence(conflict, new_item)
            elif (
                conflict.resolution_strategy
                == ConflictResolutionStrategy.MERGE_ATTRIBUTES
            ):
                await self._resolve_with_merge_attributes(conflict, new_item)
            else:
                # Manual review - just flag the conflict
                conflict.resolution_notes = "Flagged for manual review"

            conflict.resolved = True
            conflict.resolution_timestamp = datetime.now(UTC)
            self._conflicts[conflict.conflict_id] = conflict

        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict.conflict_id}: {e}")
            conflict.resolution_notes = f"Resolution failed: {e}"

        return conflict

    async def _resolve_with_temporal_invalidation(
        self, conflict: ConflictInfo, new_item: Any
    ) -> None:
        """Resolve conflict by invalidating older versions at the new item's valid_from time."""
        invalidation_time = new_item.temporal_info.valid_from

        # Invalidate conflicting entities
        for entity_uuid in conflict.entities_involved:
            if entity_uuid and entity_uuid in self._entities:
                for entity in self._entities[entity_uuid]:
                    if entity.is_valid_at(invalidation_time):
                        entity.temporal_info.invalidate_at(invalidation_time)

        # Invalidate conflicting relationships
        for rel_uuid in conflict.relationships_involved:
            if rel_uuid and rel_uuid in self._relationships:
                for relationship in self._relationships[rel_uuid]:
                    if relationship.is_valid_at(invalidation_time):
                        relationship.temporal_info.invalidate_at(invalidation_time)

        conflict.resolution_notes = (
            f"Invalidated conflicting items at {invalidation_time.isoformat()}"
        )

    async def _resolve_with_latest_wins(
        self, conflict: ConflictInfo, new_item: Any
    ) -> None:
        """Resolve conflict by keeping the item with the latest transaction time."""
        latest_transaction_time = new_item.temporal_info.transaction_time

        # Find the item with the latest transaction time
        winner = new_item

        # Check entities
        for entity_uuid in conflict.entities_involved:
            if entity_uuid and entity_uuid in self._entities:
                for entity in self._entities[entity_uuid]:
                    if entity.temporal_info.transaction_time > latest_transaction_time:
                        latest_transaction_time = entity.temporal_info.transaction_time
                        winner = entity

        # Check relationships
        for rel_uuid in conflict.relationships_involved:
            if rel_uuid and rel_uuid in self._relationships:
                for relationship in self._relationships[rel_uuid]:
                    if (
                        relationship.temporal_info.transaction_time
                        > latest_transaction_time
                    ):
                        latest_transaction_time = (
                            relationship.temporal_info.transaction_time
                        )
                        winner = relationship

        # Invalidate all others
        winner.temporal_info.valid_from
        await self._resolve_with_temporal_invalidation(conflict, winner)

        conflict.resolution_notes = (
            f"Latest wins: {winner.temporal_info.transaction_time.isoformat()}"
        )

    async def _resolve_with_highest_confidence(
        self, conflict: ConflictInfo, new_item: Any
    ) -> None:
        """Resolve conflict by keeping the item with the highest confidence score."""
        highest_confidence = getattr(new_item, "confidence", 0.0)
        winner = new_item

        # Check entities
        for entity_uuid in conflict.entities_involved:
            if entity_uuid and entity_uuid in self._entities:
                for entity in self._entities[entity_uuid]:
                    if entity.confidence > highest_confidence:
                        highest_confidence = entity.confidence
                        winner = entity

        # Check relationships
        for rel_uuid in conflict.relationships_involved:
            if rel_uuid and rel_uuid in self._relationships:
                for relationship in self._relationships[rel_uuid]:
                    if relationship.confidence > highest_confidence:
                        highest_confidence = relationship.confidence
                        winner = relationship

        # Invalidate all others
        await self._resolve_with_temporal_invalidation(conflict, winner)

        conflict.resolution_notes = f"Highest confidence wins: {highest_confidence}"

    async def _resolve_with_merge_attributes(
        self, conflict: ConflictInfo, new_item: Any
    ) -> None:
        """Resolve conflict by merging non-conflicting attributes."""
        # This is a simplified merge strategy
        # In practice, this would need more sophisticated logic
        conflict.resolution_notes = (
            "Merged non-conflicting attributes (simplified implementation)"
        )

    async def query_entities_at_time(
        self, query: TemporalQuery
    ) -> list[ExtractedEntity]:
        """Query entities as they existed at a specific point in time.

        Args:
            query: Temporal query parameters

        Returns:
            List of entities valid at the specified time
        """
        results = []
        query_time = query.query_time or datetime.now(UTC)

        for entity_uuid, versions in self._entities.items():
            for entity in versions:
                # Check if entity was valid at query time
                if entity.is_valid_at(query_time):
                    # Apply filters
                    if (
                        query.entity_types
                        and entity.entity_type.value not in query.entity_types
                    ):
                        continue
                    if (
                        query.version_filter
                        and entity.temporal_info.version != query.version_filter
                    ):
                        continue

                    results.append(entity)
                elif query.include_superseded:
                    results.append(entity)

        return results

    async def query_relationships_at_time(
        self, query: TemporalQuery
    ) -> list[ExtractedRelationship]:
        """Query relationships as they existed at a specific point in time.

        Args:
            query: Temporal query parameters

        Returns:
            List of relationships valid at the specified time
        """
        results = []
        query_time = query.query_time or datetime.now(UTC)

        for rel_uuid, versions in self._relationships.items():
            for relationship in versions:
                # Check if relationship was valid at query time
                if relationship.is_valid_at(query_time):
                    # Apply filters
                    if (
                        query.relationship_types
                        and relationship.relationship_type.value
                        not in query.relationship_types
                    ):
                        continue
                    if (
                        query.version_filter
                        and relationship.temporal_info.version != query.version_filter
                    ):
                        continue

                    results.append(relationship)
                elif query.include_superseded:
                    results.append(relationship)

        return results

    async def query_entities_in_range(
        self, query: TemporalQuery
    ) -> list[ExtractedEntity]:
        """Query entities that were valid during a time range.

        Args:
            query: Temporal query parameters with time range

        Returns:
            List of entities valid during the specified range
        """
        if not query.time_range_start or not query.time_range_end:
            raise ValueError("Time range start and end must be specified")

        results = []

        for entity_uuid, versions in self._entities.items():
            for entity in versions:
                # Check if entity's valid period overlaps with query range
                entity_end = entity.temporal_info.valid_to or datetime.now(UTC)

                if (
                    entity.temporal_info.valid_from < query.time_range_end
                    and entity_end > query.time_range_start
                ):

                    # Apply filters
                    if (
                        query.entity_types
                        and entity.entity_type.value not in query.entity_types
                    ):
                        continue
                    if (
                        query.version_filter
                        and entity.temporal_info.version != query.version_filter
                    ):
                        continue

                    results.append(entity)

        return results

    def get_entity_history(self, entity_uuid: str) -> list[ExtractedEntity]:
        """Get the complete history of an entity.

        Args:
            entity_uuid: UUID of the entity

        Returns:
            List of all versions of the entity, sorted by version
        """
        if entity_uuid not in self._entities:
            return []

        versions = self._entities[entity_uuid]
        return sorted(versions, key=lambda e: e.temporal_info.version)

    def get_relationship_history(
        self, relationship_uuid: str
    ) -> list[ExtractedRelationship]:
        """Get the complete history of a relationship.

        Args:
            relationship_uuid: UUID of the relationship

        Returns:
            List of all versions of the relationship, sorted by version
        """
        if relationship_uuid not in self._relationships:
            return []

        versions = self._relationships[relationship_uuid]
        return sorted(versions, key=lambda r: r.temporal_info.version)

    def get_conflicts(self, resolved: bool | None = None) -> list[ConflictInfo]:
        """Get conflict information.

        Args:
            resolved: Filter by resolution status (None for all)

        Returns:
            List of conflicts matching the filter
        """
        conflicts = list(self._conflicts.values())

        if resolved is not None:
            conflicts = [c for c in conflicts if c.resolved == resolved]

        return conflicts

    def get_statistics(self) -> dict[str, Any]:
        """Get temporal manager statistics.

        Returns:
            Dictionary containing statistics
        """
        total_entities = sum(len(versions) for versions in self._entities.values())
        total_relationships = sum(
            len(versions) for versions in self._relationships.values()
        )

        current_entities = 0
        current_relationships = 0

        for versions in self._entities.values():
            for entity in versions:
                if entity.is_currently_valid():
                    current_entities += 1

        for versions in self._relationships.values():
            for relationship in versions:
                if relationship.is_currently_valid():
                    current_relationships += 1

        return {
            "total_entities": total_entities,
            "current_entities": current_entities,
            "total_relationships": total_relationships,
            "current_relationships": current_relationships,
            "total_conflicts": len(self._conflicts),
            "resolved_conflicts": len(
                [c for c in self._conflicts.values() if c.resolved]
            ),
            "unresolved_conflicts": len(
                [c for c in self._conflicts.values() if not c.resolved]
            ),
            "unique_entity_uuids": len(self._entities),
            "unique_relationship_uuids": len(self._relationships),
        }

    # Enhanced Versioning Capabilities

    def validate_version_chains(self) -> dict[str, list[str]]:
        """Validate version chains for all entities and relationships.

        Returns:
            Dictionary with validation errors by UUID
        """
        errors = {}

        # Validate entity version chains
        for entity_uuid, versions in self._entities.items():
            chain_errors = self._validate_entity_version_chain(versions)
            if chain_errors:
                errors[f"entity_{entity_uuid}"] = chain_errors

        # Validate relationship version chains
        for rel_uuid, versions in self._relationships.items():
            chain_errors = self._validate_relationship_version_chain(versions)
            if chain_errors:
                errors[f"relationship_{rel_uuid}"] = chain_errors

        return errors

    def _validate_entity_version_chain(
        self, versions: list[ExtractedEntity]
    ) -> list[str]:
        """Validate version chain for a single entity.

        Args:
            versions: List of entity versions

        Returns:
            List of validation errors
        """
        errors = []
        sorted_versions = sorted(versions, key=lambda e: e.temporal_info.version)

        # Check version sequence
        for i, version in enumerate(sorted_versions):
            expected_version = i + 1
            if version.temporal_info.version != expected_version:
                errors.append(
                    f"Version sequence broken: expected {expected_version}, got {version.temporal_info.version}"
                )

            # Check supersession chain
            if i > 0:
                prev_version = sorted_versions[i - 1]
                if prev_version.temporal_info.superseded_by != version.entity_uuid:
                    errors.append(
                        f"Supersession chain broken at version {version.temporal_info.version}"
                    )
                if version.temporal_info.supersedes != prev_version.entity_uuid:
                    errors.append(
                        f"Reverse supersession chain broken at version {version.temporal_info.version}"
                    )

        return errors

    def _validate_relationship_version_chain(
        self, versions: list[ExtractedRelationship]
    ) -> list[str]:
        """Validate version chain for a single relationship.

        Args:
            versions: List of relationship versions

        Returns:
            List of validation errors
        """
        errors = []
        sorted_versions = sorted(versions, key=lambda r: r.temporal_info.version)

        # Check version sequence
        for i, version in enumerate(sorted_versions):
            expected_version = i + 1
            if version.temporal_info.version != expected_version:
                errors.append(
                    f"Version sequence broken: expected {expected_version}, got {version.temporal_info.version}"
                )

            # Check supersession chain
            if i > 0:
                prev_version = sorted_versions[i - 1]
                if (
                    prev_version.temporal_info.superseded_by
                    != version.relationship_uuid
                ):
                    errors.append(
                        f"Supersession chain broken at version {version.temporal_info.version}"
                    )
                if version.temporal_info.supersedes != prev_version.relationship_uuid:
                    errors.append(
                        f"Reverse supersession chain broken at version {version.temporal_info.version}"
                    )

        return errors

    def repair_version_chains(self) -> dict[str, int]:
        """Repair broken version chains.

        Returns:
            Dictionary with repair counts by type
        """
        repairs = {"entities": 0, "relationships": 0}

        # Repair entity version chains
        for entity_uuid, versions in self._entities.items():
            if self._repair_entity_version_chain(versions):
                repairs["entities"] += 1

        # Repair relationship version chains
        for rel_uuid, versions in self._relationships.items():
            if self._repair_relationship_version_chain(versions):
                repairs["relationships"] += 1

        logger.info(
            "Repaired {repairs['entities']} entity chains and {repairs['relationships']} relationship chains"
        )
        return repairs

    def _repair_entity_version_chain(self, versions: list[ExtractedEntity]) -> bool:
        """Repair version chain for a single entity.

        Args:
            versions: List of entity versions

        Returns:
            True if repairs were made, False otherwise
        """
        if len(versions) <= 1:
            return False

        repaired = False
        sorted_versions = sorted(
            versions, key=lambda e: e.temporal_info.transaction_time
        )

        # Fix version numbers
        for i, version in enumerate(sorted_versions):
            expected_version = i + 1
            if version.temporal_info.version != expected_version:
                version.temporal_info.version = expected_version
                repaired = True

        # Fix supersession chains
        for i in range(len(sorted_versions)):
            if i > 0:
                prev_version = sorted_versions[i - 1]
                current_version = sorted_versions[i]

                if (
                    prev_version.temporal_info.superseded_by
                    != current_version.entity_uuid
                ):
                    prev_version.temporal_info.superseded_by = (
                        current_version.entity_uuid
                    )
                    repaired = True

                if current_version.temporal_info.supersedes != prev_version.entity_uuid:
                    current_version.temporal_info.supersedes = prev_version.entity_uuid
                    repaired = True

        return repaired

    def _repair_relationship_version_chain(
        self, versions: list[ExtractedRelationship]
    ) -> bool:
        """Repair version chain for a single relationship.

        Args:
            versions: List of relationship versions

        Returns:
            True if repairs were made, False otherwise
        """
        if len(versions) <= 1:
            return False

        repaired = False
        sorted_versions = sorted(
            versions, key=lambda r: r.temporal_info.transaction_time
        )

        # Fix version numbers
        for i, version in enumerate(sorted_versions):
            expected_version = i + 1
            if version.temporal_info.version != expected_version:
                version.temporal_info.version = expected_version
                repaired = True

        # Fix supersession chains
        for i in range(len(sorted_versions)):
            if i > 0:
                prev_version = sorted_versions[i - 1]
                current_version = sorted_versions[i]

                if (
                    prev_version.temporal_info.superseded_by
                    != current_version.relationship_uuid
                ):
                    prev_version.temporal_info.superseded_by = (
                        current_version.relationship_uuid
                    )
                    repaired = True

                if (
                    current_version.temporal_info.supersedes
                    != prev_version.relationship_uuid
                ):
                    current_version.temporal_info.supersedes = (
                        prev_version.relationship_uuid
                    )
                    repaired = True

        return repaired

    async def rollback_entity_to_version(
        self, entity_uuid: str, target_version: int
    ) -> ExtractedEntity | None:
        """Rollback an entity to a specific version.

        Args:
            entity_uuid: UUID of the entity
            target_version: Version to rollback to

        Returns:
            The rolled-back entity version, or None if not found
        """
        if entity_uuid not in self._entities:
            logger.warning(f"Entity {entity_uuid} not found for rollback")
            return None

        versions = self._entities[entity_uuid]
        target_entity = None

        # Find target version
        for entity in versions:
            if entity.temporal_info.version == target_version:
                target_entity = entity
                break

        if not target_entity:
            logger.warning(
                f"Version {target_version} not found for entity {entity_uuid}"
            )
            return None

        # Invalidate all versions after target version
        rollback_time = datetime.now(UTC)
        for entity in versions:
            if entity.temporal_info.version > target_version:
                entity.temporal_info.invalidate_at(rollback_time)

        # Create new version based on target version
        rollback_entity = ExtractedEntity(
            name=target_entity.name,
            entity_type=target_entity.entity_type,
            confidence=target_entity.confidence,
            context=target_entity.context,
            metadata=target_entity.metadata.copy(),
            entity_uuid=entity_uuid,
        )

        # Set up temporal info for rollback version
        max_version = max(e.temporal_info.version for e in versions)
        rollback_entity.temporal_info = TemporalInfo(
            valid_from=rollback_time,
            transaction_time=rollback_time,
            version=max_version + 1,
            supersedes=entity_uuid,
        )

        # Add rollback version
        versions.append(rollback_entity)

        logger.info(f"Rolled back entity {entity_uuid} to version {target_version}")
        return rollback_entity

    async def rollback_relationship_to_version(
        self, relationship_uuid: str, target_version: int
    ) -> ExtractedRelationship | None:
        """Rollback a relationship to a specific version.

        Args:
            relationship_uuid: UUID of the relationship
            target_version: Version to rollback to

        Returns:
            The rolled-back relationship version, or None if not found
        """
        if relationship_uuid not in self._relationships:
            logger.warning(f"Relationship {relationship_uuid} not found for rollback")
            return None

        versions = self._relationships[relationship_uuid]
        target_relationship = None

        # Find target version
        for relationship in versions:
            if relationship.temporal_info.version == target_version:
                target_relationship = relationship
                break

        if not target_relationship:
            logger.warning(
                f"Version {target_version} not found for relationship {relationship_uuid}"
            )
            return None

        # Invalidate all versions after target version
        rollback_time = datetime.now(UTC)
        for relationship in versions:
            if relationship.temporal_info.version > target_version:
                relationship.temporal_info.invalidate_at(rollback_time)

        # Create new version based on target relationship
        rollback_relationship = ExtractedRelationship(
            source_entity=target_relationship.source_entity,
            target_entity=target_relationship.target_entity,
            relationship_type=target_relationship.relationship_type,
            confidence=target_relationship.confidence,
            context=target_relationship.context,
            evidence=target_relationship.evidence,
            metadata=target_relationship.metadata.copy(),
            relationship_uuid=relationship_uuid,
            source_entity_uuid=target_relationship.source_entity_uuid,
            target_entity_uuid=target_relationship.target_entity_uuid,
        )

        # Set up temporal info for rollback version
        max_version = max(r.temporal_info.version for r in versions)
        rollback_relationship.temporal_info = TemporalInfo(
            valid_from=rollback_time,
            transaction_time=rollback_time,
            version=max_version + 1,
            supersedes=relationship_uuid,
        )

        # Add rollback version
        versions.append(rollback_relationship)

        logger.info(
            f"Rolled back relationship {relationship_uuid} to version {target_version}"
        )
        return rollback_relationship

    def compare_entity_versions(
        self, entity_uuid: str, version1: int, version2: int
    ) -> dict[str, Any] | None:
        """Compare two versions of an entity.

        Args:
            entity_uuid: UUID of the entity
            version1: First version to compare
            version2: Second version to compare

        Returns:
            Dictionary containing comparison results, or None if versions not found
        """
        if entity_uuid not in self._entities:
            return None

        versions = self._entities[entity_uuid]
        entity1 = entity2 = None

        for entity in versions:
            if entity.temporal_info.version == version1:
                entity1 = entity
            elif entity.temporal_info.version == version2:
                entity2 = entity

        if not entity1 or not entity2:
            return None

        return {
            "entity_uuid": entity_uuid,
            "version1": version1,
            "version2": version2,
            "differences": {
                "name": {
                    "v1": entity1.name,
                    "v2": entity2.name,
                    "changed": entity1.name != entity2.name,
                },
                "entity_typef": {
                    "v1": entity1.entity_type.value,
                    "v2": entity2.entity_type.value,
                    "changed": entity1.entity_type != entity2.entity_type,
                },
                "confidencef": {
                    "v1": entity1.confidence,
                    "v2": entity2.confidence,
                    "changed": abs(entity1.confidence - entity2.confidence) > 0.001,
                },
                "contextf": {
                    "v1": entity1.context,
                    "v2": entity2.context,
                    "changed": entity1.context != entity2.context,
                },
                "metadataf": {
                    "v1": entity1.metadata,
                    "v2": entity2.metadata,
                    "changed": entity1.metadata != entity2.metadata,
                },
            },
            "temporal_infof": {
                "v1": entity1.temporal_info.to_dict(),
                "v2": entity2.temporal_info.to_dict(),
            },
        }

    def compare_relationship_versions(
        self, relationship_uuid: str, version1: int, version2: int
    ) -> dict[str, Any] | None:
        """Compare two versions of a relationship.

        Args:
            relationship_uuid: UUID of the relationship
            version1: First version to compare
            version2: Second version to compare

        Returns:
            Dictionary containing comparison results, or None if versions not found
        """
        if relationship_uuid not in self._relationships:
            return None

        versions = self._relationships[relationship_uuid]
        rel1 = rel2 = None

        for relationship in versions:
            if relationship.temporal_info.version == version1:
                rel1 = relationship
            elif relationship.temporal_info.version == version2:
                rel2 = relationship

        if not rel1 or not rel2:
            return None

        return {
            "relationship_uuid": relationship_uuid,
            "version1": version1,
            "version2": version2,
            "differences": {
                "source_entity": {
                    "v1": rel1.source_entity,
                    "v2": rel2.source_entity,
                    "changed": rel1.source_entity != rel2.source_entity,
                },
                "target_entityf": {
                    "v1": rel1.target_entity,
                    "v2": rel2.target_entity,
                    "changed": rel1.target_entity != rel2.target_entity,
                },
                "relationship_typef": {
                    "v1": rel1.relationship_type.value,
                    "v2": rel2.relationship_type.value,
                    "changed": rel1.relationship_type != rel2.relationship_type,
                },
                "confidencef": {
                    "v1": rel1.confidence,
                    "v2": rel2.confidence,
                    "changed": abs(rel1.confidence - rel2.confidence) > 0.001,
                },
                "contextf": {
                    "v1": rel1.context,
                    "v2": rel2.context,
                    "changed": rel1.context != rel2.context,
                },
                "evidencef": {
                    "v1": rel1.evidence,
                    "v2": rel2.evidence,
                    "changed": rel1.evidence != rel2.evidence,
                },
                "metadataf": {
                    "v1": rel1.metadata,
                    "v2": rel2.metadata,
                    "changed": rel1.metadata != rel2.metadata,
                },
            },
            "temporal_infof": {
                "v1": rel1.temporal_info.to_dict(),
                "v2": rel2.temporal_info.to_dict(),
            },
        }

    async def bulk_rollback_entities(
        self, rollback_operations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Perform bulk rollback operations on multiple entities.

        Args:
            rollback_operations: List of rollback operations, each containing
                                'entity_uuid' and 'target_version'

        Returns:
            Dictionary with results of bulk operation
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(rollback_operations),
        }

        for operation in rollback_operations:
            entity_uuid = operation.get("entity_uuid")
            target_version = operation.get("target_version")

            if not entity_uuid or target_version is None:
                results["failedf"].append(
                    {
                        "entity_uuid": entity_uuid,
                        "error": "Missing entity_uuid or target_version",
                    }
                )
                continue

            try:
                rolled_back = await self.rollback_entity_to_version(
                    entity_uuid, target_version
                )
                if rolled_back:
                    results["successfulf"].append(
                        {
                            "entity_uuid": entity_uuid,
                            "target_version": target_version,
                            "new_version": rolled_back.temporal_info.version,
                        }
                    )
                else:
                    results["failedf"].append(
                        {
                            "entity_uuid": entity_uuid,
                            "error": "Rollback failed - entity or version not found",
                        }
                    )
            except Exception as e:
                results["failedf"].append(
                    {
                        "entity_uuid": entity_uuid,
                        "error": str(e),
                    }
                )

        logger.info(
            "Bulk rollback completed: {len(results['successful'])} successful, {len(results['failed'])} failed"
        )
        return results

    def prune_old_versions(self, retention_policy: dict[str, Any]) -> dict[str, int]:
        """Prune old versions based on retention policy.

        Args:
            retention_policy: Dictionary containing retention rules:
                - max_versions: Maximum number of versions to keep per entity/relationship
                - max_age_days: Maximum age in days for versions
                - keep_milestones: Whether to keep milestone versions

        Returns:
            Dictionary with pruning statistics
        """
        max_versions = retention_policy.get("max_versions", 10)
        max_age_days = retention_policy.get("max_age_days", 365)
        keep_milestones = retention_policy.get("keep_milestonesf", True)

        cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
        pruned = {"entities": 0, "relationships": 0}

        # Prune entity versions
        for entity_uuid, versions in self._entities.items():
            original_count = len(versions)
            versions[:] = self._prune_versions(
                versions, max_versions, cutoff_date, keep_milestones
            )
            pruned["entities"] += original_count - len(versions)

        # Prune relationship versions
        for rel_uuid, versions in self._relationships.items():
            original_count = len(versions)
            versions[:] = self._prune_versions(
                versions, max_versions, cutoff_date, keep_milestones
            )
            pruned["relationships"] += original_count - len(versions)

        logger.info(
            "Pruned {pruned['entities']} entity versions and {pruned['relationships']} relationship versions"
        )
        return pruned

    def _prune_versions(
        self,
        versions: list[Any],
        max_versions: int,
        cutoff_date: datetime,
        keep_milestones: bool,
    ) -> list[Any]:
        """Prune versions based on retention policy.

        Args:
            versions: List of versions to prune
            max_versions: Maximum versions to keep
            cutoff_date: Cutoff date for age-based pruning
            keep_milestones: Whether to keep milestone versions

        Returns:
            Pruned list of versions
        """
        if len(versions) <= 1:
            return versions

        # Sort by version number (newest first)
        sorted_versions = sorted(
            versions, key=lambda v: v.temporal_info.version, reverse=True
        )

        # Always keep the current version
        kept_versions = [sorted_versions[0]]

        # Apply retention rules to remaining versions
        for version in sorted_versions[1:]:
            # Check age limit
            if version.temporal_info.transaction_time < cutoff_date:
                continue

            # Check version count limit
            if len(kept_versions) >= max_versions:
                # If keeping milestones, check if this is a milestone version
                if keep_milestones and self._is_milestone_version(version):
                    kept_versions.append(version)
                continue

            kept_versions.append(version)

        return kept_versions

    def _is_milestone_version(self, version: Any) -> bool:
        """Check if a version is considered a milestone.

        Args:
            version: Version to check

        Returns:
            True if this is a milestone version
        """
        # Consider first version and every 10th version as milestones
        return (
            version.temporal_info.version == 1
            or version.temporal_info.version % 10 == 0
        )
