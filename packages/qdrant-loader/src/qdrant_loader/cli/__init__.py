"""QDrant Loader CLI package.

This package contains the refactored CLI implementation organized into
domain-specific modules for better maintainability and readability.
"""

import click

from .core import (
    check_for_updates,
    get_version,
    setup_logging,
    LOG_LEVEL_OPTION,
)


@click.group(name="qdrant-loader")
@LOG_LEVEL_OPTION
@click.version_option(
    version=get_version(),
    message="qDrant Loader v.%(version)s",
)
def cli(log_level: str = "INFO") -> None:
    """QDrant Loader CLI - A comprehensive tool for loading data into QDrant vector database.

    This CLI provides commands for configuration management, data ingestion,
    project management, migration operations, and data export functionality.

    Use 'qdrant-loader COMMAND --help' for detailed help on any command.
    """
    # Initialize basic logging first
    setup_logging(log_level)

    # Check for updates in background (non-blocking)
    check_for_updates()


def create_cli():
    """Create the CLI application with all command groups registered.

    This function is called to set up the complete CLI with all
    domain-specific command groups imported and registered.

    Returns:
        click.Group: The complete CLI application
    """
    # Import command groups lazily to avoid slow startup
    from .config_commands import config_group, config_command
    from .ingest_commands import ingest_group, ingest_command, init_command
    from .migrate_commands import migrate_group, migrate_config_command
    from .export_commands import export_group, export_config_command
    from .project_commands import project_group

    # Add all command groups to the main CLI
    cli.add_command(config_group)
    cli.add_command(ingest_group)
    cli.add_command(migrate_group)
    cli.add_command(export_group)
    cli.add_command(project_group)

    # Add backward compatibility commands directly to the main CLI
    # These maintain the original command structure for existing users
    cli.add_command(config_command)
    cli.add_command(ingest_command)
    cli.add_command(init_command)
    cli.add_command(migrate_config_command)
    cli.add_command(export_config_command)

    return cli


def main():
    """Main entry point for the CLI application.

    This function creates the complete CLI with all command groups
    and executes it. It's designed to be called from console scripts
    or direct execution.
    """
    app = create_cli()
    app()


# Export the main CLI function and entry points
__all__ = ["cli", "create_cli", "main"]
