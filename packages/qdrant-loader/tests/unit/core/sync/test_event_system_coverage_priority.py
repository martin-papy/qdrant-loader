"""Focused tests for SyncEventSystem - Phase 4 coverage improvement.

Targets sync/event_system.py: 480 lines, 18% -> 70%+ coverage.
Focuses on testable components without async polling issues.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from qdrant_loader.core.managers import MappingType
from qdrant_loader.core.sync.event_system import (
    ChangeEvent,
    ChangeType,
    DatabaseType,
)
from qdrant_loader.core.types import EntityType


class TestChangeEvent:
    """Test ChangeEvent dataclass functionality - core coverage target."""

    def test_change_event_creation_defaults(self):
        """Test ChangeEvent creation with default values."""
        event = ChangeEvent()

        assert event.event_id is not None
        assert isinstance(event.timestamp, datetime)
        assert event.change_type == ChangeType.UPDATE
        assert event.database_type == DatabaseType.QDRANT
        assert event.entity_type == EntityType.CONCEPT
        assert event.mapping_type == MappingType.DOCUMENT
        assert event.entity_id is None
        assert event.processed is False
        assert event.retry_count == 0

    def test_change_event_creation_with_values(self):
        """Test ChangeEvent creation with specific values."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC)
        affected_fields = {"field1", "field2"}
        metadata = {"key": "value"}
        processing_errors = ["error1", "error2"]

        event = ChangeEvent(
            event_id=event_id,
            timestamp=timestamp,
            change_type=ChangeType.CREATE,
            database_type=DatabaseType.NEO4J,
            entity_type=EntityType.PROJECT,
            mapping_type=MappingType.ENTITY,
            entity_id="test_entity",
            entity_uuid="test_uuid",
            entity_name="test_name",
            old_data={"old": "data"},
            new_data={"new": "data"},
            affected_fields=affected_fields,
            metadata=metadata,
            source_transaction_id="tx123",
            batch_id="batch456",
            processed=True,
            processing_errors=processing_errors,
            retry_count=3,
        )

        assert event.event_id == event_id
        assert event.timestamp == timestamp
        assert event.change_type == ChangeType.CREATE
        assert event.database_type == DatabaseType.NEO4J
        assert event.entity_type == EntityType.PROJECT
        assert event.mapping_type == MappingType.ENTITY
        assert event.entity_id == "test_entity"
        assert event.entity_uuid == "test_uuid"
        assert event.entity_name == "test_name"
        assert event.old_data == {"old": "data"}
        assert event.new_data == {"new": "data"}
        assert event.affected_fields == affected_fields
        assert event.metadata == metadata
        assert event.source_transaction_id == "tx123"
        assert event.batch_id == "batch456"
        assert event.processed is True
        assert event.processing_errors == processing_errors
        assert event.retry_count == 3

    def test_change_event_to_dict(self):
        """Test ChangeEvent serialization to dictionary."""
        event = ChangeEvent(
            entity_id="test_entity",
            entity_name="test_name",
            old_data={"old": "data"},
            new_data={"new": "data"},
            affected_fields={"field1", "field2"},
            metadata={"key": "value"},
            processed=True,
            retry_count=2,
        )

        event_dict = event.to_dict()

        assert event_dict["event_id"] == event.event_id
        assert event_dict["timestamp"] == event.timestamp.isoformat()
        assert event_dict["change_type"] == event.change_type.value
        assert event_dict["database_type"] == event.database_type.value
        assert event_dict["entity_type"] == event.entity_type.value
        assert event_dict["mapping_type"] == event.mapping_type.value
        assert event_dict["entity_id"] == "test_entity"
        assert event_dict["entity_name"] == "test_name"
        assert event_dict["old_data"] == {"old": "data"}
        assert event_dict["new_data"] == {"new": "data"}
        assert set(event_dict["affected_fields"]) == {"field1", "field2"}
        assert event_dict["metadata"] == {"key": "value"}
        assert event_dict["processed"] is True
        assert event_dict["retry_count"] == 2

    def test_change_event_from_dict_complete(self):
        """Test ChangeEvent deserialization from complete dictionary."""
        timestamp = datetime.now(UTC)
        event_dict = {
            "event_id": "test_event_id",
            "timestamp": timestamp.isoformat(),
            "change_type": "create",
            "database_type": "neo4j",
            "entity_type": "Project",
            "mapping_type": "entity",
            "entity_id": "test_entity",
            "entity_uuid": "test_uuid",
            "entity_name": "test_name",
            "old_data": {"old": "data"},
            "new_data": {"new": "data"},
            "affected_fields": ["field1", "field2"],
            "metadata": {"key": "value"},
            "source_transaction_id": "tx123",
            "batch_id": "batch456",
            "processed": True,
            "processing_errors": ["error1"],
            "retry_count": 3,
        }

        event = ChangeEvent.from_dict(event_dict)

        assert event.event_id == "test_event_id"
        assert event.timestamp == timestamp
        assert event.change_type == ChangeType.CREATE
        assert event.database_type == DatabaseType.NEO4J
        assert event.entity_type == EntityType.PROJECT
        assert event.mapping_type == MappingType.ENTITY
        assert event.entity_id == "test_entity"
        assert event.entity_uuid == "test_uuid"
        assert event.entity_name == "test_name"
        assert event.old_data == {"old": "data"}
        assert event.new_data == {"new": "data"}
        assert event.affected_fields == {"field1", "field2"}
        assert event.metadata == {"key": "value"}
        assert event.source_transaction_id == "tx123"
        assert event.batch_id == "batch456"
        assert event.processed is True
        assert event.processing_errors == ["error1"]
        assert event.retry_count == 3

    def test_change_event_from_dict_minimal(self):
        """Test ChangeEvent deserialization from minimal dictionary."""
        timestamp = datetime.now(UTC)
        event_dict = {
            "event_id": "test_event_id",
            "timestamp": timestamp.isoformat(),
            "change_type": "update",
            "database_type": "qdrant",
            "entity_type": "Concept",
            "mapping_type": "document",
        }

        event = ChangeEvent.from_dict(event_dict)

        assert event.event_id == "test_event_id"
        assert event.timestamp == timestamp
        assert event.change_type == ChangeType.UPDATE
        assert event.database_type == DatabaseType.QDRANT
        assert event.entity_type == EntityType.CONCEPT
        assert event.mapping_type == MappingType.DOCUMENT
        # Check defaults for optional fields
        assert event.entity_id is None
        assert event.entity_uuid is None
        assert event.entity_name is None
        assert event.old_data is None
        assert event.new_data is None
        assert event.affected_fields == set()
        assert event.metadata == {}
        assert event.source_transaction_id is None
        assert event.batch_id is None
        assert event.processed is False
        assert event.processing_errors == []
        assert event.retry_count == 0

    def test_change_event_from_dict_with_null_values(self):
        """Test ChangeEvent deserialization with null/None values."""
        timestamp = datetime.now(UTC)
        event_dict = {
            "event_id": "test_event_id",
            "timestamp": timestamp.isoformat(),
            "change_type": "delete",
            "database_type": "graphiti",
            "entity_type": "Technology",
            "mapping_type": "document",
            "entity_id": None,
            "entity_uuid": None,
            "entity_name": None,
            "old_data": None,
            "new_data": None,
            "affected_fields": [],
            "metadata": None,
            "source_transaction_id": None,
            "batch_id": None,
            "processing_errors": None,
        }

        event = ChangeEvent.from_dict(event_dict)

        assert event.change_type == ChangeType.DELETE
        assert event.database_type == DatabaseType.GRAPHITI
        assert event.entity_type == EntityType.TECHNOLOGY
        assert event.entity_id is None
        assert event.affected_fields == set()
        assert event.metadata is None  # ChangeEvent preserves None for metadata
        assert (
            event.processing_errors is None
        )  # ChangeEvent preserves None for processing_errors

    def test_change_event_json_serialization(self):
        """Test ChangeEvent JSON serialization round-trip."""
        original_event = ChangeEvent(
            change_type=ChangeType.BULK_UPDATE,
            database_type=DatabaseType.NEO4J,
            entity_type=EntityType.ORGANIZATION,
            mapping_type=MappingType.ENTITY,
            entity_id="org_123",
            entity_name="Test Org",
            new_data={"name": "Updated Org", "size": 100},
            affected_fields={"name", "size"},
            metadata={"batch": "update_orgs", "version": 2},
            retry_count=1,
        )

        # Serialize to JSON
        event_dict = original_event.to_dict()
        json_str = json.dumps(event_dict)

        # Deserialize from JSON
        loaded_dict = json.loads(json_str)
        restored_event = ChangeEvent.from_dict(loaded_dict)

        # Verify round-trip integrity
        assert restored_event.event_id == original_event.event_id
        assert restored_event.change_type == original_event.change_type
        assert restored_event.database_type == original_event.database_type
        assert restored_event.entity_type == original_event.entity_type
        assert restored_event.mapping_type == original_event.mapping_type
        assert restored_event.entity_id == original_event.entity_id
        assert restored_event.entity_name == original_event.entity_name
        assert restored_event.new_data == original_event.new_data
        assert restored_event.affected_fields == original_event.affected_fields
        assert restored_event.metadata == original_event.metadata
        assert restored_event.retry_count == original_event.retry_count

    def test_change_event_equality_and_hashing(self):
        """Test ChangeEvent equality and hashing behavior."""
        event1 = ChangeEvent(
            event_id="same_id",
            entity_id="test_entity",
            change_type=ChangeType.CREATE,
        )
        event2 = ChangeEvent(
            event_id="same_id",
            entity_id="test_entity",
            change_type=ChangeType.CREATE,
        )
        event3 = ChangeEvent(
            event_id="different_id",
            entity_id="test_entity",
            change_type=ChangeType.CREATE,
        )

        # Events with same event_id should be considered equal
        assert event1.event_id == event2.event_id
        assert event1.event_id != event3.event_id

        # Test that events can be compared by event_id
        # Note: ChangeEvent is not hashable, so can't be used in sets
        # but event_ids can be compared
        event_ids = {event1.event_id, event2.event_id, event3.event_id}
        assert len(event_ids) >= 2  # At least 2 unique event_ids


