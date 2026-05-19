from __future__ import annotations

# pyright: reportGeneralTypeIssues=false, reportAttributeAccessIssue=false
import importlib
import os
from logging.config import fileConfig
from pathlib import Path
from typing import Any

from qdrant_loader.core.state.models import Base
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

context: Any = importlib.import_module("alembic.context")
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _is_special_sqlite_form(raw_path: str) -> bool:
    """Return True for SQLite in-memory/URI-memory forms that must not be rewritten."""
    raw_path_lower = raw_path.lower()
    if raw_path == ":memory:":
        return True
    return raw_path_lower.startswith("file:") and (
        "mode=memory" in raw_path_lower or "memory" in raw_path_lower
    )


def _deterministic_sqlalchemy_url() -> str:
    """Resolve DB URL consistently regardless of current working directory."""
    state_db_url = os.getenv("STATE_DB_URL")
    if state_db_url:
        return state_db_url

    state_db_path = os.getenv("STATE_DB_PATH")
    if state_db_path:
        # Backward compatibility: allow either legacy path values or full DSNs.
        if "://" in state_db_path:
            return state_db_path

        if _is_special_sqlite_form(state_db_path):
            return f"sqlite:///{state_db_path}"

        candidate = Path(state_db_path).expanduser()
        if not candidate.is_absolute() and config.config_file_name is not None:
            candidate = Path(config.config_file_name).resolve().parent / candidate
        return f"sqlite:///{candidate.resolve().as_posix()}"

    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url is None:
        raise ValueError("Missing sqlalchemy.url in Alembic configuration")

    parsed = make_url(configured_url)
    if parsed.drivername.startswith("sqlite"):
        raw_path = parsed.database or ""
        if _is_special_sqlite_form(raw_path):
            return configured_url

        if (
            raw_path
            and not Path(raw_path).is_absolute()
            and config.config_file_name is not None
        ):
            resolved = (
                Path(config.config_file_name).resolve().parent / raw_path
            ).resolve()
            return str(parsed.set(database=resolved.as_posix()))

    return configured_url


config.set_main_option("sqlalchemy.url", _deterministic_sqlalchemy_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
