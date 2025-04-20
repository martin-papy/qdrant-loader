"""CLI module for QDrant Loader."""

import json
import os
from pathlib import Path

import click
import tomli
from click.decorators import group, option
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo

from qdrant_loader.cli.asyncio import async_command
from qdrant_loader.config import Settings, get_settings, initialize_config
from qdrant_loader.config.state import DatabaseDirectoryError
from qdrant_loader.core.ingestion_pipeline import IngestionPipeline
from qdrant_loader.core.init_collection import init_collection
from qdrant_loader.core.qdrant_manager import QdrantConnectionError, QdrantManager
from qdrant_loader.utils.logging import LoggingConfig

# Get logger without initializing it
logger = LoggingConfig.get_logger(__name__)


def _get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        with open("pyproject.toml", "rb") as f:
            pyproject = tomli.load(f)
            return pyproject["project"]["version"]
    except Exception as e:
        logger.warning("Failed to read version from pyproject.toml", error=str(e))
        return "Unknown"  # Fallback version


def _setup_logging(log_level: str) -> None:
    """Setup logging configuration."""
    try:
        # Get logging configuration from settings if available
        log_format = "console"
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
        raise ClickException(f"Failed to setup logging: {str(e)!s}") from e


def _create_database_directory(path: Path) -> bool:
    """Create database directory with user confirmation.

    Args:
        path: Path to the database directory

    Returns:
        bool: True if directory was created, False if user declined
    """
    try:
        echo(f"The database directory does not exist: {path.absolute()}")
        if click.confirm("Would you like to create this directory?", default=True):
            path.mkdir(parents=True, mode=0o755)
            echo(f"Created directory: {path.absolute()}")
            return True
        return False
    except Exception as e:
        raise ClickException(f"Failed to create directory: {str(e)!s}") from e


def _load_config(config_path: Path | None = None, skip_validation: bool = False) -> None:
    """Load configuration from file.

    Args:
        config_path: Optional path to config file
        skip_validation: If True, skip directory validation and creation
    """
    try:
        # Step 1: If config path is provided, use it
        if config_path is not None:
            if not config_path.exists():
                logger.error("config_not_found", path=str(config_path))
                raise ClickException(f"Config file not found: {str(config_path)!s}")
            initialize_config(config_path, skip_validation=skip_validation)
            return

        # Step 2: If no config path, look for config.yaml in current folder
        default_config = Path("config.yaml")
        if default_config.exists():
            initialize_config(default_config, skip_validation=skip_validation)
            return

        # Step 3: If no file is found, raise an error
        raise ClickException(
            f"No config file found. Please specify a config file or create config.yaml in the current directory: {str(default_config)!s}"
        )

    except DatabaseDirectoryError as e:
        if skip_validation:
            # For config display, we don't need to create the directory
            return

        # Get the path from the error and expand it properly
        path = Path(os.path.expanduser(str(e.path)))
        if not _create_database_directory(path):
            raise ClickException("Database directory creation declined. Exiting.") from e

        # No need to retry _load_config since the directory is now created
        # Just initialize the config with the expanded path
        if config_path is not None:
            initialize_config(config_path, skip_validation=skip_validation)
        else:
            initialize_config(Path("config.yaml"), skip_validation=skip_validation)

    except ClickException as e:
        raise e from None
    except Exception as e:
        logger.error("config_load_failed", error=str(e))
        raise ClickException(f"Failed to load configuration: {str(e)!s}") from e


def _check_settings():
    """Check if settings are available."""
    settings = get_settings()
    if settings is None:
        logger.error("settings_not_available")
        raise ClickException("Settings not available")
    return settings


@group(name="qdrant-loader")
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
@click.version_option(
    version=_get_version(),
    message="qDrant Loader v.%(version)s",
)
def cli(log_level: str = "INFO") -> None:
    """QDrant Loader CLI."""
    _setup_logging(log_level)


