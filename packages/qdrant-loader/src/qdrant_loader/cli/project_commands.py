"""Project management CLI commands for QDrant Loader."""

from pathlib import Path

from click.decorators import group, option
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo
from rich.console import Console
from rich.panel import Panel  # noqa: F401 - kept for potential rich layouts
from rich.table import Table  # noqa: F401 - kept for potential rich layouts
from sqlalchemy import func, select

from qdrant_loader.cli.asyncio import async_command
from qdrant_loader.cli.commands.project import run_project_list as _run_project_list
from qdrant_loader.cli.commands.project import run_project_status as _run_project_status
from qdrant_loader.cli.commands.project import (
    run_project_validate as _run_project_validate,
)
from qdrant_loader.config import Settings
from qdrant_loader.config.workspace import validate_workspace_flags
from qdrant_loader.core.project_manager import ProjectManager
from qdrant_loader.core.state.models import DocumentStateRecord, IngestionHistory
from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.utils.logging import LoggingConfig

# Initialize Rich console for enhanced output formatting.
console = Console()


@group(name="project")
def project_cli():
    """Project management commands."""
    pass


def _get_all_sources_from_config(sources_config):
    """Get all sources from a SourcesConfig object."""
    all_sources = {}
    all_sources.update(sources_config.publicdocs)
    all_sources.update(sources_config.git)
    all_sources.update(sources_config.confluence)
    all_sources.update(sources_config.jira)
    all_sources.update(sources_config.localfile)
    return all_sources


async def _get_project_document_count(
    state_manager: StateManager, project_id: str
) -> int:
    """Get the count of non-deleted documents for a project."""
    try:
        # Prefer direct session factory if available (matches tests/mocks)
        session_factory = getattr(state_manager, "_session_factory", None)
        if session_factory is None:
            ctx = await state_manager.get_session()
        else:
            ctx = session_factory() if callable(session_factory) else session_factory
        async with ctx as session:  # type: ignore
            result = await session.execute(
                select(func.count(DocumentStateRecord.id))
                .filter_by(project_id=project_id)
                .filter_by(is_deleted=False)
            )
            count = result.scalar() or 0
            return count
    except Exception:
        # Return zero count if database query fails to ensure graceful degradation.
        return 0


async def _get_project_latest_ingestion(
    state_manager: StateManager, project_id: str
) -> str | None:
    """Get the latest ingestion timestamp for a project."""
    try:
        # Prefer direct session factory if available (matches tests/mocks)
        session_factory = getattr(state_manager, "_session_factory", None)
        if session_factory is None:
            ctx = await state_manager.get_session()
        else:
            ctx = session_factory() if callable(session_factory) else session_factory
        async with ctx as session:  # type: ignore
            result = await session.execute(
                select(IngestionHistory.last_successful_ingestion)
                .filter_by(project_id=project_id)
                .order_by(IngestionHistory.last_successful_ingestion.desc())
                .limit(1)
            )
            timestamp = result.scalar_one_or_none()
            return timestamp.isoformat() if timestamp else None
    except Exception:
        # Return None if database query fails to indicate no ingestion data available.
        return None


@project_cli.command()
@option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files.",
)
@option(
    "--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file."
)
@option("--env", type=ClickPath(exists=True, path_type=Path), help="Path to .env file.")
@option(
    "--format",
    type=Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for project list.",
)
@async_command
async def list(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    format: str,
):
    """List all configured projects."""
    try:
        validate_workspace_flags(workspace, config, env)
        settings, project_manager, _ = await _setup_project_manager(
            workspace, config, env
        )

        project_contexts = project_manager.get_all_project_contexts()
        if not project_contexts and format != "json":
            console.print("[yellow]No projects configured.[/yellow]")
            return

        output = _run_project_list(settings, project_manager, output_format=format)
        if format == "json":
            echo(output)
        else:
            console.print(output)
    except Exception as e:
        logger = LoggingConfig.get_logger(__name__)
        # Standardized error logging: user-friendly message + technical details + troubleshooting hint
        logger.error(
            "Failed to list projects from configuration",
            error=str(e),
            error_type=type(e).__name__,
            suggestion="Try running 'qdrant-loader project validate' to check configuration",
        )
        raise ClickException(f"Failed to list projects: {str(e)!s}") from e


