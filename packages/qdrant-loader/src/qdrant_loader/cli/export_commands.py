"""Export CLI commands.

This module contains all CLI commands related to data export,
backup operations, and configuration export functionality.
"""

from pathlib import Path

import click
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo

from .core import (
    LOG_LEVEL_OPTION,
    WORKSPACE_OPTION,
    get_logger,
    setup_logging,
    setup_workspace,
)


@click.group(name="export")
def export_group():
    """Export commands."""
    pass


@export_group.command(name="config")
@WORKSPACE_OPTION
@click.option(
    "--config-dir",
    type=ClickPath(exists=True, path_type=Path),
    help="Directory containing configuration files (connectivity.yaml, projects.yaml, fine-tuning.yaml).",
)
@click.option(
    "--format",
    type=Choice(["yaml", "json"], case_sensitive=False),
    default="yaml",
    help="Export format (yaml or json).",
)
@click.option(
    "--output",
    type=ClickPath(path_type=Path),
    help="Output file path. If not specified, prints to stdout.",
)
@click.option(
    "--include-metadata/--no-metadata",
    default=True,
    help="Include metadata about source files and configuration version.",
)
@LOG_LEVEL_OPTION
def export_config(
    workspace: Path | None,
    config_dir: Path | None,
    format: str,
    output: Path | None,
    include_metadata: bool,
    log_level: str,
):
    """Export merged configuration with source attribution.

    This command loads configuration from the three-file system
    (connectivity.yaml, projects.yaml, fine-tuning.yaml) and exports
    the merged configuration with information about which settings
    came from which file.
    """
    setup_logging(log_level)
    logger = get_logger()

    try:
        # Determine configuration directory
        if workspace:
            workspace_config = setup_workspace(workspace)
            config_directory = workspace_config.config_path.parent
        elif config_dir:
            config_directory = config_dir
        else:
            # Default to current directory
            config_directory = Path.cwd()

        logger.info("Exporting configuration", config_dir=str(config_directory))

        # Lazy import to avoid slow startup
        from qdrant_loader.config.hot_reload import HotReloadConfigLoader

        # Load configuration without hot-reload for export
        loader = HotReloadConfigLoader()
        config = loader.load_config(
            config_dir=config_directory, enable_hot_reload=False
        )

        # Export configuration with source attribution
        exported_data = loader.export_config_with_sources(
            format=format.lower(), include_metadata=include_metadata
        )

        # Ensure exported data is a string
        if isinstance(exported_data, dict):
            import json

            exported_data = json.dumps(exported_data, indent=2, default=str)

        # Output to file or stdout
        if output:
            with open(output, "w") as f:
                f.write(exported_data)
            logger.info("Configuration exported", output_file=str(output))
            echo(f"Configuration exported to {output}")
        else:
            echo(exported_data)

    except Exception as e:
        logger.error("Failed to export configuration", error=str(e))
        raise ClickException(f"Failed to export configuration: {str(e)}")


# For backward compatibility, also register the export-config command directly
@click.command(name="export-config")
@WORKSPACE_OPTION
@click.option(
    "--config-dir",
    type=ClickPath(exists=True, path_type=Path),
    help="Directory containing configuration files (connectivity.yaml, projects.yaml, fine-tuning.yaml).",
)
@click.option(
    "--format",
    type=Choice(["yaml", "json"], case_sensitive=False),
    default="yaml",
    help="Export format (yaml or json).",
)
@click.option(
    "--output",
    type=ClickPath(path_type=Path),
    help="Output file path. If not specified, prints to stdout.",
)
@click.option(
    "--include-metadata/--no-metadata",
    default=True,
    help="Include metadata about source files and configuration version.",
)
@LOG_LEVEL_OPTION
def export_config_command(
    workspace: Path | None,
    config_dir: Path | None,
    format: str,
    output: Path | None,
    include_metadata: bool,
    log_level: str,
):
    """Export merged configuration with source attribution (backward compatibility command)."""
    # This is the same as export_config but registered as a standalone command
    # for backward compatibility with the original CLI
    export_config(workspace, config_dir, format, output, include_metadata, log_level)
