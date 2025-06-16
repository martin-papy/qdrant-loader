"""Statistics and monitoring for conflict resolution system.

This module provides comprehensive statistics collection and analysis
for conflict resolution operations.
"""

from typing import Any

from ...utils.logging import LoggingConfig
from .models import ConflictRecord, ConflictStatus

logger = LoggingConfig.get_logger(__name__)


class ConflictStatistics:
    """Collects and analyzes conflict resolution statistics."""

    def __init__(self):
        """Initialize the statistics collector."""
        self._conflicts_detected = 0
        self._conflicts_resolved = 0
        self._conflicts_failed = 0
        self._manual_interventions = 0

    def increment_detected(self) -> None:
        """Increment the count of detected conflicts."""
        self._conflicts_detected += 1

    def increment_resolved(self) -> None:
        """Increment the count of resolved conflicts."""
        self._conflicts_resolved += 1

    def increment_failed(self) -> None:
        """Increment the count of failed conflict resolutions."""
        self._conflicts_failed += 1

    def increment_manual_interventions(self) -> None:
        """Increment the count of manual interventions."""
        self._manual_interventions += 1

    async def get_comprehensive_statistics(
        self,
        active_conflicts: dict[str, ConflictRecord],
        manual_review_conflicts: list[ConflictRecord],
        cache_size: int,
        advanced_merge_enabled: bool = False,
    ) -> dict[str, Any]:
        """Get comprehensive conflict resolution statistics.

        Args:
            active_conflicts: Dictionary of active conflicts
            manual_review_conflicts: List of conflicts requiring manual review
            cache_size: Size of the version cache
            advanced_merge_enabled: Whether advanced merge is enabled

        Returns:
            Dictionary containing comprehensive statistics
        """
        active_conflicts_count = len(active_conflicts)
        manual_review_count = len(manual_review_conflicts)

        # Analyze conflict types and resolution strategies
        conflict_types = {}
        resolution_strategies = {}
        merge_statistics = {
            "total_merges": 0,
            "successful_merges": 0,
            "failed_merges": 0,
            "fields_merged": 0,
            "conflicts_auto_resolved": 0,
            "conflicts_requiring_manual_review": 0,
        }

        for conflict in active_conflicts.values():
            # Count conflict types
            conflict_type = conflict.conflict_type.value
            conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1

            # Count resolution strategies
            if conflict.resolution_strategy:
                strategy = conflict.resolution_strategy.value
                resolution_strategies[strategy] = (
                    resolution_strategies.get(strategy, 0) + 1
                )

                # Analyze merge statistics
                if strategy == "merge_strategy" and conflict.resolution_data:
                    merge_statistics["total_merges"] += 1

                    if conflict.status == ConflictStatus.RESOLVED:
                        merge_statistics["successful_merges"] += 1

                        # Extract merge result data if available
                        merge_result = conflict.resolution_data.get("merge_result", {})
                        merge_statistics["fields_merged"] += merge_result.get(
                            "fields_merged", 0
                        )
                        merge_statistics["conflicts_auto_resolved"] += merge_result.get(
                            "conflicts_resolved", 0
                        )
                        merge_statistics[
                            "conflicts_requiring_manual_review"
                        ] += merge_result.get("conflicts_requiring_manual_review", 0)
                    elif conflict.status == ConflictStatus.FAILED:
                        merge_statistics["failed_merges"] += 1

        return {
            "conflicts_detected": self._conflicts_detected,
            "conflicts_resolved": self._conflicts_resolved,
            "conflicts_failed": self._conflicts_failed,
            "manual_interventions": self._manual_interventions,
            "active_conflicts": active_conflicts_count,
            "manual_review_queue": manual_review_count,
            "resolution_rate": (
                self._conflicts_resolved / max(self._conflicts_detected, 1)
            ),
            "cache_size": cache_size,
            "conflict_types": conflict_types,
            "resolution_strategies": resolution_strategies,
            "merge_statistics": merge_statistics,
            "advanced_merge_enabled": advanced_merge_enabled,
        }

    async def health_check(
        self,
        active_conflicts: dict[str, ConflictRecord],
        manual_review_conflicts: list[ConflictRecord],
        cache_size: int,
        config,
        advanced_merge_enabled: bool = False,
    ) -> dict[str, Any]:
        """Perform health check of the conflict resolution system.

        Args:
            active_conflicts: Dictionary of active conflicts
            manual_review_conflicts: List of conflicts requiring manual review
            cache_size: Size of the version cache
            config: Conflict resolution configuration
            advanced_merge_enabled: Whether advanced merge is enabled

        Returns:
            Dictionary containing health check results
        """
        try:
            stats = await self.get_comprehensive_statistics(
                active_conflicts,
                manual_review_conflicts,
                cache_size,
                advanced_merge_enabled,
            )

            return {
                "status": "healthy",
                "statistics": stats,
                "config": {
                    "default_strategy": config.default_strategy.value,
                    "auto_resolution_enabled": config.enable_auto_resolution,
                    "max_attempts": config.max_resolution_attempts,
                },
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self._conflicts_detected = 0
        self._conflicts_resolved = 0
        self._conflicts_failed = 0
        self._manual_interventions = 0
        logger.info("Conflict resolution statistics reset")

    @property
    def basic_statistics(self) -> dict[str, int]:
        """Get basic statistics.

        Returns:
            Dictionary containing basic statistics
        """
        return {
            "conflicts_detected": self._conflicts_detected,
            "conflicts_resolved": self._conflicts_resolved,
            "conflicts_failed": self._conflicts_failed,
            "manual_interventions": self._manual_interventions,
        }
