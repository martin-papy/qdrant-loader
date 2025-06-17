"""Validation configuration settings.

This module defines configuration settings for the validation and repair system,
including automatic validation triggers and integration with sync operations.
"""

from typing import Any

from pydantic import Field

from .base import BaseConfig
from .validation_rules import ValidationRulesConfig
from .repair_strategies import RepairStrategiesConfig
from .notifications import NotificationSettingsConfig


class ValidationConfig(BaseConfig):
    """Configuration for validation and repair system."""

    # Automatic validation settings
    enable_auto_validation: bool = Field(
        default=True, description="Enable automatic validation after sync operations"
    )

    enable_post_ingestion_validation: bool = Field(
        default=True, description="Enable validation after document ingestion"
    )

    enable_post_sync_validation: bool = Field(
        default=True, description="Enable validation after sync operations"
    )

    # Validation timing and retry settings
    validation_delay_seconds: float = Field(
        default=2.0,
        description="Delay before triggering validation (to allow operations to settle)",
    )

    max_validation_retries: int = Field(
        default=3, description="Maximum number of validation retry attempts"
    )

    validation_retry_delay_seconds: float = Field(
        default=5.0, description="Delay between validation retry attempts"
    )

    validation_timeout_seconds: int = Field(
        default=300, description="Timeout for validation operations"
    )

    # Auto-repair settings
    enable_auto_repair: bool = Field(
        default=False, description="Enable automatic repair of validation issues"
    )

    auto_repair_max_attempts: int = Field(
        default=1, description="Maximum number of automatic repair attempts"
    )

    auto_repair_timeout_seconds: int = Field(
        default=600, description="Timeout for automatic repair operations"
    )

    # Validation scope settings
    validate_after_document_operations: bool = Field(
        default=True,
        description="Validate after document create/update/delete operations",
    )

    validate_after_entity_operations: bool = Field(
        default=True,
        description="Validate after entity create/update/delete operations",
    )

    validate_after_bulk_operations: bool = Field(
        default=True, description="Validate after bulk operations"
    )

    # Performance settings
    validation_batch_size: int = Field(
        default=100, description="Batch size for validation operations"
    )

    max_concurrent_validations: int = Field(
        default=2, description="Maximum number of concurrent validation operations"
    )

    # Logging and monitoring
    log_validation_events: bool = Field(
        default=True, description="Log validation events for monitoring"
    )

    log_validation_performance: bool = Field(
        default=False, description="Log detailed validation performance metrics"
    )

    # Scheduled validation settings
    enable_scheduled_validation: bool = Field(
        default=False, description="Enable scheduled validation jobs"
    )

    default_schedule_interval: str = Field(
        default="daily", description="Default schedule interval (hourly, daily, weekly)"
    )

    schedule_persistence_enabled: bool = Field(
        default=True, description="Enable job persistence across application restarts"
    )

    max_concurrent_scheduled_jobs: int = Field(
        default=1, description="Maximum number of concurrent scheduled validation jobs"
    )

    scheduled_job_timeout_seconds: int = Field(
        default=1800, description="Timeout for scheduled validation jobs (30 minutes)"
    )

    schedule_overlap_prevention: bool = Field(
        default=True, description="Prevent overlapping scheduled validation jobs"
    )

    # Extended configuration sections
    validation_rules: ValidationRulesConfig = Field(
        default_factory=ValidationRulesConfig,
        description="Comprehensive validation rules and scanner configuration",
    )

    repair_strategies: RepairStrategiesConfig = Field(
        default_factory=RepairStrategiesConfig,
        description="Comprehensive repair strategies and handler configuration",
    )

    notification_settings: NotificationSettingsConfig = Field(
        default_factory=NotificationSettingsConfig,
        description="Comprehensive notification settings and policies",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "enable_auto_validation": self.enable_auto_validation,
            "enable_post_ingestion_validation": self.enable_post_ingestion_validation,
            "enable_post_sync_validation": self.enable_post_sync_validation,
            "validation_delay_seconds": self.validation_delay_seconds,
            "max_validation_retries": self.max_validation_retries,
            "validation_retry_delay_seconds": self.validation_retry_delay_seconds,
            "validation_timeout_seconds": self.validation_timeout_seconds,
            "enable_auto_repair": self.enable_auto_repair,
            "auto_repair_max_attempts": self.auto_repair_max_attempts,
            "auto_repair_timeout_seconds": self.auto_repair_timeout_seconds,
            "validate_after_document_operations": self.validate_after_document_operations,
            "validate_after_entity_operations": self.validate_after_entity_operations,
            "validate_after_bulk_operations": self.validate_after_bulk_operations,
            "validation_batch_size": self.validation_batch_size,
            "max_concurrent_validations": self.max_concurrent_validations,
            "log_validation_events": self.log_validation_events,
            "log_validation_performance": self.log_validation_performance,
            "enable_scheduled_validation": self.enable_scheduled_validation,
            "default_schedule_interval": self.default_schedule_interval,
            "schedule_persistence_enabled": self.schedule_persistence_enabled,
            "max_concurrent_scheduled_jobs": self.max_concurrent_scheduled_jobs,
            "scheduled_job_timeout_seconds": self.scheduled_job_timeout_seconds,
            "schedule_overlap_prevention": self.schedule_overlap_prevention,
            "validation_rules": self.validation_rules.to_dict(),
            "repair_strategies": self.repair_strategies.to_dict(),
            "notification_settings": self.notification_settings.to_dict(),
        }
