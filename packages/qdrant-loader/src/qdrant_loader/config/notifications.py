"""Notification settings configuration.

This module defines configuration for notification settings, channels,
and notification policies for validation and repair events.
"""

from typing import Any

from pydantic import Field

from .base import BaseConfig


class NotificationChannelConfig(BaseConfig):
    """Configuration for individual notification channels."""

    enabled: bool = Field(default=True, description="Enable this notification channel")

    channel_type: str = Field(
        description="Type of notification channel (email, slack, webhook, log)"
    )

    endpoint: str | None = Field(
        default=None, description="Endpoint URL for webhook/API-based channels"
    )

    credentials: dict[str, str] = Field(
        default_factory=dict, description="Credentials for the notification channel"
    )

    retry_attempts: int = Field(
        default=3, description="Number of retry attempts for failed notifications"
    )

    retry_delay_seconds: int = Field(
        default=60, description="Delay between retry attempts"
    )

    timeout_seconds: int = Field(
        default=30, description="Timeout for notification delivery"
    )

    rate_limit_per_hour: int | None = Field(
        default=None, description="Maximum notifications per hour (None for unlimited)"
    )

    custom_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Channel-specific custom parameters"
    )


class NotificationTemplateConfig(BaseConfig):
    """Configuration for notification templates."""

    subject_template: str = Field(description="Template for notification subject/title")

    body_template: str = Field(description="Template for notification body/content")

    format_type: str = Field(
        default="text", description="Format type (text, html, markdown)"
    )

    include_details: bool = Field(
        default=True, description="Include detailed information in notifications"
    )

    include_metadata: bool = Field(
        default=False, description="Include metadata in notifications"
    )

    custom_fields: dict[str, str] = Field(
        default_factory=dict, description="Custom fields to include in notifications"
    )


