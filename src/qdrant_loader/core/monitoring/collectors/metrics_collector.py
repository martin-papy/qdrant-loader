"""
Metrics collector for performance monitoring.
"""

from typing import Dict, cast, Any
from qdrant_loader.core.monitoring.managers.storage_manager import MetricsStorage


class MetricsCollector:
    """Collects and aggregates metrics."""
    def __init__(self, storage: MetricsStorage):
        self.storage = storage

    async def collect_metrics(self) -> Dict:
        """Collect and aggregate metrics."""
        return {
            'operations': await self._collect_operation_metrics(),
            'batches': await self._collect_batch_metrics(),
            'documents': await self._collect_document_metrics(),
            'chunks': await self._collect_chunk_metrics(),
            'overall': await self._collect_overall_metrics()
        }

    async def _collect_operation_metrics(self) -> Dict:
        """Collect operation metrics."""
        metrics = {}
        for op_type, operations in self.storage.operations.items():
            if not operations:
                continue

            valid_operations = [op for op in operations if op.duration is not None]
            if not valid_operations:
                continue

            durations = [cast(float, op.duration) for op in valid_operations]
            metrics[op_type] = {
                'count': len(valid_operations),
                'success_count': sum(1 for op in valid_operations if op.success),
                'error_count': sum(1 for op in valid_operations if not op.success),
                'average_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'durations': durations
            }
        return metrics

    async def _collect_document_metrics(self) -> Dict[str, Any]:
        """Collect document-specific metrics."""
        doc_metrics = self.storage.document_metrics
        return {
            'total_documents': doc_metrics['total_documents'],
            'documents_by_source': doc_metrics['documents_by_source'],
            'documents_by_type': doc_metrics['documents_by_type'],
            'average_document_size': sum(doc_metrics['document_sizes']) / len(doc_metrics['document_sizes']) if doc_metrics['document_sizes'] else 0,
            'min_document_size': min(doc_metrics['document_sizes']) if doc_metrics['document_sizes'] else 0,
            'max_document_size': max(doc_metrics['document_sizes']) if doc_metrics['document_sizes'] else 0
        }

    async def _collect_batch_metrics(self) -> Dict:
        """Collect batch metrics."""
        metrics = {}
        for batch_type, batches in self.storage.batches.items():
            if not batches:
                continue

            valid_batches = [b for b in batches if b.duration is not None]
            if not valid_batches:
                continue

            durations = [cast(float, b.duration) for b in valid_batches]
            metrics[batch_type] = {
                'count': len(valid_batches),
                'success_count': sum(1 for b in valid_batches if b.error_count == 0),
                'error_count': sum(1 for b in valid_batches if b.error_count > 0),
                'average_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'average_batch_size': sum(b.batch_size for b in valid_batches) / len(valid_batches),
                'durations': durations
            }
        return metrics

    async def _collect_chunk_metrics(self) -> Dict[str, Any]:
        """Collect chunk-specific metrics."""
        chunk_metrics = self.storage.chunk_metrics
        total_documents = len(chunk_metrics['chunks_per_document'])
        return {
            'total_chunks': chunk_metrics['total_chunks'],
            'average_chunks_per_document': sum(chunk_metrics['chunks_per_document'].values()) / total_documents if total_documents > 0 else 0,
            'average_chunk_size': sum(chunk_metrics['chunk_sizes']) / len(chunk_metrics['chunk_sizes']) if chunk_metrics['chunk_sizes'] else 0,
            'min_chunk_size': min(chunk_metrics['chunk_sizes']) if chunk_metrics['chunk_sizes'] else 0,
            'max_chunk_size': max(chunk_metrics['chunk_sizes']) if chunk_metrics['chunk_sizes'] else 0,
            'chunk_strategies': chunk_metrics['chunk_strategies']
        }

    async def _collect_overall_metrics(self) -> Dict:
        """Collect overall metrics."""
        operation_metrics = await self._collect_operation_metrics()
        batch_metrics = await self._collect_batch_metrics()

        total_operations = sum(m['count'] for m in operation_metrics.values())
        successful_operations = sum(m['success_count'] for m in operation_metrics.values())
        failed_operations = sum(m['error_count'] for m in operation_metrics.values())
        total_batches = sum(m['count'] for m in batch_metrics.values())
        successful_batches = sum(m['success_count'] for m in batch_metrics.values())
        failed_batches = sum(m['error_count'] for m in batch_metrics.values())

        all_durations = [
            cast(float, op.duration)
            for ops in self.storage.operations.values()
            for op in ops
            if op.duration is not None
        ]
        all_batch_durations = [
            cast(float, b.duration)
            for batches in self.storage.batches.values()
            for b in batches
            if b.duration is not None
        ]

        return {
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'total_batches': total_batches,
            'successful_batches': successful_batches,
            'failed_batches': failed_batches,
            'average_operation_duration': sum(all_durations) / len(all_durations) if all_durations else 0,
            'average_batch_duration': sum(all_batch_durations) / len(all_batch_durations) if all_batch_durations else 0
        } 