"""CLI module for QDrant Loader."""

import asyncio
import importlib.metadata
import logging
from pathlib import Path
from typing import Optional
import os

import click
import structlog
from click.decorators import group, option
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo

from qdrant_loader.config import get_settings, initialize_config, Settings
from qdrant_loader.config.state import DatabaseDirectoryError
from qdrant_loader.core.ingestion_pipeline import IngestionPipeline
from qdrant_loader.core.init_collection import init_collection
from qdrant_loader.core.qdrant_manager import QdrantConnectionError, QdrantManager

logger = structlog.get_logger()


def _setup_logging(log_level: str) -> None:
    """Setup logging configuration."""
    try:
        level = getattr(logging, log_level.upper())
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level))
    except AttributeError:
        raise ClickException(f"Invalid log level: {log_level}")


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
        logger.error("directory_creation_failed", error=str(e))
        raise ClickException(f"Failed to create directory: {str(e)}")


def _load_config(config_path: Optional[Path] = None, skip_validation: bool = False) -> None:
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
                raise ClickException(f"Config file not found: {str(config_path)}")
            initialize_config(config_path, skip_validation=skip_validation)
            return

        # Step 2: If no config path, look for config.yaml in current folder
        default_config = Path("config.yaml")
        if default_config.exists():
            initialize_config(default_config, skip_validation=skip_validation)
            return

        # Step 3: If no file is found, raise an error
        logger.error("config_not_found", path=str(default_config))
        raise ClickException(
            "No config file found. Please specify a config file or create config.yaml in the current directory"
        )

    except DatabaseDirectoryError as e:
        if skip_validation:
            # For config display, we don't need to create the directory
            return

        # Get the path from the error and expand it properly
        path = Path(os.path.expanduser(str(e.path)))
        if not _create_database_directory(path):
            raise ClickException("Database directory creation declined. Exiting.")

        # No need to retry _load_config since the directory is now created
        # Just initialize the config with the expanded path
        if config_path is not None:
            initialize_config(config_path, skip_validation=skip_validation)
        else:
            initialize_config(Path("config.yaml"), skip_validation=skip_validation)

    except ClickException:
        raise


def _check_settings():
    """Check if settings are available."""
    settings = get_settings()
    if settings is None:
        logger.error("settings_not_available")
        raise ClickException("Settings not available")
    return settings


@group()
def cli():
    """QDrant Loader - A tool for collecting and vectorizing technical content."""
    pass


@cli.command()
@option("--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file.")
@option("--force", is_flag=True, help="Force reinitialization of collection.")
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
def init(config: Optional[Path], force: bool, log_level: str):
    """Initialize QDrant collection."""
    try:
        _setup_logging(log_level)
        _load_config(config)
        settings = _check_settings()

        result = asyncio.run(init_collection(settings, force))
        if result:
            logger.info("collection_initialized")
        else:
            logger.error("collection_initialization_failed")
            raise ClickException("Failed to initialize collection")

    except ClickException:
        raise
    except Exception as e:
        logger.error("init_failed", error=str(e))
        raise ClickException(f"Failed to initialize collection: {str(e)}")


@cli.command()
@option("--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file.")
@option("--source-type", type=str, help="Source type to process (e.g., confluence, jira).")
@option("--source", type=str, help="Source name to process.")
@option("--verbose", is_flag=True, help="Enable verbose output.")
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
def ingest(
    config: Optional[Path],
    source_type: Optional[str],
    source: Optional[str],
    verbose: bool,
    log_level: str,
):
    """Ingest documents into QDrant."""
    try:
        _setup_logging(log_level)
        _load_config(config)
        settings = _check_settings()

        if source and not source_type:
            logger.error("source_name_without_type")
            raise ClickException("Source name provided without source type")

        # Check if collection exists
        try:
            qdrant_manager = QdrantManager(settings)
            if qdrant_manager.client is None:
                raise ClickException("Failed to initialize Qdrant client")

            collections = qdrant_manager.client.get_collections()
            if not any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections.collections):
                logger.error("collection_not_found", collection=settings.QDRANT_COLLECTION_NAME)
                raise ClickException(
                    f"Collection '{settings.QDRANT_COLLECTION_NAME}' does not exist. "
                    "Please run 'qdrant-loader init' first to create the collection."
                )
        except QdrantConnectionError as e:
            logger.error("connection_failed", error=str(e))
            raise ClickException(str(e))
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                raise QdrantConnectionError(
                    "Failed to connect to Qdrant: Connection refused. Please check if the Qdrant server is running and accessible at the specified URL.",
                    original_error=error_msg,
                    url=settings.QDRANT_URL,
                )
            elif "Invalid API key" in error_msg:
                raise QdrantConnectionError(
                    "Failed to connect to Qdrant: Invalid API key. Please check your QDRANT_API_KEY environment variable.",
                    original_error=error_msg,
                )
            elif "timeout" in error_msg.lower():
                raise QdrantConnectionError(
                    "Failed to connect to Qdrant: Connection timeout. Please check if the Qdrant server is running and accessible at the specified URL.",
                    original_error=error_msg,
                    url=settings.QDRANT_URL,
                )
            else:
                raise QdrantConnectionError(
                    "Failed to connect to Qdrant: Unexpected error. Please check your configuration and ensure the Qdrant server is running.",
                    original_error=error_msg,
                    url=settings.QDRANT_URL,
                )

        pipeline = IngestionPipeline(settings=settings)
        asyncio.run(
            pipeline.process_documents(
                sources_config=settings.sources_config, source_type=source_type, source_name=source
            )
        )
        logger.info("ingestion_completed")

    except ClickException as e:
        logger.error("ingestion_failed", error=str(e))
        raise
    except Exception as e:
        logger.error("ingestion_failed", error=str(e))
        raise ClickException(f"Failed to process documents: {str(e)}")


@cli.command()
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
@option("--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file.")
def config(log_level: str, config: Optional[Path]):
    """Display current configuration."""
    try:
        _setup_logging(log_level)

        # Load and validate config without initializing global settings
        config_path = config or Path("config.yaml")
        if not config_path.exists():
            logger.error("config_not_found", path=str(config_path))
            raise ClickException(
                "No config file found. Please specify a config file or create config.yaml in the current directory"
            )

        # Create a temporary Settings instance for validation
        settings = Settings.from_yaml(config_path, skip_validation=True)

        # Get the expanded database path
        expanded_path = os.path.expanduser(settings.STATE_DB_PATH)
        settings.global_config.state_management.database_path = expanded_path

        echo("Current Configuration:")
        echo(settings.model_dump_json(indent=2))

    except ClickException as e:
        logger.error("config_display_failed", error=str(e))
        raise
    except Exception as e:
        logger.error("config_display_failed", error=str(e))
        raise ClickException(f"Failed to display configuration: {str(e)}")


@cli.command()
@option(
    "--log-level",
    type=Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level.",
)
def version(log_level: str):
    """Display QDrant Loader version."""
    try:
        _setup_logging(log_level)
        version = importlib.metadata.version("qdrant-loader")
        echo(f"QDrant Loader version {version}")
    except Exception as e:
        logger.error("version_display_failed", error=str(e))
        raise ClickException(f"Failed to get version information: {str(e)}")


if __name__ == "__main__":
    cli()
