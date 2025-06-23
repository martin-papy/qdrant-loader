"""Multi-file configuration loader.

This module provides functionality to load and merge configuration from three
domain-specific files: connectivity.yaml, projects.yaml, and fine-tuning.yaml.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from ..utils.logging import LoggingConfig
from .domain_models import DomainConfigValidator
from .enhanced_validator import EnhancedDomainValidator
from .models import ParsedConfig
from .parser import MultiProjectConfigParser
from .validation_errors import (
    ConfigValidationError,
    ValidationErrorCollector,
    ValidationSeverity,
)
from .validator import ConfigValidator

logger = LoggingConfig.get_logger(__name__)


class ConfigDomain:
    """Configuration domain constants and management."""

    CONNECTIVITY = "connectivity"
    PROJECTS = "projects"
    FINE_TUNING = "fine-tuning"
    METADATA_EXTRACTION = "metadata-extraction"
    VALIDATION = "validation"

    # Core domains required for basic functionality
    CORE_DOMAINS = {CONNECTIVITY, PROJECTS, FINE_TUNING}
    
    # Optional domains that enhance functionality
    OPTIONAL_DOMAINS = {METADATA_EXTRACTION, VALIDATION}
    
    # All available domains
    ALL_DOMAINS = CORE_DOMAINS | OPTIONAL_DOMAINS

    # Predefined domain combinations for common use cases
    MINIMAL = {CONNECTIVITY, PROJECTS}  # Database connections and basic project config
    BASIC = {CONNECTIVITY, PROJECTS}  # Basic operations without fine-tuning
    STANDARD = CORE_DOMAINS  # All core domains (default)
    FULL = ALL_DOMAINS  # All domains including optional ones

    # Domain dependencies - which domains are required for specific operations
    DOMAIN_DEPENDENCIES = {
        PROJECTS: {CONNECTIVITY},  # Projects require connectivity
        FINE_TUNING: set(),  # Fine-tuning is independent
        METADATA_EXTRACTION: set(),  # Metadata extraction is independent
        VALIDATION: set(),  # Validation is independent
    }

    @classmethod
    def validate_domain_combination(cls, domains: set[str]) -> tuple[bool, list[str]]:
        """Validate that a domain combination satisfies dependencies.

        Args:
            domains: Set of domains to validate

        Returns:
            Tuple of (is_valid, list_of_missing_dependencies)
        """
        missing_deps = []

        for domain in domains:
            if domain in cls.DOMAIN_DEPENDENCIES:
                required_deps = cls.DOMAIN_DEPENDENCIES[domain]
                missing = required_deps - domains
                if missing:
                    missing_deps.extend([f"{domain} requires {dep}" for dep in missing])

        return len(missing_deps) == 0, missing_deps

    @classmethod
    def get_predefined_combination(cls, name: str) -> set[str]:
        """Get a predefined domain combination by name.

        Args:
            name: Name of the predefined combination

        Returns:
            Set of domain names in the combination

        Raises:
            ValueError: If the combination name is not recognized
        """
        combinations = {
            "minimal": cls.MINIMAL,
            "basic": cls.BASIC,
            "standard": cls.STANDARD,
            "full": cls.FULL,
        }

        if name.lower() not in combinations:
            available = ", ".join(combinations.keys())
            raise ValueError(
                f"Unknown domain combination '{name}'. Available: {available}"
            )

        return combinations[name.lower()]

    @classmethod
    def resolve_domains(
        cls, domains: set[str] | None = None, preset: str | None = None, use_case: str | None = None
    ) -> set[str]:
        """Resolve the final set of domains to load.

        Args:
            domains: Explicit set of domains to load
            preset: Predefined domain combination name
            use_case: Use case identifier for automatic domain selection

        Returns:
            Set of domain names to load

        Raises:
            ValueError: If domain validation fails
        """
        if domains is not None and preset is not None:
            raise ValueError("Cannot specify both explicit domains and preset")

        if preset is not None:
            resolved_domains = cls.get_predefined_combination(preset)
        elif domains is not None:
            resolved_domains = domains.copy()
        else:
            # Default to standard domains (core functionality)
            resolved_domains = cls.STANDARD.copy()

        # Validate domain combination
        is_valid, errors = cls.validate_domain_combination(resolved_domains)
        if not is_valid:
            raise ValueError(f"Invalid domain combination: {'; '.join(errors)}")

        return resolved_domains

    @classmethod
    def get_use_case_domains(cls, use_case: str) -> set[str]:
        """Get recommended domains for specific use cases.

        Args:
            use_case: Use case identifier

        Returns:
            Set of recommended domains
        """
        use_cases = {
            "config_validation": cls.BASIC,  # Skip fine-tuning for faster validation
            "config_export": {cls.PROJECTS, cls.CONNECTIVITY},  # Projects + connectivity for export
            "basic_ingestion": cls.BASIC,  # Skip fine-tuning for basic ingestion
            "full_processing": cls.FULL,  # All domains for complete processing
            "migration": cls.FULL,  # All domains for migration
            "status_check": cls.MINIMAL,  # Connectivity + projects for status
        }

        return use_cases.get(use_case, cls.FULL).copy()


class MultiFileConfigLoader:
    """Loads and merges configuration from multiple domain-specific files."""

    def __init__(
        self,
        validator: ConfigValidator | None = None,
        enhanced_validation: bool = True,
        fail_fast: bool = False,
        validate_connectivity: bool = False,
    ):
        """Initialize the multi-file configuration loader.

        Args:
            validator: Optional configuration validator instance
            enhanced_validation: If True, use enhanced domain validation
            fail_fast: If True, stop validation on first critical error
            validate_connectivity: If True, perform actual connectivity tests
        """
        self.validator = validator or ConfigValidator()
        self.parser = MultiProjectConfigParser(self.validator)
        self.domain_validator = DomainConfigValidator()

        # Enhanced validation setup
        self.enhanced_validation = enhanced_validation
        if enhanced_validation:
            self.enhanced_validator = EnhancedDomainValidator(
                fail_fast=fail_fast,
                validate_connectivity=validate_connectivity,
            )

    def load_config(
        self,
        config_dir: Path,
        domains: set[str] | None = None,
        env_path: Path | None = None,
        skip_validation: bool = False,
        preset: str | None = None,
        use_case: str | None = None,
        measure_performance: bool = False,
    ) -> ParsedConfig:
        """Load and merge configuration from multiple domain files.

        Args:
            config_dir: Directory containing configuration files
            domains: Set of domains to load (defaults to all domains)
            env_path: Optional path to .env file
            skip_validation: If True, skip directory validation
            preset: Predefined domain combination ('minimal', 'basic', 'full')
            use_case: Use case identifier for automatic domain selection
            measure_performance: If True, log performance metrics

        Returns:
            ParsedConfig: Merged configuration

        Raises:
            FileNotFoundError: If required configuration files are missing
            ValidationError: If configuration validation fails
            ValueError: If domain combination is invalid
        """
        import time

        start_time = time.time() if measure_performance else None

        # Step 1: Resolve domains from various sources
        if use_case:
            resolved_domains = ConfigDomain.get_use_case_domains(use_case)
            logger.info(
                "Using domains for use case",
                use_case=use_case,
                domains=list(resolved_domains),
            )
        else:
            resolved_domains = ConfigDomain.resolve_domains(domains, preset, use_case)

        # Step 1.1: Auto-discover optional domains if they exist
        # This allows optional files to be loaded automatically when present
        all_discovered_files = self._discover_config_files(config_dir, ConfigDomain.ALL_DOMAINS)
        for optional_domain in ConfigDomain.OPTIONAL_DOMAINS:
            if optional_domain in all_discovered_files and optional_domain not in resolved_domains:
                resolved_domains.add(optional_domain)
                logger.debug(f"Auto-discovered optional domain: {optional_domain}")

        # Step 2: Validate domain combination
        is_valid, missing_deps = ConfigDomain.validate_domain_combination(
            resolved_domains
        )
        if not is_valid:
            raise ValueError(
                f"Invalid domain combination. Missing dependencies: {'; '.join(missing_deps)}"
            )

        logger.debug(
            "Loading multi-file configuration with selective domains",
            config_dir=str(config_dir),
            domains=list(resolved_domains),
            total_available=len(ConfigDomain.ALL_DOMAINS),
            loading_percentage=f"{len(resolved_domains)/len(ConfigDomain.ALL_DOMAINS)*100:.1f}%",
        )

        # Step 3: Load environment variables
        env_start = time.time() if measure_performance else None
        self._load_environment_variables(env_path)
        if measure_performance and env_start is not None:
            logger.debug(
                "Environment loading time",
                duration_ms=f"{(time.time() - env_start) * 1000:.2f}",
            )

        # Step 4: Check for domain-specific files
        discovery_start = time.time() if measure_performance else None
        domain_files = self._discover_config_files(config_dir, resolved_domains)
        if measure_performance and discovery_start is not None:
            logger.debug(
                "File discovery time",
                duration_ms=f"{(time.time() - discovery_start) * 1000:.2f}",
            )

        # Step 5: Ensure we have at least one domain file
        if not domain_files:
            raise FileNotFoundError(
                f"No configuration files found in {config_dir}. "
                f"Expected domain-specific files: {', '.join(sorted(resolved_domains))}.yaml"
            )

        # Log selective loading benefits
        skipped_domains = ConfigDomain.ALL_DOMAINS - resolved_domains
        if skipped_domains:
            logger.info(
                "Selective loading enabled - skipping domains for faster startup",
                loaded_domains=list(resolved_domains),
                skipped_domains=list(skipped_domains),
                files_loaded=len(domain_files),
                files_skipped=len(skipped_domains),
            )

        # Step 6: Load and validate domain configurations
        validation_start = time.time() if measure_performance else None
        validated_domains = self._load_and_validate_domains(
            config_dir, domain_files, resolved_domains
        )
        if measure_performance and validation_start is not None:
            logger.debug(
                "Domain validation time",
                duration_ms=f"{(time.time() - validation_start) * 1000:.2f}",
            )

        # Step 7: Merge validated domain configurations
        merge_start = time.time() if measure_performance else None
        merged_config = self._merge_validated_domains(
            validated_domains, resolved_domains
        )
        if measure_performance and merge_start is not None:
            logger.debug(
                "Configuration merging time",
                duration_ms=f"{(time.time() - merge_start) * 1000:.2f}",
            )

        # Step 8: Process environment variables
        env_sub_start = time.time() if measure_performance else None
        merged_config = self._substitute_env_vars(merged_config)
        if measure_performance and env_sub_start is not None:
            logger.debug(
                "Environment substitution time",
                duration_ms=f"{(time.time() - env_sub_start) * 1000:.2f}",
            )

        # Step 9: Parse and validate merged configuration
        parse_start = time.time() if measure_performance else None
        parsed_config = self.parser.parse(
            merged_config, skip_validation=skip_validation
        )
        if measure_performance and parse_start is not None:
            logger.debug(
                "Configuration parsing time",
                duration_ms=f"{(time.time() - parse_start) * 1000:.2f}",
            )

        # Log performance summary
        if measure_performance and start_time is not None:
            total_time = time.time() - start_time
            logger.info(
                "Configuration loading performance summary",
                total_time_ms=f"{total_time * 1000:.2f}",
                domains_loaded=len(resolved_domains),
                domains_total=len(ConfigDomain.ALL_DOMAINS),
                selective_loading=len(resolved_domains) < len(ConfigDomain.ALL_DOMAINS),
            )

        logger.debug(
            "Successfully loaded multi-file configuration with selective domains"
        )
        return parsed_config

    def _load_environment_variables(self, env_path: Path | None) -> None:
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
        self, config_dir: Path, domains: set[str]
    ) -> dict[str, Path]:
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
        domain_files: dict[str, Path],
        requested_domains: set[str],
    ) -> dict[str, Any]:
        """Load and validate configuration from domain files using domain-specific models.

        Args:
            config_dir: Directory containing configuration files
            domain_files: Mapping of domain names to file paths
            requested_domains: Set of domains that were requested

        Returns:
            Dict mapping domain names to validated configuration objects
        """
        validated_domains = {}

        # Use enhanced validation if enabled
        if self.enhanced_validation:
            return self._load_and_validate_domains_enhanced(
                config_dir, domain_files, requested_domains
            )

        # Load and validate each domain file (legacy validation)
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
                    elif domain == ConfigDomain.METADATA_EXTRACTION:
                        validated_config = self.domain_validator.validate_metadata_extraction(
                            raw_config
                        )
                    elif domain == ConfigDomain.VALIDATION:
                        validated_config = self.domain_validator.validate_validation(
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

    def _load_and_validate_domains_enhanced(
        self,
        config_dir: Path,
        domain_files: dict[str, Path],
        requested_domains: set[str],
    ) -> dict[str, Any]:
        """Load and validate configuration using enhanced validation.

        Args:
            config_dir: Directory containing configuration files
            domain_files: Mapping of domain names to file paths
            requested_domains: Set of domains that were requested

        Returns:
            Dict mapping domain names to validated configuration objects

        Raises:
            ConfigValidationError: If validation fails with enhanced error reporting
        """
        # Load raw configuration data for all domains
        domain_configs = {}
        for domain in requested_domains:
            if domain in domain_files:
                try:
                    raw_config = self._load_domain_file(domain_files[domain])
                    domain_configs[domain] = raw_config
                    logger.debug(f"Loaded raw configuration for {domain}")
                except Exception as e:
                    logger.error(f"Failed to load {domain} configuration", error=str(e))
                    # Create a validation error for file loading issues
                    error_collector = ValidationErrorCollector()
                    error_collector.add_error(
                        ConfigValidationError(
                            message=f"Failed to load {domain} configuration file: {str(e)}",
                            domain=domain,
                            file_path=domain_files[domain],
                            severity=ValidationSeverity.CRITICAL,
                            remediation=f"Check {domain}.yaml file format and accessibility",
                        )
                    )
                    error_collector.raise_if_critical()
            else:
                logger.warning(f"Domain configuration not found: {domain}")

        # Perform enhanced validation
        error_collector = self.enhanced_validator.validate_all_domains(
            domain_configs, domain_files
        )

        # Handle validation results
        if error_collector.has_critical_errors():
            # Log detailed error report
            error_report = error_collector.format_errors_for_display(
                include_warnings=True, include_info=False
            )
            logger.error("Configuration validation failed", error_report=error_report)

            # Raise with comprehensive error information
            error_collector.raise_if_critical()

        elif error_collector.has_any_issues():
            # Log warnings and info messages
            warning_report = error_collector.format_errors_for_display(
                include_warnings=True, include_info=True
            )
            logger.warning(
                "Configuration validation completed with warnings",
                warning_report=warning_report,
            )

        # Convert validated configurations back to the expected format
        validated_domains = {}
        for domain, raw_config in domain_configs.items():
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
                elif domain == ConfigDomain.METADATA_EXTRACTION:
                    validated_config = self.domain_validator.validate_metadata_extraction(
                        raw_config
                    )
                elif domain == ConfigDomain.VALIDATION:
                    validated_config = self.domain_validator.validate_validation(
                        raw_config
                    )
                else:
                    validated_config = raw_config

                validated_domains[domain] = validated_config
                logger.debug(f"Successfully validated {domain} configuration")

            except ValidationError as e:
                # This should not happen if enhanced validation worked correctly
                logger.error(f"Unexpected validation error for {domain}", error=str(e))
                raise

        return validated_domains

    def _merge_validated_domains(
        self, validated_domains: dict[str, Any], requested_domains: set[str]
    ) -> dict[str, Any]:
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

        # Validate that we have minimum required configuration (only if enhanced validation is enabled)
        if self.enhanced_validation:
            self._validate_minimum_config(merged_config, requested_domains)

        return merged_config

    def _load_domain_file(self, file_path: Path) -> dict[str, Any]:
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
        self, base: dict[str, Any], update: dict[str, Any]
    ) -> dict[str, Any]:
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
        self, config: dict[str, Any], requested_domains: set[str]
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
            # Check for qdrant configuration - it could be at top level or under 'global'
            qdrant_config = None
            if "qdrant" in config:
                qdrant_config = config["qdrant"]
            elif "global" in config and isinstance(config["global"], dict):
                qdrant_config = config["global"].get("qdrant")
            
            if not qdrant_config:
                errors.append("QDrant configuration is required in connectivity domain")
            elif not self._has_valid_value(qdrant_config.get("url")):
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
            raise ValueError(
                f"Minimum configuration validation failed: {'; '.join(errors)}"
            )

    def _has_valid_value(self, value: Any) -> bool:
        """Check if a configuration value is valid (either has a value or is an environment variable).
        
        Args:
            value: Configuration value to check
            
        Returns:
            True if value is valid (not None/empty) or is an environment variable pattern
        """
        if value is None:
            return False
        
        if isinstance(value, str):
            # Empty string is invalid
            if not value.strip():
                return False
            # Environment variable patterns are considered valid
            # ${VAR_NAME} or ${VAR_NAME:-default}
            if value.strip().startswith("${") and value.strip().endswith("}"):
                return True
            # Non-empty string is valid
            return True
        
        # Non-string, non-None values are valid
        return True

    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        """Recursively substitute environment variables in configuration data.

        Supports the following patterns:
        - ${VAR_NAME}: Simple variable substitution
        - ${VAR_NAME:-default_value}: Variable with default value
        - $HOME: Home directory expansion

        Args:
            data: Configuration data to process

        Returns:
            Processed data with environment variables substituted
        """
        if isinstance(data, str):
            # First expand $HOME if present
            if "$HOME" in data:
                data = data.replace("$HOME", os.path.expanduser("~"))

            # Handle ${VAR_NAME} and ${VAR_NAME:-default} patterns
            pattern = r"\${([^}]+)}"
            matches = re.finditer(pattern, data)
            result = data

            for match in matches:
                full_match = match.group(0)  # ${VAR_NAME} or ${VAR_NAME:-default}
                var_expression = match.group(1)  # VAR_NAME or VAR_NAME:-default

                # Check if there's a default value specified
                if ":-" in var_expression:
                    var_name, default_value = var_expression.split(":-", 1)
                    env_value = os.getenv(var_name, default_value)
                    logger.debug(
                        "Environment variable substitution with default",
                        variable=var_name,
                        has_env_value=var_name in os.environ,
                        using_default=var_name not in os.environ,
                    )
                else:
                    var_name = var_expression
                    env_value = os.getenv(var_name)

                    if env_value is None:
                        # Only warn about missing variables that are commonly required
                        # Skip STATE_DB_PATH as it's often overridden in workspace mode
                        if var_name not in ["STATE_DB_PATH"]:
                            logger.warning(
                                "Environment variable not found",
                                variable=var_name,
                                suggestion=f"Set {var_name} in your .env file or environment",
                            )
                        continue

                    logger.debug(
                        "Environment variable substitution",
                        variable=var_name,
                        value_length=len(env_value) if env_value else 0,
                    )

                # If the environment variable contains $HOME, expand it
                if env_value and "$HOME" in env_value:
                    env_value = env_value.replace("$HOME", os.path.expanduser("~"))

                # Replace the full match with the resolved value
                result = result.replace(full_match, env_value)

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
    domains: set[str] | None = None,
    env_path: Path | None = None,
    skip_validation: bool = False,
    preset: str | None = None,
    use_case: str | None = None,
    measure_performance: bool = False,
    enhanced_validation: bool = True,
    fail_fast: bool = False,
    validate_connectivity: bool = False,
) -> ParsedConfig:
    """Convenience function to load multi-file configuration.

    Args:
        config_dir: Directory containing configuration files
        domains: Set of domains to load (defaults to all domains)
        env_path: Optional path to .env file
        skip_validation: If True, skip directory validation
        preset: Predefined domain combination ('minimal', 'basic', 'full')
        use_case: Use case identifier for automatic domain selection
        measure_performance: If True, log performance metrics
        enhanced_validation: If True, use enhanced domain validation
        fail_fast: If True, stop validation on first critical error
        validate_connectivity: If True, perform actual connectivity tests

    Returns:
        ParsedConfig: Merged configuration
    """
    loader = MultiFileConfigLoader(
        enhanced_validation=enhanced_validation,
        fail_fast=fail_fast,
        validate_connectivity=validate_connectivity,
    )
    return loader.load_config(
        config_dir=config_dir,
        domains=domains,
        env_path=env_path,
        skip_validation=skip_validation,
        preset=preset,
        use_case=use_case,
        measure_performance=measure_performance,
    )