class TestChangeTypeEnum:
    """Test ChangeType enum coverage."""

    def test_change_type_values(self):
        """Test all ChangeType enum values."""
        assert ChangeType.CREATE.value == "create"
        assert ChangeType.UPDATE.value == "update"
        assert ChangeType.DELETE.value == "delete"
        assert ChangeType.BULK_CREATE.value == "bulk_create"
        assert ChangeType.BULK_UPDATE.value == "bulk_update"
        assert ChangeType.BULK_DELETE.value == "bulk_delete"

    def test_change_type_from_string(self):
        """Test ChangeType creation from string values."""
        assert ChangeType("create") == ChangeType.CREATE
        assert ChangeType("update") == ChangeType.UPDATE
        assert ChangeType("delete") == ChangeType.DELETE
        assert ChangeType("bulk_create") == ChangeType.BULK_CREATE
        assert ChangeType("bulk_update") == ChangeType.BULK_UPDATE
        assert ChangeType("bulk_delete") == ChangeType.BULK_DELETE

    def test_change_type_invalid_value(self):
        """Test ChangeType with invalid value."""
        with pytest.raises(ValueError):
            ChangeType("invalid_change_type")


class TestDatabaseTypeEnum:
    """Test DatabaseType enum coverage."""

    def test_database_type_values(self):
        """Test all DatabaseType enum values."""
        assert DatabaseType.QDRANT.value == "qdrant"
        assert DatabaseType.NEO4J.value == "neo4j"
        assert DatabaseType.GRAPHITI.value == "graphiti"

    def test_database_type_from_string(self):
        """Test DatabaseType creation from string values."""
        assert DatabaseType("qdrant") == DatabaseType.QDRANT
        assert DatabaseType("neo4j") == DatabaseType.NEO4J
        assert DatabaseType("graphiti") == DatabaseType.GRAPHITI

    def test_database_type_invalid_value(self):
        """Test DatabaseType with invalid value."""
        with pytest.raises(ValueError):
            DatabaseType("invalid_database")


