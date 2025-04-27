"""
Storage manager for performance monitoring metrics.
"""

from typing import Dict, List
from qdrant_loader.core.monitoring.models import OperationMetrics, BatchMetrics


class MetricsStorage:
    """Handles storage and retrieval of metrics."""
    def __init__(self):
        self.operations: Dict[str, List[OperationMetrics]] = {
            'document_processing': [],
            'chunking': [],
            'embedding': [],
            'upserting': [],
            'state_update': []
        }
        self.batches: Dict[str, List[BatchMetrics]] = {
            'document_batch': [],
            'embedding_batch': [],
            'upsert_batch': []
        }
        self.current_operations: Dict[str, OperationMetrics] = {}
        self.current_batches: Dict[str, BatchMetrics] = {} 