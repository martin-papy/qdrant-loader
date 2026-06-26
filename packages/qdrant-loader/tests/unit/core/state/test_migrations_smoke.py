"""Smoke tests for state DB Alembic migrations."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _build_alembic_config(package_root: Path, db_path: Path) -> Config:
    cfg = Config(str(package_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(package_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return cfg


def test_jobs_migration_smoke_upgrade_and_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure WS-4.1 migration creates and removes jobs schema artifacts."""
    # Keep this test isolated from developer shell env overrides.
    monkeypatch.delenv("STATE_DB_PATH", raising=False)
    # STATE_DB_URL takes precedence in env.py; clear it so downgrade("base")
    # can never run against a developer/CI Postgres instead of the temp SQLite DB.
    monkeypatch.delenv("STATE_DB_URL", raising=False)

    package_root = Path(__file__).resolve().parents[4]
    db_path = tmp_path / "state_ws41.db"
    cfg = _build_alembic_config(package_root, db_path)

    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)

    assert "jobs" in inspector.get_table_names()

    expected_columns = {
        "id",
        "type",
        "payload_json",
        "status",
        "enqueued_at",
        "started_at",
        "finished_at",
        "attempts",
        "last_error",
        "visibility_deadline",
    }
    actual_columns = {col["name"] for col in inspector.get_columns("jobs")}
    assert expected_columns == actual_columns

    indexes = inspector.get_indexes("jobs")
    assert any(
        idx.get("name") == "ix_jobs_status_enqueued_at"
        and idx.get("column_names") == ["status", "enqueued_at"]
        for idx in indexes
    )
    engine.dispose()

    command.downgrade(cfg, "base")

    engine_after = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector_after = inspect(engine_after)
    assert "jobs" not in inspector_after.get_table_names()
    engine_after.dispose()
