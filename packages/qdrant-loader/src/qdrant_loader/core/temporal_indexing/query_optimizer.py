"""Temporal query optimizer.

This module provides query optimization capabilities for temporal queries,
including index selection, query planning, and performance estimation.
"""

import hashlib
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ...utils.logging import LoggingConfig
from .index_types import (
    IndexType,
    TemporalIndex,
    TemporalQueryHint,
    TemporalQueryPlan,
)

logger = LoggingConfig.get_logger(__name__)


class TemporalQueryOptimizer:
    """Optimizer for temporal queries."""

    def __init__(self):
        """Initialize the query optimizer."""
        self.available_indexes: Dict[str, TemporalIndex] = {}
        self.query_cache: Dict[str, TemporalQueryPlan] = {}
        self.performance_history: Dict[str, List[float]] = {}

    def register_index(self, index: TemporalIndex) -> None:
        """Register an index with the optimizer.

        Args:
            index: Temporal index to register
        """
        self.available_indexes[index.config.index_id] = index
        logger.debug(f"Registered index {index.config.index_name} with optimizer")

    def unregister_index(self, index_id: str) -> None:
        """Unregister an index from the optimizer.

        Args:
            index_id: ID of index to unregister
        """
        if index_id in self.available_indexes:
            del self.available_indexes[index_id]
            logger.debug(f"Unregistered index {index_id} from optimizer")

    def create_query_plan(
        self,
        query_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        entity_ids: Optional[List[str]] = None,
        hints: Optional[TemporalQueryHint] = None,
    ) -> TemporalQueryPlan:
        """Create an optimized query execution plan.

        Args:
            query_type: Type of query (range, point, entity_timeline, etc.)
            start_time: Optional start time for range queries
            end_time: Optional end time for range queries
            entity_ids: Optional list of entity IDs to filter by
            hints: Optional query optimization hints

        Returns:
            Optimized query execution plan
        """
        # Create query signature for caching
        query_signature = self._create_query_signature(
            query_type, start_time, end_time, entity_ids, hints
        )

        # Check cache first
        if query_signature in self.query_cache:
            cached_plan = self.query_cache[query_signature]
            logger.debug(f"Using cached query plan {cached_plan.plan_id}")
            return cached_plan

        # Create new plan
        plan = TemporalQueryPlan(query_hash=query_signature)

        # Select optimal indexes
        selected_indexes = self._select_indexes(
            query_type, start_time, end_time, entity_ids, hints
        )

        if selected_indexes:
            plan.primary_index = selected_indexes[0]
            plan.secondary_indexes = selected_indexes[1:]

        # Determine execution strategy
        plan.execution_strategy = self._determine_execution_strategy(
            query_type, selected_indexes, hints
        )

        # Estimate costs and performance
        plan.estimated_cost = self._estimate_query_cost(
            query_type, selected_indexes, start_time, end_time, entity_ids
        )
        plan.estimated_rows = self._estimate_result_size(
            query_type, selected_indexes, start_time, end_time, entity_ids
        )
        plan.estimated_execution_time_ms = self._estimate_execution_time(
            plan.estimated_cost, plan.execution_strategy
        )
        plan.estimated_memory_usage_mb = self._estimate_memory_usage(
            plan.estimated_rows, plan.execution_strategy
        )

        # Set optimization flags
        plan.use_index_intersection = self._should_use_index_intersection(
            selected_indexes, query_type
        )
        plan.use_temporal_clustering = self._should_use_temporal_clustering(
            query_type, hints
        )
        plan.cache_intermediate_results = self._should_cache_intermediate_results(
            plan.estimated_execution_time_ms, plan.estimated_memory_usage_mb
        )

        # Cache the plan
        self.query_cache[query_signature] = plan

        logger.debug(f"Created query plan {plan.plan_id} for {query_type}")
        return plan

    def _create_query_signature(
        self,
        query_type: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        entity_ids: Optional[List[str]],
        hints: Optional[TemporalQueryHint],
    ) -> str:
        """Create a unique signature for the query."""
        signature_parts = [query_type]

        if start_time:
            signature_parts.append(f"start:{start_time.isoformat()}")
        if end_time:
            signature_parts.append(f"end:{end_time.isoformat()}")
        if entity_ids:
            signature_parts.append(f"entities:{','.join(sorted(entity_ids))}")
        if hints:
            signature_parts.append(f"hints:{hints.preferred_indexes}")

        signature_str = "|".join(signature_parts)
        return hashlib.md5(signature_str.encode()).hexdigest()

    def _select_indexes(
        self,
        query_type: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        entity_ids: Optional[List[str]],
        hints: Optional[TemporalQueryHint],
    ) -> List[str]:
        """Select the best indexes for the query."""
        candidates = []

        # Filter active indexes
        active_indexes = {
            idx_id: idx
            for idx_id, idx in self.available_indexes.items()
            if idx.is_active()
        }

        if not active_indexes:
            return []

        # Apply hint preferences
        if hints and hints.preferred_indexes:
            preferred = [
                idx_id for idx_id in hints.preferred_indexes if idx_id in active_indexes
            ]
            if preferred:
                return preferred

        # Apply hint avoidance
        avoid_set = set(hints.avoid_indexes) if hints and hints.avoid_indexes else set()

        # Score indexes based on query type and characteristics
        for idx_id, index in active_indexes.items():
            if idx_id in avoid_set:
                continue

            score = self._score_index_for_query(
                index, query_type, start_time, end_time, entity_ids
            )
            candidates.append((score, idx_id))

        # Sort by score (higher is better)
        candidates.sort(reverse=True)

        # Return top candidates
        return [idx_id for _, idx_id in candidates[:3]]

    def _score_index_for_query(
        self,
        index: TemporalIndex,
        query_type: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        entity_ids: Optional[List[str]],
    ) -> float:
        """Score an index for a specific query."""
        score = 0.0

        # Base score by index type
        if query_type == "range_query":
            if index.config.index_type == IndexType.BTREE:
                score += 10.0
            elif index.config.index_type == IndexType.COMPOSITE:
                score += 8.0
        elif query_type == "entity_timeline":
            if index.config.index_type == IndexType.COMPOSITE:
                score += 10.0
            elif index.config.index_type == IndexType.BTREE:
                score += 6.0
        elif query_type == "point_query":
            if index.config.index_type == IndexType.HASH:
                score += 10.0
            elif index.config.index_type == IndexType.BTREE:
                score += 8.0

        # Performance-based scoring
        stats = index.statistics
        if stats.total_queries > 0:
            # Favor indexes with good performance
            if stats.average_query_time_ms < 10:
                score += 5.0
            elif stats.average_query_time_ms < 50:
                score += 3.0
            elif stats.average_query_time_ms < 100:
                score += 1.0

            # Favor indexes with good cache hit ratio
            cache_ratio = stats.cache_hit_ratio()
            score += cache_ratio * 3.0

        # Size-based scoring (smaller indexes are faster for small queries)
        if stats.total_entries < 10000:
            score += 2.0
        elif stats.total_entries < 100000:
            score += 1.0

        # Fragmentation penalty
        score -= stats.fragmentation_ratio * 5.0

        return max(0.0, score)

    def _determine_execution_strategy(
        self,
        query_type: str,
        selected_indexes: List[str],
        hints: Optional[TemporalQueryHint],
    ) -> str:
        """Determine the best execution strategy."""
        if hints and hints.parallel_execution and len(selected_indexes) > 1:
            return "parallel"
        elif hints and hints.streaming_results:
            return "streaming"
        else:
            return "sequential"

    def _estimate_query_cost(
        self,
        query_type: str,
        selected_indexes: List[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        entity_ids: Optional[List[str]],
    ) -> float:
        """Estimate the computational cost of the query."""
        if not selected_indexes:
            return 1000.0  # High cost for no index

        primary_index = self.available_indexes.get(selected_indexes[0])
        if not primary_index:
            return 1000.0

        base_cost = 1.0

        # Cost based on index size
        entries = primary_index.statistics.total_entries
        if entries > 0:
            base_cost += entries * 0.001  # Linear cost factor

        # Cost based on query type
        if query_type == "range_query" and start_time and end_time:
            # Range queries have higher cost
            base_cost *= 2.0
        elif query_type == "entity_timeline" and entity_ids:
            # Entity queries scale with number of entities
            base_cost *= len(entity_ids) * 0.5

        # Cost reduction for good cache performance
        cache_ratio = primary_index.statistics.cache_hit_ratio()
        base_cost *= 1.0 - cache_ratio * 0.5

        return base_cost

    def _estimate_result_size(
        self,
        query_type: str,
        selected_indexes: List[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        entity_ids: Optional[List[str]],
    ) -> int:
        """Estimate the number of results the query will return."""
        if not selected_indexes:
            return 0

        primary_index = self.available_indexes.get(selected_indexes[0])
        if not primary_index:
            return 0

        total_entries = primary_index.statistics.total_entries

        if query_type == "point_query":
            return min(10, total_entries)  # Point queries return few results
        elif query_type == "entity_timeline" and entity_ids:
            # Estimate based on entities and total entries
            return min(total_entries // len(entity_ids), total_entries)
        elif query_type == "range_query":
            # Estimate based on time range selectivity
            return min(total_entries // 10, total_entries)  # Assume 10% selectivity

        return min(100, total_entries)  # Default estimate

    def _estimate_execution_time(self, cost: float, strategy: str) -> float:
        """Estimate query execution time in milliseconds."""
        base_time = cost * 0.1  # Base time factor

        if strategy == "parallel":
            base_time *= 0.6  # Parallel execution speedup
        elif strategy == "streaming":
            base_time *= 1.2  # Streaming overhead

        return base_time

    def _estimate_memory_usage(self, result_size: int, strategy: str) -> float:
        """Estimate memory usage in MB."""
        base_memory = result_size * 0.001  # 1KB per result estimate

        if strategy == "streaming":
            base_memory *= 0.1  # Streaming uses less memory
        elif strategy == "parallel":
            base_memory *= 1.5  # Parallel execution uses more memory

        return max(0.1, base_memory)

    def _should_use_index_intersection(
        self, selected_indexes: List[str], query_type: str
    ) -> bool:
        """Determine if index intersection should be used."""
        return len(selected_indexes) > 1 and query_type in [
            "range_query",
            "entity_timeline",
        ]

    def _should_use_temporal_clustering(
        self, query_type: str, hints: Optional[TemporalQueryHint]
    ) -> bool:
        """Determine if temporal clustering should be used."""
        if hints and not hints.use_clustering:
            return False
        return query_type in ["range_query", "entity_timeline"]

    def _should_cache_intermediate_results(
        self, execution_time_ms: float, memory_usage_mb: float
    ) -> bool:
        """Determine if intermediate results should be cached."""
        # Cache if query is expensive but not too memory-intensive
        return execution_time_ms > 100 and memory_usage_mb < 50

    def record_query_performance(
        self, plan_id: str, actual_execution_time_ms: float
    ) -> None:
        """Record actual query performance for learning.

        Args:
            plan_id: ID of the executed query plan
            actual_execution_time_ms: Actual execution time
        """
        if plan_id not in self.performance_history:
            self.performance_history[plan_id] = []

        self.performance_history[plan_id].append(actual_execution_time_ms)

        # Keep only recent history
        if len(self.performance_history[plan_id]) > 100:
            self.performance_history[plan_id] = self.performance_history[plan_id][-100:]

    def get_optimizer_statistics(self) -> Dict[str, Any]:
        """Get optimizer performance statistics."""
        return {
            "registered_indexes": len(self.available_indexes),
            "cached_plans": len(self.query_cache),
            "performance_history_entries": sum(
                len(history) for history in self.performance_history.values()
            ),
            "active_indexes": sum(
                1 for idx in self.available_indexes.values() if idx.is_active()
            ),
        }

    def clear_cache(self) -> None:
        """Clear the query plan cache."""
        self.query_cache.clear()
        logger.debug("Cleared query plan cache")
