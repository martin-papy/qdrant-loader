"""Worker scheduling configuration."""

from __future__ import annotations

import re
from typing import Any

from pydantic import Field, field_validator

from qdrant_loader.config.base import BaseConfig

_SHORT_DURATION_RE = re.compile(
    r"^\s*(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?\s*$",
    re.IGNORECASE,
)
_ISO_DURATION_RE = re.compile(
    r"^P(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)$",
    re.IGNORECASE,
)


def parse_interval_seconds(value: int | float | str) -> int:
    """Parse an interval value into seconds.

    Accepted formats:
    - Integer/float seconds: 300, 300.0
    - Numeric strings: "300"
    - Short duration strings: "30s", "5m", "2h", "1h30m"
    - ISO-8601 duration (time portion): "PT5M", "PT1H30M"
    """
    if isinstance(value, bool):
        raise ValueError("interval must be a positive duration")

    if isinstance(value, (int, float)):
        seconds = int(value)
        if seconds < 1:
            raise ValueError("interval must be at least 1 second")
        return seconds

    if not isinstance(value, str):
        raise ValueError("interval must be an int, float, or string duration")

    raw = value.strip()
    if not raw:
        raise ValueError("interval cannot be empty")

    if raw.isdigit():
        seconds = int(raw)
        if seconds < 1:
            raise ValueError("interval must be at least 1 second")
        return seconds

    short_match = _SHORT_DURATION_RE.match(raw)
    if short_match:
        hours = int(short_match.group("hours") or 0)
        minutes = int(short_match.group("minutes") or 0)
        seconds = int(short_match.group("seconds") or 0)
        total = hours * 3600 + minutes * 60 + seconds
        if total < 1:
            raise ValueError("interval must be at least 1 second")
        return total

    iso_match = _ISO_DURATION_RE.match(raw)
    if iso_match:
        hours = int(iso_match.group("hours") or 0)
        minutes = int(iso_match.group("minutes") or 0)
        seconds = int(iso_match.group("seconds") or 0)
        total = hours * 3600 + minutes * 60 + seconds
        if total < 1:
            raise ValueError("interval must be at least 1 second")
        return total

    raise ValueError(
        "Invalid interval format. Use seconds, short durations like '5m', or ISO-8601 like 'PT5M'."
    )


class IncrementalPullScheduleConfig(BaseConfig):
    """Periodic scheduling config for INCREMENTAL_PULL jobs."""

    enabled: bool = Field(default=False, description="Enable periodic scheduling")
    interval_seconds: int = Field(
        default=300,
        alias="interval",
        description="Interval in seconds (supports '5m', 'PT5M', or integer seconds)",
    )
    dedup_statuses: list[str] = Field(
        default_factory=lambda: ["pending", "running"],
        description="Job statuses considered active for deduplication",
    )
    payload_defaults: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra payload fields merged into each scheduled job payload",
    )

    @field_validator("interval_seconds", mode="before")
    @classmethod
    def validate_interval_seconds(cls, value: int | float | str) -> int:
        return parse_interval_seconds(value)

    @field_validator("dedup_statuses")
    @classmethod
    def validate_dedup_statuses(cls, values: list[str]) -> list[str]:
        allowed = {"pending", "running", "done", "failed", "cancelled"}
        normalized = []
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("dedup statuses must be non-empty strings")
            status = item.strip().lower()
            if status not in allowed:
                raise ValueError(
                    f"Invalid dedup status '{item}'. Allowed: {sorted(allowed)}"
                )
            normalized.append(status)

        if not normalized:
            raise ValueError("dedup_statuses cannot be empty")
        return normalized

    @field_validator("payload_defaults")
    @classmethod
    def validate_payload_defaults(cls, value: dict[str, Any]) -> dict[str, Any]:
        def _validate_json_like(v: Any, path: str) -> Any:
            if v is None or isinstance(v, (str, int, float, bool)):
                return v

            if isinstance(v, list):
                return [
                    _validate_json_like(item, f"{path}[{idx}]")
                    for idx, item in enumerate(v)
                ]

            if isinstance(v, dict):
                cleaned: dict[str, Any] = {}
                for key, item in v.items():
                    if not isinstance(key, str):
                        raise ValueError(f"{path} keys must be strings")
                    cleaned[key] = _validate_json_like(item, f"{path}.{key}")
                return cleaned

            raise ValueError(
                f"{path} contains unsupported type {type(v).__name__}; "
                "allowed types are str, int, float, bool, None, list, dict"
            )

        if not isinstance(value, dict):
            raise ValueError("payload_defaults must be a dictionary")

        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("payload_defaults keys must be strings")
            cleaned[key] = _validate_json_like(item, f"payload_defaults.{key}")
        return cleaned


class WorkerSchedulesConfig(BaseConfig):
    """Container for worker schedule definitions."""

    incremental_pull: IncrementalPullScheduleConfig = Field(
        default_factory=IncrementalPullScheduleConfig
    )


class WorkerRuntimeConfig(BaseConfig):
    """Runtime knobs for worker pool behavior."""

    worker_count: int = Field(
        default=4,
        ge=1,
        description="Number of concurrent workers draining the queue",
    )
    lease_seconds: int = Field(
        default=60,
        ge=1,
        description="Visibility lease duration (seconds) when a job is claimed",
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum claim attempts per job before marking failed",
    )
    retry_backoff_base_seconds: int = Field(
        default=5,
        ge=0,
        description="Exponential retry base in seconds (0 disables backoff)",
    )


class WorkersConfig(BaseConfig):
    """Worker runtime and scheduling configuration."""

    runtime: WorkerRuntimeConfig = Field(default_factory=WorkerRuntimeConfig)
    schedules: WorkerSchedulesConfig = Field(default_factory=WorkerSchedulesConfig)
