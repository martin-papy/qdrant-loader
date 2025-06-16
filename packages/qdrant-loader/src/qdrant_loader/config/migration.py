"""Configuration migration tool.

This module provides functionality to migrate legacy single-file configurations
to the new three-file domain-specific format (connectivity.yaml, projects.yaml, fine-tuning.yaml).
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..utils.logging import LoggingConfig
from .multi_file_loader import ConfigDomain, MultiFileConfigLoader

logger = LoggingConfig.get_logger(__name__)


class ConfigMigrationError(Exception):
    """Exception raised during configuration migration."""

    pass


class ConfigMigrator:
    """Migrates legacy configuration files to the new domain-specific format."""

    def __init__(self):
        """Initialize the configuration migrator."""
        self.loader = MultiFileConfigLoader()

        # Define domain mapping for legacy configuration sections
        self.domain_mapping = {
            ConfigDomain.CONNECTIVITY: {
                "global.qdrant",
                "global.neo4j",
                "global.embedding",
                "global.state_management",
            },
            ConfigDomain.PROJECTS: {
                "projects",
            },
            ConfigDomain.FINE_TUNING: {
                "global.chunking",
                "global.file_conversion",
                "chunking",
                "file_conversion",
            },
        }

    def migrate_config(
        self,
        legacy_config_path: Path,
        output_dir: Path,
        dry_run: bool = False,
        create_backup: bool = True,
        force: bool = False,
    ) -> dict[str, Any]:
        """Migrate a legacy configuration file to the new domain-specific format."""
        logger.info(
            "Starting configuration migration",
            legacy_config=str(legacy_config_path),
            output_dir=str(output_dir),
            dry_run=dry_run,
        )

        # Validate inputs
        if not legacy_config_path.exists():
            raise FileNotFoundError(
                f"Legacy configuration file not found: {legacy_config_path}"
            )

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        # Load legacy configuration
        legacy_config = self._load_legacy_config(legacy_config_path)

        # Split configuration into domains
        domain_configs = self._split_into_domains(legacy_config)

        if dry_run:
            return {
                "dry_run": True,
                "domain_configs": domain_configs,
                "would_create_files": [
                    str(output_dir / f"{domain}.yaml")
                    for domain in domain_configs.keys()
                ],
            }

        # Create backup if requested
        backup_path = None
        if create_backup:
            backup_path = self._create_backup(legacy_config_path)

        try:
            # Execute migration
            created_files = self._execute_migration(domain_configs, output_dir, force)

            migration_results = {
                "success": True,
                "created_files": created_files,
                "backup_path": str(backup_path) if backup_path else None,
                "migration_timestamp": datetime.now().isoformat(),
            }

            logger.info("Configuration migration completed successfully")
            return migration_results

        except Exception as e:
            logger.error("Configuration migration failed", error=str(e))
            raise ConfigMigrationError(f"Migration failed: {e}") from e

    def _load_legacy_config(self, config_path: Path) -> dict[str, Any]:
        """Load legacy configuration file."""
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ConfigMigrationError(
                    "Configuration file must contain a YAML dictionary"
                )

            logger.debug(
                "Successfully loaded legacy configuration", path=str(config_path)
            )
            return config

        except yaml.YAMLError as e:
            raise ConfigMigrationError(
                f"Invalid YAML in configuration file: {e}"
            ) from e
        except Exception as e:
            raise ConfigMigrationError(f"Failed to load configuration file: {e}") from e

    def _split_into_domains(self, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Split legacy configuration into domain-specific configurations."""
        domain_configs = {
            ConfigDomain.CONNECTIVITY: {},
            ConfigDomain.PROJECTS: {},
            ConfigDomain.FINE_TUNING: {},
        }

        # Handle global section specially
        if "global" in config:
            global_config = config["global"]

            # Split global section into domains
            for key, value in global_config.items():
                if key in ["qdrant", "neo4j", "embedding", "state_management"]:
                    domain_configs[ConfigDomain.CONNECTIVITY][key] = value
                elif key in ["chunking", "file_conversion"]:
                    domain_configs[ConfigDomain.FINE_TUNING][key] = value
                else:
                    # Default to connectivity for unknown global settings
                    domain_configs[ConfigDomain.CONNECTIVITY][key] = value

        # Handle projects section
        if "projects" in config:
            domain_configs[ConfigDomain.PROJECTS]["projects"] = config["projects"]

        # Handle top-level fine-tuning sections
        for key in ["chunking", "file_conversion"]:
            if key in config:
                domain_configs[ConfigDomain.FINE_TUNING][key] = config[key]

        # Remove empty domains
        domain_configs = {
            domain: config_data
            for domain, config_data in domain_configs.items()
            if config_data
        }

        logger.debug(
            "Configuration split into domains", domains=list(domain_configs.keys())
        )
        return domain_configs

    def _create_backup(self, config_path: Path) -> Path:
        """Create a backup of the legacy configuration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = (
            config_path.parent
            / f"{config_path.stem}.backup.{timestamp}{config_path.suffix}"
        )

        shutil.copy2(config_path, backup_path)
        logger.info("Created configuration backup", backup_path=str(backup_path))

        return backup_path

    def _execute_migration(
        self, domain_configs: dict[str, dict[str, Any]], output_dir: Path, force: bool
    ) -> list[str]:
        """Execute the configuration migration."""
        created_files = []

        for domain, config_data in domain_configs.items():
            output_file = output_dir / f"{domain}.yaml"

            # Check for conflicts
            if output_file.exists() and not force:
                raise ConfigMigrationError(
                    f"Output file already exists: {output_file}. Use --force to overwrite."
                )

            try:
                # Write domain configuration
                with open(output_file, "w", encoding="utf-8") as f:
                    # Add header comment
                    f.write(f"# {domain.title()} Configuration\n")
                    f.write("# Generated by configuration migration tool\n")
                    f.write(f"# Migration timestamp: {datetime.now().isoformat()}\n")
                    f.write(
                        "# Environment variables can be used with ${VARIABLE_NAME} syntax\n\n"
                    )

                    # Write configuration data
                    yaml.dump(
                        config_data,
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                        indent=2,
                        allow_unicode=True,
                    )

                created_files.append(str(output_file))
                logger.info(
                    "Created domain configuration file",
                    domain=domain,
                    path=str(output_file),
                )

            except Exception as e:
                raise ConfigMigrationError(
                    f"Failed to write {domain} configuration: {e}"
                ) from e

        return created_files


def migrate_legacy_config(
    legacy_config_path: Path,
    output_dir: Path,
    dry_run: bool = False,
    create_backup: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Convenience function to migrate a legacy configuration file."""
    migrator = ConfigMigrator()
    return migrator.migrate_config(
        legacy_config_path=legacy_config_path,
        output_dir=output_dir,
        dry_run=dry_run,
        create_backup=create_backup,
        force=force,
    )