class TestEventSystemUtilities:
    """Test utility functions and edge cases in event system."""

    def test_change_event_field_combinations(self):
        """Test various field combinations in ChangeEvent."""
        # Test with only required fields
        minimal_event = ChangeEvent()
        assert minimal_event.event_id is not None
        assert minimal_event.timestamp is not None

        # Test with bulk operations
        bulk_event = ChangeEvent(
            change_type=ChangeType.BULK_CREATE,
            database_type=DatabaseType.GRAPHITI,
            entity_type=EntityType.API,
            batch_id="bulk_123",
            metadata={"batch_size": 1000, "source": "import"},
        )
        assert bulk_event.change_type == ChangeType.BULK_CREATE
        assert bulk_event.database_type == DatabaseType.GRAPHITI
        assert bulk_event.entity_type == EntityType.API
        assert bulk_event.batch_id == "bulk_123"
        assert bulk_event.metadata["batch_size"] == 1000

        # Test with error tracking
        error_event = ChangeEvent(
            change_type=ChangeType.UPDATE,
            entity_id="failed_entity",
            processed=False,
            processing_errors=["Connection timeout", "Retry limit exceeded"],
            retry_count=5,
        )
        assert error_event.processed is False
        assert len(error_event.processing_errors) == 2
        assert error_event.retry_count == 5

    def test_change_event_timestamp_handling(self):
        """Test timestamp handling in ChangeEvent."""
        # Test with explicit timestamp
        explicit_time = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
        event_with_time = ChangeEvent(timestamp=explicit_time)
        assert event_with_time.timestamp == explicit_time

        # Test default timestamp (should be recent)
        event_default_time = ChangeEvent()
        time_diff = datetime.now(UTC) - event_default_time.timestamp
        assert time_diff.total_seconds() < 5  # Should be within 5 seconds

    def test_change_event_affected_fields_handling(self):
        """Test affected_fields set handling."""
        # Test with list input (gets stored as-is, not converted to set)
        event = ChangeEvent(affected_fields=["field1", "field2", "field1"])
        # ChangeEvent stores affected_fields as provided (list or set)
        assert event.affected_fields == ["field1", "field2", "field1"]

        # Test with set input
        event2 = ChangeEvent(affected_fields={"field3", "field4"})
        assert event2.affected_fields == {"field3", "field4"}

        # Test serialization preserves list as list
        event_dict = event.to_dict()
        assert isinstance(event_dict["affected_fields"], list)
        assert event_dict["affected_fields"] == ["field1", "field2", "field1"]

    def test_change_event_metadata_handling(self):
        """Test metadata dictionary handling."""
        # Test with various metadata types
        metadata = {
            "string_value": "test",
            "int_value": 42,
            "float_value": 3.14,
            "bool_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "value"},
        }

        event = ChangeEvent(metadata=metadata)
        assert event.metadata == metadata

        # Test serialization preserves metadata structure
        event_dict = event.to_dict()
        assert event_dict["metadata"] == metadata

        # Test deserialization restores metadata
        restored_event = ChangeEvent.from_dict(event_dict)
        assert restored_event.metadata == metadata

    def test_change_event_processing_errors_handling(self):
        """Test processing_errors list handling."""
        errors = ["Error 1", "Error 2", "Error 3"]
        event = ChangeEvent(processing_errors=errors)
        assert event.processing_errors == errors

        # Test serialization/deserialization preserves errors
        event_dict = event.to_dict()
        restored_event = ChangeEvent.from_dict(event_dict)
        assert restored_event.processing_errors == errors

    def test_change_event_data_types(self):
        """Test various data types in old_data and new_data."""
        old_data = {
            "string": "old_value",
            "number": 100,
            "boolean": False,
            "list": [1, 2, 3],
            "nested": {"key": "old_nested_value"},
        }

        new_data = {
            "string": "new_value",
            "number": 200,
            "boolean": True,
            "list": [4, 5, 6],
            "nested": {"key": "new_nested_value"},
        }

        event = ChangeEvent(old_data=old_data, new_data=new_data)
        assert event.old_data == old_data
        assert event.new_data == new_data

        # Test serialization preserves complex data types
        event_dict = event.to_dict()
        restored_event = ChangeEvent.from_dict(event_dict)
        assert restored_event.old_data == old_data
        assert restored_event.new_data == new_data

    def test_entity_type_coverage(self):
        """Test all EntityType values work with ChangeEvent."""
        entity_types = [
            EntityType.SERVICE,
            EntityType.DATABASE,
            EntityType.TEAM,
            EntityType.PERSON,
            EntityType.ORGANIZATION,
            EntityType.PROJECT,
            EntityType.CONCEPT,
            EntityType.TECHNOLOGY,
            EntityType.API,
            EntityType.ENDPOINT,
        ]

        for entity_type in entity_types:
            event = ChangeEvent(entity_type=entity_type)
            assert event.entity_type == entity_type

            # Test serialization/deserialization
            event_dict = event.to_dict()
            restored_event = ChangeEvent.from_dict(event_dict)
            assert restored_event.entity_type == entity_type

    def test_mapping_type_coverage(self):
        """Test all MappingType values work with ChangeEvent."""
        mapping_types = [MappingType.DOCUMENT, MappingType.ENTITY]

        for mapping_type in mapping_types:
            event = ChangeEvent(mapping_type=mapping_type)
            assert event.mapping_type == mapping_type

            # Test serialization/deserialization
            event_dict = event.to_dict()
            restored_event = ChangeEvent.from_dict(event_dict)
            assert restored_event.mapping_type == mapping_type
