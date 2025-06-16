"""Project management CLI commands.

This module contains all CLI commands related to project management,
including listing, status checking, validation, and project lifecycle operations.
"""

import json
from pathlib import Path

import click
from click.exceptions import ClickException
from click.types import Choice
from click.utils import echo

from qdrant_loader.cli.asyncio import async_command

from .core import (
    CONFIG_OPTION,
    ENV_OPTION,
    LOG_LEVEL_OPTION,
    WORKSPACE_OPTION,
    check_settings,
    get_logger,
    load_config_with_workspace,
    setup_logging,
    setup_workspace,
    validate_workspace_flags,
)


@click.group(name="project")
def project_group():
    """Project management commands for multi-project configurations."""
    pass


def _get_all_sources_from_config(sources_config):
    """Get all sources from a SourcesConfig object.

    Args:
        sources_config: SourcesConfig object containing various source types

    Returns:
        dict: Combined dictionary of all sources from all source types
    """
    all_sources = {}

    # Handle both object and dict-like sources
    if hasattr(sources_config, "__dict__"):
        # Handle SourcesConfig object
        for attr_name in ["publicdocs", "git", "confluence", "jira", "localfile"]:
            if hasattr(sources_config, attr_name):
                attr_value = getattr(sources_config, attr_name)
                if isinstance(attr_value, dict):
                    all_sources.update(attr_value)
                elif hasattr(attr_value, "__dict__"):
                    all_sources.update(attr_value.__dict__)
    elif isinstance(sources_config, dict):
        # Handle dict-like sources
        for source_type, sources in sources_config.items():
            if isinstance(sources, dict):
                all_sources.update(sources)

    return all_sources


@project_group.command(name="list")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--format",
    type=Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for project list.",
)
@LOG_LEVEL_OPTION
@async_command
async def list_projects(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    format: str,
    log_level: str,
):
    """List all configured projects with their basic information.

    This command displays all projects defined in the configuration,
    showing their IDs, display names, descriptions, and source counts.

    Examples:
        # List projects in table format
        qdrant-loader project list

        # List projects in JSON format
        qdrant-loader project list --format json

        # List projects with specific workspace
        qdrant-loader project list --workspace ./my-workspace
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

        # Load configuration and initialize components
        settings, project_manager = await _setup_project_manager(
            workspace_config, config, env
        )

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
            # Table output using Rich (if available) or simple text
            try:
                from rich.console import Console
                from rich.table import Table

                console = Console()

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

            except ImportError:
                # Fallback to simple text output if Rich is not available
                if not project_contexts:
                    echo("No projects configured.")
                    return

                echo("Configured Projects:")
                echo("=" * 80)
                echo(
                    f"{'Project ID':<20} {'Display Name':<25} {'Sources':<10} {'Collection'}"
                )
                echo("-" * 80)

                for context in project_contexts.values():
                    source_count = (
                        len(_get_all_sources_from_config(context.config.sources))
                        if context.config
                        else 0
                    )
                    echo(
                        f"{context.project_id:<20} {(context.display_name or 'N/A'):<25} {source_count:<10} {context.collection_name or 'N/A'}"
                    )

    except Exception as e:
        logger = get_logger()
        logger.error("project_list_failed", error=str(e))
        raise ClickException(f"Failed to list projects: {str(e)}") from e


@project_group.command(name="status")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--project-id",
    type=str,
    help="Specific project ID to check status for.",
)
@click.option(
    "--format",
    type=Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for project status.",
)
@LOG_LEVEL_OPTION
@async_command
async def project_status(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project_id: str | None,
    format: str,
    log_level: str,
):
    """Show detailed project status including configuration and health information.

    This command provides comprehensive status information for projects,
    including configuration details, source counts, and collection information.

    Examples:
        # Show status for all projects
        qdrant-loader project status

        # Show status for specific project
        qdrant-loader project status --project-id my-project

        # Show status in JSON format
        qdrant-loader project status --format json
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

        # Load configuration and initialize components
        settings, project_manager = await _setup_project_manager(
            workspace_config, config, env
        )

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
                        "description": context.description,
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
            # Rich panel output or simple text fallback
            try:
                from rich.console import Console
                from rich.panel import Panel

                console = Console()

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

            except ImportError:
                # Fallback to simple text output
                if not project_contexts:
                    echo("No projects configured.")
                    return

                for context in project_contexts.values():
                    source_count = (
                        len(_get_all_sources_from_config(context.config.sources))
                        if context.config
                        else 0
                    )

                    echo(f"\nProject: {context.project_id}")
                    echo("=" * (len(context.project_id) + 9))
                    echo(f"Display Name: {context.display_name or 'N/A'}")
                    echo(f"Description: {context.description or 'N/A'}")
                    echo(f"Collection: {context.collection_name or 'N/A'}")
                    echo(f"Sources: {source_count}")
                    echo("Documents: N/A (requires database)")
                    echo("Latest Ingestion: N/A (requires database)")

    except Exception as e:
        logger = get_logger()
        logger.error("project_status_failed", error=str(e))
        raise ClickException(f"Failed to get project status: {str(e)}") from e


