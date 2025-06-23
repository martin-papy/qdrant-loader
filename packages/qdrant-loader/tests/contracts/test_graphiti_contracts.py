"""Contract tests for Graphiti AI service integration."""

import pytest
from datetime import datetime, UTC
from typing import Any, Dict

from tests.contracts.base import ComponentContractTest, ContractTestStatus
from tests.contracts.schemas import (
    GraphitiExtractionRequestContract,
    GraphitiExtractionResultContract,
    GraphitiStorageRequestContract, 
    ExtractedEntityContract,
    ExtractedRelationshipContract,
    TemporalInfoContract,
    EntityTypeContract,
    RelationshipTypeContract,
)


class GraphitiExtractionContractTest(ComponentContractTest):
    """Contract tests for Graphiti entity extraction."""
    
    def __init__(self):
        super().__init__("Graphiti Extraction", "GraphitiManager")
    
    def run(self, **kwargs) -> Any:
        """Run Graphiti extraction contract validation tests."""
        # Test extraction request contract
        valid_request = {
            "text": "John Doe is a software engineer at TechCorp working on the DataFlow project.",
            "document_id": "doc_123",
            "extraction_config": {
                "extract_relationships": True,
                "confidence_threshold": 0.8
            }
        }
        
        result = self.validate_input_contract(valid_request, GraphitiExtractionRequestContract)
        if result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Graphiti extraction request contract failed: {result.message}",
                details=result.details
            )
        
        # Test extraction result contract
        temporal_info = {
            "valid_from": datetime.now(UTC),
            "transaction_time": datetime.now(UTC),
            "version": 1
        }
        
        valid_result = {
            "entities": [
                {
                    "name": "John Doe",
                    "entity_type": EntityTypeContract.PERSON,
                    "confidence": 0.95,
                    "context": "software engineer",
                    "metadata": {"role": "engineer"},
                    "temporal_info": temporal_info,
                    "entity_uuid": "uuid_123"
                }
            ],
            "relationships": [
                {
                    "source_entity": "John Doe",
                    "target_entity": "TechCorp",
                    "relationship_type": RelationshipTypeContract.BELONGS_TO,
                    "confidence": 0.90,
                    "context": "employment",
                    "evidence": "software engineer at TechCorp",
                    "metadata": {},
                    "temporal_info": temporal_info,
                    "relationship_uuid": "rel_123"
                }
            ],
            "processing_time": 1.5,
            "document_id": "doc_123",
            "extraction_metadata": {"model_version": "v1.0"}
        }
        
        result_validation = self.validate_output_contract(valid_result, GraphitiExtractionResultContract)
        if result_validation.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Graphiti extraction result contract failed: {result_validation.message}",
                details=result_validation.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "Graphiti extraction contract validation successful"
        )


class GraphitiStorageContractTest(ComponentContractTest):
    """Contract tests for Graphiti storage operations."""
    
    def __init__(self):
        super().__init__("Graphiti Storage", "GraphitiManager")
    
    def run(self, **kwargs) -> Any:
        """Run Graphiti storage contract validation tests."""
        # Test storage request contract
        temporal_info = {
            "valid_from": datetime.now(UTC),
            "transaction_time": datetime.now(UTC),
            "version": 1
        }
        
        valid_storage_request = {
            "entities": [
                {
                    "name": "TechCorp",
                    "entity_type": EntityTypeContract.ORGANIZATION,
                    "confidence": 0.98,
                    "context": "technology company",
                    "metadata": {"industry": "technology"},
                    "temporal_info": temporal_info,
                    "entity_uuid": "org_456"
                }
            ],
            "relationships": [
                {
                    "source_entity": "DataFlow",
                    "target_entity": "TechCorp",
                    "relationship_type": RelationshipTypeContract.BELONGS_TO,
                    "confidence": 0.85,
                    "context": "project ownership",
                    "evidence": "DataFlow project at TechCorp",
                    "metadata": {"project_type": "software"},
                    "temporal_info": temporal_info,
                    "relationship_uuid": "rel_456"
                }
            ],
            "transaction_id": "tx_789",
            "storage_config": {"batch_size": 100}
        }
        
        result = self.validate_input_contract(valid_storage_request, GraphitiStorageRequestContract)
        if result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Graphiti storage request contract failed: {result.message}",
                details=result.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "Graphiti storage contract validation successful"
        )


class GraphitiEntityContractTest(ComponentContractTest):
    """Contract tests for Graphiti entity structures."""
    
    def __init__(self):
        super().__init__("Graphiti Entity Validation", "GraphitiManager")
    
    def run(self, **kwargs) -> Any:
        """Run Graphiti entity contract validation tests."""
        # Test temporal info contract
        valid_temporal = {
            "valid_from": datetime.now(UTC),
            "transaction_time": datetime.now(UTC),
            "version": 1
        }
        
        temporal_result = self.validate_input_contract(valid_temporal, TemporalInfoContract)
        if temporal_result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Temporal info contract failed: {temporal_result.message}",
                details=temporal_result.details
            )
        
        # Test entity contract
        valid_entity = {
            "name": "Machine Learning",
            "entity_type": EntityTypeContract.CONCEPT,
            "confidence": 0.92,
            "context": "AI technology domain",
            "metadata": {"domain": "artificial_intelligence"},
            "temporal_info": valid_temporal,
            "entity_uuid": "concept_ml"
        }
        
        entity_result = self.validate_input_contract(valid_entity, ExtractedEntityContract)
        if entity_result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Entity contract failed: {entity_result.message}",
                details=entity_result.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "Graphiti entity contract validation successful"
        )


def test_graphiti_extraction_contracts():
    """Test Graphiti extraction contracts."""
    test = GraphitiExtractionContractTest()
    result = test.run()
    assert result.passed, f"Graphiti extraction contract test failed: {result.message}"


def test_graphiti_storage_contracts():
    """Test Graphiti storage contracts."""
    test = GraphitiStorageContractTest()
    result = test.run()
    assert result.passed, f"Graphiti storage contract test failed: {result.message}"


def test_graphiti_entity_contracts():
    """Test Graphiti entity contracts."""
    test = GraphitiEntityContractTest()
    result = test.run()
    assert result.passed, f"Graphiti entity contract test failed: {result.message}" 