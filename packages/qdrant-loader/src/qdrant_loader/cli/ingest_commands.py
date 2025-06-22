"""Data ingestion CLI commands.

This module contains all CLI commands related to data ingestion from
various sources like Git, Confluence, JIRA, and other data sources.
Includes commands for initialization, running ingestion pipelines,
and monitoring ingestion status.
"""

import asyncio
from pathlib import Path

import click
from click.exceptions import ClickException

from qdrant_loader.cli.asyncio import async_command

# Import init_collection for tests
from qdrant_loader.core.init_collection import init_collection

from .core import (
    CONFIG_OPTION,
    ENV_OPTION,
    LOG_LEVEL_OPTION,
    WORKSPACE_OPTION,
    cancel_all_tasks,
    check_settings,
    get_logger,
    handle_sigint_for_ingest,
    load_config_with_workspace,
    setup_logging,
    setup_workspace,
    validate_workspace_flags,
)


class IngestionManager:
    """Manager for handling ingestion operations."""

    def __init__(self, settings, project=None, source_type=None, source=None):
        """Initialize ingestion manager.

        Args:
            settings: Application settings
            project: Optional project filter
            source_type: Optional source type filter
            source: Optional source filter
        """
        self.settings = settings
        self.project = project
        self.source_type = source_type
        self.source = source

    async def run_ingestion(self):
        """Run the ingestion process."""
        # Lazy import to avoid slow startup
        from qdrant_loader.core.ingestion_pipeline import IngestionPipeline

        pipeline = IngestionPipeline(self.settings)
        await pipeline.run(
            project_filter=self.project,
            source_type_filter=self.source_type,
            source_filter=self.source,
        )


class IngestStatusChecker:
    """Checker for ingestion status operations."""

    def __init__(self, settings, project=None):
        """Initialize status checker.

        Args:
            settings: Application settings
            project: Optional project filter
        """
        self.settings = settings
        self.project = project

    async def get_status(self):
        """Get ingestion status."""
        # Lazy import to avoid slow startup
        from qdrant_loader.core.status_checker import get_ingestion_status

        return await get_ingestion_status(self.settings, project_filter=self.project)


@click.group(name="ingest")
def ingest_group():
    """Data ingestion commands for processing documents from various sources."""
    pass


async def run_init(settings, force: bool) -> None:
    """Run initialization process.

    Args:
        settings: Application settings
        force: Whether to force reinitialization

    Raises:
        ClickException: If initialization fails
    """
    try:
        result = init_collection(settings, force)
        if not result:
            raise ClickException("Failed to initialize collection")

        # Provide user-friendly feedback
        if force:
            get_logger().info(
                "Collection recreated successfully",
                collection=settings.qdrant_collection_name,
            )
        else:
            get_logger().info(
                "Collection initialized successfully",
                collection=settings.qdrant_collection_name,
            )

    except Exception as e:
        get_logger().error("init_failed", error=str(e))
        raise ClickException(f"Failed to initialize collection: {str(e)}") from e


@ingest_group.command(name="init")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option("--force", is_flag=True, help="Force reinitialization of collection.")
@LOG_LEVEL_OPTION
@async_command
async def init(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    force: bool,
    log_level: str,
):
    """Initialize QDrant collection and prepare for data ingestion.

    This command sets up the QDrant collection with the proper schema
    and configuration needed for document ingestion. Use --force to
    recreate an existing collection.

    Examples:
        # Initialize collection
        qdrant-loader ingest init

        # Force recreate existing collection
        qdrant-loader ingest init --force

        # Initialize with specific workspace
        qdrant-loader ingest init --workspace ./my-workspace
    """
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)

        # Load configuration
        load_config_with_workspace(workspace_config, config, env)
        settings = check_settings()

        # Delete and recreate the database file if it exists
        db_path = settings.global_config.state_management.database_path
        if db_path != ":memory:":
            import os

            from .core import create_database_directory

            # Ensure the directory exists
            db_dir = Path(db_path).parent
            if not db_dir.exists():
                if not create_database_directory(db_dir):
                    raise ClickException(
                        "Database directory creation declined. Exiting."
                    )

            # Delete the database file if it exists and force
            if os.path.exists(db_path) and force:
                get_logger().info("Resetting state database", database_path=db_path)
                os.remove(db_path)
                get_logger().info(
                    "State database reset completed", database_path=db_path
                )
            elif force:
                get_logger().info(
                    "State database reset skipped (no existing database)",
                    database_path=db_path,
                )

        await run_init(settings, force)

    except ClickException as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error("init_failed", error=str(e))
        raise e from None
    except Exception as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error("init_failed", error=str(e))
        raise ClickException(f"Failed to initialize collection: {str(e)}") from e


