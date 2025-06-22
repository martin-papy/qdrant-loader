"""Comprehensive tests for the temporal tracking system.

This module tests all temporal tracking features including:
- Temporal field accuracy
- Conflict resolution
- Versioning mechanisms
- Historical queries
- Timezone handling
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from qdrant_loader.core.managers.temporal_manager import (
    TemporalManager,
    TemporalQuery,
)
from qdrant_loader.core.types import (
    EntityType,
    ExtractedEntity,
    ExtractedRelationship,
    RelationshipType,
    TemporalInfo,
)
from qdrant_loader.utils.timezone_utils import TimezoneError, TimezoneUtils


class TestTemporalInfo:
    """Test TemporalInfo class functionality."""

    def test_temporal_info_creation(self):
        """Test basic TemporalInfo creation and defaults."""
        temporal_info = TemporalInfo()

        assert temporal_info.valid_from is not None
        assert temporal_info.valid_to is None
        assert temporal_info.transaction_time is not None
        assert temporal_info.version == 1
        assert temporal_info.superseded_by is None
        assert temporal_info.supersedes is None

    def test_temporal_info_validity_checks(self):
        """Test temporal validity checking methods."""
        now = datetime.now(UTC)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        # Currently valid temporal info
        temporal_info = TemporalInfo(valid_from=past)
        assert temporal_info.is_valid_at(now)
        assert temporal_info.is_currently_valid()

        # Future temporal info
        temporal_info = TemporalInfo(valid_from=future)
        assert not temporal_info.is_valid_at(now)
        assert not temporal_info.is_currently_valid()

        # Expired temporal info
        temporal_info = TemporalInfo(valid_from=past, valid_to=now)
        assert temporal_info.is_valid_at(past + timedelta(minutes=30))
        assert not temporal_info.is_valid_at(now)
        assert not temporal_info.is_currently_valid()

    def test_temporal_info_invalidation(self):
        """Test temporal invalidation functionality."""
        temporal_info = TemporalInfo()
        invalidation_time = datetime.now(UTC) + timedelta(hours=1)

        temporal_info.invalidate_at(invalidation_time)
        assert temporal_info.valid_to == invalidation_time

    def test_temporal_info_serialization(self):
        """Test temporal info to_dict and from_dict methods."""
        original = TemporalInfo(
            valid_from=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            valid_to=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
            transaction_time=datetime(2023, 6, 15, 10, 30, 0, tzinfo=UTC),
            version=5,
            superseded_by="uuid-123",
            supersedes="uuid-456",
        )

        # Test serialization
        data = original.to_dict()
        assert "valid_from" in data
        assert "valid_to" in data
        assert "transaction_time" in data
        assert data["version"] == 5
        assert data["superseded_by"] == "uuid-123"
        assert data["supersedes"] == "uuid-456"

        # Test deserialization
        restored = TemporalInfo.from_dict(data)
        assert restored.valid_from == original.valid_from
        assert restored.valid_to == original.valid_to
        assert restored.transaction_time == original.transaction_time
        assert restored.version == original.version
        assert restored.superseded_by == original.superseded_by
        assert restored.supersedes == original.supersedes

    def test_temporal_info_timezone_methods(self):
        """Test timezone conversion methods in TemporalInfo."""
        temporal_info = TemporalInfo(
            valid_from=datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)
        )

        # Test timezone conversion
        est_time = temporal_info.get_valid_from_in_timezone("America/New_York")
        assert est_time is not None
        assert est_time.hour == 8  # UTC 12:00 -> EST 08:00 (during DST)

        # Test formatting
        formatted = temporal_info.format_for_timezone("America/New_York")
        assert "valid_from" in formatted
        assert "valid_to" in formatted
        assert "transaction_time" in formatted

        # Test setting from timezone
        temporal_info.set_valid_from_from_timezone(
            "2023-06-15 14:00:00", "America/New_York"
        )
        # Should be converted to UTC (14:00 EST -> 18:00 UTC during DST)
        assert temporal_info.valid_from.hour == 18


class TestTimezoneUtils:
    """Test TimezoneUtils functionality."""

    def test_timezone_validation(self):
        """Test timezone validation and normalization."""
        # Valid timezones
        assert TimezoneUtils.validate_timezone("UTC") == "UTC"
        assert TimezoneUtils.validate_timezone("America/New_York") == "America/New_York"
        assert TimezoneUtils.validate_timezone("EST") == "America/New_York"  # Alias

        # Invalid timezone
        with pytest.raises(TimezoneError):
            TimezoneUtils.validate_timezone("Invalid/Timezone")

        # Empty timezone
        with pytest.raises(TimezoneError):
            TimezoneUtils.validate_timezone("")

    def test_utc_conversion(self):
        """Test UTC conversion utilities."""
        # Naive datetime (assumed UTC)
        naive_dt = datetime(2023, 6, 15, 12, 0, 0)
        utc_dt = TimezoneUtils.ensure_utc(naive_dt)
        assert utc_dt is not None
        assert utc_dt.tzinfo == UTC

        # Already UTC datetime
        utc_original = datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)
        utc_result = TimezoneUtils.ensure_utc(utc_original)
        assert utc_result == utc_original

        # None input - test that method signature allows None but returns None
        # Note: This tests the method's behavior with None input
        result = TimezoneUtils.ensure_utc(None)  # type: ignore
        assert result is None

    def test_timezone_conversion(self):
        """Test timezone conversion methods."""
        utc_dt = datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)

        # Convert to EST
        est_dt = TimezoneUtils.convert_to_timezone(utc_dt, "America/New_York")
        assert est_dt is not None
        assert est_dt.hour == 8  # UTC 12:00 -> EST 08:00 (during DST)

        # Convert from EST to UTC
        est_naive = datetime(2023, 6, 15, 8, 0, 0)
        utc_converted = TimezoneUtils.convert_from_timezone(
            est_naive, "America/New_York"
        )
        assert utc_converted is not None
        assert utc_converted.hour == 12  # EST 08:00 -> UTC 12:00 (during DST)

    def test_dst_transition_detection(self):
        """Test DST transition detection."""
        # Spring forward (2023-03-12 in US)
        spring_dt = datetime(2023, 3, 12, 2, 30, 0)
        dst_info = TimezoneUtils.is_dst_transition(spring_dt, "America/New_York")
        assert dst_info["is_transition"]
        assert dst_info["transition_type"] == "spring_forward"

        # Fall back (2023-11-05 in US)
        fall_dt = datetime(2023, 11, 5, 1, 30, 0)
        dst_info = TimezoneUtils.is_dst_transition(fall_dt, "America/New_York")
        assert dst_info["is_transition"]
        assert dst_info["transition_type"] == "fall_back"

        # Regular time (no transition)
        regular_dt = datetime(2023, 6, 15, 12, 0, 0)
        dst_info = TimezoneUtils.is_dst_transition(regular_dt, "America/New_York")
        assert not dst_info["is_transition"]

    def test_timezone_info_retrieval(self):
        """Test timezone information retrieval."""
        # UTC info
        utc_info = TimezoneUtils.get_timezone_info("UTC")
        assert utc_info["timezone"] == "UTC"
        assert utc_info["current_offset"] == "+00:00"
        assert not utc_info["dst_active"]

        # EST info
        est_info = TimezoneUtils.get_timezone_info("America/New_York")
        assert est_info["timezone"] == "America/New_York"
        assert "current_offset" in est_info
        assert "dst_active" in est_info

    def test_datetime_formatting_and_parsing(self):
        """Test datetime formatting and parsing with timezones."""
        utc_dt = datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)

        # Format for timezone
        formatted = TimezoneUtils.format_datetime_for_timezone(
            utc_dt, "America/New_York", "%Y-%m-%d %H:%M:%S %Z"
        )
        assert "2023-06-15 08:00:00" in formatted  # EST time

        # Parse from timezone
        parsed = TimezoneUtils.parse_datetime_with_timezone(
            "2023-06-15 08:00:00", "America/New_York"
        )
        assert parsed is not None
        assert parsed.hour == 12  # Converted to UTC


class TestExtractedEntity:
    """Test ExtractedEntity functionality."""

    def test_entity_creation(self):
        """Test basic entity creation."""
        entity = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.95,
            context="Test context",
        )

        assert entity.name == "TestService"
        assert entity.entity_type == EntityType.SERVICE
        assert entity.confidence == 0.95
        assert entity.context == "Test context"
        assert entity.temporal_info is not None
        assert entity.entity_uuid is None

    def test_entity_validity_checks(self):
        """Test entity temporal validity checks."""
        entity = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
        )

        # Should be currently valid by default
        assert entity.is_currently_valid()
        assert entity.is_valid_at(datetime.now(UTC))

    def test_entity_versioning(self):
        """Test entity version creation."""
        original = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.8,
            entity_uuid="test-uuid",
        )

        # Create new version
        updated_fields = {"confidence": 0.95, "context": "Updated context"}
        new_version = original.create_new_version(updated_fields)

        assert new_version.confidence == 0.95
        assert new_version.context == "Updated context"
        assert new_version.entity_uuid == "test-uuid"  # Same UUID
        assert new_version.temporal_info.version == 2
        assert new_version.temporal_info.supersedes == "test-uuid"
        assert original.temporal_info.superseded_by == new_version.entity_uuid

    def test_entity_serialization(self):
        """Test entity serialization."""
        entity = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.95,
            context="Test context",
            metadata={"key": "value"},
            entity_uuid="test-uuid",
        )

        data = entity.to_dict()
        assert data["name"] == "TestService"
        assert data["entity_type"] == "Service"
        assert data["confidence"] == 0.95
        assert data["context"] == "Test context"
        assert data["metadata"]["key"] == "value"
        assert data["entity_uuid"] == "test-uuid"
        assert "temporal_info" in data


class TestExtractedRelationship:
    """Test ExtractedRelationship functionality."""

    def test_relationship_creation(self):
        """Test basic relationship creation."""
        relationship = ExtractedRelationship(
            source_entity="ServiceA",
            target_entity="ServiceB",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.9,
            context="Test relationship",
            evidence="Found in documentation",
        )

        assert relationship.source_entity == "ServiceA"
        assert relationship.target_entity == "ServiceB"
        assert relationship.relationship_type == RelationshipType.DEPENDS_ON
        assert relationship.confidence == 0.9
        assert relationship.context == "Test relationship"
        assert relationship.evidence == "Found in documentation"
        assert relationship.temporal_info is not None

    def test_relationship_versioning(self):
        """Test relationship version creation."""
        original = ExtractedRelationship(
            source_entity="ServiceA",
            target_entity="ServiceB",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.8,
            relationship_uuid="rel-uuid",
        )

        # Create new version
        updated_fields = {"confidence": 0.95, "evidence": "Updated evidence"}
        new_version = original.create_new_version(updated_fields)

        assert new_version.confidence == 0.95
        assert new_version.evidence == "Updated evidence"
        assert new_version.relationship_uuid == "rel-uuid"  # Same UUID
        assert new_version.temporal_info.version == 2


@pytest.fixture
def mock_graphiti_manager():
    """Create a mock GraphitiManager for testing."""
    return Mock()


@pytest.fixture
def temporal_manager(mock_graphiti_manager):
    """Create a TemporalManager instance for testing."""
    return TemporalManager(mock_graphiti_manager)


class TestTemporalManager:
    """Test TemporalManager functionality."""

    @pytest.mark.asyncio
    async def test_add_entity_basic(self, temporal_manager):
        """Test basic entity addition."""
        entity = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.95,
        )

        entity_uuid, conflicts = await temporal_manager.add_entity(entity)

        assert entity_uuid is not None
        assert len(conflicts) == 0
        assert entity.entity_uuid == entity_uuid

        # Verify entity is stored
        history = temporal_manager.get_entity_history(entity_uuid)
        assert len(history) == 1
        assert history[0].name == "TestService"

    @pytest.mark.asyncio
    async def test_add_relationship_basic(self, temporal_manager):
        """Test basic relationship addition."""
        relationship = ExtractedRelationship(
            source_entity="ServiceA",
            target_entity="ServiceB",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.9,
        )

        rel_uuid, conflicts = await temporal_manager.add_relationship(relationship)

        assert rel_uuid is not None
        assert len(conflicts) == 0
        assert relationship.relationship_uuid == rel_uuid

        # Verify relationship is stored
        history = temporal_manager.get_relationship_history(rel_uuid)
        assert len(history) == 1
        assert history[0].source_entity == "ServiceA"

    @pytest.mark.asyncio
    async def test_conflict_detection_and_resolution(self, temporal_manager):
        """Test conflict detection and resolution."""
        # Add first entity
        entity1 = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.8,
        )
        entity1.temporal_info.valid_from = datetime(2023, 1, 1, tzinfo=UTC)

        uuid1, conflicts1 = await temporal_manager.add_entity(entity1)
        assert len(conflicts1) == 0

        # Add conflicting entity (same name, overlapping time)
        entity2 = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.9,
        )
        entity2.temporal_info.valid_from = datetime(2023, 6, 1, tzinfo=UTC)

        uuid2, conflicts2 = await temporal_manager.add_entity(entity2)

        # Should detect and resolve conflict
        assert len(conflicts2) > 0
        assert conflicts2[0].conflict_type == "entity_overlap"
        assert conflicts2[0].resolved

    @pytest.mark.asyncio
    async def test_temporal_queries(self, temporal_manager):
        """Test temporal query functionality."""
        # Add entities with different temporal ranges
        entity1 = ExtractedEntity(name="Service1", entity_type=EntityType.SERVICE)
        entity1.temporal_info.valid_from = datetime(2023, 1, 1, tzinfo=UTC)
        entity1.temporal_info.valid_to = datetime(2023, 6, 1, tzinfo=UTC)

        entity2 = ExtractedEntity(name="Service2", entity_type=EntityType.SERVICE)
        entity2.temporal_info.valid_from = datetime(2023, 3, 1, tzinfo=UTC)
        entity2.temporal_info.valid_to = datetime(2023, 9, 1, tzinfo=UTC)

        await temporal_manager.add_entity(entity1)
        await temporal_manager.add_entity(entity2)

        # Point-in-time query
        query = TemporalQuery(query_time=datetime(2023, 4, 1, tzinfo=UTC))
        results = await temporal_manager.query_entities_at_time(query)
        assert len(results) == 2  # Both entities valid at this time

        # Range query
        query = TemporalQuery(
            time_range_start=datetime(2023, 7, 1, tzinfo=UTC),
            time_range_end=datetime(2023, 8, 1, tzinfo=UTC),
        )
        results = await temporal_manager.query_entities_in_range(query)
        assert len(results) == 1  # Only entity2 valid in this range

    @pytest.mark.asyncio
    async def test_timezone_aware_queries(self, temporal_manager):
        """Test timezone-aware query methods."""
        # Add entity
        entity = ExtractedEntity(name="TestService", entity_type=EntityType.SERVICE)
        entity.temporal_info.valid_from = datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC)

        await temporal_manager.add_entity(entity)

        # Query using EST time (should convert to UTC internally)
        results = await temporal_manager.query_entities_at_time_in_timezone(
            "2023-06-15 08:00:00", "America/New_York"  # 8 AM EST = 12 PM UTC
        )
        assert len(results) == 1
        assert results[0].name == "TestService"

        # Range query with timezone
        results = await temporal_manager.query_entities_in_range_in_timezone(
            "2023-06-15 07:00:00",  # 7 AM EST
            "2023-06-15 09:00:00",  # 9 AM EST
            "America/New_York",
        )
        assert len(results) == 1

    def test_version_chain_validation(self, temporal_manager):
        """Test version chain validation and repair."""
        # Create entities with broken version chains
        entity1 = ExtractedEntity(name="Test", entity_type=EntityType.SERVICE)
        entity1.entity_uuid = "test-uuid"
        entity1.temporal_info.version = 1

        entity2 = ExtractedEntity(name="Test", entity_type=EntityType.SERVICE)
        entity2.entity_uuid = "test-uuid"
        entity2.temporal_info.version = 3  # Missing version 2

        # Manually add to storage (bypassing normal add_entity)
        temporal_manager._entities["test-uuid"] = [entity1, entity2]

        # Validate version chains
        issues = temporal_manager.validate_version_chains()
        assert "test-uuid" in issues["entities"]
        assert len(issues["entities"]["test-uuid"]) > 0

        # Repair version chains
        repairs = temporal_manager.repair_version_chains()
        assert repairs["entities"] > 0

    @pytest.mark.asyncio
    async def test_rollback_functionality(self, temporal_manager):
        """Test entity rollback functionality."""
        # Add entity and create versions
        entity = ExtractedEntity(name="TestService", entity_type=EntityType.SERVICE)
        uuid, _ = await temporal_manager.add_entity(entity)

        # Create new version
        updated_entity = entity.create_new_version({"confidence": 0.95})
        temporal_manager._entities[uuid].append(updated_entity)

        # Rollback to version 1
        rolled_back = await temporal_manager.rollback_entity_to_version(uuid, 1)
        assert rolled_back is not None
        assert rolled_back.temporal_info.version == 3  # New version created
        assert rolled_back.confidence == entity.confidence  # Original confidence

    def test_version_comparison(self, temporal_manager):
        """Test version comparison functionality."""
        # Create two versions of an entity
        entity1 = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.8,
            context="Original context",
        )
        entity1.entity_uuid = "test-uuid"
        entity1.temporal_info.version = 1

        entity2 = ExtractedEntity(
            name="TestService",
            entity_type=EntityType.SERVICE,
            confidence=0.95,
            context="Updated context",
        )
        entity2.entity_uuid = "test-uuid"
        entity2.temporal_info.version = 2

        # Add to storage
        temporal_manager._entities["test-uuid"] = [entity1, entity2]

        # Compare versions
        comparison = temporal_manager.compare_entity_versions("test-uuid", 1, 2)
        assert comparison is not None
        assert comparison["fields"]["confidence"]["changed"]
        assert comparison["fields"]["context"]["changed"]
        assert comparison["fields"]["confidence"]["v1"] == 0.8
        assert comparison["fields"]["confidence"]["v2"] == 0.95

    def test_version_pruning(self, temporal_manager):
        """Test version pruning functionality."""
        # Create multiple versions of an entity
        base_entity = ExtractedEntity(name="Test", entity_type=EntityType.SERVICE)
        base_entity.entity_uuid = "test-uuid"

        versions = []
        for i in range(15):  # Create 15 versions
            entity = ExtractedEntity(name="Test", entity_type=EntityType.SERVICE)
            entity.entity_uuid = "test-uuid"
            entity.temporal_info.version = i + 1
            entity.temporal_info.transaction_time = datetime.now(UTC) - timedelta(
                days=i
            )
            versions.append(entity)

        temporal_manager._entities["test-uuid"] = versions

        # Prune with policy: max 5 versions, max 30 days old
        retention_policy = {
            "max_versions": 5,
            "max_age_days": 30,
            "keep_milestones": True,
        }

        pruned = temporal_manager.prune_old_versions(retention_policy)
        assert pruned["entities"] > 0

        # Check remaining versions
        remaining = temporal_manager._entities["test-uuid"]
        assert len(remaining) <= 5

    def test_statistics_collection(self, temporal_manager):
        """Test statistics collection."""
        # Add some test data
        entity = ExtractedEntity(name="Test", entity_type=EntityType.SERVICE)
        relationship = ExtractedRelationship(
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        asyncio.run(temporal_manager.add_entity(entity))
        asyncio.run(temporal_manager.add_relationship(relationship))

        # Get statistics
        stats = temporal_manager.get_statistics()

        assert stats["total_entities"] == 1
        assert stats["total_relationships"] == 1
        assert stats["total_conflicts"] == 0
        assert "entity_types" in stats
        assert "relationship_types" in stats

    @pytest.mark.asyncio
    async def test_temporal_aggregates(self, temporal_manager):
        """Test temporal aggregation queries."""
        # Add entities with different timestamps
        for i in range(5):
            entity = ExtractedEntity(name=f"Service{i}", entity_type=EntityType.SERVICE)
            entity.temporal_info.valid_from = datetime(2023, 1, i + 1, tzinfo=UTC)
            await temporal_manager.add_entity(entity)

        # Query aggregates
        query = TemporalQuery(
            time_range_start=datetime(2023, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2023, 1, 31, tzinfo=UTC),
        )

        aggregates = await temporal_manager.query_temporal_aggregates(query, "count")
        assert aggregates["entity_count"] == 5
        assert aggregates["relationship_count"] == 0

    @pytest.mark.asyncio
    async def test_cross_temporal_relationships(self, temporal_manager):
        """Test cross-temporal relationship queries."""
        # Add entities
        entity1 = ExtractedEntity(name="ServiceA", entity_type=EntityType.SERVICE)
        entity2 = ExtractedEntity(name="ServiceB", entity_type=EntityType.SERVICE)

        await temporal_manager.add_entity(entity1)
        await temporal_manager.add_entity(entity2)

        # Add relationship
        relationship = ExtractedRelationship(
            source_entity="ServiceA",
            target_entity="ServiceB",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        await temporal_manager.add_relationship(relationship)

        # Query cross-temporal relationships
        results = await temporal_manager.find_cross_temporal_relationships(
            "ServiceA", "ServiceB"
        )
        assert len(results) == 1
        assert results[0].relationship_type == RelationshipType.DEPENDS_ON

    @pytest.mark.asyncio
    async def test_temporal_graph_traversal(self, temporal_manager):
        """Test temporal graph traversal functionality."""
        # Create a small graph: A -> B -> C
        entities = ["ServiceA", "ServiceB", "ServiceC"]
        for name in entities:
            entity = ExtractedEntity(name=name, entity_type=EntityType.SERVICE)
            await temporal_manager.add_entity(entity)

        # Add relationships
        rel1 = ExtractedRelationship(
            source_entity="ServiceA",
            target_entity="ServiceB",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        rel2 = ExtractedRelationship(
            source_entity="ServiceB",
            target_entity="ServiceC",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        await temporal_manager.add_relationship(rel1)
        await temporal_manager.add_relationship(rel2)

        # Traverse graph
        result = await temporal_manager.traverse_temporal_graph("ServiceA", max_depth=3)

        assert "paths" in result
        assert "entities_found" in result
        assert "relationships_traversed" in result
        assert len(result["entities_found"]) >= 2  # Should find at least ServiceB

    def test_timezone_validation_in_manager(self, temporal_manager):
        """Test timezone validation methods in TemporalManager."""
        # Valid timezone
        result = temporal_manager.validate_timezone_input("America/New_York")
        assert result["valid"]
        assert result["normalized_timezone"] == "America/New_York"

        # Invalid timezone
        result = temporal_manager.validate_timezone_input("Invalid/Timezone")
        assert not result["valid"]
        assert "error" in result

        # Timezone with datetime validation
        result = temporal_manager.validate_timezone_input(
            "America/New_York", "2023-06-15 14:00:00"
        )
        assert result["valid"]
        assert result["datetime_valid"]
        assert result["parsed_datetime_utc"] is not None

    def test_dst_transition_info_in_manager(self, temporal_manager):
        """Test DST transition info method in TemporalManager."""
        # Spring forward transition
        dst_info = temporal_manager.get_dst_transition_info(
            "2023-03-12 02:30:00", "America/New_York"
        )
        assert dst_info["is_transition"]
        assert dst_info["transition_type"] == "spring_forward"

        # Regular time (no transition)
        dst_info = temporal_manager.get_dst_transition_info(
            "2023-06-15 12:00:00", "America/New_York"
        )
        assert not dst_info["is_transition"]

    def test_formatting_methods(self, temporal_manager):
        """Test entity and relationship formatting methods."""
        # Create test data
        entity = ExtractedEntity(name="TestService", entity_type=EntityType.SERVICE)
        relationship = ExtractedRelationship(
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
        )

        # Test formatting
        formatted_entities = temporal_manager.format_entities_for_timezone(
            [entity], "America/New_York"
        )
        assert len(formatted_entities) == 1
        assert "temporal_info_formatted" in formatted_entities[0]

        formatted_relationships = temporal_manager.format_relationships_for_timezone(
            [relationship], "America/New_York"
        )
        assert len(formatted_relationships) == 1
        assert "temporal_info_formatted" in formatted_relationships[0]


class TestTemporalQueryFiltering:
    """Test advanced temporal query filtering capabilities."""

    @pytest.fixture
    def populated_temporal_manager(self, temporal_manager):
        """Create a temporal manager with test data."""

        async def setup():
            # Add various entities
            entities = [
                ExtractedEntity(
                    name="ServiceA", entity_type=EntityType.SERVICE, confidence=0.9
                ),
                ExtractedEntity(
                    name="ServiceB", entity_type=EntityType.SERVICE, confidence=0.8
                ),
                ExtractedEntity(
                    name="DatabaseX", entity_type=EntityType.DATABASE, confidence=0.95
                ),
                ExtractedEntity(
                    name="TeamAlpha", entity_type=EntityType.TEAM, confidence=0.7
                ),
            ]

            for entity in entities:
                await temporal_manager.add_entity(entity)

            # Add relationships
            relationships = [
                ExtractedRelationship(
                    source_entity="ServiceA",
                    target_entity="DatabaseX",
                    relationship_type=RelationshipType.USES,
                    confidence=0.9,
                ),
                ExtractedRelationship(
                    source_entity="ServiceB",
                    target_entity="DatabaseX",
                    relationship_type=RelationshipType.USES,
                    confidence=0.8,
                ),
                ExtractedRelationship(
                    source_entity="TeamAlpha",
                    target_entity="ServiceA",
                    relationship_type=RelationshipType.MANAGES,
                    confidence=0.85,
                ),
            ]

            for relationship in relationships:
                await temporal_manager.add_relationship(relationship)

        asyncio.run(setup())
        return temporal_manager

    @pytest.mark.asyncio
    async def test_entity_filtering_by_type(self, populated_temporal_manager):
        """Test filtering entities by type."""
        query = TemporalQuery(
            query_time=datetime.now(UTC),
            entity_types=["Service"],
        )

        results = await populated_temporal_manager.query_entities_at_time(query)
        assert len(results) == 2  # ServiceA and ServiceB
        assert all(entity.entity_type == EntityType.SERVICE for entity in results)

    @pytest.mark.asyncio
    async def test_entity_filtering_by_confidence(self, populated_temporal_manager):
        """Test filtering entities by confidence threshold."""
        query = TemporalQuery(
            query_time=datetime.now(UTC),
            min_confidence=0.85,
        )

        results = await populated_temporal_manager.query_entities_at_time(query)
        assert len(results) == 2  # ServiceA (0.9) and DatabaseX (0.95)
        assert all(entity.confidence >= 0.85 for entity in results)

    @pytest.mark.asyncio
    async def test_relationship_filtering_by_type(self, populated_temporal_manager):
        """Test filtering relationships by type."""
        query = TemporalQuery(
            query_time=datetime.now(UTC),
            relationship_types=["uses"],
        )

        results = await populated_temporal_manager.query_relationships_at_time(query)
        assert len(results) == 2  # Both USES relationships
        assert all(rel.relationship_type == RelationshipType.USES for rel in results)

    @pytest.mark.asyncio
    async def test_query_sorting_and_limiting(self, populated_temporal_manager):
        """Test query sorting and limiting functionality."""
        query = TemporalQuery(
            query_time=datetime.now(UTC),
            sort_by="confidence",
            sort_descending=True,
            limit=2,
        )

        results = await populated_temporal_manager.query_entities_at_time(query)
        assert len(results) == 2
        # Should be sorted by confidence descending
        assert results[0].confidence >= results[1].confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
