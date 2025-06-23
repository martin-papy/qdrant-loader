"""Contract tests for processing pipeline components."""

import pytest
from datetime import datetime, UTC
from typing import Any, Dict

from tests.contracts.base import ComponentContractTest, ContractTestStatus
from tests.contracts.schemas import (
    DocumentProcessingRequestContract,
    DocumentProcessingResultContract,
    EmbeddingRequestContract,
    EmbeddingResultContract,
)


class DocumentProcessingContractTest(ComponentContractTest):
    """Contract tests for document processing pipeline."""
    
    def __init__(self):
        super().__init__("Document Processing", "DocumentProcessor")
    
    def run(self, **kwargs) -> Any:
        """Run document processing contract validation tests."""
        # Test processing request contract
        valid_request = {
            "document_id": "doc_456",
            "content": "This is a test document about artificial intelligence and machine learning technologies.",
            "document_type": "text/plain",
            "source_metadata": {
                "source": "test_upload",
                "author": "Test User",
                "created_at": datetime.now(UTC).isoformat()
            },
            "processing_options": {
                "extract_entities": True,
                "generate_embeddings": True,
                "chunk_size": 1000
            }
        }
        
        result = self.validate_input_contract(valid_request, DocumentProcessingRequestContract)
        if result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Document processing request contract failed: {result.message}",
                details=result.details
            )
        
        # Test processing result contract
        valid_result = {
            "document_id": "doc_456",
            "qdrant_point_id": "point_456",
            "neo4j_node_ids": ["node_789", "node_790"],
            "entities_extracted": 5,
            "relationships_extracted": 3,
            "processing_time": 2.5,
            "status": "completed",
            "errors": []
        }
        
        result_validation = self.validate_output_contract(valid_result, DocumentProcessingResultContract)
        if result_validation.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Document processing result contract failed: {result_validation.message}",
                details=result_validation.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "Document processing contract validation successful"
        )


class EmbeddingServiceContractTest(ComponentContractTest):
    """Contract tests for embedding service."""
    
    def __init__(self):
        super().__init__("Embedding Service", "EmbeddingService")
    
    def run(self, **kwargs) -> Any:
        """Run embedding service contract validation tests."""
        # Test embedding request contract
        valid_request = {
            "text": "Machine learning is a subset of artificial intelligence.",
            "model_name": "text-embedding-ada-002",
            "embedding_config": {
                "normalize": True,
                "batch_size": 1
            }
        }
        
        result = self.validate_input_contract(valid_request, EmbeddingRequestContract)
        if result.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Embedding request contract failed: {result.message}",
                details=result.details
            )
        
        # Test embedding result contract
        valid_result = {
            "embedding": [0.1, 0.2, -0.1, 0.5, 0.8] * 307,  # 1535 dimensions (typical for ada-002)
            "model_name": "text-embedding-ada-002",
            "dimensions": 1535,
            "processing_time": 0.3
        }
        
        result_validation = self.validate_output_contract(valid_result, EmbeddingResultContract)
        if result_validation.failed:
            return self.create_result(
                ContractTestStatus.FAILED,
                f"Embedding result contract failed: {result_validation.message}",
                details=result_validation.details
            )
        
        return self.create_result(
            ContractTestStatus.PASSED,
            "Embedding service contract validation successful"
        )


def test_document_processing_contracts():
    """Test document processing contracts."""
    test = DocumentProcessingContractTest()
    result = test.run()
    assert result.passed, f"Document processing contract test failed: {result.message}"


def test_embedding_service_contracts():
    """Test embedding service contracts."""
    test = EmbeddingServiceContractTest()
    result = test.run()
    assert result.passed, f"Embedding service contract test failed: {result.message}" 