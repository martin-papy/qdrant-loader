"""Standalone tests for the contract testing framework."""

import pytest
from datetime import datetime, UTC

from tests.contracts.base import (
    ContractValidator,
    ContractTestStatus,
    ContractTestResult,
    ComponentContractTest,
)
from tests.contracts.schemas import (
    QdrantPointContract,
    TemporalInfoContract,
    EntityTypeContract,
)


class SimpleContractTest(ComponentContractTest):
    """Simple contract test for framework validation."""
    
    def __init__(self):
        super().__init__("Framework Validation", "TestComponent")
    
    def run(self, **kwargs):
        """Run a simple contract validation test."""
        # Test valid data
        valid_data = {
            "id": "test_123",
            "vector": [0.1, 0.2, 0.3],
            "metadata": {"test": True}
        }
        
        result = self.validate_input_contract(valid_data, QdrantPointContract)
        if result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Contract validation failed: {result.message}",
                details=result.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "Contract framework validation successful"
        )


def test_contract_validator():
    """Test the ContractValidator class directly."""
    validator = ContractValidator()
    
    # Test valid data
    valid_temporal = {
        "valid_from": datetime.now(UTC),
        "transaction_time": datetime.now(UTC),
        "version": 1
    }
    
    result = validator.validate_schema(valid_temporal, TemporalInfoContract)
    assert result.passed, f"Valid temporal data should pass: {result.message}"
    
    # Test invalid data  
    invalid_temporal = {
        "valid_from": datetime.now(UTC),
        "transaction_time": datetime.now(UTC),
        "version": 0  # Invalid: version must be >= 1
    }
    
    result = validator.validate_schema(invalid_temporal, TemporalInfoContract)
    assert result.failed, "Invalid temporal data should fail validation"


def test_required_fields_validation():
    """Test required fields validation."""
    validator = ContractValidator()
    
    # Test with all required fields
    complete_data = {"field1": "value1", "field2": "value2", "field3": "value3"}
    result = validator.validate_required_fields(complete_data, ["field1", "field2"])
    assert result.passed, "Data with all required fields should pass"
    
    # Test with missing fields
    incomplete_data = {"field1": "value1"}
    result = validator.validate_required_fields(incomplete_data, ["field1", "field2"])
    assert result.failed, "Data with missing required fields should fail"


def test_field_types_validation():
    """Test field types validation."""
    validator = ContractValidator()
    
    # Test with correct types
    correct_data = {"name": "test", "count": 42, "active": True}
    field_types = {"name": str, "count": int, "active": bool}
    result = validator.validate_field_types(correct_data, field_types)
    assert result.passed, "Data with correct types should pass"
    
    # Test with incorrect types
    incorrect_data = {"name": "test", "count": "not_a_number", "active": True}
    result = validator.validate_field_types(incorrect_data, field_types)
    assert result.failed, "Data with incorrect types should fail"


def test_qdrant_point_contract():
    """Test QDrant point contract validation."""
    validator = ContractValidator()
    
    # Valid QDrant point
    valid_point = {
        "id": "doc_123",
        "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
        "metadata": {"document_type": "text"}
    }
    
    result = validator.validate_schema(valid_point, QdrantPointContract)
    assert result.passed, f"Valid QDrant point should pass: {result.message}"
    
    # Invalid QDrant point (empty vector)
    invalid_point = {
        "id": "doc_124",
        "vector": [],  # Empty vector should fail
        "metadata": {}
    }
    
    result = validator.validate_schema(invalid_point, QdrantPointContract)
    assert result.failed, "QDrant point with empty vector should fail"


def test_entity_type_contract():
    """Test entity type contract validation."""
    validator = ContractValidator()
    
    # Test valid entity type
    valid_entity_type = EntityTypeContract.PERSON
    assert valid_entity_type == "Person"
    
    # Test enum values
    assert EntityTypeContract.ORGANIZATION == "Organization"
    assert EntityTypeContract.TECHNOLOGY == "Technology"
    assert EntityTypeContract.CONCEPT == "Concept"


def test_simple_contract_test():
    """Test the simple contract test implementation."""
    test = SimpleContractTest()
    result = test.run()
    assert result.passed, f"Simple contract test should pass: {result.message}"


def test_contract_test_result():
    """Test ContractTestResult functionality."""
    # Test passed result
    passed_result = ContractTestResult(
        test_name="Test Pass",
        status=ContractTestStatus.PASSED,
        message="Test passed successfully"
    )
    assert passed_result.passed
    assert not passed_result.failed
    
    # Test failed result
    failed_result = ContractTestResult(
        test_name="Test Fail",
        status=ContractTestStatus.FAILED,
        message="Test failed"
    )
    assert not failed_result.passed
    assert failed_result.failed


if __name__ == "__main__":
    # Run tests directly
    test_contract_validator()
    test_required_fields_validation()
    test_field_types_validation()
    test_qdrant_point_contract()
    test_entity_type_contract()
    test_simple_contract_test()
    test_contract_test_result()
    print("✅ All contract framework tests passed!") 