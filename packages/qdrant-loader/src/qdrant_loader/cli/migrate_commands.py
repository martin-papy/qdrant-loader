"""Migration CLI commands.

This module contains all CLI commands related to database migrations,
configuration migrations, and data transformations.
"""

from pathlib import Path

import click
from click.exceptions import ClickException
from click.types import Path as ClickPath
from click.utils import echo

from .core import (
    LOG_LEVEL_OPTION,
    get_logger,
    setup_logging,
)


@click.group(name="migrate")
def migrate_group():
    """Migration commands."""
    pass


@migrate_group.command(name="config")
@click.argument(
    "legacy_config",
    type=ClickPath(exists=True, path_type=Path),
    required=True,
)
@click.option(
    "--output-dir",
    type=ClickPath(path_type=Path),
    help="Directory where the new configuration files will be created. Defaults to the same directory as the legacy config.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be migrated without creating files.",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create a backup of the legacy configuration file before migration.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing configuration files if they exist.",
)
@LOG_LEVEL_OPTION
def migrate_config(
    legacy_config: Path,
    output_dir: Path | None,
    dry_run: bool,
    backup: bool,
    force: bool,
    log_level: str,
):
    """Migrate legacy configuration file to new domain-specific format.

    This command converts a legacy single-file configuration (config.yaml)
    to the new three-file domain-specific format:
    - connectivity.yaml (database connections, LLM providers, authentication)
    - projects.yaml (project definitions, data sources)
    - fine-tuning.yaml (processing parameters, performance tuning)

    LEGACY_CONFIG: Path to the legacy configuration file to migrate.

    Examples:
        # Dry run to see what would be migrated
        qdrant-loader migrate config config.yaml --dry-run

        # Migrate with backup (default)
        qdrant-loader migrate config config.yaml --output-dir ./new-config

        # Force overwrite existing files
        qdrant-loader migrate config config.yaml --force
    """
    # Setup logging
    setup_logging(log_level)
    logger = get_logger()

    try:
        # Lazy import to avoid slow startup
        from qdrant_loader.config.migration import migrate_legacy_config

        # Default output directory to same as legacy config
        if output_dir is None:
            output_dir = legacy_config.parent

        logger.info(
            "Starting configuration migration",
            legacy_config=str(legacy_config),
            output_dir=str(output_dir),
            dry_run=dry_run,
        )

        # Perform migration
        results = migrate_legacy_config(
            legacy_config_path=legacy_config,
            output_dir=output_dir,
            dry_run=dry_run,
            create_backup=backup,
            force=force,
        )

        # Display results
        if dry_run:
            echo("🔍 Migration Preview (Dry Run)")
            echo("=" * 40)
            echo(f"Legacy config: {legacy_config}")
            echo(f"Output directory: {output_dir}")
            echo()

            if "would_create_config_dir" in results:
                echo(f"📁 Config directory that would be created: {results['would_create_config_dir']}")
                echo()

            if "domain_configs" in results:
                echo("📁 Domain configurations that would be created:")
                for domain, config_data in results["domain_configs"].items():
                    echo(f"  • {domain}.yaml ({len(config_data)} sections)")
                echo()

            if "would_create_files" in results:
                echo("📄 Files that would be created:")
                for file_path in results["would_create_files"]:
                    echo(f"  • {file_path}")
                echo()

            if "would_delete_legacy_config" in results:
                echo(f"🗑️  Legacy config that would be deleted: {results['would_delete_legacy_config']}")
                echo()

            echo("💡 Run without --dry-run to perform the actual migration.")

        else:
            echo("✅ Configuration migration completed successfully!")
            echo("=" * 50)
            echo(f"Legacy config: {legacy_config}")
            echo(f"Output directory: {output_dir}")
            echo()

            if results.get("backup_path"):
                echo(f"💾 Backup created: {results['backup_path']}")
                echo()

            echo(f"📁 Config directory created: {output_dir}/config")
            echo()

            if "created_files" in results:
                echo("📄 Created configuration files:")
                for file_path in results["created_files"]:
                    echo(f"  • {file_path}")
                echo()

            echo(f"🗑️  Deleted legacy config: {legacy_config}")
            echo()

            echo(
                "🎉 Your configuration has been successfully migrated to the new format!"
            )
            echo("   You can now use the new domain-specific configuration files.")
            echo("   All configuration files are now organized in the config/ directory.")

    except Exception as e:
        logger.error("Migration failed", error=str(e))
        raise ClickException(f"Configuration migration failed: {e}") from e