@ingest_group.command(name="run")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--project",
    type=str,
    help="Project ID to process. If specified, --source-type and --source will filter within this project.",
)
@click.option(
    "--source-type",
    type=str,
    help="Source type to process (e.g., confluence, jira, git). If --project is specified, filters within that project; otherwise applies to all projects.",
)
@click.option(
    "--source",
    type=str,
    help="Source name to process. If --project is specified, filters within that project; otherwise applies to all projects.",
)
@LOG_LEVEL_OPTION
@click.option(
    "--profile/--no-profile",
    default=False,
    help="Run the ingestion under cProfile and save output to 'profile.out' (for performance analysis).",
)
@async_command
async def run_ingest(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project: str | None,
    source_type: str | None,
    source: str | None,
    log_level: str,
    profile: bool,
):
    """Ingest documents from configured sources.

    This command processes documents from various data sources (Git, Confluence,
    JIRA, etc.) and stores them in the QDrant vector database. You can filter
    the ingestion by project, source type, or specific sources.

    Examples:
        # Ingest all projects
        qdrant-loader ingest run

        # Ingest specific project
        qdrant-loader ingest run --project my-project

        # Ingest specific source type from all projects
        qdrant-loader ingest run --source-type git

        # Ingest specific source type from specific project
        qdrant-loader ingest run --project my-project --source-type git

        # Ingest specific source from specific project
        qdrant-loader ingest run --project my-project --source-type git --source my-repo

        # Run with performance profiling
        qdrant-loader ingest run --profile
    """
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)

        # Load configuration
        load_config_with_workspace(workspace_config, config, env)
        settings = check_settings()

        # Lazy import to avoid slow startup
        from qdrant_loader.core.managers.qdrant_manager import QdrantManager

        qdrant_manager = QdrantManager(settings)

        async def run_ingest_pipeline():
            # Lazy import to avoid slow startup
            from qdrant_loader.core.async_ingestion_pipeline import (
                AsyncIngestionPipeline,
            )

            # Create pipeline with workspace-aware metrics path
            if workspace_config:
                pipeline = AsyncIngestionPipeline(
                    settings, qdrant_manager, metrics_dir=workspace_config.metrics_path
                )
            else:
                pipeline = AsyncIngestionPipeline(settings, qdrant_manager)

            try:
                await pipeline.process_documents(
                    project_id=project,
                    source_type=source_type,
                    source=source,
                )
            finally:
                # Ensure proper cleanup of the async pipeline
                await pipeline.cleanup()

        stop_event = handle_sigint_for_ingest()

        try:
            if profile:
                import cProfile

                profiler = cProfile.Profile()
                profiler.enable()
                try:
                    await run_ingest_pipeline()
                finally:
                    profiler.disable()
                    profiler.dump_stats("profile.out")
                    from qdrant_loader.utils.logging import LoggingConfig

                    LoggingConfig.get_logger(__name__).info(
                        "Profile saved to profile.out"
                    )
            else:
                await run_ingest_pipeline()

            from qdrant_loader.utils.logging import LoggingConfig

            logger = LoggingConfig.get_logger(__name__)
            logger.info("Pipeline finished, awaiting cleanup.")

            # Wait for all pending tasks
            pending = [
                t
                for t in asyncio.all_tasks()
                if t is not asyncio.current_task() and not t.done()
            ]
            if pending:
                logger.debug(f"Awaiting {len(pending)} pending tasks before exit...")
                await asyncio.gather(*pending, return_exceptions=True)
            await asyncio.sleep(0.1)
        except Exception as e:
            from qdrant_loader.utils.logging import LoggingConfig

            logger = LoggingConfig.get_logger(__name__)
            logger.error(f"Exception in ingest: {e}")
            raise
        finally:
            if stop_event.is_set():
                await cancel_all_tasks()
                from qdrant_loader.utils.logging import LoggingConfig

                logger = LoggingConfig.get_logger(__name__)
                logger.debug("All tasks cancelled, exiting after SIGINT.")

    except ClickException as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error("ingest_failed", error=str(e))
        raise e from None
    except Exception as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error("ingest_failed", error=str(e))
        raise ClickException(f"Failed to run ingestion: {str(e)}") from e


