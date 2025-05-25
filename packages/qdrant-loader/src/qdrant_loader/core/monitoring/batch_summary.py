"""
Batch summary statistics for tracking comprehensive batch metrics.
"""

import statistics
from dataclasses import dataclass, field


@dataclass
class BatchSummary:
    """Comprehensive statistics for a batch of documents."""

    # Basic statistics
    total_documents: int = 0
    total_chunks: int = 0
    total_size_bytes: int = 0
    processing_time: float = 0.0

    # Success/failure metrics
    success_count: int = 0
    error_count: int = 0
    success_rate: float = 0.0

    # Size distribution
    document_sizes: list[int] = field(default_factory=list)
    chunk_sizes: list[int] = field(default_factory=list)

    # Source-specific metrics
    source_counts: dict[str, int] = field(default_factory=dict)
    source_success_rates: dict[str, float] = field(default_factory=dict)

    def update_batch_stats(
        self,
        num_documents: int,
        num_chunks: int,
        total_size: int,
        processing_time: float,
        success_count: int,
        error_count: int,
        document_sizes: list[int] | None = None,
        chunk_sizes: list[int] | None = None,
        source: str | None = None,
    ) -> None:
        """Update batch statistics with new data.

        Args:
            num_documents: Number of documents in the batch
            num_chunks: Number of chunks generated
            total_size: Total size of documents in bytes
            processing_time: Time taken to process the batch
            success_count: Number of successful operations
            error_count: Number of failed operations
            document_sizes: List of individual document sizes
            chunk_sizes: List of individual chunk sizes
            source: Source identifier for the batch
        """
        # Update basic statistics
        self.total_documents += num_documents
        self.total_chunks += num_chunks
        self.total_size_bytes += total_size
        self.processing_time += processing_time

        # Update success/failure metrics
        self.success_count += success_count
        self.error_count += error_count
        total_ops = self.success_count + self.error_count
        self.success_rate = self.success_count / total_ops if total_ops > 0 else 0.0

        # Update size distributions
        if document_sizes:
            self.document_sizes.extend(document_sizes)
        if chunk_sizes:
            self.chunk_sizes.extend(chunk_sizes)

        # Update source-specific metrics
        if source:
            self.source_counts[source] = (
                self.source_counts.get(source, 0) + num_documents
            )
            source_success = (
                self.source_success_rates.get(source, 0.0) * self.source_counts[source]
            )
            source_success += success_count
            self.source_success_rates[source] = (
                source_success / self.source_counts[source]
            )

    def get_size_statistics(self) -> dict[str, dict[str, float]]:
        """Calculate size distribution statistics.

        Returns:
            Dictionary containing size distribution metrics
        """
        stats: dict[str, dict[str, float]] = {}

        if self.document_sizes:
            stats["document_size"] = {
                "min": float(min(self.document_sizes)),
                "max": float(max(self.document_sizes)),
                "mean": float(statistics.mean(self.document_sizes)),
                "median": float(statistics.median(self.document_sizes)),
            }

        if self.chunk_sizes:
            stats["chunk_size"] = {
                "min": float(min(self.chunk_sizes)),
                "max": float(max(self.chunk_sizes)),
                "mean": float(statistics.mean(self.chunk_sizes)),
                "median": float(statistics.median(self.chunk_sizes)),
            }

        return stats

    def get_source_statistics(self) -> dict[str, dict[str, float]]:
        """Get statistics for each source.

        Returns:
            Dictionary containing source-specific metrics
        """
        return {
            source: {
                "document_count": float(count),
                "success_rate": self.source_success_rates.get(source, 0.0),
            }
            for source, count in self.source_counts.items()
        }

    def get_summary(
        self,
    ) -> dict[str, dict[str, int | float] | dict[str, dict[str, float]]]:
        """Get a complete summary of batch statistics.

        Returns:
            Dictionary containing all batch statistics
        """
        return {
            "basic_stats": {
                "total_documents": self.total_documents,
                "total_chunks": self.total_chunks,
                "total_size_bytes": self.total_size_bytes,
                "processing_time": self.processing_time,
                "success_rate": self.success_rate,
            },
            "size_statistics": self.get_size_statistics(),
            "source_statistics": self.get_source_statistics(),
        }
