"""CLI module for QDrant Loader."""

from pathlib import Path

import click
from click.decorators import group, option
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo

from qdrant_loader.cli.async_utils import cancel_all_tasks as _cancel_all_tasks_helper
from qdrant_loader.cli.asyncio import async_command
from qdrant_loader.cli.commands import run_init as _commands_run_init
from qdrant_loader.cli.config_loader import setup_workspace as _setup_workspace_impl
from qdrant_loader.cli.logging_utils import get_logger as _get_logger_impl  # noqa: F401
from qdrant_loader.cli.logging_utils import (  # noqa: F401
    setup_logging as _setup_logging_impl,
)
from qdrant_loader.cli.path_utils import (
    create_database_directory as _create_db_dir_helper,
)
from qdrant_loader.cli.update_check import check_for_updates as _check_updates_helper
from qdrant_loader.cli.version import get_version_str as _get_version_str

# Use minimal imports at startup to improve CLI responsiveness.
logger = None  # Logger will be initialized when first accessed.


def _get_version() -> str:
    try:
        return _get_version_str()
    except Exception:
        # Maintain CLI resilience: if version lookup fails for any reason,
        # surface as 'unknown' rather than crashing the CLI.
        return "unknown"


# Back-compat helpers for tests: implement wrappers that operate on this module's global logger


def _get_logger():
    global logger
    if logger is None:
        from qdrant_loader.utils.logging import LoggingConfig

        logger = LoggingConfig.get_logger(__name__)
    return logger


def _setup_logging(log_level: str, workspace_config=None) -> None:
    try:
        from qdrant_loader.utils.logging import LoggingConfig

        log_format = "console"
        log_file = (
            str(workspace_config.logs_path) if workspace_config else "qdrant-loader.log"
        )
        LoggingConfig.setup(level=log_level, format=log_format, file=log_file)
        # update module-global logger
        global logger
        logger = LoggingConfig.get_logger(__name__)
    except Exception as e:  # pragma: no cover - exercised via tests with mock
        from click.exceptions import ClickException

        raise ClickException(f"Failed to setup logging: {str(e)!s}") from e


def _check_for_updates() -> None:
    _check_updates_helper(_get_version())


def _setup_workspace(workspace_path: Path):
    workspace_config = _setup_workspace_impl(workspace_path)
    return workspace_config


@group(name="qdrant-loader")
@option(
    "--log-level",
    type=Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Set the logging level.",
)
@click.version_option(
    version=_get_version(),
    message="qDrant Loader v.%(version)s",
)
def cli(log_level: str = "INFO") -> None:
    """QDrant Loader CLI."""
    # Check for available updates in background without blocking CLI startup.
    _check_for_updates()


def _create_database_directory(path: Path) -> bool:
    """Create database directory with user confirmation.

    Args:
        path: Path to the database directory

    Returns:
        bool: True if directory was created, False if user declined
    """
    try:
        abs_path = path.resolve()
        _get_logger().info("The database directory does not exist", path=str(abs_path))
        created = _create_db_dir_helper(abs_path)
        if created:
            _get_logger().info(f"Created directory: {abs_path}")
        return created
    except ClickException:
        # Propagate ClickException from helper directly
        raise
    except Exception as e:
        # Wrap any other unexpected errors
        raise ClickException(f"Failed to create directory: {str(e)!s}") from e


def _load_config(
    config_path: Path | None = None,
    env_path: Path | None = None,
    skip_validation: bool = False,
) -> None:
    """Load configuration from file.

    Args:
        config_path: Optional path to config file
        env_path: Optional path to .env file
        skip_validation: If True, skip directory validation and creation
    """
    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.config import initialize_config

        # Step 1: If config path is provided, use it
        if config_path is not None:
            if not config_path.exists():
                _get_logger().error("config_not_found", path=str(config_path))
                raise ClickException(f"Config file not found: {str(config_path)!s}")
            initialize_config(config_path, env_path, skip_validation=skip_validation)
            return

        # Step 2: If no config path, look for config.yaml in current folder
        default_config = Path("config.yaml")
        if default_config.exists():
            initialize_config(default_config, env_path, skip_validation=skip_validation)
            return

        # Step 4: If no file is found, raise an error
        raise ClickException(
            f"No config file found. Please specify a config file or create config.yaml in the current directory: {str(default_config)!s}"
        )

    except Exception as e:
        # Handle DatabaseDirectoryError and other exceptions
        from qdrant_loader.config.state import DatabaseDirectoryError

        if isinstance(e, DatabaseDirectoryError):
            if skip_validation:
                # For config display, we don't need to create the directory
                return

            # Get the path from the error - it's already a Path object
            error_path = e.path
            # Resolve to absolute path for consistency
            abs_path = error_path.resolve()

            if not _create_database_directory(abs_path):
                raise ClickException(
                    "Database directory creation declined. Exiting."
                ) from e

            # No need to retry _load_config since the directory is now created
            # Just initialize the config with the expanded path
            if config_path is not None:
                initialize_config(
                    config_path, env_path, skip_validation=skip_validation
                )
            else:
                initialize_config(
                    Path("config.yaml"), env_path, skip_validation=skip_validation
                )
        elif isinstance(e, ClickException):
            raise e from None
        else:
            _get_logger().error("config_load_failed", error=str(e))
            raise ClickException(f"Failed to load configuration: {str(e)!s}") from e


