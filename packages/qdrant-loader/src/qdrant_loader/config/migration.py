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
            config_dir = output_dir / "config"
            would_create_files = [
                str(config_dir / f"{domain}.yaml")
                for domain in domain_configs.keys()
            ]
            
            # Add .env file to the list if it exists
            env_file = output_dir / ".env"
            if env_file.exists():
                would_create_files.append(str(config_dir / ".env"))
            
            return {
                "dry_run": True,
                "domain_configs": domain_configs,
                "would_create_files": would_create_files,
                "would_create_config_dir": str(config_dir),
                "would_delete_legacy_config": str(legacy_config_path),
            }

        # Create backup if requested
        backup_path = None
        if create_backup:
            backup_path = self._create_backup(legacy_config_path)

        try:
            # Execute migration
            created_files = self._execute_migration(domain_configs, output_dir, force, legacy_config_path)

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
                    # Special handling for embedding configuration
                    if key == "embedding":
                        value = self._enhance_embedding_config(value)
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

    def _enhance_embedding_config(self, embedding_config: dict[str, Any]) -> dict[str, Any]:
        """Enhance embedding configuration with required provider field."""
        if not isinstance(embedding_config, dict):
            return embedding_config

        # Make a copy to avoid modifying the original
        enhanced_config = embedding_config.copy()

        # If provider is already set, don't override it
        if "provider" in enhanced_config:
            return enhanced_config

        # Detect provider based on endpoint and model
        provider = self._detect_embedding_provider(enhanced_config)
        if provider:
            enhanced_config["provider"] = provider
            logger.info(
                "Added missing embedding provider during migration",
                provider=provider,
                detected_from=self._get_detection_source(enhanced_config),
            )
        else:
            # Default to OpenAI if we can't detect
            enhanced_config["provider"] = "openai"
            logger.warning(
                "Could not detect embedding provider, defaulting to 'openai'",
                config_keys=list(enhanced_config.keys()),
            )

        return enhanced_config

    def _detect_embedding_provider(self, config: dict[str, Any]) -> str | None:
        """Detect embedding provider from configuration."""
        # Check endpoint URL
        endpoint = config.get("endpoint", "").lower()
        if "openai" in endpoint or "api.openai.com" in endpoint:
            return "openai"
        elif "anthropic" in endpoint:
            return "anthropic"
        elif "huggingface" in endpoint or "hf.co" in endpoint:
            return "huggingface"
        elif "localhost" in endpoint or "127.0.0.1" in endpoint:
            # Likely local deployment
            model = config.get("model", "").lower()
            if "openai" in model or "text-embedding" in model:
                return "openai"
            elif "bge" in model or "baai" in model:
                return "huggingface"

        # Check model name patterns
        model = config.get("model", "").lower()
        if model.startswith("text-embedding"):
            return "openai"
        elif model.startswith("baai/") or "bge" in model:
            return "huggingface"

        # Check API key patterns
        api_key = config.get("api_key", "")
        if isinstance(api_key, str):
            api_key_lower = api_key.lower()
            if "openai" in api_key_lower:
                return "openai"
            elif "anthropic" in api_key_lower:
                return "anthropic"

        return None

    def _get_detection_source(self, config: dict[str, Any]) -> str:
        """Get description of what was used to detect the provider."""
        sources = []
        if "endpoint" in config:
            sources.append(f"endpoint='{config['endpoint']}'")
        if "model" in config:
            sources.append(f"model='{config['model']}'")
        return ", ".join(sources) if sources else "default detection"

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
        self, domain_configs: dict[str, dict[str, Any]], output_dir: Path, force: bool, legacy_config_path: Path
    ) -> list[str]:
        """Execute the configuration migration."""
        created_files = []

        # Create config subdirectory
        config_dir = output_dir / "config"
        config_dir.mkdir(exist_ok=True)
        logger.info("Created config directory", path=str(config_dir))

        # Write domain configuration files to config directory
        for domain, config_data in domain_configs.items():
            output_file = config_dir / f"{domain}.yaml"

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

        # Move .env file to config directory if it exists
        env_file = output_dir / ".env"
        if env_file.exists():
            target_env_file = config_dir / ".env"
            if target_env_file.exists() and not force:
                raise ConfigMigrationError(
                    f"Environment file already exists in config directory: {target_env_file}. Use --force to overwrite."
                )
            
            shutil.move(str(env_file), str(target_env_file))
            created_files.append(str(target_env_file))
            logger.info("Moved environment file to config directory", 
                       from_path=str(env_file), 
                       to_path=str(target_env_file))

        # Delete the original legacy config file after successful migration
        try:
            legacy_config_path.unlink()
            logger.info("Deleted legacy configuration file", path=str(legacy_config_path))
        except Exception as e:
            logger.warning(
                "Failed to delete legacy configuration file", 
                path=str(legacy_config_path), 
                error=str(e)
            )

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
