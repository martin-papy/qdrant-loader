"""CLI module for QDrant Loader."""
import click
import asyncio
import importlib.metadata
from pathlib import Path
import structlog
import logging
from typing import Optional
from qdrant_loader.config import initialize_config, get_settings
from qdrant_loader.core.ingestion_pipeline import IngestionPipeline
from qdrant_loader.core.init_collection import init_collection

logger = structlog.get_logger()

def _setup_logging(log_level: str) -> None:
    """Setup logging configuration."""
    try:
        level = getattr(logging, log_level.upper())
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(level)
        )
    except AttributeError:
        raise click.ClickException(f"Invalid log level: {log_level}")

def _load_config(config_path: Optional[Path] = None) -> None:
    """Load configuration from file."""
    try:
        # Step 1: If config path is provided, use it
        if config_path is not None:
            if not config_path.exists():
                logger.error("config_not_found", path=str(config_path))
                raise click.ClickException(f"Config file not found: {str(config_path)}")
            initialize_config(config_path)
            return

        # Step 2: If no config path, look for config.yaml in current folder
        default_config = Path('config.yaml')
        if default_config.exists():
            initialize_config(default_config)
            return

        # Step 3: If no file is found, raise an error
        logger.error("config_not_found", path=str(default_config))
        raise click.ClickException("No config file found. Please specify a config file or create config.yaml in the current directory")

    except click.ClickException:
        raise
    except Exception as e:
        logger.error("config_load_failed", error=str(e))
        raise click.ClickException(f"Failed to load configuration: {str(e)}")

def _check_settings():
    """Check if settings are available."""
    settings = get_settings()
    if settings is None:
        logger.error("settings_not_available")
        raise click.ClickException("Settings not available")
    return settings

@click.group()
def cli():
    """QDrant Loader - A tool for collecting and vectorizing technical content."""
    pass

@cli.command()
@click.option('--config', type=click.Path(exists=True, path_type=Path), help='Path to config file.')
@click.option('--force', is_flag=True, help='Force reinitialization of collection.')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
              default='INFO', help='Set the logging level.')
def init(config: Optional[Path], force: bool, log_level: str):
    """Initialize QDrant collection."""
    try:
        _setup_logging(log_level)
        _load_config(config)
        settings = _check_settings()
        
        asyncio.run(init_collection(settings, force))
        logger.info("collection_initialized")
        
    except click.ClickException as e:
        logger.error("init_failed", error=str(e))
        raise
    except Exception as e:
        logger.error("init_failed", error=str(e))
        raise click.ClickException(f"Failed to initialize collection: {str(e)}")

@cli.command()
@click.option('--config', type=click.Path(exists=True, path_type=Path), help='Path to config file.')
@click.option('--source-type', type=str, help='Source type to process (e.g., confluence, jira).')
@click.option('--source', type=str, help='Source name to process.')
@click.option('--verbose', is_flag=True, help='Enable verbose output.')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
              default='INFO', help='Set the logging level.')
def ingest(config: Optional[Path], source_type: Optional[str], source: Optional[str], verbose: bool, log_level: str):
    """Ingest documents into QDrant."""
    try:
        _setup_logging(log_level)
        _load_config(config)
        settings = _check_settings()
        
        if source and not source_type:
            logger.error("source_name_without_type")
            raise click.ClickException("Source name provided without source type")
        
        pipeline = IngestionPipeline()
        asyncio.run(pipeline.process_documents(
            config=settings.sources_config,
            source_type=source_type,
            source_name=source
        ))
        logger.info("ingestion_completed")
        
    except click.ClickException as e:
        logger.error("ingestion_failed", error=str(e))
        raise
    except Exception as e:
        logger.error("ingestion_failed", error=str(e))
        raise click.ClickException(f"Failed to process documents: {str(e)}")

@cli.command()
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
              default='INFO', help='Set the logging level.')
def config(log_level: str):
    """Display current configuration."""
    try:
        _setup_logging(log_level)
        settings = _check_settings()
        click.echo("Current Configuration:")
        click.echo(settings.model_dump_json(indent=2))
    except click.ClickException as e:
        logger.error("config_display_failed", error=str(e))
        raise
    except Exception as e:
        logger.error("config_display_failed", error=str(e))
        raise click.ClickException(f"Failed to display configuration: {str(e)}")

@cli.command()
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
              default='INFO', help='Set the logging level.')
def version(log_level: str):
    """Display QDrant Loader version."""
    try:
        _setup_logging(log_level)
        version = importlib.metadata.version('qdrant-loader')
        click.echo(f"QDrant Loader version {version}")
    except Exception as e:
        logger.error("version_display_failed", error=str(e))
        raise click.ClickException(f"Failed to get version information: {str(e)}")

if __name__ == '__main__':
    cli() 