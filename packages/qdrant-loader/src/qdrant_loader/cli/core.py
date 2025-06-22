"""Core CLI utilities and shared functionality.

This module contains common utilities, decorators, error handling,
and shared functions used across all CLI modules.
"""

import asyncio
import os
import signal
from pathlib import Path

import click
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo

# Import WorkspaceConfig for tests

# Global logger instance - initialized lazily
logger = None


def get_logger():
    """Get logger with lazy import to avoid slow startup."""
    global logger
    if logger is None:
        from qdrant_loader.utils.logging import LoggingConfig

        logger = LoggingConfig.get_logger(__name__)
    return logger


def get_version() -> str:
    """Get version using importlib.metadata."""
    try:
        from importlib.metadata import version

        return version("qdrant-loader")
    except ImportError:
        # Fallback for older Python versions
        return "unknown"
    except Exception:
        # Fallback if package not found or other error
        return "unknown"


def check_for_updates():
    """Check for version updates in the background."""
    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.utils.version_check import check_version_async

        current_version = get_version()
        check_version_async(current_version, silent=False)
    except Exception:
        # Silently fail if version check doesn't work
        pass


def setup_logging(log_level: str, workspace_config=None) -> None:
    """Setup logging configuration with workspace support.

    Args:
        log_level: Logging level
        workspace_config: Optional workspace configuration for custom log path

    Raises:
        ClickException: If logging setup fails
    """
    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.utils.logging import LoggingConfig

        # Get logging configuration from settings if available
        log_format = "console"

        # Use workspace log path if available, otherwise default
        if workspace_config:
            log_file = str(workspace_config.logs_path)
        else:
            log_file = "qdrant-loader.log"

        # Reconfigure logging with the provided configuration
        LoggingConfig.setup(
            level=log_level,
            format=log_format,
            file=log_file,
        )

        # Update the global logger with new configuration
        global logger
        logger = LoggingConfig.get_logger(__name__)

    except Exception as e:
        raise ClickException(f"Failed to setup logging: {str(e)}") from e


def setup_workspace(workspace_path: Path):
    """Setup and validate workspace configuration.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        WorkspaceConfig: Validated workspace configuration

    Raises:
        ClickException: If workspace setup fails
    """
    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.config.workspace import (
            create_workspace_structure,
            setup_workspace,
        )

        # Create workspace structure if needed
        create_workspace_structure(workspace_path)

        # Setup and validate workspace
        workspace_config = setup_workspace(workspace_path)

        # Use the global logger (now properly initialized)
        logger = get_logger()
        logger.info("Using workspace", workspace=str(workspace_config.workspace_path))
        if workspace_config.env_path:
            logger.info(
                "Environment file found", env_path=str(workspace_config.env_path)
            )

        if workspace_config.config_path:
            logger.info(
                "Config file found", config_path=str(workspace_config.config_path)
            )

        return workspace_config

    except ValueError as e:
        raise ClickException(str(e)) from e
    except Exception as e:
        raise ClickException(f"Failed to setup workspace: {str(e)}") from e


