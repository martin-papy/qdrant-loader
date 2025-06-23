"""Base classes and utilities for contract testing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError


class ContractTestStatus(Enum):
    """Status of contract test execution."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ContractTestResult:
    """Result of a contract test execution."""
    
    test_name: str
    status: ContractTestStatus
    message: str = ""
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        """Check if the test passed."""
        return self.status == ContractTestStatus.PASSED
    
    @property
    def failed(self) -> bool:
        """Check if the test failed."""
        return self.status == ContractTestStatus.FAILED


class ContractValidator:
    """Validates data against Pydantic schemas for contract testing."""
    
    @staticmethod
    def validate_schema(data: Any, schema: Type[BaseModel]) -> ContractTestResult:
        """Validate data against a Pydantic schema.
        
        Args:
            data: Data to validate
            schema: Pydantic model schema
            
        Returns:
            ContractTestResult indicating success or failure
        """
        try:
            # Attempt to validate the data
            if isinstance(data, dict):
                validated = schema(**data)
            else:
                validated = schema.parse_obj(data)
            
            return ContractTestResult(
                test_name=f"Schema validation: {schema.__name__}",
                status=ContractTestStatus.PASSED,
                message=f"Data successfully validated against {schema.__name__}",
                details={"validated_data": validated.model_dump()}
            )
            
        except ValidationError as e:
            return ContractTestResult(
                test_name=f"Schema validation: {schema.__name__}",
                status=ContractTestStatus.FAILED,
                message=f"Schema validation failed: {str(e)}",
                details={"validation_errors": e.errors(), "input_data": data}
            )
        except Exception as e:
            return ContractTestResult(
                test_name=f"Schema validation: {schema.__name__}",
                status=ContractTestStatus.ERROR,
                message=f"Unexpected error during validation: {str(e)}",
                details={"error_type": type(e).__name__, "input_data": data}
            )
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> ContractTestResult:
        """Validate that required fields are present in data.
        
        Args:
            data: Data dictionary to check
            required_fields: List of required field names
            
        Returns:
            ContractTestResult indicating success or failure
        """
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return ContractTestResult(
                test_name="Required fields validation",
                status=ContractTestStatus.FAILED,
                message=f"Missing required fields: {missing_fields}",
                details={"missing_fields": missing_fields, "provided_fields": list(data.keys())}
            )
        
        return ContractTestResult(
            test_name="Required fields validation",
            status=ContractTestStatus.PASSED,
            message="All required fields present",
            details={"validated_fields": required_fields}
        )
    
    @staticmethod
    def validate_field_types(data: Dict[str, Any], field_types: Dict[str, Type]) -> ContractTestResult:
        """Validate field types in data.
        
        Args:
            data: Data dictionary to check
            field_types: Dictionary mapping field names to expected types
            
        Returns:
            ContractTestResult indicating success or failure
        """
        type_errors = []
        
        for field_name, expected_type in field_types.items():
            if field_name in data:
                actual_value = data[field_name]
                if not isinstance(actual_value, expected_type):
                    type_errors.append({
                        "field": field_name,
                        "expected_type": expected_type.__name__,
                        "actual_type": type(actual_value).__name__,
                        "actual_value": actual_value
                    })
        
        if type_errors:
            return ContractTestResult(
                test_name="Field types validation",
                status=ContractTestStatus.FAILED,
                message=f"Type validation failed for {len(type_errors)} fields",
                details={"type_errors": type_errors}
            )
        
        return ContractTestResult(
            test_name="Field types validation",
            status=ContractTestStatus.PASSED,
            message="All field types are correct",
            details={"validated_fields": list(field_types.keys())}
        )


class ContractTest(ABC):
    """Abstract base class for contract tests."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.validator = ContractValidator()
    
    @abstractmethod
    def run(self, *args, **kwargs) -> ContractTestResult:
        """Execute the contract test.
        
        Returns:
            ContractTestResult with test outcome
        """
        pass
    
    def validate_input_contract(self, data: Any, schema: Type[BaseModel]) -> ContractTestResult:
        """Validate input data against a contract schema.
        
        Args:
            data: Input data to validate
            schema: Pydantic schema for validation
            
        Returns:
            ContractTestResult
        """
        return self.validator.validate_schema(data, schema)
    
    def validate_output_contract(self, data: Any, schema: Type[BaseModel]) -> ContractTestResult:
        """Validate output data against a contract schema.
        
        Args:
            data: Output data to validate
            schema: Pydantic schema for validation
            
        Returns:
            ContractTestResult
        """
        return self.validator.validate_schema(data, schema)


class ComponentContractTest(ContractTest):
    """Base class for testing contracts between components."""
    
    def __init__(self, name: str, component_name: str, description: str = ""):
        super().__init__(name, description)
        self.component_name = component_name
    
    def create_result(self, status: ContractTestStatus, message: str, **details) -> ContractTestResult:
        """Create a test result with component context.
        
        Args:
            status: Test status
            message: Result message
            **details: Additional details
            
        Returns:
            ContractTestResult
        """
        return ContractTestResult(
            test_name=f"{self.component_name}: {self.name}",
            status=status,
            message=message,
            details=details
        )


class ContractTestSuite:
    """Collection of contract tests for execution."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tests: List[ContractTest] = []
    
    def add_test(self, test: ContractTest) -> None:
        """Add a test to the suite.
        
        Args:
            test: ContractTest to add
        """
        self.tests.append(test)
    
    def run_all(self) -> List[ContractTestResult]:
        """Run all tests in the suite.
        
        Returns:
            List of ContractTestResult
        """
        results = []
        for test in self.tests:
            try:
                start_time = datetime.now(UTC)
                result = test.run()
                end_time = datetime.now(UTC)
                result.execution_time = (end_time - start_time).total_seconds()
                results.append(result)
            except Exception as e:
                results.append(ContractTestResult(
                    test_name=test.name,
                    status=ContractTestStatus.ERROR,
                    message=f"Test execution failed: {str(e)}",
                    details={"error_type": type(e).__name__}
                ))
        return results
    
    def run_filtered(self, filter_func: callable) -> List[ContractTestResult]:
        """Run tests that match the filter criteria.
        
        Args:
            filter_func: Function to filter tests
            
        Returns:
            List of ContractTestResult
        """
        filtered_tests = [test for test in self.tests if filter_func(test)]
        suite = ContractTestSuite(f"{self.name} (filtered)", self.description)
        suite.tests = filtered_tests
        return suite.run_all()
    
    @property
    def test_count(self) -> int:
        """Get the number of tests in the suite."""
        return len(self.tests) 