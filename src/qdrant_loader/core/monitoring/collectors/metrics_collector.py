"""
Metrics collector for performance monitoring.
"""

from typing import Dict, cast
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