@ingest_group.command(name="status")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--project",
    type=str,
    help="Project ID to check status for. If not specified, shows status for all projects.",
)
@LOG_LEVEL_OPTION
def check_status(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project: str | None,
    log_level: str,
):
    """Check the status of data ingestion and collection health.

    This command provides information about the current state of the
    QDrant collection, ingestion progress, and any potential issues.

    Examples:
        # Check overall ingestion status
        qdrant-loader ingest status

        # Check status for specific project
        qdrant-loader ingest status --project my-project

        # Check status with detailed logging
        qdrant-loader ingest status --log-level DEBUG
    """
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)

        # Load configuration
        load_config_with_workspace(workspace_config, config, env)
        settings = check_settings()

        # Lazy import to avoid slow startup
        from qdrant_loader.core.managers.qdrant_manager import QdrantManager

        qdrant_manager = QdrantManager(settings)

        # Check collection status
        try:
            client = qdrant_manager._ensure_client_connected()

            # Check if collection exists
            collections = client.get_collections()
            collection_exists = any(
                c.name == settings.qdrant_collection_name
                for c in collections.collections
            )

            if collection_exists:
                # Get collection info
                collection_info = client.get_collection(settings.qdrant_collection_name)
                click.echo("✅ QDrant Collection Status:")
                click.echo(f"  Collection: {settings.qdrant_collection_name}")
                click.echo("  Status: Active")
                click.echo(f"  Vector Count: {collection_info.points_count}")
                # Get vector size from the first vector configuration
                vectors = collection_info.config.params.vectors
                if isinstance(vectors, dict) and vectors:
                    first_vector = next(iter(vectors.values()))
                    vector_size = first_vector.size
                else:
                    vector_size = "Unknown"
                click.echo(f"  Vector Size: {vector_size}")
            else:
                click.echo("❌ QDrant Collection Status:")
                click.echo(f"  Collection: {settings.qdrant_collection_name}")
                click.echo("  Status: Not found or not accessible")
                click.echo(
                    "  💡 Run 'qdrant-loader ingest init' to initialize the collection"
                )
        except Exception as e:
            click.echo("❌ QDrant Collection Status:")
            click.echo(f"  Error: {str(e)}")
            click.echo("  💡 Check your QDrant configuration and connection")

        # Check project configurations if specified
        if project:
            if (
                settings.projects_config
                and project in settings.projects_config.projects
            ):
                project_config = settings.projects_config.projects[project]
                click.echo(f"\n📁 Project '{project}' Configuration:")
                click.echo(f"  Display Name: {project_config.display_name}")
                click.echo(
                    f"  Description: {project_config.description or 'No description'}"
                )

                # Count sources
                source_count = 0
                if hasattr(project_config.sources, "__dict__"):
                    source_count = len(
                        [s for s in project_config.sources.__dict__.values() if s]
                    )
                elif isinstance(project_config.sources, dict):
                    source_count = len(project_config.sources)

                click.echo(f"  Sources: {source_count} configured")
            else:
                click.echo(f"\n❌ Project '{project}' not found in configuration")
        else:
            # Show summary of all projects
            if settings.projects_config and settings.projects_config.projects:
                click.echo("\n📁 Projects Summary:")
                click.echo(
                    f"  Total Projects: {len(settings.projects_config.projects)}"
                )
                for proj_id, proj_config in settings.projects_config.projects.items():
                    source_count = 0
                    if hasattr(proj_config.sources, "__dict__"):
                        source_count = len(
                            [s for s in proj_config.sources.__dict__.values() if s]
                        )
                    elif isinstance(proj_config.sources, dict):
                        source_count = len(proj_config.sources)

                    click.echo(f"    • {proj_id}: {source_count} sources")
            else:
                click.echo("\n📁 No projects configured")

    except Exception as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error("status_check_failed", error=str(e))
        raise ClickException(f"Failed to check ingestion status: {str(e)}") from e


# For backward compatibility, also register the main ingest command
@click.command(name="ingest")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--project",
    type=str,
    help="Project ID to process. If specified, --source-type and --source will filter within this project.",
)
@click.option(
    "--source-type",
    type=str,
    help="Source type to process (e.g., confluence, jira, git). If --project is specified, filters within that project; otherwise applies to all projects.",
)
@click.option(
    "--source",
    type=str,
    help="Source name to process. If --project is specified, filters within that project; otherwise applies to all projects.",
)
@LOG_LEVEL_OPTION
@click.option(
    "--profile/--no-profile",
    default=False,
    help="Run the ingestion under cProfile and save output to 'profile.out' (for performance analysis).",
)
@async_command
async def ingest_command(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project: str | None,
    source_type: str | None,
    source: str | None,
    log_level: str,
    profile: bool,
):
    """Ingest documents from configured sources (backward compatibility command).

    This is the original ingest command for backward compatibility.
    For new usage, prefer 'qdrant-loader ingest run'.
    """
    # This is the same as run_ingest but registered as a standalone command
    # for backward compatibility with the original CLI
    await run_ingest(
        workspace, config, env, project, source_type, source, log_level, profile
    )


# For backward compatibility, also register the init command
@click.command(name="init")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option("--force", is_flag=True, help="Force reinitialization of collection.")
@LOG_LEVEL_OPTION
@async_command
async def init_command(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    force: bool,
    log_level: str,
):
    """Initialize QDrant collection (backward compatibility command).

    This is the original init command for backward compatibility.
    For new usage, prefer 'qdrant-loader ingest init'.
    """
    # This is the same as init but registered as a standalone command
    # for backward compatibility with the original CLI
    await init(workspace, config, env, force, log_level)
