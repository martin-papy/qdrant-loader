from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Alembic using DB path resolved from qdrant-loader Settings "
            "(workspace/config/env aware)."
        )
    )
    parser.add_argument(
        "alembic_args",
        nargs=argparse.REMAINDER,
        help=("Arguments passed to Alembic, e.g.: upgrade head, current, history"),
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Workspace directory containing config.yaml and optional .env",
    )
    parser.add_argument(
        "--config", dest="config_path", type=Path, help="Path to config.yaml"
    )
    parser.add_argument("--env", dest="env_path", type=Path, help="Path to .env file")
    parser.add_argument(
        "--alembic-config",
        dest="alembic_config",
        type=Path,
        default=Path("packages/qdrant-loader/alembic.ini"),
        help="Path to alembic.ini (default: packages/qdrant-loader/alembic.ini)",
    )
    return parser


def _resolve_state_db_path(
    workspace: Path | None, config_path: Path | None, env_path: Path | None
) -> str:
    repo_root = Path(__file__).resolve().parent.parent
    package_root = repo_root / "packages" / "qdrant-loader"
    src_path = package_root / "src"

    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    try:
        from qdrant_loader.cli.config_loader import (
            load_config_with_workspace,
            setup_workspace,
        )
        from qdrant_loader.config import get_settings
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "Failed to import qdrant_loader settings modules; "
            f"check package installation and sys.path (expected source path: {src_path})"
        ) from exc

    workspace_config = setup_workspace(workspace) if workspace else None

    resolved_config = config_path
    if resolved_config is None and workspace is None:
        default_config = repo_root / "config.yaml"
        if default_config.exists():
            resolved_config = default_config

    if resolved_config is not None:
        resolved_config = resolved_config.resolve()
    if env_path is not None:
        env_path = env_path.resolve()

    load_config_with_workspace(
        workspace_config=workspace_config,
        config_path=resolved_config,
        env_path=env_path,
        skip_validation=False,
    )

    settings = get_settings()
    try:
        return settings.global_config.state_management.database_path
    except (AttributeError, TypeError) as exc:
        raise RuntimeError(
            "Invalid settings structure: missing global_config.state_management.database_path"
        ) from exc


def _is_special_sqlite_form(raw_path: str) -> bool:
    raw_path_lower = raw_path.lower()
    if raw_path == ":memory:":
        return True
    return raw_path_lower.startswith("file:") and (
        "mode=memory" in raw_path_lower or "memory" in raw_path_lower
    )


def _to_sqlalchemy_database_url(database_value: str) -> str:
    """Convert configured database value into a SQLAlchemy URL.

    Accepts either a full DSN (e.g. postgresql+asyncpg://...) or a SQLite
    filesystem path (existing behavior).
    """
    raw_value = database_value.strip()
    if not raw_value:
        raise RuntimeError("Resolved empty database value from settings")

    if "://" in raw_value:
        return raw_value

    if _is_special_sqlite_form(raw_value):
        return f"sqlite:///{raw_value}"

    candidate = Path(raw_value).expanduser()
    return f"sqlite:///{candidate.resolve().as_posix()}"


def _redact_database_url(database_url: str) -> str:
    """Redact credentials in DSN-style database URLs before logging."""
    try:
        parts = urlsplit(database_url)
    except ValueError:
        return database_url

    if not parts.scheme or not parts.netloc:
        return database_url

    if "@" not in parts.netloc:
        return database_url

    userinfo, hostinfo = parts.netloc.rsplit("@", 1)
    if ":" not in userinfo:
        return database_url

    username, _password = userinfo.split(":", 1)
    redacted_netloc = f"{username}:***@{hostinfo}"
    return urlunsplit(
        (parts.scheme, redacted_netloc, parts.path, parts.query, parts.fragment)
    )


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    alembic_args = args.alembic_args or ["upgrade", "head"]
    if alembic_args and alembic_args[0] == "--":
        alembic_args = alembic_args[1:]

    repo_root = Path(__file__).resolve().parent.parent
    package_root = repo_root / "packages" / "qdrant-loader"
    alembic_config = args.alembic_config.resolve()
    if not alembic_config.exists() or not alembic_config.is_file():
        raise SystemExit(f"Alembic config file not found: {alembic_config}")

    if args.workspace and (args.config_path or args.env_path):
        parser.error("Cannot combine --workspace with --config/--env")

    database_value = _resolve_state_db_path(
        args.workspace, args.config_path, args.env_path
    )
    database_url = _to_sqlalchemy_database_url(database_value)

    child_env = os.environ.copy()
    child_env["STATE_DB_URL"] = database_url

    cmd = [sys.executable, "-m", "alembic", "-c", str(alembic_config), *alembic_args]
    print(f"Resolved STATE_DB_URL={_redact_database_url(database_url)}")
    print("Running:", " ".join(cmd))

    result = subprocess.run(cmd, cwd=package_root, env=child_env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
