"""Configuration management CLI commands.

This module contains all CLI commands related to configuration management,
including initialization, validation, display, updates, and format conversions.
"""

import json
from pathlib import Path

import click
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath
from click.utils import echo

from .core import (
    CONFIG_OPTION,
    DOMAINS_OPTION,
    ENV_OPTION,
    LOG_LEVEL_OPTION,
    PERFORMANCE_OPTION,
    PRESET_OPTION,
    USE_CASE_OPTION,
    WORKSPACE_OPTION,
    check_settings,
    get_logger,
    load_config_with_workspace,
    setup_logging,
    setup_workspace,
    validate_workspace_flags,
)


@click.group(name="config")
def config_group():
    """Configuration management commands."""
    pass


@config_group.command(name="show")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
@DOMAINS_OPTION
@PRESET_OPTION
@USE_CASE_OPTION
@PERFORMANCE_OPTION
def show_config(
    workspace: Path | None,
    log_level: str,
    config: Path | None,
    env: Path | None,
    domains: str | None,
    preset: str | None,
    use_case: str | None,
    measure_performance: bool,
):
    """Display current configuration."""
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)

        # Load configuration with selective loading support
        load_config_with_workspace(
            workspace_config=workspace_config,
            config_path=config,
            env_path=env,
            skip_validation=True,
            domains=domains,
            preset=preset,
            use_case=use_case,
            measure_performance=measure_performance,
        )
        settings = check_settings()

        # Display configuration
        echo("Current Configuration:")
        echo(json.dumps(settings.model_dump(mode="json"), indent=2))

    except Exception as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error("config_failed", error=str(e))
        raise ClickException(f"Failed to display configuration: {str(e)}") from e


@config_group.command(name="validate")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
@DOMAINS_OPTION
@PRESET_OPTION
@USE_CASE_OPTION
@PERFORMANCE_OPTION
@click.option(
    "--strict",
    is_flag=True,
    help="Enable strict validation mode with additional checks.",
)
def validate_config(
    workspace: Path | None,
    log_level: str,
    config: Path | None,
    env: Path | None,
    domains: str | None,
    preset: str | None,
    use_case: str | None,
    measure_performance: bool,
    strict: bool,
):
    """Validate configuration files and settings."""
    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)

        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)
        logger = get_logger()

        logger.info("Starting configuration validation", strict=strict)

        # Load configuration with validation enabled and selective loading support
        load_config_with_workspace(
            workspace_config=workspace_config,
            config_path=config,
            env_path=env,
            skip_validation=False,
            domains=domains,
            preset=preset,
            use_case=use_case,
            measure_performance=measure_performance,
        )
        settings = check_settings()

        # Basic validation passed
        echo("✅ Configuration validation passed!")
        echo("📁 Configuration loaded successfully")

        # Additional strict validation
        if strict:
            echo("\n🔍 Running strict validation checks...")

            # Check for required sections
            validation_errors = []

            if not settings.global_config:
                validation_errors.append("Missing global configuration section")
            elif not settings.global_config.qdrant:
                validation_errors.append(
                    "Missing Qdrant configuration in global section"
                )

            if not settings.projects_config or not settings.projects_config.projects:
                validation_errors.append("No projects defined in configuration")

            # Check project configurations
            if settings.projects_config and settings.projects_config.projects:
                for (
                    project_id,
                    project_config,
                ) in settings.projects_config.projects.items():
                    if not project_config.sources:
                        validation_errors.append(
                            f"Project '{project_id}' has no data sources configured"
                        )

                    # Check each source configuration
                    if hasattr(project_config.sources, "__dict__"):
                        # Handle SourcesConfig object
                        sources_dict = project_config.sources.__dict__
                    else:
                        # Handle dict-like sources
                        sources_dict = (
                            project_config.sources
                            if isinstance(project_config.sources, dict)
                            else {}
                        )

                    for source_name, source_config in sources_dict.items():
                        if source_config and hasattr(source_config, "source_type"):
                            if not source_config.source_type:
                                validation_errors.append(
                                    f"Project '{project_id}', source '{source_name}': missing source_type"
                                )
                        if source_config and hasattr(source_config, "source"):
                            if not source_config.source:
                                validation_errors.append(
                                    f"Project '{project_id}', source '{source_name}': missing source configuration"
                                )

            if validation_errors:
                echo("\n❌ Strict validation found issues:")
                for error in validation_errors:
                    echo(f"  • {error}")
                raise ClickException("Configuration validation failed in strict mode")
            else:
                echo(
                    "✅ Strict validation passed - configuration is complete and valid!"
                )

    except Exception as e:
        from qdrant_loader.utils.logging import LoggingConfig

        LoggingConfig.get_logger(__name__).error(
            "config_validation_failed", error=str(e)
        )
        raise ClickException(f"Configuration validation failed: {str(e)}") from e


