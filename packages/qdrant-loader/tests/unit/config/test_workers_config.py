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
    assert cfg.schedules.incremental_pull.enabled is False
    assert cfg.schedules.incremental_pull.interval_seconds == 300
