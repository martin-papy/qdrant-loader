"""
Processing statistics for tracking rate-related metrics.
"""

import time
from dataclasses import dataclass, field


@dataclass
class ProcessingStats:
    """Statistics for tracking processing rates and performance metrics."""

    # Overall processing metrics
    total_documents: int = 0
    total_chunks: int = 0
    total_processing_time: float = 0.0

    # Rate tracking
    overall_rate: float = 0.0  # documents per second
    chunk_rate: float = 0.0  # chunks per second

    # Time-based rate tracking (5-second windows)
    rate_windows: list[dict[str, float]] = field(default_factory=list)
    current_window_start: float | None = None
    current_window_docs: int = 0
    current_window_chunks: int = 0

    # Source-specific metrics
    source_metrics: dict[str, dict[str, float]] = field(default_factory=dict)

    def update_rates(
        self, num_documents: int, num_chunks: int, processing_time: float
    ) -> None:
        """Update processing rates with new batch data.

        Args:
            num_documents: Number of documents processed
            num_chunks: Number of chunks generated
            processing_time: Time taken to process the batch
        """
        self.total_documents += num_documents
        self.total_chunks += num_chunks
        self.total_processing_time += processing_time

        # Update overall rates
        if self.total_processing_time > 0:
            self.overall_rate = self.total_documents / self.total_processing_time
            self.chunk_rate = self.total_chunks / self.total_processing_time

        # Update time-based window
        current_time = time.time()
        if self.current_window_start is None:
            self.current_window_start = current_time

        self.current_window_docs += num_documents
        self.current_window_chunks += num_chunks

        # Check if we need to create a new window
        if current_time - self.current_window_start >= 5.0:
            window_duration = current_time - self.current_window_start
            self.rate_windows.append(
                {
                    "start_time": self.current_window_start,
                    "end_time": current_time,
                    "doc_rate": self.current_window_docs / window_duration,
                    "chunk_rate": self.current_window_chunks / window_duration,
                }
            )

            # Reset current window
            self.current_window_start = current_time
            self.current_window_docs = 0
            self.current_window_chunks = 0

    def update_source_metrics(
        self, source: str, num_documents: int, processing_time: float
    ) -> None:
        """Update metrics for a specific source.

        Args:
            source: Source identifier
            num_documents: Number of documents processed
            processing_time: Time taken to process the documents
        """
        if source not in self.source_metrics:
            self.source_metrics[source] = {
                "total_documents": 0,
                "total_time": 0.0,
                "rate": 0.0,
            }

        metrics = self.source_metrics[source]
        metrics["total_documents"] += num_documents
        metrics["total_time"] += processing_time

        if metrics["total_time"] > 0:
            metrics["rate"] = metrics["total_documents"] / metrics["total_time"]

    def get_latest_rates(self) -> dict[str, float]:
        """Get the most recent processing rates.

        Returns:
            Dictionary containing the latest rate metrics
        """
        return {
            "overall_rate": self.overall_rate,
            "chunk_rate": self.chunk_rate,
            "current_window_rate": (
                self.current_window_docs / (time.time() - self.current_window_start)
                if self.current_window_start is not None
                else 0.0
            ),
        }