def load_config_with_workspace(
    workspace_config=None,
    config_path: Path | None = None,
    env_path: Path | None = None,
    skip_validation: bool = False,
    domains: str | None = None,
    preset: str | None = None,
    use_case: str | None = None,
    measure_performance: bool = False,
) -> None:
    """Load configuration with workspace or traditional mode.

    Args:
        workspace_config: Optional workspace configuration
        config_path: Optional path to config file (traditional mode)
        env_path: Optional path to .env file (traditional mode)
        skip_validation: If True, skip directory validation and creation
        domains: Comma-separated list of domains to load
        preset: Predefined domain combination
        use_case: Use case identifier for automatic domain selection
        measure_performance: If True, log performance metrics

    Raises:
        ClickException: If configuration loading fails
    """
    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.config.legacy_detection import (
            detect_legacy_configuration,
            get_migration_guidance,
        )

        if workspace_config:
            # Workspace mode
            get_logger().debug("Loading configuration in workspace mode", is_multi_file=workspace_config.is_multi_file)

            if workspace_config.is_multi_file:
                # New multi-file format - load directly from config directory
                get_logger().debug("Loading multi-file configuration from config directory", 
                                 config_dir=str(workspace_config.config_dir))

                # Parse domains if provided
                domains_set = None
                if domains:
                    domains_set = {d.strip() for d in domains.split(",") if d.strip()}

                # Use multi-file configuration loading with selective domains
                from qdrant_loader.config import initialize_multi_file_config_with_workspace

                initialize_multi_file_config_with_workspace(
                    workspace_config=workspace_config,
                    domains=domains_set,
                    skip_validation=skip_validation,
                    preset=preset,
                    use_case=use_case,
                    measure_performance=measure_performance,
                )
            else:
                # Legacy single-file format - check if migration is needed
                get_logger().debug("Loading legacy single-file configuration")

                # Check for legacy configuration in workspace directory
                is_legacy, legacy_config_path, reason = detect_legacy_configuration(
                    search_dir=workspace_config.workspace_path
                )

                if is_legacy and legacy_config_path:
                    # Legacy configuration detected in workspace
                    guidance = get_migration_guidance(
                        legacy_config_path,
                        suggested_output_dir=workspace_config.workspace_path,
                    )

                    get_logger().warning(
                        "Legacy configuration detected in workspace",
                        file=str(legacy_config_path),
                        workspace=str(workspace_config.workspace_path),
                        reason=reason,
                    )

                    # Display helpful migration message
                    echo("⚠️  Legacy Configuration Detected in Workspace")
                    echo("=" * 55)
                    echo(f"Workspace: {workspace_config.workspace_path}")
                    echo(f"Legacy config: {legacy_config_path}")
                    echo(f"Reason: {reason}")
                    echo()
                    echo("🔄 Migration Required")
                    echo(
                        "The configuration format has been updated to use domain-specific files:"
                    )
                    echo("  • connectivity.yaml (database connections, LLM providers)")
                    echo("  • projects.yaml (project definitions, data sources)")
                    echo("  • fine-tuning.yaml (processing parameters, performance tuning)")
                    echo()
                    echo("📋 Migration Commands:")
                    echo(f"  Preview migration: {guidance['dry_run_command']}")
                    echo(f"  Migrate config:    {guidance['migration_command']}")
                    echo()
                    echo("💡 Run the preview command first to see what will be migrated.")

                    raise ClickException(
                        "Legacy configuration detected in workspace. Please migrate to the new format using the commands above."
                    )

                # Use legacy workspace config loading
                from qdrant_loader.config import initialize_config_with_workspace

                initialize_config_with_workspace(
                    workspace_config=workspace_config,
                    skip_validation=skip_validation,
                )
        else:
            # Traditional mode
            get_logger().debug("Loading configuration in traditional mode")
            load_config(config_path, env_path, skip_validation)

    except Exception as e:
        get_logger().error("config_load_failed", error=str(e))
        raise ClickException(f"Failed to load configuration: {str(e)}") from e


def create_database_directory(path: Path) -> bool:
    """Create database directory with user confirmation.

    Args:
        path: Path to the database directory

    Returns:
        bool: True if directory was created, False if user declined

    Raises:
        ClickException: If directory creation fails
    """
    try:
        get_logger().info(
            "The database directory does not exist", path=str(path.absolute())
        )
        if click.confirm("Would you like to create this directory?", default=True):
            path.mkdir(parents=True, mode=0o755)
            get_logger().info(f"Created directory: {path.absolute()}")
            return True
        return False
    except Exception as e:
        raise ClickException(f"Failed to create directory: {str(e)}") from e


