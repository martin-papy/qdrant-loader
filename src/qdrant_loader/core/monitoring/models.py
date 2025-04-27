"""
Data models for performance monitoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    is_completed: bool = False


@dataclass
class BatchMetrics:
    """Metrics for a batch of operations."""
    batch_size: int
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success_count: int = 0
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    is_completed: bool = False


@dataclass
class MonitorConfig:
    """Configuration for performance monitoring."""
    metrics_dir: Optional[str] = None
    lock_timeout: float = 10.0
    lock_max_retries: int = 3
    lock_retry_delay: float = 0.1
    cleanup_interval: float = 60.0
    max_operation_age: float = 3600.0 