"""Configuration module.

This module provides the main configuration interface for the application.
It combines global settings with source-specific configurations.
"""

import os
import re
import threading
from pathlib import Path
from typing import Any, Optional, Set

import yaml
from dotenv import load_dotenv
from pydantic import (
    Field,
    ValidationError,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..utils.logging import LoggingConfig
from .chunking import ChunkingConfig

# Import consolidated configs
from .global_config import GlobalConfig, SemanticAnalysisConfig

# Import multi-project support
from .models import (
    ParsedConfig,
    ProjectConfig,
    ProjectContext,
    ProjectDetail,
    ProjectInfo,
    ProjectsConfig,
    ProjectStats,
)
from .multi_file_loader import (
    ConfigDomain,
    MultiFileConfigLoader,
    load_multi_file_config,
)
from .neo4j import Neo4jConfig
from .parser import MultiProjectConfigParser
from .sources import SourcesConfig
from .state import StateManagementConfig
from .validation import ValidationConfig
from .validator import ConfigValidator
from .workspace import WorkspaceConfig

# Load environment variables from .env file
load_dotenv(override=False)

# Get logger without initializing it
logger = LoggingConfig.get_logger(__name__)


# Lazy import function for connector configs
def _get_connector_configs():
    """Lazy import connector configs to avoid circular dependencies."""
    from ..connectors.confluence.config import ConfluenceSpaceConfig
    from ..connectors.git.config import GitAuthConfig, GitRepoConfig
    from ..connectors.jira.config import JiraProjectConfig
    from ..connectors.publicdocs.config import PublicDocsSourceConfig, SelectorsConfig

    return {
        "ConfluenceSpaceConfig": ConfluenceSpaceConfig,
        "GitAuthConfig": GitAuthConfig,
        "GitRepoConfig": GitRepoConfig,
        "JiraProjectConfig": JiraProjectConfig,
        "PublicDocsSourceConfig": PublicDocsSourceConfig,
        "SelectorsConfig": SelectorsConfig,
    }


__all__ = [
    "ChunkingConfig",
    "GlobalConfig",
    "Neo4jConfig",
    "SemanticAnalysisConfig",
    "Settings",
    "SourcesConfig",
    "StateManagementConfig",
    "ValidationConfig",
    # Multi-project support
    "ProjectContext",
    "ProjectConfig",
    "ProjectsConfig",
    "ParsedConfig",
    "ProjectStats",
    "ProjectInfo",
    "ProjectDetail",
    "MultiProjectConfigParser",
    "ConfigValidator",
    # Multi-file configuration
    "MultiFileConfigLoader",
    "ConfigDomain",
    "load_multi_file_config",
    # Functions
    "get_global_config",
    "get_settings",
    "initialize_config",
    "initialize_config_with_workspace",
    "initialize_multi_file_config",
    "initialize_multi_file_config_with_workspace",
]


# Add lazy loading for connector configs
def __getattr__(name):
    """Lazy import connector configs to avoid circular dependencies."""
    connector_configs = _get_connector_configs()
    if name in connector_configs:
        return connector_configs[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


class ThreadSafeSettingsManager:
    """Thread-safe singleton manager for global configuration settings."""

    _instance: Optional["ThreadSafeSettingsManager"] = None
    _lock = threading.RLock()

    def __init__(self):
        """Initialize the settings manager."""
        self._settings: Settings | None = None
        self._settings_lock = threading.RLock()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "ThreadSafeSettingsManager":
        """Get the singleton instance of the settings manager.

        Returns:
            ThreadSafeSettingsManager: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize_multi_file_config(
        self,
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
    ) -> None:
        """Initialize configuration from multiple domain-specific files in a thread-safe manner.

        Args:
            config_dir: Directory containing configuration files.
            domains: Set of domains to load (defaults to all domains).
            env_path: Optional path to the .env file.
            skip_validation: If True, skip directory validation and creation.
            preset: Predefined domain combination ('minimal', 'basic', 'full').
            use_case: Use case identifier for automatic domain selection.
            measure_performance: If True, log performance metrics.
            enhanced_validation: If True, use enhanced domain validation.
            fail_fast: If True, stop validation on first critical error.
            validate_connectivity: If True, perform actual connectivity tests.

        Raises:
            FileNotFoundError: If configuration files are not found.
            ValidationError: If configuration validation fails.
        """
        with self._settings_lock:
            logger.debug(
                "Initializing multi-file configuration (thread-safe)",
                config_dir=str(config_dir),
                domains=list(domains) if domains else "all",
                preset=preset,
                use_case=use_case,
            )

            try:
                new_settings = Settings.from_multi_file(
                    config_dir=config_dir,
                    domains=domains,
                    env_path=env_path,
                    skip_validation=skip_validation,
                    preset=preset,
                    use_case=use_case,
                    measure_performance=measure_performance,
                    enhanced_validation=enhanced_validation,
                    fail_fast=fail_fast,
                    validate_connectivity=validate_connectivity,
                )

                # Atomic update of settings
                self._settings = new_settings
                self._initialized = True

                logger.info(
                    "Multi-file configuration initialized successfully (thread-safe)"
                )

            except Exception as e:
                logger.error(
                    "Failed to initialize multi-file configuration (thread-safe)",
                    error=str(e),
                )
                raise

    def initialize_multi_file_config_with_workspace(
        self,
        workspace_config: WorkspaceConfig,
        domains: set[str] | None = None,
        skip_validation: bool = False,
        preset: str | None = None,
        use_case: str | None = None,
        measure_performance: bool = False,
        enhanced_validation: bool = True,
        fail_fast: bool = False,
        validate_connectivity: bool = False,
    ) -> None:
        """Initialize configuration from multiple domain-specific files with workspace support in a thread-safe manner.

        Args:
            workspace_config: Workspace configuration containing paths and overrides.
            domains: Set of domains to load (defaults to all domains).
            skip_validation: If True, skip directory validation and creation.
            preset: Predefined domain combination ('minimal', 'basic', 'full').
            use_case: Use case identifier for automatic domain selection.
            measure_performance: If True, log performance metrics.
            enhanced_validation: If True, use enhanced domain validation.
            fail_fast: If True, stop validation on first critical error.
            validate_connectivity: If True, perform actual connectivity tests.

        Raises:
            FileNotFoundError: If configuration files are not found.
            ValidationError: If configuration validation fails.
        """
        with self._settings_lock:
            logger.debug(
                "Initializing multi-file configuration with workspace (thread-safe)",
                workspace_path=str(workspace_config.workspace_path),
                domains=list(domains) if domains else "all",
                preset=preset,
                use_case=use_case,
            )

            try:
                # Determine the correct config directory based on workspace format
                if workspace_config.is_multi_file:
                    if workspace_config.config_dir is None:
                        raise ValueError(
                            f"Multi-file workspace format detected but config_dir is None in workspace: {workspace_config.workspace_path}"
                        )
                    config_dir = workspace_config.config_dir
                    logger.debug("Using multi-file config directory", config_dir=str(config_dir))
                else:
                    # For legacy single-file format, use workspace root
                    config_dir = workspace_config.workspace_path
                    logger.debug("Using legacy workspace root as config directory", config_dir=str(config_dir))

                # Ensure config_dir is a Path object (should always be the case, but being defensive)
                if not isinstance(config_dir, Path):
                    raise ValueError(f"config_dir must be a Path object, got {type(config_dir)}: {config_dir}")

                # Load configuration from appropriate directory with selective loading support
                new_settings = Settings.from_multi_file(
                    config_dir=config_dir,
                    domains=domains,
                    env_path=workspace_config.env_path,
                    skip_validation=skip_validation,
                    preset=preset,
                    use_case=use_case,
                    measure_performance=measure_performance,
                    enhanced_validation=enhanced_validation,
                    fail_fast=fail_fast,
                    validate_connectivity=validate_connectivity,
                )

                # Override state database path from workspace config
                logger.debug(
                    "Overriding state database path from workspace config",
                    path=str(workspace_config.database_path),
                )
                new_settings.global_config.state_management.database_path = str(
                    workspace_config.database_path
                )

                # Atomic update of settings
                self._settings = new_settings
                self._initialized = True

                logger.info(
                    "Multi-file configuration with workspace initialized successfully (thread-safe)"
                )

            except Exception as e:
                logger.error(
                    "Failed to initialize multi-file configuration with workspace (thread-safe)",
                    error=str(e),
                )
                raise

    def get_settings(self) -> "Settings":
        """Get the current settings instance in a thread-safe manner.

        Returns:
            Settings: The current settings instance

        Raises:
            RuntimeError: If settings have not been initialized
        """
        with self._settings_lock:
            if not self._initialized or self._settings is None:
                raise RuntimeError(
                    "Settings not initialized. Call initialize_multi_file_config() or "
                    "initialize_multi_file_config_with_workspace() first."
                )
            return self._settings

    def update_settings(self, new_settings: "Settings") -> None:
        """Update the settings instance in a thread-safe manner.

        This method is primarily used by hot-reload functionality.

        Args:
            new_settings: The new settings instance to use
        """
        with self._settings_lock:
            self._settings = new_settings
            self._initialized = True
            logger.debug("Settings updated successfully (thread-safe)")

    def is_initialized(self) -> bool:
        """Check if settings have been initialized.

        Returns:
            bool: True if settings are initialized, False otherwise
        """
        with self._settings_lock:
            return self._initialized and self._settings is not None


# Global settings manager instance
_settings_manager = ThreadSafeSettingsManager.get_instance()


def get_settings() -> "Settings":
    """Get the global settings instance.

    Returns:
        Settings: The global settings instance.
    """
    return _settings_manager.get_settings()


def get_global_config() -> GlobalConfig:
    """Get the global configuration instance.

    Returns:
        GlobalConfig: The global configuration instance.
    """
    return get_settings().global_config


def initialize_multi_file_config(
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
) -> None:
    """Initialize global configuration from multiple domain-specific files.

    Args:
        config_dir: Directory containing configuration files.
        domains: Set of domains to load (defaults to all domains).
        env_path: Optional path to the .env file.
        skip_validation: If True, skip directory validation and creation.
        preset: Predefined domain combination ('minimal', 'basic', 'full').
        use_case: Use case identifier for automatic domain selection.
        measure_performance: If True, log performance metrics.

    Raises:
        FileNotFoundError: If configuration files are not found.
        ValidationError: If configuration validation fails.
    """
    _settings_manager.initialize_multi_file_config(
        config_dir=config_dir,
        domains=domains,
        env_path=env_path,
        skip_validation=skip_validation,
        preset=preset,
        use_case=use_case,
        measure_performance=measure_performance,
        enhanced_validation=enhanced_validation,
        fail_fast=fail_fast,
        validate_connectivity=validate_connectivity,
    )


def initialize_multi_file_config_with_workspace(
    workspace_config: WorkspaceConfig,
    domains: set[str] | None = None,
    skip_validation: bool = False,
    preset: str | None = None,
    use_case: str | None = None,
    measure_performance: bool = False,
    enhanced_validation: bool = True,
    fail_fast: bool = False,
    validate_connectivity: bool = False,
) -> None:
    """Initialize configuration from multiple domain-specific files with workspace support.

    Args:
        workspace_config: Workspace configuration containing paths and overrides
        domains: Set of domains to load (defaults to all domains)
        skip_validation: If True, skip directory validation and creation
        preset: Predefined domain combination ('minimal', 'basic', 'full')
        use_case: Use case identifier for automatic domain selection
        measure_performance: If True, log performance metrics
        enhanced_validation: If True, use enhanced domain validation
        fail_fast: If True, stop validation on first critical error
        validate_connectivity: If True, perform actual connectivity tests

    Raises:
        FileNotFoundError: If configuration files are not found
        ValidationError: If configuration validation fails
    """
    _settings_manager.initialize_multi_file_config_with_workspace(
        workspace_config=workspace_config,
        domains=domains,
        skip_validation=skip_validation,
        preset=preset,
        use_case=use_case,
        measure_performance=measure_performance,
        enhanced_validation=enhanced_validation,
        fail_fast=fail_fast,
        validate_connectivity=validate_connectivity,
    )


def initialize_config_with_workspace(
    workspace_config: WorkspaceConfig,
    skip_validation: bool = False,
) -> None:
    """Initialize configuration with workspace support (legacy single-file mode).

    Args:
        workspace_config: Workspace configuration containing paths and overrides
        skip_validation: If True, skip directory validation and creation

    Raises:
        FileNotFoundError: If configuration files are not found
        ValidationError: If configuration validation fails
    """
    # For now, delegate to multi-file config initialization
    # This maintains backward compatibility while using the new system
    initialize_multi_file_config_with_workspace(
        workspace_config=workspace_config,
        skip_validation=skip_validation,
    )


def initialize_config(
    config_path: Path,
    env_path: Path | None = None,
    skip_validation: bool = False,
) -> None:
    """Initialize configuration from a single file (legacy mode).

    Args:
        config_path: Path to the configuration file
        env_path: Optional path to the .env file
        skip_validation: If True, skip directory validation and creation

    Raises:
        FileNotFoundError: If configuration files are not found
        ValidationError: If configuration validation fails
    """
    # For legacy single-file configs, we need to handle them differently
    # For now, this is a placeholder that would need proper implementation
    # based on the legacy configuration format
    raise NotImplementedError(
        "Legacy single-file configuration loading is not yet implemented. "
        "Please use the multi-file configuration format or migrate your configuration."
    )


class Settings(BaseSettings):
    """Main configuration class combining global and source-specific settings."""

    # Configuration objects - these are the only fields we need
    global_config: GlobalConfig = Field(
        default_factory=GlobalConfig, description="Global configuration settings"
    )
    projects_config: ProjectsConfig = Field(
        default_factory=ProjectsConfig, description="Multi-project configurations"
    )

    model_config = SettingsConfigDict(
        env_file=None,  # Disable automatic .env loading - we handle this manually
        env_file_encoding="utf-8",
        extra="allow",
    )

    def __init__(self, **data):
        """Initialize Settings with thread-safe property access."""
        super().__init__(**data)
        self._property_lock = threading.RLock()

    @model_validator(mode="after")  # type: ignore
    def validate_source_configs(self) -> "Settings":
        """Validate that required configuration is present for configured sources."""
        logger.debug("Validating source configurations")

        # Validate that qdrant configuration is present in global config
        if not self.global_config.qdrant:
            raise ValueError("Qdrant configuration is required in global config")

        # Validate that required fields are not empty after variable substitution
        if not self.global_config.qdrant.url:
            raise ValueError(
                "Qdrant URL is required but was not provided or substituted"
            )

        if not self.global_config.qdrant.collection_name:
            raise ValueError(
                "Qdrant collection name is required but was not provided or substituted"
            )

        # Note: Source validation is now handled at the project level
        # Each project's sources are validated when the project is processed

        logger.debug("Source configuration validation successful")
        return self

    @property
    def qdrant_url(self) -> str:
        """Get the Qdrant URL from global configuration."""
        with self._property_lock:
            if not self.global_config.qdrant:
                raise ValueError("Qdrant configuration is not available")
            return self.global_config.qdrant.url

    @property
    def qdrant_api_key(self) -> str | None:
        """Get the Qdrant API key from global configuration."""
        with self._property_lock:
            if not self.global_config.qdrant:
                return None
            return self.global_config.qdrant.api_key

    @property
    def qdrant_collection_name(self) -> str:
        """Get the Qdrant collection name from global configuration."""
        with self._property_lock:
            if not self.global_config.qdrant:
                raise ValueError("Qdrant configuration is not available")
            return self.global_config.qdrant.collection_name

    @property
    def neo4j_uri(self) -> str:
        """Get the Neo4j URI from global configuration."""
        with self._property_lock:
            if not self.global_config.neo4j:
                raise ValueError("Neo4j configuration is not available")
            return self.global_config.neo4j.uri

    @property
    def neo4j_user(self) -> str:
        """Get the Neo4j user from global configuration."""
        with self._property_lock:
            if not self.global_config.neo4j:
                raise ValueError("Neo4j configuration is not available")
            return self.global_config.neo4j.user

    @property
    def neo4j_password(self) -> str:
        """Get the Neo4j password from global configuration."""
        with self._property_lock:
            if not self.global_config.neo4j:
                raise ValueError("Neo4j configuration is not available")
            return self.global_config.neo4j.password

    @property
    def neo4j_database(self) -> str:
        """Get the Neo4j database name from global configuration."""
        with self._property_lock:
            if not self.global_config.neo4j:
                raise ValueError("Neo4j configuration is not available")
            return self.global_config.neo4j.database

    @property
    def openai_api_key(self) -> str:
        """Get the OpenAI API key from embedding configuration."""
        with self._property_lock:
            api_key = self.global_config.embedding.api_key
            if not api_key:
                raise ValueError(
                    "OpenAI API key is required but was not provided or substituted in embedding configuration"
                )
            return api_key

    @property
    def state_db_path(self) -> str:
        """Get the state database path from global configuration."""
        with self._property_lock:
            return self.global_config.state_management.database_path

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
            return {k: Settings._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Settings._substitute_env_vars(item) for item in data]
        return data

    @classmethod
    def from_multi_file(
        cls,
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
    ) -> "Settings":
        """Load configuration from multiple domain-specific files.

        Args:
            config_dir: Directory containing configuration files.
            domains: Set of domains to load (defaults to all domains).
            env_path: Optional path to the .env file.
            skip_validation: If True, skip directory validation and creation.
            preset: Predefined domain combination ('minimal', 'basic', 'full').
            use_case: Use case identifier for automatic domain selection.
            measure_performance: If True, log performance metrics.
            enhanced_validation: If True, use enhanced domain validation.
            fail_fast: If True, stop validation on first critical error.
            validate_connectivity: If True, perform actual connectivity tests.

        Returns:
            Settings: Loaded configuration.
        """
        logger.debug(
            "Loading multi-file configuration",
            config_dir=str(config_dir),
            domains=list(domains) if domains else "all",
            preset=preset,
            use_case=use_case,
        )

        try:
            # Use the multi-file loader to load and merge configurations
            parsed_config = load_multi_file_config(
                config_dir=config_dir,
                domains=domains,
                env_path=env_path,
                skip_validation=skip_validation,
                preset=preset,
                use_case=use_case,
                measure_performance=measure_performance,
                enhanced_validation=enhanced_validation,
                fail_fast=fail_fast,
                validate_connectivity=validate_connectivity,
            )

            # Create settings instance with parsed configuration
            settings = cls(
                global_config=parsed_config.global_config,
                projects_config=parsed_config.projects_config,
            )

            logger.debug(
                "Successfully created Settings instance from multi-file configuration"
            )
            return settings

        except Exception as e:
            logger.error("Failed to load multi-file configuration", error=str(e))
            raise

    def to_dict(self) -> dict:
        """Convert the configuration to a dictionary.

        Returns:
            dict: Configuration as a dictionary.
        """
        return {
            "global": self.global_config.to_dict(),
            "projects": self.projects_config.to_dict(),
        }