@config_group.command(name="init")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@click.option(
    "--template",
    type=Choice(["basic", "advanced", "minimal"], case_sensitive=False),
    default="basic",
    help="Configuration template to use for initialization.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing configuration files.",
)
def init_config(workspace: Path | None, log_level: str, template: str, force: bool):
    """Initialize new configuration files from templates."""
    try:
        # Setup logging
        setup_logging(log_level)
        logger = get_logger()

        # Determine target directory
        if workspace:
            workspace_config = setup_workspace(workspace)
            config_dir = workspace_config.config_path.parent
        else:
            config_dir = Path.cwd()

        logger.info(
            "Initializing configuration", config_dir=str(config_dir), template=template
        )

        # Check for existing configuration files
        config_files = [
            config_dir / "connectivity.yaml",
            config_dir / "projects.yaml",
            config_dir / "fine-tuning.yaml",
        ]

        existing_files = [f for f in config_files if f.exists()]

        if existing_files and not force:
            echo("❌ Configuration files already exist:")
            for f in existing_files:
                echo(f"  • {f}")
            echo("\nUse --force to overwrite existing files.")
            raise ClickException("Configuration files already exist")

        # For now, create basic template files since the templates module doesn't exist yet
        # This is a placeholder implementation
        echo("⚠️  Configuration template creation is not yet implemented.")
        echo("💡 Please create the following files manually:")
        for file_path in config_files:
            echo(f"  • {file_path}")

        echo("\n📖 Refer to the documentation for configuration file examples.")
        raise ClickException("Configuration template creation not yet implemented")

    except Exception as e:
        logger = get_logger()
        logger.error("Configuration initialization failed", error=str(e))
        raise ClickException(f"Failed to initialize configuration: {str(e)}") from e


@config_group.command(name="export")
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


@config_group.command(name="check")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
def check_config(
    workspace: Path | None, log_level: str, config: Path | None, env: Path | None
):
    """Check configuration file format and detect legacy configurations."""
    try:
        # Setup logging
        setup_logging(log_level)
        logger = get_logger()

        # Determine configuration path
        config_path = None
        if workspace:
            workspace_config = setup_workspace(workspace)
            config_path = workspace_config.config_path
        elif config:
            config_path = config
        else:
            # Check for default config files
            default_configs = [
                Path("config.yaml"),
                Path("connectivity.yaml"),
                Path("projects.yaml"),
                Path("fine-tuning.yaml"),
            ]
            existing_configs = [c for c in default_configs if c.exists()]
            if existing_configs:
                config_path = existing_configs[0]

        if not config_path or not config_path.exists():
            echo("❌ No configuration file found")
            echo("💡 Run 'qdrant-loader config init' to create new configuration files")
            raise ClickException("No configuration file found")

        logger.info("Checking configuration format", config_path=str(config_path))

        # Lazy import to avoid slow startup
        from qdrant_loader.config.legacy_detection import detect_legacy_configuration

        # Check if configuration is legacy format
        is_legacy, legacy_path, reason = detect_legacy_configuration(
            config_path=config_path, search_dir=workspace
        )

        if is_legacy:
            echo("🔍 Configuration Format Check Results:")
            echo("=" * 40)
            echo(f"📄 Configuration file: {legacy_path}")
            echo(f"📋 Format: Legacy (single-file)")
            echo(f"🔍 Detection reason: {reason}")
            echo()
            echo("💡 Migration recommended:")
            echo("  The legacy configuration format is still supported but deprecated.")
            echo(
                "  Consider migrating to the new domain-specific format for better organization."
            )
            echo()
            echo("🚀 To migrate your configuration:")
            echo(f"  qdrant-loader migrate config --legacy-config {legacy_path}")
        else:
            echo("✅ Configuration Format Check Results:")
            echo("=" * 40)
            echo(
                f"📄 Configuration directory: {config_path.parent if config_path.name in ['connectivity.yaml', 'projects.yaml', 'fine-tuning.yaml'] else config_path}"
            )
            echo(f"📋 Format: Modern (domain-specific files)")
            echo("✅ Your configuration is using the recommended format!")

    except Exception as e:
        logger = get_logger()
        logger.error("Configuration check failed", error=str(e))
        raise ClickException(f"Failed to check configuration: {str(e)}") from e


# For backward compatibility, also register the commands directly on the config group
# This allows both 'qdrant-loader config show' and 'qdrant-loader config' to work
@click.command(name="config")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@CONFIG_OPTION
@ENV_OPTION
def config_command(
    workspace: Path | None, log_level: str, config: Path | None, env: Path | None
):
    """Display current configuration (backward compatibility command)."""
    # This is the same as show_config but registered as a standalone command
    # for backward compatibility with the original CLI
    show_config(workspace, log_level, config, env)
