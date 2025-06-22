"""Validation rules configuration.

This module defines configuration for validation rules, scanner behavior,
and validation thresholds for different types of validation checks.
"""

from typing import Any

from pydantic import Field

from .base import BaseConfig


class ScannerConfig(BaseConfig):
    """Configuration for individual validation scanners."""

    enabled: bool = Field(default=True, description="Enable this scanner")

    max_entities: int | None = Field(
        default=None, description="Maximum entities to scan (None for unlimited)"
    )

    severity_threshold: str = Field(
        default="warning",
        description="Minimum severity to report (info, warning, error, critical)",
    )

    auto_repair_enabled: bool = Field(
        default=False,
        description="Enable automatic repair for issues found by this scanner",
    )

    scan_interval_hours: int | None = Field(
        default=None, description="Automatic scan interval in hours (None to disable)"
    )

    timeout_seconds: int = Field(
        default=300, description="Timeout for scanner execution"
    )

    custom_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Scanner-specific custom parameters"
    )


class ValidationRulesConfig(BaseConfig):
    """Configuration for validation rules and scanner behavior."""

    # Global scanner settings
    global_max_entities: int | None = Field(
        default=10000, description="Global maximum entities to scan per scanner"
    )

    global_timeout_seconds: int = Field(
        default=600, description="Global timeout for validation operations"
    )

    parallel_scanner_limit: int = Field(
        default=3, description="Maximum number of scanners to run in parallel"
    )

    # Individual scanner configurations
    missing_mappings: ScannerConfig = Field(
        default_factory=lambda: ScannerConfig(
            enabled=True,
            max_entities=5000,
            severity_threshold="warning",
            auto_repair_enabled=True,
            scan_interval_hours=24,
            custom_parameters={
                "check_qdrant_orphans": True,
                "check_neo4j_orphans": True,
                "exclude_system_nodes": True,
            },
        ),
        description="Configuration for missing mappings scanner",
    )

    orphaned_records: ScannerConfig = Field(
        default_factory=lambda: ScannerConfig(
            enabled=True,
            max_entities=5000,
            severity_threshold="error",
            auto_repair_enabled=True,
            scan_interval_hours=12,
            custom_parameters={
                "cleanup_inactive_mappings": True,
                "grace_period_hours": 1,
            },
        ),
        description="Configuration for orphaned records scanner",
    )

    data_mismatches: ScannerConfig = Field(
        default_factory=lambda: ScannerConfig(
            enabled=True,
            max_entities=1000,
            severity_threshold="warning",
            auto_repair_enabled=False,
            scan_interval_hours=48,
            custom_parameters={
                "check_content_hash": True,
                "check_metadata": True,
                "check_timestamps": True,
                "tolerance_threshold": 0.1,
            },
        ),
        description="Configuration for data mismatches scanner",
    )

    version_inconsistencies: ScannerConfig = Field(
        default_factory=lambda: ScannerConfig(
            enabled=True,
            max_entities=2000,
            severity_threshold="error",
            auto_repair_enabled=False,
            scan_interval_hours=24,
            custom_parameters={
                "check_version_fields": ["version", "updated_at", "revision"],
                "version_tolerance_seconds": 300,
            },
        ),
        description="Configuration for version inconsistencies scanner",
    )

    sync_failures: ScannerConfig = Field(
        default_factory=lambda: ScannerConfig(
            enabled=True,
            max_entities=1000,
            severity_threshold="error",
            auto_repair_enabled=True,
            scan_interval_hours=6,
            custom_parameters={
                "retry_failed_syncs": True,
                "max_retry_attempts": 3,
                "retry_delay_minutes": 30,
            },
        ),
        description="Configuration for sync failures scanner",
    )

    constraint_violations: ScannerConfig = Field(
        default_factory=lambda: ScannerConfig(
            enabled=True,
            max_entities=None,  # Check all constraints
            severity_threshold="critical",
            auto_repair_enabled=False,
            scan_interval_hours=72,
            custom_parameters={
                "check_database_constraints": True,
                "check_business_rules": True,
                "check_data_integrity": True,
            },
        ),
        description="Configuration for constraint violations scanner",
    )

    performance_issues: ScannerConfig = Field(
        default_factory=lambda: ScannerConfig(
            enabled=True,
            max_entities=None,
            severity_threshold="warning",
            auto_repair_enabled=False,
            scan_interval_hours=24,
            custom_parameters={
                "query_timeout_threshold_ms": 5000,
                "memory_usage_threshold_mb": 1000,
                "connection_pool_threshold": 0.8,
                "index_efficiency_threshold": 0.7,
            },
        ),
        description="Configuration for performance issues scanner",
    )

    # Validation thresholds
    health_score_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "excellent": 95.0,
            "good": 85.0,
            "fair": 70.0,
            "poor": 50.0,
            "critical": 30.0,
        },
        description="Health score thresholds for system status classification",
    )

    # Issue severity weights for health score calculation
    severity_weights: dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 25,
            "error": 10,
            "warning": 3,
            "info": 1,
        },
        description="Weights for different severity levels in health score calculation",
    )

    # Auto-repair limits
    auto_repair_limits: dict[str, int] = Field(
        default_factory=lambda: {
            "max_repairs_per_run": 100,
            "max_repairs_per_category": 50,
            "max_repairs_per_hour": 200,
            "max_critical_repairs": 10,
        },
        description="Limits for automatic repair operations",
    )

    def get_scanner_config(self, scanner_name: str) -> ScannerConfig | None:
        """Get configuration for a specific scanner.

        Args:
            scanner_name: Name of the scanner

        Returns:
            Scanner configuration or None if not found
        """
        return getattr(self, scanner_name, None)

    def get_enabled_scanners(self) -> list[str]:
        """Get list of enabled scanner names.

        Returns:
            List of enabled scanner names
        """
        enabled_scanners = []
        for scanner_name in [
            "missing_mappings",
            "orphaned_records",
            "data_mismatches",
            "version_inconsistencies",
            "sync_failures",
            "constraint_violations",
            "performance_issues",
        ]:
            config = self.get_scanner_config(scanner_name)
            if config and config.enabled:
                enabled_scanners.append(scanner_name)
        return enabled_scanners

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "global_max_entities": self.global_max_entities,
            "global_timeout_seconds": self.global_timeout_seconds,
            "parallel_scanner_limit": self.parallel_scanner_limit,
            "scanners": {
                "missing_mappings": self.missing_mappings.model_dump(),
                "orphaned_records": self.orphaned_records.model_dump(),
                "data_mismatches": self.data_mismatches.model_dump(),
                "version_inconsistencies": self.version_inconsistencies.model_dump(),
                "sync_failures": self.sync_failures.model_dump(),
                "constraint_violations": self.constraint_violations.model_dump(),
                "performance_issues": self.performance_issues.model_dump(),
            },
            "health_score_thresholds": self.health_score_thresholds,
            "severity_weights": self.severity_weights,
            "auto_repair_limits": self.auto_repair_limits,
        }