def load_config(
    config_path: Path | None = None,
    env_path: Path | None = None,
    skip_validation: bool = False,
) -> None:
    """Load configuration from file.

    Args:
        config_path: Optional path to config file
        env_path: Optional path to .env file
        skip_validation: If True, skip directory validation and creation

    Raises:
        ClickException: If configuration loading fails
    """
    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.config import initialize_config
        from qdrant_loader.config.legacy_detection import (
            detect_legacy_configuration,
            get_migration_guidance,
        )

        # Step 1: Check for legacy configuration before attempting to load
        is_legacy, legacy_config_path, reason = detect_legacy_configuration(
            config_path=config_path,
            search_dir=Path.cwd() if config_path is None else config_path.parent,
        )

        if is_legacy and legacy_config_path:
            # Legacy configuration detected - provide migration guidance
            guidance = get_migration_guidance(legacy_config_path)

            get_logger().warning(
                "Legacy configuration detected",
                file=str(legacy_config_path),
                reason=reason,
            )

            # Display helpful migration message
            echo("⚠️  Legacy Configuration Detected")
            echo("=" * 50)
            echo(f"Found legacy configuration file: {legacy_config_path}")
            echo(f"Reason: {reason}")
            echo()
            echo("🔄 Migration Required")
            echo(
                "The configuration format has been updated to use domain-specific files:"
            )
            echo("  • connectivity.yaml (database connections, LLM providers)")
            echo("  • projects.yaml (project definitions, data sources)")
            echo("  • fine-tuning.yaml (processing parameters, performance tuning)")
            echo()
            echo("📋 Migration Commands:")
            echo(f"  Preview migration: {guidance['dry_run_command']}")
            echo(f"  Migrate config:    {guidance['migration_command']}")
            echo()
            echo("💡 Run the preview command first to see what will be migrated.")

            raise ClickException(
                "Legacy configuration detected. Please migrate to the new format using the commands above."
            )

        # Step 2: If config path is provided, use it
        if config_path is not None:
            if not config_path.exists():
                get_logger().error("config_not_found", path=str(config_path))
                raise ClickException(f"Config file not found: {str(config_path)}")
            initialize_config(config_path, env_path, skip_validation=skip_validation)
            return

        # Step 3: If no config path, look for config.yaml in current folder
        default_config = Path("config.yaml")
        if default_config.exists():
            initialize_config(default_config, env_path, skip_validation=skip_validation)
            return

        # Step 4: If no file is found, raise an error
        raise ClickException(
            f"No config file found. Please specify a config file or create config.yaml in the current directory: {str(default_config)}"
        )

    except Exception as e:
        # Handle DatabaseDirectoryError and other exceptions
        from qdrant_loader.config.state import DatabaseDirectoryError

        if isinstance(e, DatabaseDirectoryError):
            if skip_validation:
                # For config display, we don't need to create the directory
                return

            # Get the path from the error and expand it properly
            path = Path(os.path.expanduser(str(e.path)))
            if not create_database_directory(path):
                raise ClickException(
                    "Database directory creation declined. Exiting."
                ) from e

            # No need to retry load_config since the directory is now created
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
            get_logger().error("config_load_failed", error=str(e))
            raise ClickException(f"Failed to load configuration: {str(e)}") from e


def check_settings():
    """Check if settings are available.

    Returns:
        Settings: The loaded settings object

    Raises:
        ClickException: If settings are not available
    """
    # Lazy import to avoid slow startup
    from qdrant_loader.config import get_settings

    settings = get_settings()
    if settings is None:
        get_logger().error("settings_not_available")
        raise ClickException("Settings not available")
    return settings


async def cancel_all_tasks():
    """Cancel all running asyncio tasks."""
    tasks = [t for t in asyncio.all_tasks() if not t.done()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


# Common Click options that are reused across commands
WORKSPACE_OPTION = click.option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files. All output will be stored here.",
)

CONFIG_OPTION = click.option(
    "--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file."
)

ENV_OPTION = click.option(
    "--env", type=ClickPath(exists=True, path_type=Path), help="Path to .env file."
)

LOG_LEVEL_OPTION = click.option(
    "--log-level",
    type=Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Set the logging level.",
)

# Selective configuration loading options
DOMAINS_OPTION = click.option(
    "--domains",
    help="Comma-separated list of configuration domains to load (connectivity,projects,fine-tuning).",
)

PRESET_OPTION = click.option(
    "--preset",
    type=Choice(["minimal", "basic", "full"], case_sensitive=False),
    help="Predefined domain combination: minimal (connectivity only), basic (connectivity+projects), full (all domains).",
)

USE_CASE_OPTION = click.option(
    "--use-case",
    type=Choice(
        [
            "config_validation",
            "config_export",
            "basic_ingestion",
            "full_processing",
            "migration",
            "status_check",
        ],
        case_sensitive=False,
    ),
    help="Automatically select domains based on use case.",
)

PERFORMANCE_OPTION = click.option(
    "--measure-performance",
    is_flag=True,
    help="Measure and log configuration loading performance.",
)


def validate_workspace_flags(
    workspace: Path | None, config: Path | None, env: Path | None
) -> None:
    """Validate workspace flag combinations.

    Args:
        workspace: Workspace path
        config: Config file path
        env: Environment file path

    Raises:
        ClickException: If flag combination is invalid
    """
    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.config.workspace import validate_workspace_flags

        validate_workspace_flags(workspace, config, env)
    except Exception as e:
        raise ClickException(str(e)) from e


def handle_sigint_for_ingest():
    """Create a SIGINT handler for ingestion commands."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_sigint():
        from qdrant_loader.utils.logging import LoggingConfig

        logger = LoggingConfig.get_logger(__name__)
        logger.debug("SIGINT received, cancelling all tasks...")
        stop_event.set()

    loop.add_signal_handler(signal.SIGINT, _handle_sigint)
    return stop_event