def _check_settings():
    """Check if settings are available."""
    # Lazy import to avoid slow startup
    from qdrant_loader.config import get_settings

    settings = get_settings()
    if settings is None:
        _get_logger().error("settings_not_available")
        raise ClickException("Settings not available")
    return settings


def _load_config_with_workspace(
    workspace_config,
    config_path: Path | None = None,
    env_path: Path | None = None,
    skip_validation: bool = False,
):
    """Compatibility wrapper used by tests and project commands.

    Delegates to qdrant_loader.cli.config_loader.load_config_with_workspace.
    """
    from qdrant_loader.cli.config_loader import (
        load_config_with_workspace as _load_with_ws,
    )

    _load_with_ws(
        workspace_config,
        config_path=config_path,
        env_path=env_path,
        skip_validation=skip_validation,
    )


async def _run_init(settings, force: bool) -> None:
    """Run initialization process via command helper, keeping existing logging."""
    try:
        await _commands_run_init(settings, force)
        if force:
            _get_logger().info(
                "Collection recreated successfully",
                collection=settings.qdrant_collection_name,
            )
        else:
            _get_logger().info(
                "Collection initialized successfully",
                collection=settings.qdrant_collection_name,
            )
    except Exception as e:
        _get_logger().error("init_failed", error=str(e))
        raise ClickException(f"Failed to initialize collection: {str(e)!s}") from e


@cli.command()
@option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files. All output will be stored here.",
)
@option(
    "--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file."
)
@option("--env", type=ClickPath(exists=True, path_type=Path), help="Path to .env file.")
@option("--force", is_flag=True, help="Force reinitialization of collection.")
@option(
    "--log-level",
    type=Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Set the logging level.",
)
@async_command
async def init(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    force: bool,
    log_level: str,
):
    """Initialize QDrant collection."""
    from qdrant_loader.cli.commands.init_cmd import run_init_command

    await run_init_command(workspace, config, env, force, log_level)


async def _cancel_all_tasks():
    await _cancel_all_tasks_helper()


@cli.command()
@option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files. All output will be stored here.",
)
@option(
    "--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file."
)
@option("--env", type=ClickPath(exists=True, path_type=Path), help="Path to .env file.")
@option(
    "--project",
    type=str,
    help="Project ID to process. If specified, --source-type and --source will filter within this project.",
)
@option(
    "--source-type",
    type=str,
    help="Source type to process (e.g., confluence, jira, git). If --project is specified, filters within that project; otherwise applies to all projects.",
)
@option(
    "--source",
    type=str,
    help="Source name to process. If --project is specified, filters within that project; otherwise applies to all projects.",
)
@option(
    "--log-level",
    type=Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Set the logging level.",
)
@option(
    "--profile/--no-profile",
    default=False,
    help="Run the ingestion under cProfile and save output to 'profile.out' (for performance analysis).",
)
@option(
    "--force",
    is_flag=True,
    help="Force processing of all documents, bypassing change detection. Warning: May significantly increase processing time and costs.",
)
@async_command
async def ingest(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project: str | None,
    source_type: str | None,
    source: str | None,
    log_level: str,
    profile: bool,
    force: bool,
):
    """Ingest documents from configured sources.

    Examples:
      # Ingest all projects
      qdrant-loader ingest

      # Ingest specific project
      qdrant-loader ingest --project my-project

      # Ingest specific source type from all projects
      qdrant-loader ingest --source-type git

      # Ingest specific source type from specific project
      qdrant-loader ingest --project my-project --source-type git

      # Ingest specific source from specific project
      qdrant-loader ingest --project my-project --source-type git --source my-repo

      # Force processing of all documents (bypass change detection)
      qdrant-loader ingest --force
    """
    from qdrant_loader.cli.commands.ingest_cmd import run_ingest_command

    await run_ingest_command(
        workspace,
        config,
        env,
        project,
        source_type,
        source,
        log_level,
        profile,
        force,
    )


@cli.command()
@option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files. All output will be stored here.",
)
@option(
    "--log-level",
    type=Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Set the logging level.",
)
@option(
    "--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file."
)
@option("--env", type=ClickPath(exists=True, path_type=Path), help="Path to .env file.")
def config(
    workspace: Path | None, log_level: str, config: Path | None, env: Path | None
):
    """Display current configuration."""
    try:
        echo("Current Configuration:")
        from qdrant_loader.cli.commands.config import (
            run_show_config as _run_show_config,
        )

        output = _run_show_config(workspace, config, env, log_level)
        echo(output)
    except Exception as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error("config_failed", error=str(e))
        raise ClickException(f"Failed to display configuration: {str(e)!s}") from e


# Add project management commands with lazy import
def _add_project_commands():
    """Lazily add project commands to avoid slow startup."""
    from qdrant_loader.cli.project_commands import project_cli

    cli.add_command(project_cli)


# Only add project commands when CLI is actually used
if __name__ == "__main__":
    _add_project_commands()
    cli()
else:
    # For when imported as a module, add commands on first access
    import atexit

    atexit.register(_add_project_commands)
