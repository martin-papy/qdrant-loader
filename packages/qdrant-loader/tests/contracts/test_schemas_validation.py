"""Simple validation tests for contract schemas."""

from datetime import datetime, UTC
from pydantic import ValidationError

# Import our contract schemas directly
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from .schemas import (
    QdrantPointContract,
    Neo4jNodeContract,
    TemporalInfoContract,
    EntityTypeContract,
    ExtractedEntityContract,
)


def test_qdrant_point_schema():
    """Test QDrant point contract schema validation."""
    print("Testing QDrant Point Contract...")
    
    # Valid data should pass
    valid_data = {
        "id": "doc_123",
        "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
        "metadata": {"document_type": "text", "source": "test"}
    }
    
    try:
        point = QdrantPointContract(**valid_data)
        print(f"✅ Valid QDrant point: {point.id}")
    except ValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
        assert False, f"Valid data should pass validation: {e}"
    
    # Invalid data should fail
    invalid_data = {
        "id": "doc_124",
        "vector": [],  # Empty vector should fail
        "metadata": {}
    }
    
    try:
        point = QdrantPointContract(**invalid_data)
        print(f"❌ Invalid data passed validation unexpectedly")
        assert False, "Empty vector should have been rejected"
    except ValidationError:
        print("✅ Empty vector correctly rejected")


def test_neo4j_node_schema():
    """Test Neo4j node contract schema validation."""
    print("\nTesting Neo4j Node Contract...")
    
    # Valid data should pass
    valid_data = {
        "id": "entity_123",
        "labels": ["Document", "TextDocument"],
        "properties": {
            "name": "Test Document",
            "created_at": datetime.now(UTC).isoformat()
        }
    }
    
    try:
        node = Neo4jNodeContract(**valid_data)
        print(f"✅ Valid Neo4j node: {node.id} with labels {node.labels}")
    except ValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
        assert False, f"Valid data should pass validation: {e}"
    
    # Invalid data should fail
    invalid_data = {
        "id": "entity_124",
        "labels": [],  # Empty labels should fail
        "properties": {}
    }
    
    try:
        node = Neo4jNodeContract(**invalid_data)
        print(f"❌ Invalid data passed validation unexpectedly")
        assert False, "Empty labels should have been rejected"
    except ValidationError:
        print("✅ Empty labels correctly rejected")


def test_temporal_info_schema():
    """Test temporal information contract schema validation."""
    print("\nTesting Temporal Info Contract...")
    
    # Valid data should pass
    now = datetime.now(UTC)
    valid_data = {
        "valid_from": now,
        "transaction_time": now,
        "version": 1
    }
    
    try:
        temporal = TemporalInfoContract(**valid_data)
        print(f"✅ Valid temporal info: version {temporal.version}")
    except ValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
        assert False, f"Valid data should pass validation: {e}"
    
    # Invalid version should fail
    invalid_data = {
        "valid_from": now,
        "transaction_time": now,
        "version": 0  # Must be >= 1
    }
    
    try:
        temporal = TemporalInfoContract(**invalid_data)
        print(f"❌ Invalid version passed validation unexpectedly")
        assert False, "Invalid version (0) should have been rejected"
    except ValidationError:
        print("✅ Invalid version correctly rejected")


def test_entity_types():
    """Test entity type enum validation."""
    print("\nTesting Entity Types...")
    
    # Test enum values
    assert EntityTypeContract.PERSON == "Person"
    assert EntityTypeContract.ORGANIZATION == "Organization"
    assert EntityTypeContract.TECHNOLOGY == "Technology"
    assert EntityTypeContract.CONCEPT == "Concept"
    
    print("✅ All entity type enums validated correctly")


def test_extracted_entity_schema():
    """Test extracted entity contract schema validation."""
    print("\nTesting Extracted Entity Contract...")
    
    # Valid entity should pass
    now = datetime.now(UTC)
    temporal_data = {
        "valid_from": now,
        "transaction_time": now,
        "version": 1
    }
    
    valid_entity = {
        "name": "John Doe",
        "entity_type": EntityTypeContract.PERSON,
        "confidence": 0.95,
        "context": "software engineer",
        "metadata": {"role": "engineer"},
        "temporal_info": temporal_data,
        "entity_uuid": "uuid_123"
    }
    
    try:
        entity = ExtractedEntityContract(**valid_entity)
        print(f"✅ Valid extracted entity: {entity.name} ({entity.entity_type})")
    except ValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
        assert False, f"Valid data should pass validation: {e}"
    
    # Invalid confidence should fail
    invalid_entity = valid_entity.copy()
    invalid_entity["confidence"] = 1.5  # Must be <= 1.0
    
    try:
        entity = ExtractedEntityContract(**invalid_entity)
        print(f"❌ Invalid confidence passed validation unexpectedly")
        assert False, "Invalid confidence (1.5) should have been rejected"
    except ValidationError:
        print("✅ Invalid confidence correctly rejected")


def main():
    """Run all contract schema validation tests."""
    print("🧪 Running Contract Schema Validation Tests\n")
    
    tests = [
        test_qdrant_point_schema,
        test_neo4j_node_schema, 
        test_temporal_info_schema,
        test_entity_types,
        test_extracted_entity_schema,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main()) 