@project_cli.command()
@option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files.",
)
@option(
    "--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file."
)
@option("--env", type=ClickPath(exists=True, path_type=Path), help="Path to .env file.")
@option(
    "--project-id",
    type=str,
    help="Specific project ID to check status for.",
)
@option(
    "--format",
    type=Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for project status.",
)
@async_command
async def status(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project_id: str | None,
    format: str,
):
    """Show project status including document counts and ingestion history."""
    try:
        validate_workspace_flags(workspace, config, env)
        settings, project_manager, state_manager = await _setup_project_manager(
            workspace, config, env
        )
        if project_id:
            context = project_manager.get_project_context(project_id)
            if not context:
                raise ClickException(f"Project '{project_id}' not found")
        output = await _run_project_status(
            settings,
            project_manager,
            state_manager,
            project_id=project_id,
            output_format=format,
        )
        if format == "json":
            echo(output)
        else:
            console.print(output)
    except Exception as e:
        logger = LoggingConfig.get_logger(__name__)
        # Standardized error logging: user-friendly message + technical details + troubleshooting hint
        logger.error(
            "Failed to retrieve project status information",
            error=str(e),
            error_type=type(e).__name__,
            suggestion="Verify project configuration and database connectivity",
        )
        raise ClickException(f"Failed to get project status: {str(e)!s}") from e


@project_cli.command()
@option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files.",
)
@option(
    "--config", type=ClickPath(exists=True, path_type=Path), help="Path to config file."
)
@option("--env", type=ClickPath(exists=True, path_type=Path), help="Path to .env file.")
@option(
    "--project-id",
    type=str,
    help="Specific project ID to validate.",
)
@async_command
async def validate(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project_id: str | None,
):
    """Validate project configurations."""
    try:
        validate_workspace_flags(workspace, config, env)
        settings, project_manager, _ = await _setup_project_manager(
            workspace, config, env
        )
        results, all_valid = _run_project_validate(
            settings, project_manager, project_id=project_id
        )
        for result in results:
            if result["valid"]:
                console.print(
                    f"[green]✓[/green] Project '{result['project_id']}' is valid ({result['source_count']} sources)"
                )
            else:
                console.print(
                    f"[red]✗[/red] Project '{result['project_id']}' has errors:"
                )
                for error in result["errors"]:
                    console.print(f"  [red]•[/red] {error}")
        if not all_valid:
            raise ClickException("Project validation failed")
    except Exception as e:
        logger = LoggingConfig.get_logger(__name__)
        # Standardized error logging: user-friendly message + technical details + troubleshooting hint
        logger.error(
            "Failed to validate project configurations",
            error=str(e),
            error_type=type(e).__name__,
            suggestion="Check config.yaml syntax and data source accessibility",
        )
        raise ClickException(f"Failed to validate projects: {str(e)!s}") from e


async def _setup_project_manager(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
) -> tuple[Settings, ProjectManager, StateManager]:
    """Setup project manager and state manager with configuration loading."""
    from qdrant_loader.cli.cli import (
        _check_settings,
        _load_config_with_workspace,
        _setup_workspace,
    )

    # Setup workspace if provided
    workspace_config = None
    if workspace:
        workspace_config = _setup_workspace(workspace)

    # Load configuration
    _load_config_with_workspace(workspace_config, config, env)
    settings = _check_settings()

    # Create project manager
    if not settings.global_config or not settings.global_config.qdrant:
        raise ClickException("Global configuration or Qdrant configuration is missing")

    project_manager = ProjectManager(
        projects_config=settings.projects_config,
        global_collection_name=settings.global_config.qdrant.collection_name,
    )

    # Initialize project contexts directly from configuration (without database)
    await _initialize_project_contexts_from_config(project_manager)

    # Create and initialize state manager
    state_manager = StateManager(settings.global_config.state_management)
    try:
        await state_manager.initialize()
    except Exception:
        # If state manager initialization fails, we'll continue without it
        # The database queries will return default values (0 count, None timestamp)
        pass

    return settings, project_manager, state_manager


async def _initialize_project_contexts_from_config(
    project_manager: ProjectManager,
) -> None:
    """Initialize project contexts directly from configuration without database."""
    logger = LoggingConfig.get_logger(__name__)
    logger.debug("Initializing project contexts from configuration")

    for project_id, project_config in project_manager.projects_config.projects.items():
        logger.debug(f"Creating context for project: {project_id}")

        # Determine collection name using the project's method
        collection_name = project_config.get_effective_collection_name(
            project_manager.global_collection_name
        )

        # Create project context
        from qdrant_loader.core.project_manager import ProjectContext

        context = ProjectContext(
            project_id=project_id,
            display_name=project_config.display_name,
            description=project_config.description,
            collection_name=collection_name,
            config=project_config,
        )

        project_manager._project_contexts[project_id] = context
        logger.debug(f"Created context for project: {project_id}")

    logger.debug(
        f"Initialized {len(project_manager._project_contexts)} project contexts"
    )