@project_group.command(name="validate")
@WORKSPACE_OPTION
@CONFIG_OPTION
@ENV_OPTION
@click.option(
    "--project-id",
    type=str,
    help="Specific project ID to validate.",
)
@LOG_LEVEL_OPTION
@async_command
async def validate_projects(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project_id: str | None,
    log_level: str,
):
    """Validate project configurations for completeness and correctness.

    This command checks project configurations for common issues like
    missing required fields, invalid source configurations, and other
    potential problems that could affect ingestion.

    Examples:
        # Validate all projects
        qdrant-loader project validate

        # Validate specific project
        qdrant-loader project validate --project-id my-project

        # Validate with detailed logging
        qdrant-loader project validate --log-level DEBUG
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

        # Load configuration and initialize components
        settings, project_manager = await _setup_project_manager(
            workspace_config, config, env
        )

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
        try:
            from rich.console import Console

            console = Console()

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

        except ImportError:
            # Fallback to simple text output
            for result in validation_results:
                if result["valid"]:
                    echo(
                        f"✓ Project '{result['project_id']}' is valid ({result['source_count']} sources)"
                    )
                else:
                    echo(f"✗ Project '{result['project_id']}' has errors:")
                    for error in result["errors"]:
                        echo(f"  • {error}")

            if all_valid:
                echo("\nAll projects are valid!")
            else:
                echo("\nSome projects have validation errors.")

        if not all_valid:
            raise ClickException("Project validation failed")

    except Exception as e:
        logger = get_logger()
        logger.error("project_validate_failed", error=str(e))
        raise ClickException(f"Failed to validate projects: {str(e)}") from e


async def _setup_project_manager(
    workspace_config,
    config: Path | None,
    env: Path | None,
    domains: str | None = None,
    preset: str | None = None,
    use_case: str | None = None,
    measure_performance: bool = False,
):
    """Setup project manager with configuration loading.

    Args:
        workspace_config: Workspace configuration object
        config: Path to config file
        env: Path to env file
        domains: Comma-separated list of domains to load
        preset: Predefined domain combination
        use_case: Use case identifier for automatic domain selection
        measure_performance: If True, log performance metrics

    Returns:
        tuple: (settings, project_manager)
    """
    # Load configuration
    load_config_with_workspace(
        workspace_config,
        config,
        env,
        domains=domains,
        preset=preset,
        use_case=use_case,
        measure_performance=measure_performance,
    )
    settings = check_settings()

    # Create project manager
    if not settings.global_config or not settings.global_config.qdrant:
        raise ClickException("Global configuration or Qdrant configuration is missing")

    # Lazy import to avoid slow startup
    from qdrant_loader.core.managers.project_manager import ProjectManager

    project_manager = ProjectManager(
        projects_config=settings.projects_config,
        global_collection_name=settings.global_config.qdrant.collection_name,
    )

    # Initialize project contexts directly from configuration (without database)
    await _initialize_project_contexts_from_config(project_manager)

    return settings, project_manager


async def _initialize_project_contexts_from_config(
    project_manager,
) -> None:
    """Initialize project contexts directly from configuration without database.

    Args:
        project_manager: ProjectManager instance to initialize
    """
    logger = get_logger()
    logger.debug("Initializing project contexts from configuration")

    for project_id, project_config in project_manager.projects_config.projects.items():
        logger.debug(f"Creating context for project: {project_id}")

        # Determine collection name using the project's method
        collection_name = project_config.get_effective_collection_name(
            project_manager.global_collection_name
        )

        # Create project context
        from qdrant_loader.core.managers.project_manager import ProjectContext

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
