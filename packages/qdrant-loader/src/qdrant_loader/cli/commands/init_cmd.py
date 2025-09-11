from __future__ import annotations

from pathlib import Path

from click.exceptions import ClickException

from qdrant_loader.cli.config_loader import (
    load_config_with_workspace as _load_config_with_workspace,
)
from qdrant_loader.cli.config_loader import setup_workspace as _setup_workspace_impl
from qdrant_loader.cli.path_utils import (
    create_database_directory as _create_db_dir_helper,
)
from qdrant_loader.cli.update_check import check_for_updates as _check_updates_helper
from qdrant_loader.cli.version import get_version_str as _get_version_str
from qdrant_loader.config import get_settings
from qdrant_loader.config.state import DatabaseDirectoryError
from qdrant_loader.config.workspace import validate_workspace_flags
from qdrant_loader.utils.logging import LoggingConfig

from . import run_init as _commands_run_init


async def run_init_command(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    force: bool,
    log_level: str,
    max_retries: int = 1,
) -> None:
    """Implementation for the `init` CLI command.

    Keeps side-effects and logging identical to the previous inline implementation.
    """
    attempts = 0
    while True:
        try:
            # Validate flag combinations
            validate_workspace_flags(workspace, config, env)

            # Setup logging first (workspace-aware later). Use core reconfigure if available.
            if getattr(LoggingConfig, "reconfigure", None):  # type: ignore[attr-defined]
                if getattr(LoggingConfig, "_initialized", False):  # type: ignore[attr-defined]
                    LoggingConfig.reconfigure(file="qdrant-loader.log")  # type: ignore[attr-defined]
                else:
                    LoggingConfig.setup(
                        level=log_level, format="console", file="qdrant-loader.log"
                    )
            else:
                import logging as _py_logging

                _py_logging.getLogger().handlers = []
                LoggingConfig.setup(
                    level=log_level, format="console", file="qdrant-loader.log"
                )
            logger = LoggingConfig.get_logger(__name__)

            # Check for updates (non-blocking semantics preserved by immediate return)
            try:
                _check_updates_helper(_get_version_str())
            except Exception:
                # Update check failures should not break the command
                pass

            # Setup workspace if provided
            workspace_config = None
            if workspace:
                workspace_config = _setup_workspace_impl(workspace)
                logger.info(
                    "Using workspace", workspace=str(workspace_config.workspace_path)
                )
                if getattr(workspace_config, "env_path", None):
                    logger.info(
                        "Environment file found",
                        env_path=str(workspace_config.env_path),
                    )
                if getattr(workspace_config, "config_path", None):
                    logger.info(
                        "Config file found",
                        config_path=str(workspace_config.config_path),
                    )

            # Setup logging again with workspace-aware file path
            log_file = (
                str(workspace_config.logs_path)
                if workspace_config
                else "qdrant-loader.log"
            )
            if getattr(LoggingConfig, "reconfigure", None):  # type: ignore[attr-defined]
                LoggingConfig.reconfigure(file=log_file)  # type: ignore[attr-defined]
            else:
                import logging as _py_logging

                _py_logging.getLogger().handlers = []
                LoggingConfig.setup(level=log_level, format="console", file=log_file)

            # Load configuration
            _load_config_with_workspace(workspace_config, config, env)

            # Fetch settings
            settings = get_settings()
            if settings is None:
                logger.error("settings_not_available")
                raise ClickException("Settings not available")

            # Delete and recreate the database file if it exists
            db_path_str = settings.global_config.state_management.database_path
            if db_path_str != ":memory:":
                db_path = Path(db_path_str)
                db_dir = db_path.parent
                if not db_dir.exists():
                    if not _create_database_directory(db_dir):
                        raise ClickException(
                            "Database directory creation declined. Exiting."
                        )

                if db_path.exists() and force:
                    logger.info("Resetting state database", database_path=str(db_path))
                    db_path.unlink()
                    logger.info(
                        "State database reset completed", database_path=str(db_path)
                    )
                elif force:
                    logger.info(
                        "State database reset skipped (no existing database)",
                        database_path=str(db_path),
                    )

            # Run initialization via command helper
            await _commands_run_init(settings, force)
            if force:
                logger.info(
                    "Collection recreated successfully",
                    collection=settings.qdrant_collection_name,
                )
            else:
                logger.info(
                    "Collection initialized successfully",
                    collection=settings.qdrant_collection_name,
                )

            # Completed successfully
            return

        except DatabaseDirectoryError as e:
            # Mirror original behavior for directory creation prompts, then retry if allowed
            if workspace is None:
                # derive from current directory
                target = Path(e.path).resolve()
            else:
                target = e.path.resolve()
            if not _create_database_directory(target):
                raise ClickException(
                    "Database directory creation declined. Exiting."
                ) from e

            if attempts >= max_retries:
                raise ClickException(
                    "Initialization aborted after exhausting retries for database directory creation."
                ) from e
            attempts += 1
            continue

        except ClickException:
            raise
        except Exception as e:
            logger = LoggingConfig.get_logger(__name__)
            logger.error("init_failed", error=str(e))
            raise ClickException(f"Failed to initialize collection: {str(e)!s}") from e


def _create_database_directory(path: Path) -> bool:
    """Create database directory with logging (non-interactive)."""
    try:
        abs_path = path.resolve()
        LoggingConfig.get_logger(__name__).info(
            "The database directory does not exist", path=str(abs_path)
        )
        created = _create_db_dir_helper(abs_path)
        if created:
            LoggingConfig.get_logger(__name__).info(f"Created directory: {abs_path}")
        return created
    except Exception as e:  # pragma: no cover - error path
        raise ClickException(f"Failed to create directory: {str(e)!s}") from e