class NotificationSettingsConfig(BaseConfig):
    """Configuration for notification settings and policies."""

    # Global notification settings
    global_enabled: bool = Field(
        default=True, description="Enable notifications globally"
    )

    default_channels: list[str] = Field(
        default_factory=lambda: ["log"], description="Default notification channels"
    )

    notification_cooldown_minutes: int = Field(
        default=15, description="Cooldown period between similar notifications"
    )

    batch_notifications: bool = Field(
        default=True, description="Batch similar notifications together"
    )

    batch_window_minutes: int = Field(
        default=5, description="Time window for batching notifications"
    )

    # Notification channels
    channels: dict[str, NotificationChannelConfig] = Field(
        default_factory=lambda: {
            "log": NotificationChannelConfig(
                enabled=True,
                channel_type="log",
                custom_parameters={
                    "log_level": "INFO",
                    "logger_name": "qdrant_loader.validation.notifications",
                },
            ),
            "email": NotificationChannelConfig(
                enabled=False,
                channel_type="email",
                custom_parameters={
                    "smtp_server": "localhost",
                    "smtp_port": 587,
                    "use_tls": True,
                    "from_address": "noreply@qdrant-loader.local",
                    "to_addresses": [],
                },
            ),
            "slack": NotificationChannelConfig(
                enabled=False,
                channel_type="slack",
                custom_parameters={
                    "webhook_url": "",
                    "channel": "#alerts",
                    "username": "QDrant Loader",
                    "icon_emoji": ":warning:",
                },
            ),
            "webhook": NotificationChannelConfig(
                enabled=False,
                channel_type="webhook",
                custom_parameters={
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "auth_type": "none",
                },
            ),
        },
        description="Configuration for notification channels",
    )

    # Event-specific notification settings
    validation_events: dict[str, Any] = Field(
        default_factory=lambda: {
            "validation_started": {
                "enabled": False,
                "channels": ["log"],
                "severity_threshold": "info",
            },
            "validation_completed": {
                "enabled": True,
                "channels": ["log"],
                "severity_threshold": "info",
                "notify_if_issues_found": True,
            },
            "validation_failed": {
                "enabled": True,
                "channels": ["log", "email"],
                "severity_threshold": "error",
                "immediate_notification": True,
            },
            "critical_issues_found": {
                "enabled": True,
                "channels": ["log", "email", "slack"],
                "severity_threshold": "critical",
                "immediate_notification": True,
                "escalation_required": True,
            },
        },
        description="Notification settings for validation events",
    )

    repair_events: dict[str, Any] = Field(
        default_factory=lambda: {
            "repair_started": {
                "enabled": False,
                "channels": ["log"],
                "severity_threshold": "info",
            },
            "repair_completed": {
                "enabled": True,
                "channels": ["log"],
                "severity_threshold": "info",
                "notify_on_success": True,
            },
            "repair_failed": {
                "enabled": True,
                "channels": ["log", "email"],
                "severity_threshold": "error",
                "immediate_notification": True,
                "include_error_details": True,
            },
            "manual_intervention_required": {
                "enabled": True,
                "channels": ["log", "email", "slack"],
                "severity_threshold": "warning",
                "immediate_notification": True,
                "escalation_required": True,
            },
        },
        description="Notification settings for repair events",
    )

    system_events: dict[str, Any] = Field(
        default_factory=lambda: {
            "system_health_degraded": {
                "enabled": True,
                "channels": ["log", "email"],
                "health_score_threshold": 70.0,
                "immediate_notification": True,
            },
            "system_health_critical": {
                "enabled": True,
                "channels": ["log", "email", "slack"],
                "health_score_threshold": 30.0,
                "immediate_notification": True,
                "escalation_required": True,
            },
            "database_connectivity_lost": {
                "enabled": True,
                "channels": ["log", "email", "slack"],
                "immediate_notification": True,
                "escalation_required": True,
            },
            "performance_degradation": {
                "enabled": True,
                "channels": ["log"],
                "performance_threshold": 0.5,  # 50% degradation
            },
        },
        description="Notification settings for system events",
    )

    # Notification templates
    templates: dict[str, NotificationTemplateConfig] = Field(
        default_factory=lambda: {
            "validation_completed": NotificationTemplateConfig(
                subject_template="Validation Completed - {total_issues} issues found",
                body_template="""
Validation Report Summary:
- Total Issues: {total_issues}
- Critical: {critical_issues}
- Errors: {error_issues}
- Warnings: {warning_issues}
- System Health Score: {health_score}%

Report ID: {report_id}
Generated: {generated_at}
""",
                format_type="text",
                include_details=True,
            ),
            "repair_failed": NotificationTemplateConfig(
                subject_template="Repair Operation Failed - {issue_category}",
                body_template="""
Repair operation failed:
- Issue ID: {issue_id}
- Category: {issue_category}
- Repair Action: {repair_action}
- Error: {error_message}
- Attempts: {attempt_count}/{max_attempts}

Manual intervention may be required.
""",
                format_type="text",
                include_details=True,
                include_metadata=True,
            ),
            "critical_issues": NotificationTemplateConfig(
                subject_template="CRITICAL: {critical_count} Critical Issues Detected",
                body_template="""
CRITICAL VALIDATION ISSUES DETECTED

{critical_count} critical issues require immediate attention:

{critical_issues_list}

System Health Score: {health_score}%
Immediate action required.

Report ID: {report_id}
""",
                format_type="text",
                include_details=True,
            ),
        },
        description="Notification templates for different event types",
    )

    # Escalation settings
    escalation_settings: dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "escalation_delay_minutes": 30,
            "max_escalation_levels": 3,
            "escalation_channels": ["email", "slack"],
            "escalation_recipients": {
                "level_1": ["admin@example.com"],
                "level_2": ["manager@example.com"],
                "level_3": ["director@example.com"],
            },
        },
        description="Escalation settings for critical notifications",
    )

    def get_channel_config(
        self, channel_name: str
    ) -> NotificationChannelConfig | None:
        """Get configuration for a specific notification channel.

        Args:
            channel_name: Name of the notification channel

        Returns:
            Channel configuration or None if not found
        """
        return self.channels.get(channel_name)

    def get_enabled_channels(self) -> list[str]:
        """Get list of enabled notification channel names.

        Returns:
            List of enabled channel names
        """
        return [name for name, config in self.channels.items() if config.enabled]

    def get_template_config(
        self, template_name: str
    ) -> NotificationTemplateConfig | None:
        """Get configuration for a specific notification template.

        Args:
            template_name: Name of the notification template

        Returns:
            Template configuration or None if not found
        """
        return self.templates.get(template_name)

    def should_notify_for_event(
        self, event_type: str, event_category: str = "validation"
    ) -> bool:
        """Check if notifications should be sent for a specific event.

        Args:
            event_type: Type of event (e.g., 'validation_completed')
            event_category: Category of event ('validation', 'repair', 'system')

        Returns:
            True if notifications should be sent
        """
        if not self.global_enabled:
            return False

        event_config = None
        if event_category == "validation":
            event_config = self.validation_events.get(event_type)
        elif event_category == "repair":
            event_config = self.repair_events.get(event_type)
        elif event_category == "system":
            event_config = self.system_events.get(event_type)

        return bool(event_config and event_config.get("enabled", False))

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "global_enabled": self.global_enabled,
            "default_channels": self.default_channels,
            "notification_cooldown_minutes": self.notification_cooldown_minutes,
            "batch_notifications": self.batch_notifications,
            "batch_window_minutes": self.batch_window_minutes,
            "channels": {
                name: config.model_dump() for name, config in self.channels.items()
            },
            "validation_events": self.validation_events,
            "repair_events": self.repair_events,
            "system_events": self.system_events,
            "templates": {
                name: config.model_dump() for name, config in self.templates.items()
            },
            "escalation_settings": self.escalation_settings,
        }