async def _run_init(settings: Settings, force: bool) -> None:
    """Run initialization process."""
    try:
        result = await init_collection(settings, force)
        if not result:
            raise ClickException("Failed to initialize collection")
        logger.info("collection_initialized")
    except Exception as e:
        logger.error("init_failed", error=str(e))
        raise ClickException(f"Failed to initialize collection: {str(e)!s}") from e


@cli.command()
@option("--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file.")
@option("--force", is_flag=True, help="Force reinitialization of collection.")
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
@async_command
async def init(config: Path | None, force: bool, log_level: str):
    """Initialize QDrant collection."""
    try:
        _setup_logging(log_level)
        _load_config(config)
        settings = _check_settings()

        # Delete and recreate the database file if it exists
        db_path = settings.global_config.state_management.database_path
        if db_path != ":memory:":
            # Ensure the directory exists
            db_dir = Path(db_path).parent
            if not db_dir.exists():
                if not _create_database_directory(db_dir):
                    raise ClickException("Database directory creation declined. Exiting.")

            # Delete the database file if it exists and force is True
            if os.path.exists(db_path) and force:
                logger.info(f"Deleting existing database file: {db_path}")
                os.remove(db_path)

        await _run_init(settings, force)

    except ClickException as e:
        logger.error("init_failed", error=str(e))
        raise e from None
    except Exception as e:
        logger.error("init_failed", error=str(e))
        raise ClickException(f"Failed to initialize collection: {str(e)!s}") from e


async def _run_ingest(settings: Settings, source_type: str | None, source: str | None) -> None:
    """Run ingestion process."""
    try:
        # Initialize QDrant manager
        qdrant_manager = QdrantManager(settings)
        qdrant_manager.connect()
        logger.info("Successfully connected to qDrant")

        # Check if collection exists
        client = qdrant_manager._ensure_client_connected()
        collections = client.get_collections()
        if not any(c.name == qdrant_manager.collection_name for c in collections.collections):
            logger.error("collection_not_found")
            raise ClickException("Collection not found")

        # Initialize pipeline
        pipeline = IngestionPipeline(settings, qdrant_manager)
        await pipeline.initialize()

        # Process documents
        documents = await pipeline.process_documents(
            source_type=source_type,
            source=source,
        )

        if documents:
            logger.info(f"Successfully processed {len(documents)} documents")

    except QdrantConnectionError as e:
        logger.error("qdrant_connection_failed", error=str(e))
        raise ClickException(f"Failed to connect to QDrant: {str(e)!s}") from e
    except Exception as e:
        logger.error("ingestion_failed", error=str(e))
        raise ClickException(f"Failed to process documents: {str(e)!s}") from e


@cli.command()
@option("--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file.")
@option("--source-type", type=str, help="Source type to process (e.g., confluence, jira).")
@option("--source", type=str, help="Source name to process.")
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
@async_command
async def ingest(
    config: Path | None,
    source_type: str | None,
    source: str | None,
    log_level: str,
):
    """Ingest documents into QDrant collection."""
    try:
        _setup_logging(log_level)
        _load_config(config)
        settings = _check_settings()

        if source and not source_type:
            logger.error("source_without_type")
            raise ClickException("Source without type")

        await _run_ingest(settings, source_type, source)

    except ClickException as e:
        logger.error("ingest_failed", error=str(e))
        raise e from None
    except Exception as e:
        logger.error("ingest_failed", error=str(e))
        raise ClickException(f"Failed to process documents: {str(e)!s}") from e


@cli.command()
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
@option("--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file.")
def config(log_level: str, config: Path | None):
    """Display current configuration."""
    try:
        _setup_logging(log_level)
        _load_config(config, skip_validation=True)
        settings = _check_settings()

        # Display configuration
        echo("Current Configuration:")
        echo(json.dumps(settings.model_dump(mode="json"), indent=2))

    except Exception as e:
        logger.error("config_failed", error=str(e))
        raise ClickException(f"Failed to display configuration: {str(e)!s}") from e


if __name__ == "__main__":
    cli()
