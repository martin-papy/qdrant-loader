"""Configuration for pipeline workers and queues."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for pipeline workers and queues."""

    max_chunk_workers: int = 10
    max_embed_workers: int = 4
    max_upsert_workers: int = 4
    queue_size: int = 1000
    upsert_batch_size: int | None = None
    enable_metrics: bool = False
