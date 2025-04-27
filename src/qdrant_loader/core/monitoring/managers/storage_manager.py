"""
Storage manager for performance monitoring metrics.
"""

from typing import Dict, List, Any, Optional
from qdrant_loader.core.monitoring.models import OperationMetrics, BatchMetrics


class MetricsStorage:
    """Storage for performance metrics."""

    def __init__(self):
        """Initialize metrics storage."""
        # Operation metrics
        self.operations: Dict[str, List[OperationMetrics]] = {
            'document_processing': [],
            'batch_processing': []
        }
        self.durations: Dict[str, List[float]] = {}
        self.errors: Dict[str, List[str]] = {}

        # Document metrics
        self.document_counts: Dict[str, int] = {}
        self.document_errors: Dict[str, List[Dict[str, str]]] = {}
        self.document_sizes: Dict[str, List[int]] = {}

        # Chunk metrics
        self.chunk_counts: Dict[str, int] = {}
        self.chunk_sizes: Dict[str, List[int]] = {}
        self.chunk_tokens: Dict[str, List[int]] = {}

        self.batches: Dict[str, List[BatchMetrics]] = {
            'document_batch': [],
            'embedding_batch': [],
            'upsert_batch': []
        }
        self.current_operations: Dict[str, OperationMetrics] = {}
        self.current_batches: Dict[str, BatchMetrics] = {}
        
        # Document-specific metrics
        self.document_metrics: Dict[str, Any] = {
            'total_documents': 0,
            'documents_by_source': {},
            'documents_by_type': {},
            'document_sizes': [],
            'document_processing_times': []
        }
        
        # Chunk-specific metrics
        self.chunk_metrics: Dict[str, Any] = {
            'total_chunks': 0,
            'chunks_per_document': {},
            'chunk_sizes': [],
            'chunk_strategies': {},
            'chunk_processing_times': []
        }

    def add_operation(self, operation_type: str, metrics: OperationMetrics) -> None:
        """Add operation metrics to storage.

        Args:
            operation_type: Type of operation (e.g., 'document_processing')
            metrics: Operation metrics to store
        """
        if operation_type not in self.operations:
            self.operations[operation_type] = []
        self.operations[operation_type].append(metrics)

    def get_operation_metrics(self, operation_type: str) -> List[OperationMetrics]:
        """Get all metrics for a specific operation type.

        Args:
            operation_type: Type of operation to get metrics for

        Returns:
            List of operation metrics for the specified type
        """
        return self.operations.get(operation_type, []) 