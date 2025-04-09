"""
Command Line Interface for QDrant Loader.
"""
import click
import structlog
from pathlib import Path
from typing import Optional
import asyncio

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
            click.echo("Force reinitialization requested")
        
        init_collection()
        logger.info("Collection initialization completed successfully")
        click.echo("Collection initialization completed successfully")
    except Exception as e:
        logger.error("Failed to initialize collection", error=str(e))
        raise click.ClickException(f"Failed to initialize collection: {str(e)}")

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to configuration file (defaults to config.yaml in current directory)')
@click.option('--source-type', type=click.Choice(['confluence', 'git', 'public-docs', 'jira']),
              help='Type of source to ingest (confluence, git, public-docs, or jira)')
@click.option('--source', '-s', help='Specific source name to ingest')
def ingest(config: Optional[str], source_type: Optional[str], source: Optional[str]):
    """Run the ingestion pipeline.
    
    If no config file is specified, will look for config.yaml in the current directory.
    
    Examples:
        \b
        # Ingest all sources (using config.yaml from current directory)
        qdrant-loader ingest
        
        # Ingest using specific config file
        qdrant-loader ingest --config custom-config.yaml
        
        # Ingest only Confluence sources
        qdrant-loader ingest --source-type confluence
        
        # Ingest a specific Confluence space
        qdrant-loader ingest --source-type confluence --source my-space
        
        # Ingest only Git repositories
        qdrant-loader ingest --source-type git
        
        # Ingest a specific Git repository
        qdrant-loader ingest --source-type git --source my-repo
        
        # Ingest only JIRA sources
        qdrant-loader ingest --source-type jira
        
        # Ingest a specific JIRA project
        qdrant-loader ingest --source-type jira --source my-project
    """
    try:
        # Try to find config file
        config_path = config
        if config_path is None:
            default_config = Path('config.yaml')
            if default_config.exists():
                config_path = str(default_config)
                logger.info("Using default config.yaml from current directory")
            else:
                raise click.ClickException(
                    "No config file specified and no config.yaml found in current directory. "
                    "Please provide a config file with --config or create config.yaml in the current directory."
                )
        
        # Initialize configuration from the YAML file
        try:
            from .config import initialize_config
            initialize_config(Path(config_path))
        except Exception as e:
            raise click.ClickException(f"Failed to load configuration: {str(e)}")
        
        # Get settings after initialization
        settings = get_settings()
        if not settings:
            raise click.ClickException("Settings not available. Please check your environment variables.")
        
        # Validate source type and name if provided
        if source and not source_type:
            raise click.ClickException("--source-type must be specified when using --source")
        
        pipeline = IngestionPipeline()
        logger.info("Starting ingestion pipeline", 
                   config_path=config_path, 
                   source_type=source_type,
                   source=source)
        
        # Process documents with the initialized configuration
        asyncio.run(pipeline.process_documents(settings.sources_config, source_type=source_type, source_name=source))
        
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