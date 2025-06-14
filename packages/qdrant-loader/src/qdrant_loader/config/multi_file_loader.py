"""Multi-file configuration loader.

This module provides functionality to load and merge configuration from three
domain-specific files: connectivity.yaml, projects.yaml, and fine-tuning.yaml.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from ..utils.logging import LoggingConfig
from .domain_models import DomainConfigValidator
from .global_config import GlobalConfig
from .models import ParsedConfig, ProjectsConfig
from .parser import MultiProjectConfigParser
from .validator import ConfigValidator

logger = LoggingConfig.get_logger(__name__)


class ConfigDomain:
    """Configuration domain constants."""

    CONNECTIVITY = "connectivity"
    PROJECTS = "projects"
    FINE_TUNING = "fine-tuning"

    ALL_DOMAINS = {CONNECTIVITY, PROJECTS, FINE_TUNING}


class MultiFileConfigLoader:
    """Loads and merges configuration from multiple domain-specific files."""

    def __init__(self, validator: Optional[ConfigValidator] = None):
        """Initialize the multi-file configuration loader.

        Args:
            validator: Optional configuration validator instance
        """
        self.validator = validator or ConfigValidator()
        self.parser = MultiProjectConfigParser(self.validator)
        self.domain_validator = DomainConfigValidator()

    def load_config(
        self,
        config_dir: Path,
        domains: Optional[Set[str]] = None,
        env_path: Optional[Path] = None,
        skip_validation: bool = False,
    ) -> ParsedConfig:
        """Load and merge configuration from multiple domain files.

        Args:
            config_dir: Directory containing configuration files
            domains: Set of domains to load (defaults to all domains)
            env_path: Optional path to .env file
            skip_validation: If True, skip directory validation

        Returns:
            ParsedConfig: Merged configuration

        Raises:
            FileNotFoundError: If required configuration files are missing
            ValidationError: If configuration validation fails
        """
        if domains is None:
            domains = ConfigDomain.ALL_DOMAINS.copy()

        logger.debug(
            "Loading multi-file configuration",
            config_dir=str(config_dir),
            domains=list(domains),
        )

        # Step 1: Load environment variables
        self._load_environment_variables(env_path)

        # Step 2: Check for domain-specific files
        domain_files = self._discover_config_files(config_dir, domains)

        # Step 3: Ensure we have at least one domain file
        if not domain_files:
            raise FileNotFoundError(
                f"No configuration files found in {config_dir}. "
                f"Expected domain-specific files: {', '.join(sorted(domains))}.yaml"
            )

        # Step 4: Load and validate domain configurations
        validated_domains = self._load_and_validate_domains(
            config_dir, domain_files, domains
        )

        # Step 5: Merge validated domain configurations
        merged_config = self._merge_validated_domains(validated_domains, domains)

        # Step 6: Process environment variables
        merged_config = self._substitute_env_vars(merged_config)

        # Step 7: Parse and validate merged configuration
        parsed_config = self.parser.parse(
            merged_config, skip_validation=skip_validation
        )

        logger.debug("Successfully loaded multi-file configuration")
        return parsed_config

    def _load_environment_variables(self, env_path: Optional[Path]) -> None:
        """Load environment variables from .env file.

        Args:
            env_path: Optional path to .env file
        """
        if env_path is not None:
            logger.debug("Loading custom environment file", path=str(env_path))
            if not env_path.exists():
                raise FileNotFoundError(f"Environment file not found: {env_path}")
            load_dotenv(env_path, override=True)
        else:
            logger.debug("Loading default environment variables")
            load_dotenv(override=False)

    def _discover_config_files(
        self, config_dir: Path, domains: Set[str]
    ) -> Dict[str, Path]:
        """Discover available configuration files for requested domains.

        Args:
            config_dir: Directory to search for configuration files
            domains: Set of domains to look for

        Returns:
            Dict mapping domain names to file paths
        """
        domain_files = {}

        for domain in domains:
            # Try both .yaml and .yml extensions
            for ext in [".yaml", ".yml"]:
                config_file = config_dir / f"{domain}{ext}"
                if config_file.exists():
                    domain_files[domain] = config_file
                    logger.debug(f"Found {domain} configuration", path=str(config_file))
                    break

        logger.debug(
            "Configuration file discovery complete",
            found_domains=list(domain_files.keys()),
            missing_domains=list(domains - set(domain_files.keys())),
        )

        return domain_files

    def _load_and_validate_domains(
        self,
        config_dir: Path,
        domain_files: Dict[str, Path],
        requested_domains: Set[str],
    ) -> Dict[str, Any]:
        """Load and validate configuration from domain files using domain-specific models.

        Args:
            config_dir: Directory containing configuration files
            domain_files: Mapping of domain names to file paths
            requested_domains: Set of domains that were requested

        Returns:
            Dict mapping domain names to validated configuration objects
        """
        validated_domains = {}

        # Load and validate each domain file
        for domain in requested_domains:
            if domain in domain_files:
                # Load raw configuration data
                raw_config = self._load_domain_file(domain_files[domain])

                # Validate using domain-specific model
                try:
                    if domain == ConfigDomain.CONNECTIVITY:
                        validated_config = self.domain_validator.validate_connectivity(
                            raw_config
                        )
                    elif domain == ConfigDomain.PROJECTS:
                        validated_config = self.domain_validator.validate_projects(
                            raw_config
                        )
                    elif domain == ConfigDomain.FINE_TUNING:
                        validated_config = self.domain_validator.validate_fine_tuning(
                            raw_config
                        )
                    else:
                        logger.warning(f"Unknown domain: {domain}, skipping validation")
                        validated_config = raw_config

                    validated_domains[domain] = validated_config
                    logger.debug(f"Successfully validated {domain} configuration")

                except ValidationError as e:
                    logger.error(
                        f"Validation failed for {domain} configuration",
                        path=str(domain_files[domain]),
                        error=str(e),
                    )
                    raise
            else:
                logger.warning(f"Domain configuration not found: {domain}")

        return validated_domains

    def _merge_validated_domains(
        self, validated_domains: Dict[str, Any], requested_domains: Set[str]
    ) -> Dict[str, Any]:
        """Merge validated domain configurations into a unified configuration.

        Args:
            validated_domains: Dict of validated domain configurations
            requested_domains: Set of domains that were requested

        Returns:
            Merged configuration dictionary
        """
        merged_config = {}

        # Convert validated domain objects back to dictionaries and merge
        for domain, validated_config in validated_domains.items():
            if hasattr(validated_config, "to_dict"):
                domain_dict = validated_config.to_dict()
            else:
                domain_dict = validated_config

            merged_config = self._deep_merge(merged_config, domain_dict)
            logger.debug(f"Merged {domain} configuration")

        # Validate that we have minimum required configuration
        self._validate_minimum_config(merged_config, requested_domains)

        return merged_config

    def _load_domain_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a single domain file.

        Args:
            file_path: Path to the domain configuration file

        Returns:
            Configuration dictionary

        Raises:
            yaml.YAMLError: If YAML parsing fails
        """
        logger.debug("Loading domain configuration file", path=str(file_path))

        try:
            with open(file_path) as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                logger.warning("Empty configuration file", path=str(file_path))
                return {}

            return config_data

        except yaml.YAMLError as e:
            logger.error(
                "Failed to parse YAML configuration", path=str(file_path), error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to load configuration file", path=str(file_path), error=str(e)
            )
            raise

    def _deep_merge(
        self, base: Dict[str, Any], update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary
            update: Dictionary to merge into base

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in update.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_minimum_config(
        self, config: Dict[str, Any], requested_domains: Set[str]
    ) -> None:
        """Validate that minimum required configuration is present.

        Args:
            config: Merged configuration dictionary
            requested_domains: Set of domains that were requested

        Raises:
            ValidationError: If minimum configuration is not met
        """
        errors = []

        # Check for connectivity requirements
        if ConfigDomain.CONNECTIVITY in requested_domains:
            if "qdrant" not in config:
                errors.append("QDrant configuration is required in connectivity domain")
            elif not config["qdrant"].get("url"):
                errors.append("QDrant URL is required in connectivity configuration")

        # Check for projects requirements
        if ConfigDomain.PROJECTS in requested_domains:
            if "projects" not in config:
                errors.append("Projects configuration is required in projects domain")
            elif not config["projects"]:
                errors.append(
                    "At least one project must be defined in projects configuration"
                )

        if errors:
            raise ValidationError(
                f"Minimum configuration validation failed: {'; '.join(errors)}"
            )

    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        """Recursively substitute environment variables in configuration data.

        Args:
            data: Configuration data to process

        Returns:
            Processed data with environment variables substituted
        """
        if isinstance(data, str):
            # First expand $HOME if present
            if "$HOME" in data:
                data = data.replace("$HOME", os.path.expanduser("~"))

            # Then handle ${VAR_NAME} pattern
            pattern = r"\${([^}]+)}"
            matches = re.finditer(pattern, data)
            result = data
            for match in matches:
                var_name = match.group(1)
                env_value = os.getenv(var_name)
                if env_value is None:
                    # Only warn about missing variables that are commonly required
                    # Skip STATE_DB_PATH as it's often overridden in workspace mode
                    if var_name not in ["STATE_DB_PATH"]:
                        logger.warning(
                            "Environment variable not found", variable=var_name
                        )
                    continue
                # If the environment variable contains $HOME, expand it
                if "$HOME" in env_value:
                    env_value = env_value.replace("$HOME", os.path.expanduser("~"))
                result = result.replace(f"${{{var_name}}}", env_value)

            return result
        elif isinstance(data, dict):
            return {
                k: MultiFileConfigLoader._substitute_env_vars(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [MultiFileConfigLoader._substitute_env_vars(item) for item in data]
        return data


def load_multi_file_config(
    config_dir: Path,
    domains: Optional[Set[str]] = None,
    env_path: Optional[Path] = None,
    skip_validation: bool = False,
) -> ParsedConfig:
    """Convenience function to load multi-file configuration.

    Args:
        config_dir: Directory containing configuration files
        domains: Set of domains to load (defaults to all domains)
        env_path: Optional path to .env file
        skip_validation: If True, skip directory validation

    Returns:
        ParsedConfig: Merged configuration
    """
    loader = MultiFileConfigLoader()
    return loader.load_config(
        config_dir=config_dir,
        domains=domains,
        env_path=env_path,
        skip_validation=skip_validation,
    )
