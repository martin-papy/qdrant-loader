from __future__ import annotations

import pytest
from qdrant_loader.config.workers import (
    IncrementalPullScheduleConfig,
    WorkersConfig,
    parse_interval_seconds,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (300, 300),
        ("300", 300),
        ("30s", 30),
        ("5m", 300),
        ("2h", 7200),
        ("1h30m", 5400),
        ("PT5M", 300),
        ("PT1H30M", 5400),
    ],
)
def test_parse_interval_seconds_formats(raw, expected):
    assert parse_interval_seconds(raw) == expected


@pytest.mark.parametrize("raw", [0, "", "0s", "PT0S", "abc", True])
def test_parse_interval_seconds_invalid(raw):
    with pytest.raises(ValueError):
        parse_interval_seconds(raw)


def test_schedule_config_accepts_alias_interval_formats():
    cfg = IncrementalPullScheduleConfig(enabled=True, interval="5m")
    assert cfg.interval_seconds == 300


def test_workers_config_defaults_incremental_pull_disabled():
    cfg = WorkersConfig()
    assert cfg.runtime.worker_count == 4
    assert cfg.runtime.lease_seconds == 60
    assert cfg.runtime.max_attempts == 3
    assert cfg.runtime.retry_backoff_base_seconds == 5
    assert cfg.schedules.incremental_pull.enabled is False
    assert cfg.schedules.incremental_pull.interval_seconds == 300


def test_workers_runtime_rejects_invalid_retry_values():
    with pytest.raises(ValueError):
        WorkersConfig(runtime={"max_attempts": 0})

    with pytest.raises(ValueError):
        WorkersConfig(runtime={"retry_backoff_base_seconds": -1})


def test_payload_defaults_accepts_json_like_values():
    cfg = IncrementalPullScheduleConfig(
        enabled=True,
        interval=300,
        payload_defaults={
            "force": False,
            "attempt": 1,
            "threshold": 0.5,
            "tag": "nightly",
            "extra": {"a": 1, "b": ["x", None, True]},
        },
    )

    assert cfg.payload_defaults["force"] is False
    assert cfg.payload_defaults["extra"]["b"][1] is None


def test_payload_defaults_rejects_unsupported_types():
    with pytest.raises(ValueError, match="unsupported type"):
        IncrementalPullScheduleConfig(
            enabled=True,
            interval=300,
            payload_defaults={"bad": object()},
        )


def test_payload_defaults_rejects_non_string_nested_dict_keys():
    with pytest.raises(ValueError, match="keys must be strings"):
        IncrementalPullScheduleConfig(
            enabled=True,
            interval=300,
            payload_defaults={"bad": {1: "x"}},
        )
