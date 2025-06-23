"""Contract tests for database layer components (QDrant and Neo4j)."""

import pytest
from datetime import datetime, UTC
from typing import Any, Dict

from tests.contracts.base import ComponentContractTest, ContractTestStatus
from tests.contracts.schemas import (
    QdrantPointContract,
    QdrantSearchRequestContract,
    Neo4jNodeContract,
    IDMappingContract,
)


class QdrantContractTest(ComponentContractTest):
    """Contract tests for QDrant database operations."""
    
    def __init__(self):
        super().__init__("QDrant Operations", "QdrantManager")
    
    def run(self, **kwargs) -> Any:
        """Run QDrant contract validation tests."""
        # Test point insertion contract
        valid_point = {
            "id": "doc_123",
            "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            "metadata": {"document_type": "text", "source": "test"}
        }
        
        result = self.validate_input_contract(valid_point, QdrantPointContract)
        if result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"QDrant point contract failed: {result.message}",
                details=result.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "QDrant contract validation successful"
        )


class Neo4jContractTest(ComponentContractTest):
    """Contract tests for Neo4j database operations."""
    
    def __init__(self):
        super().__init__("Neo4j Operations", "Neo4jManager")
    
    def run(self, **kwargs) -> Any:
        """Run Neo4j contract validation tests."""
        # Test node creation contract
        valid_node = {
            "id": "entity_123",
            "labels": ["Document", "TextDocument"], 
            "properties": {
                "name": "Test Document",
                "created_at": datetime.now(UTC).isoformat()
            }
        }
        
        result = self.validate_input_contract(valid_node, Neo4jNodeContract)
        if result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Neo4j node contract failed: {result.message}",
                details=result.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "Neo4j contract validation successful"
        )


def test_qdrant_contracts():
    """Test QDrant database contracts."""
    test = QdrantContractTest()
    result = test.run()
    assert result.passed, f"QDrant contract test failed: {result.message}"


def test_neo4j_contracts():
    """Test Neo4j database contracts."""
    test = Neo4jContractTest()
    result = test.run()
    assert result.passed, f"Neo4j contract test failed: {result.message}" 