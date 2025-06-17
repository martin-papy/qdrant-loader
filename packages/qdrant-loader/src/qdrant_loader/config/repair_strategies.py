"""Repair strategies configuration.

This module defines configuration for repair strategies, repair handler behavior,
and repair operation policies for different types of validation issues.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from .base import BaseConfig


class RepairHandlerConfig(BaseConfig):
    """Configuration for individual repair handlers."""

    enabled: bool = Field(default=True, description="Enable this repair handler")

    auto_execute: bool = Field(
        default=False, description="Automatically execute repairs without confirmation"
    )

    max_attempts: int = Field(
        default=3, description="Maximum number of repair attempts"
    )

    retry_delay_seconds: int = Field(
        default=30, description="Delay between retry attempts"
    )

    timeout_seconds: int = Field(
        default=300, description="Timeout for repair execution"
    )

    batch_size: int = Field(
        default=10, description="Number of issues to repair in a single batch"
    )

    confirmation_required: bool = Field(
        default=True, description="Require confirmation before executing repairs"
    )

    dry_run_first: bool = Field(
        default=True, description="Perform dry run before actual repair"
    )

    backup_before_repair: bool = Field(
        default=False, description="Create backup before performing repair"
    )

    custom_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Handler-specific custom parameters"
    )


class RepairStrategiesConfig(BaseConfig):
    """Configuration for repair strategies and handler behavior."""

    # Global repair settings
    global_max_repairs_per_run: int = Field(
        default=100, description="Global maximum repairs per execution run"
    )

    global_timeout_seconds: int = Field(
        default=1800, description="Global timeout for repair operations (30 minutes)"
    )

    parallel_repair_limit: int = Field(
        default=2, description="Maximum number of repair handlers to run in parallel"
    )

    require_approval_for_critical: bool = Field(
        default=True, description="Require manual approval for critical repairs"
    )

    # Individual repair handler configurations
    create_mapping: RepairHandlerConfig = Field(
        default_factory=lambda: RepairHandlerConfig(
            enabled=True,
            auto_execute=True,
            max_attempts=3,
            retry_delay_seconds=10,
            timeout_seconds=60,
            batch_size=20,
            confirmation_required=False,
            dry_run_first=False,
            backup_before_repair=False,
            custom_parameters={
                "prefer_existing_entities": True,
                "create_bidirectional_mapping": True,
                "validate_after_creation": True,
            },
        ),
        description="Configuration for create mapping repair handler",
    )

    delete_orphaned: RepairHandlerConfig = Field(
        default_factory=lambda: RepairHandlerConfig(
            enabled=True,
            auto_execute=False,
            max_attempts=2,
            retry_delay_seconds=30,
            timeout_seconds=120,
            batch_size=10,
            confirmation_required=True,
            dry_run_first=True,
            backup_before_repair=True,
            custom_parameters={
                "grace_period_hours": 24,
                "verify_orphan_status": True,
                "cascade_delete": False,
            },
        ),
        description="Configuration for delete orphaned repair handler",
    )

    update_data: RepairHandlerConfig = Field(
        default_factory=lambda: RepairHandlerConfig(
            enabled=True,
            auto_execute=False,
            max_attempts=3,
            retry_delay_seconds=60,
            timeout_seconds=300,
            batch_size=5,
            confirmation_required=True,
            dry_run_first=True,
            backup_before_repair=True,
            custom_parameters={
                "conflict_resolution_strategy": "merge",
                "preserve_user_data": True,
                "update_timestamps": True,
                "validate_data_integrity": True,
            },
        ),
        description="Configuration for update data repair handler",
    )

    sync_entities: RepairHandlerConfig = Field(
        default_factory=lambda: RepairHandlerConfig(
            enabled=True,
            auto_execute=True,
            max_attempts=5,
            retry_delay_seconds=120,
            timeout_seconds=600,
            batch_size=3,
            confirmation_required=False,
            dry_run_first=False,
            backup_before_repair=False,
            custom_parameters={
                "sync_direction": "bidirectional",
                "force_sync": False,
                "preserve_local_changes": True,
                "sync_metadata": True,
            },
        ),
        description="Configuration for sync entities repair handler",
    )

    resolve_conflict: RepairHandlerConfig = Field(
        default_factory=lambda: RepairHandlerConfig(
            enabled=True,
            auto_execute=False,
            max_attempts=2,
            retry_delay_seconds=300,
            timeout_seconds=900,
            batch_size=1,
            confirmation_required=True,
            dry_run_first=True,
            backup_before_repair=True,
            custom_parameters={
                "conflict_resolution_algorithm": "timestamp_based",
                "manual_review_required": True,
                "preserve_conflict_history": True,
            },
        ),
        description="Configuration for resolve conflict repair handler",
    )

    rebuild_index: RepairHandlerConfig = Field(
        default_factory=lambda: RepairHandlerConfig(
            enabled=True,
            auto_execute=False,
            max_attempts=1,
            retry_delay_seconds=600,
            timeout_seconds=3600,
            batch_size=1,
            confirmation_required=True,
            dry_run_first=False,
            backup_before_repair=True,
            custom_parameters={
                "rebuild_scope": "affected_only",
                "optimize_after_rebuild": True,
                "verify_integrity": True,
            },
        ),
        description="Configuration for rebuild index repair handler",
    )

    manual_intervention: RepairHandlerConfig = Field(
        default_factory=lambda: RepairHandlerConfig(
            enabled=True,
            auto_execute=False,
            max_attempts=1,
            retry_delay_seconds=0,
            timeout_seconds=0,  # No timeout for manual intervention
            batch_size=1,
            confirmation_required=True,
            dry_run_first=False,
            backup_before_repair=False,
            custom_parameters={
                "notification_required": True,
                "escalation_timeout_hours": 24,
                "assign_to_role": "admin",
            },
        ),
        description="Configuration for manual intervention repair handler",
    )

    # Repair policies
    repair_policies: Dict[str, Any] = Field(
        default_factory=lambda: {
            "auto_repair_severity_threshold": "warning",  # Auto-repair for warning and above
            "critical_issue_escalation": True,
            "repair_window_hours": [2, 6],  # Preferred repair window (2 AM to 6 AM)
            "max_concurrent_repairs": 5,
            "repair_cooldown_minutes": 30,
            "rollback_on_failure": True,
        },
        description="General repair policies and constraints",
    )

    # Repair prioritization
    repair_priorities: Dict[str, int] = Field(
        default_factory=lambda: {
            "critical_data_loss": 10,
            "orphaned_records": 8,
            "missing_mappings": 7,
            "sync_failures": 6,
            "data_mismatches": 5,
            "version_inconsistencies": 4,
            "constraint_violations": 3,
            "performance_issues": 2,
        },
        description="Priority levels for different types of repairs (1-10, higher is more urgent)",
    )

    # Notification settings for repairs
    repair_notifications: Dict[str, Any] = Field(
        default_factory=lambda: {
            "notify_on_start": False,
            "notify_on_completion": True,
            "notify_on_failure": True,
            "notify_on_critical": True,
            "notification_channels": ["log", "email"],
            "escalation_after_failures": 3,
        },
        description="Notification settings for repair operations",
    )

    def get_repair_handler_config(
        self, handler_name: str
    ) -> Optional[RepairHandlerConfig]:
        """Get configuration for a specific repair handler.

        Args:
            handler_name: Name of the repair handler

        Returns:
            Repair handler configuration or None if not found
        """
        return getattr(self, handler_name, None)

    def get_enabled_handlers(self) -> List[str]:
        """Get list of enabled repair handler names.

        Returns:
            List of enabled repair handler names
        """
        enabled_handlers = []
        for handler_name in [
            "create_mapping",
            "delete_orphaned",
            "update_data",
            "sync_entities",
            "resolve_conflict",
            "rebuild_index",
            "manual_intervention",
        ]:
            config = self.get_repair_handler_config(handler_name)
            if config and config.enabled:
                enabled_handlers.append(handler_name)
        return enabled_handlers

    def get_auto_executable_handlers(self) -> List[str]:
        """Get list of repair handlers that can auto-execute.

        Returns:
            List of auto-executable repair handler names
        """
        auto_handlers = []
        for handler_name in self.get_enabled_handlers():
            config = self.get_repair_handler_config(handler_name)
            if config and config.auto_execute:
                auto_handlers.append(handler_name)
        return auto_handlers

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "global_max_repairs_per_run": self.global_max_repairs_per_run,
            "global_timeout_seconds": self.global_timeout_seconds,
            "parallel_repair_limit": self.parallel_repair_limit,
            "require_approval_for_critical": self.require_approval_for_critical,
            "handlers": {
                "create_mapping": self.create_mapping.model_dump(),
                "delete_orphaned": self.delete_orphaned.model_dump(),
                "update_data": self.update_data.model_dump(),
                "sync_entities": self.sync_entities.model_dump(),
                "resolve_conflict": self.resolve_conflict.model_dump(),
                "rebuild_index": self.rebuild_index.model_dump(),
                "manual_intervention": self.manual_intervention.model_dump(),
            },
            "repair_policies": self.repair_policies,
            "repair_priorities": self.repair_priorities,
            "repair_notifications": self.repair_notifications,
        }
