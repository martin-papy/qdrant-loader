from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


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
        raw_db_path = settings.global_config.state_management.database_path
    except (AttributeError, TypeError) as exc:
        raise RuntimeError(
            "Invalid settings structure: missing global_config.state_management.database_path"
        ) from exc

    # Normalize file path to absolute path anchored at repository root.
    # This prevents cwd-dependent behavior for values like "./state.db".
    # Always return a filesystem path or ':memory:' (never a sqlite:// URI).
    if raw_db_path in (":memory:", "sqlite:///:memory:", "sqlite://:memory:"):
        return ":memory:"
    # Remove any leading 'sqlite://', 'sqlite:///', or 'sqlite:'
    import re

    # Regex: match 'sqlite:' with any number of slashes after
    path = re.sub(r"^sqlite:(//+)?", "", raw_db_path)
    expanded = Path(os.path.expanduser(os.path.expandvars(path)))
    if expanded.is_absolute():
        return str(expanded)
    return str((repo_root / expanded).resolve())


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

    db_path = _resolve_state_db_path(args.workspace, args.config_path, args.env_path)

    # Report invocation mode for DB path resolution.
    if args.workspace:
        config_source = "workspace"
    elif args.config_path or args.env_path:
        config_source = "config/env flags"
    else:
        config_source = "default (repo root)"
    print(f"[INFO] Using database path from {config_source}: {db_path}")

    child_env = os.environ.copy()
    child_env["STATE_DB_PATH"] = db_path

    cmd = [sys.executable, "-m", "alembic", "-c", str(alembic_config), *alembic_args]
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=package_root, env=child_env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
