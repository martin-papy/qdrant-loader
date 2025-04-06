"""
Command Line Interface for QDrant Loader.
"""
import click
import structlog
from pathlib import Path
from typing import Optional

from .config import get_settings, get_global_config, Settings, SourcesConfig
from .ingestion_pipeline import IngestionPipeline
from .init_collection import init_collection
from .utils.logger import setup_logging

logger = structlog.get_logger()

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), 
              default='INFO', help='Set the logging level')
def cli(verbose: bool, log_level: str):
    """QDrant Loader - A tool for collecting and vectorizing technical content."""
    # Configure logging
    setup_logging(log_level=log_level)
    if verbose:
        logger.info("Verbose mode enabled")

@cli.command()
@click.option('--force', '-f', is_flag=True, help='Force reinitialization of collection')
def init(force: bool):
    """Initialize the qDrant collection."""
    try:
        settings = get_settings()
        if not settings:
            raise click.ClickException("Settings not available. Please check your environment variables.")
        
        if force:
            logger.info("Force reinitialization requested")
        
        init_collection()
        logger.info("Collection initialization completed successfully")
    except Exception as e:
        logger.error("Failed to initialize collection", error=str(e))
        raise click.ClickException(f"Failed to initialize collection: {str(e)}")

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--source', '-s', help='Specific source to ingest')
def ingest(config: Optional[str], source: Optional[str]):
    """Run the ingestion pipeline."""
    try:
        settings = get_settings()
        if not settings:
            raise click.ClickException("Settings not available. Please check your environment variables.")
        
        # Load configuration
        config_path = config or "config.yaml"
        if not Path(config_path).exists():
            raise click.ClickException(f"Configuration file not found: {config_path}")
        
        # Load and parse the configuration file
        try:
            sources_config = SourcesConfig.from_yaml(config_path)
        except Exception as e:
            raise click.ClickException(f"Failed to load configuration: {str(e)}")
        
        pipeline = IngestionPipeline()
        logger.info("Starting ingestion pipeline", config_path=config_path, source=source)
        
        # Process documents with the parsed configuration
        pipeline.process_documents(sources_config)
        
        logger.info("Ingestion completed successfully")
    except Exception as e:
        logger.error("Failed to run ingestion pipeline", error=str(e))
        raise click.ClickException(f"Failed to run ingestion pipeline: {str(e)}")

@cli.command()
def config():
    """Show current configuration."""
    try:
        settings = get_settings()
        if not settings:
            raise click.ClickException("Settings not available. Please check your environment variables.")
        
        global_config = get_global_config()
        
        click.echo("Current Configuration:")
        click.echo("\nEnvironment Settings:")
        for field in Settings.model_fields:
            if field.startswith("QDRANT_") or field.startswith("OPENAI_"):
                value = getattr(settings, field)
                click.echo(f"  {field}: {'*' * len(value) if 'KEY' in field else value}")
        
        click.echo("\nGlobal Configuration:")
        click.echo(f"  Chunking: {global_config.chunking}")
        click.echo(f"  Embedding Model: {global_config.embedding.model}")
        click.echo(f"  Logging: {global_config.logging}")
        
    except Exception as e:
        logger.error("Failed to show configuration", error=str(e))
        raise click.ClickException(f"Failed to show configuration: {str(e)}")

@cli.command()
def version():
    """Show version information."""
    try:
        from importlib.metadata import version
        click.echo(f"QDrant Loader version: {version('qdrant-loader')}")
    except Exception as e:
        logger.error("Failed to get version information", error=str(e))
        raise click.ClickException(f"Failed to get version information: {str(e)}")

if __name__ == '__main__':
    cli() 