"""Project management CLI commands for QDrant Loader."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import click
from click.decorators import group, option
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from qdrant_loader.cli.asyncio import async_command
from qdrant_loader.config import Settings, get_settings
from qdrant_loader.config.workspace import WorkspaceConfig, validate_workspace_flags
from qdrant_loader.core.project_manager import ProjectManager
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.utils.logging import LoggingConfig

# Rich console for better output formatting
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
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Load configuration and initialize components
        settings, project_manager = await _setup_project_manager(workspace, config, env)

        # Get project contexts
        project_contexts = project_manager.get_all_project_contexts()

        if format == "json":
            # JSON output
            projects_data = []
            for context in project_contexts.values():
                source_count = (
                    len(_get_all_sources_from_config(context.config.sources))
                    if context.config
                    else 0
                )
                projects_data.append(
                    {
                        "project_id": context.project_id,
                        "display_name": context.display_name,
                        "description": context.description,
                        "collection_name": context.collection_name or "N/A",
                        "source_count": source_count,
                    }
                )
            echo(json.dumps(projects_data, indent=2))
        else:
            # Table output using Rich
            if not project_contexts:
                console.print("[yellow]No projects configured.[/yellow]")
                return

            table = Table(title="Configured Projects")
            table.add_column("Project ID", style="cyan", no_wrap=True)
            table.add_column("Display Name", style="magenta")
            table.add_column("Description", style="green")
            table.add_column("Collection", style="blue")
            table.add_column("Sources", justify="right", style="yellow")

            for context in project_contexts.values():
                source_count = (
                    len(_get_all_sources_from_config(context.config.sources))
                    if context.config
                    else 0
                )
                table.add_row(
                    context.project_id,
                    context.display_name or "N/A",
                    context.description or "N/A",
                    context.collection_name or "N/A",
                    str(source_count),
                )

            console.print(table)

    except Exception as e:
        logger = LoggingConfig.get_logger(__name__)
        logger.error("project_list_failed", error=str(e))
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
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Load configuration and initialize components
        settings, project_manager = await _setup_project_manager(workspace, config, env)

        # Get project contexts
        if project_id:
            context = project_manager.get_project_context(project_id)
            if not context:
                raise ClickException(f"Project '{project_id}' not found")
            project_contexts = {project_id: context}
        else:
            project_contexts = project_manager.get_all_project_contexts()

        if format == "json":
            # JSON output
            status_data = []
            for context in project_contexts.values():
                status_data.append(
                    {
                        "project_id": context.project_id,
                        "display_name": context.display_name,
                        "collection_name": context.collection_name or "N/A",
                        "source_count": (
                            len(_get_all_sources_from_config(context.config.sources))
                            if context.config
                            else 0
                        ),
                        "document_count": "N/A",  # TODO: Implement database query
                        "latest_ingestion": None,  # TODO: Implement database query
                    }
                )
            echo(json.dumps(status_data, indent=2))
        else:
            # Table output using Rich
            if not project_contexts:
                console.print("[yellow]No projects configured.[/yellow]")
                return

            for context in project_contexts.values():
                source_count = (
                    len(_get_all_sources_from_config(context.config.sources))
                    if context.config
                    else 0
                )

                # Create project panel
                project_info = f"""[bold cyan]Project ID:[/bold cyan] {context.project_id}
[bold magenta]Display Name:[/bold magenta] {context.display_name or 'N/A'}
[bold green]Description:[/bold green] {context.description or 'N/A'}
[bold blue]Collection:[/bold blue] {context.collection_name or 'N/A'}
[bold yellow]Sources:[/bold yellow] {source_count}
[bold red]Documents:[/bold red] N/A (requires database)
[bold red]Latest Ingestion:[/bold red] N/A (requires database)"""

                console.print(
                    Panel(project_info, title=f"Project: {context.project_id}")
                )

    except Exception as e:
        logger = LoggingConfig.get_logger(__name__)
        logger.error("project_status_failed", error=str(e))
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
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Load configuration and initialize components
        settings, project_manager = await _setup_project_manager(workspace, config, env)

        # Get project contexts to validate
        if project_id:
            context = project_manager.get_project_context(project_id)
            if not context:
                raise ClickException(f"Project '{project_id}' not found")
            project_contexts = {project_id: context}
        else:
            project_contexts = project_manager.get_all_project_contexts()

        validation_results = []
        all_valid = True

        for context in project_contexts.values():
            try:
                # Basic validation - check that config exists and has required fields
                if not context.config:
                    validation_results.append(
                        {
                            "project_id": context.project_id,
                            "valid": False,
                            "errors": ["Missing project configuration"],
                            "source_count": 0,
                        }
                    )
                    all_valid = False
                    continue

                # Check source configurations
                source_errors = []
                all_sources = _get_all_sources_from_config(context.config.sources)

                for source_name, source_config in all_sources.items():
                    try:
                        # Basic validation - check required fields
                        if (
                            not hasattr(source_config, "source_type")
                            or not source_config.source_type
                        ):
                            source_errors.append(
                                f"Missing source_type for {source_name}"
                            )
                        if (
                            not hasattr(source_config, "source")
                            or not source_config.source
                        ):
                            source_errors.append(f"Missing source for {source_name}")
                    except Exception as e:
                        source_errors.append(f"Error in {source_name}: {str(e)}")

                validation_results.append(
                    {
                        "project_id": context.project_id,
                        "valid": len(source_errors) == 0,
                        "errors": source_errors,
                        "source_count": len(all_sources),
                    }
                )

                if source_errors:
                    all_valid = False

            except Exception as e:
                validation_results.append(
                    {
                        "project_id": context.project_id,
                        "valid": False,
                        "errors": [str(e)],
                        "source_count": 0,
                    }
                )
                all_valid = False

        # Display results
        for result in validation_results:
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

        if all_valid:
            console.print("\n[green]All projects are valid![/green]")
        else:
            console.print("\n[red]Some projects have validation errors.[/red]")
            raise ClickException("Project validation failed")

    except Exception as e:
        logger = LoggingConfig.get_logger(__name__)
        logger.error("project_validate_failed", error=str(e))
        raise ClickException(f"Failed to validate projects: {str(e)!s}") from e


async def _setup_project_manager(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
) -> tuple[Settings, ProjectManager]:
    """Setup project manager with configuration loading."""
    from qdrant_loader.cli.cli import (
        _setup_workspace,
        _load_config_with_workspace,
        _check_settings,
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

    return settings, project_manager


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
