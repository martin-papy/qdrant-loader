"""Temporal index types and data structures.

This module defines the core types, enums, and data classes used
throughout the temporal indexing system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ...utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class IndexType(Enum):
    """Types of temporal indexes."""

    BTREE = "btree"
    COMPOSITE = "composite"
    HASH = "hash"
    RANGE = "range"
    CLUSTERING = "clustering"


class IndexStatus(Enum):
    """Status of a temporal index."""

    BUILDING = "building"
    ACTIVE = "active"
    REBUILDING = "rebuilding"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class TemporalIndexConfig:
    """Configuration for temporal indexes."""

    index_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    index_name: str = ""
    index_type: IndexType = IndexType.BTREE

    # Index fields
    temporal_field: str = "valid_from"  # Primary temporal field
    entity_field: Optional[str] = None  # Entity identifier field
    additional_fields: List[str] = field(default_factory=list)

    # Performance settings
    page_size: int = 4096
    cache_size_mb: int = 64
    max_depth: int = 10

    # Maintenance settings
    auto_rebuild: bool = True
    rebuild_threshold: float = 0.3  # Rebuild when 30% fragmented
    maintenance_interval_hours: int = 24

    # Clustering settings (for clustering indexes)
    cluster_by_entity: bool = True
    cluster_time_window_hours: int = 24

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "index_id": self.index_id,
            "index_name": self.index_name,
            "index_type": self.index_type.value,
            "temporal_field": self.temporal_field,
            "entity_field": self.entity_field,
            "additional_fields": self.additional_fields,
            "page_size": self.page_size,
            "cache_size_mb": self.cache_size_mb,
            "max_depth": self.max_depth,
            "auto_rebuild": self.auto_rebuild,
            "rebuild_threshold": self.rebuild_threshold,
            "maintenance_interval_hours": self.maintenance_interval_hours,
            "cluster_by_entity": self.cluster_by_entity,
            "cluster_time_window_hours": self.cluster_time_window_hours,
        }


@dataclass
class TemporalIndexStatistics:
    """Statistics for temporal index performance."""

    index_id: str
    index_name: str

    # Size statistics
    total_entries: int = 0
    index_size_bytes: int = 0
    memory_usage_bytes: int = 0

    # Performance statistics
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_query_time_ms: float = 0.0

    # Maintenance statistics
    last_rebuild: Optional[datetime] = None
    fragmentation_ratio: float = 0.0
    maintenance_operations: int = 0

    # Time range coverage
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None

    def cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "index_id": self.index_id,
            "index_name": self.index_name,
            "total_entries": self.total_entries,
            "index_size_bytes": self.index_size_bytes,
            "memory_usage_bytes": self.memory_usage_bytes,
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_ratio": self.cache_hit_ratio(),
            "average_query_time_ms": self.average_query_time_ms,
            "last_rebuild": (
                self.last_rebuild.isoformat() if self.last_rebuild else None
            ),
            "fragmentation_ratio": self.fragmentation_ratio,
            "maintenance_operations": self.maintenance_operations,
            "earliest_timestamp": (
                self.earliest_timestamp.isoformat() if self.earliest_timestamp else None
            ),
            "latest_timestamp": (
                self.latest_timestamp.isoformat() if self.latest_timestamp else None
            ),
        }


@dataclass
class TemporalIndex:
    """Base class for temporal indexes."""

    config: TemporalIndexConfig
    status: IndexStatus = IndexStatus.BUILDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Index data structure (implementation-specific)
    _index_data: Dict[str, Any] = field(default_factory=dict)
    _cache: Dict[str, Any] = field(default_factory=dict)

    # Statistics
    statistics: TemporalIndexStatistics = field(init=False)

    def __post_init__(self):
        """Initialize statistics after creation."""
        self.statistics = TemporalIndexStatistics(
            index_id=self.config.index_id, index_name=self.config.index_name
        )

    def is_active(self) -> bool:
        """Check if index is active and ready for queries."""
        return self.status == IndexStatus.ACTIVE

    def needs_rebuild(self) -> bool:
        """Check if index needs rebuilding."""
        return (
            self.statistics.fragmentation_ratio > self.config.rebuild_threshold
            or self.status == IndexStatus.ERROR
        )

    async def rebuild(self) -> bool:
        """Rebuild the index from scratch.

        Returns:
            True if rebuild was successful
        """
        # Base implementation - should be overridden by subclasses
        logger.warning(
            f"Rebuild not implemented for index type {self.config.index_type}"
        )
        return False

    def get_memory_usage(self) -> int:
        """Calculate approximate memory usage in bytes.

        Returns:
            Memory usage in bytes
        """
        # Base implementation - should be overridden by subclasses
        return 0


@dataclass
class TemporalQueryHint:
    """Query optimization hints for temporal queries."""

    # Index preferences
    preferred_indexes: List[str] = field(default_factory=list)
    avoid_indexes: List[str] = field(default_factory=list)

    # Query strategy hints
    use_clustering: bool = True
    use_caching: bool = True
    parallel_execution: bool = False

    # Performance hints
    expected_result_size: Optional[int] = None
    time_range_selectivity: Optional[float] = None  # 0.0 to 1.0

    # Memory hints
    max_memory_mb: Optional[int] = None
    streaming_results: bool = False


@dataclass
class TemporalQueryPlan:
    """Execution plan for temporal queries."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_hash: str = ""

    # Selected indexes
    primary_index: Optional[str] = None
    secondary_indexes: List[str] = field(default_factory=list)

    # Execution strategy
    execution_strategy: str = "sequential"  # sequential, parallel, streaming
    estimated_cost: float = 0.0
    estimated_rows: int = 0

    # Optimization decisions
    use_index_intersection: bool = False
    use_temporal_clustering: bool = False
    cache_intermediate_results: bool = False

    # Performance predictions
    estimated_execution_time_ms: float = 0.0
    estimated_memory_usage_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "plan_id": self.plan_id,
            "query_hash": self.query_hash,
            "primary_index": self.primary_index,
            "secondary_indexes": self.secondary_indexes,
            "execution_strategy": self.execution_strategy,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "use_index_intersection": self.use_index_intersection,
            "use_temporal_clustering": self.use_temporal_clustering,
            "cache_intermediate_results": self.cache_intermediate_results,
            "estimated_execution_time_ms": self.estimated_execution_time_ms,
            "estimated_memory_usage_mb": self.estimated_memory_usage_mb,
        }
