"""Configuration module.

This module provides the main configuration interface for the application.
It combines global settings with source-specific configurations.
"""

import os
import re
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
from .neo4j import Neo4jConfig
from .parser import MultiProjectConfigParser
from .sources import SourcesConfig
from .state import StateManagementConfig
from .validator import ConfigValidator
from .workspace import WorkspaceConfig
from .multi_file_loader import (
    MultiFileConfigLoader,
    ConfigDomain,
    load_multi_file_config,
)

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


_global_settings: Optional["Settings"] = None


def get_settings() -> "Settings":
    """Get the global settings instance.

    Returns:
        Settings: The global settings instance.
    """
    if _global_settings is None:
        raise RuntimeError(
            "Settings not initialized. Call initialize_config() or initialize_config_with_workspace() first."
        )
    return _global_settings


def get_global_config() -> GlobalConfig:
    """Get the global configuration instance.

    Returns:
        GlobalConfig: The global configuration instance.
    """
    return get_settings().global_config


def initialize_multi_file_config(
    config_dir: Path,
    domains: Optional[Set[str]] = None,
    env_path: Path | None = None,
    skip_validation: bool = False,
) -> None:
    """Initialize global configuration from multiple domain-specific files.

    Args:
        config_dir: Directory containing configuration files.
        domains: Set of domains to load (defaults to all domains).
        env_path: Optional path to the .env file.
        skip_validation: If True, skip directory validation and creation.

    Raises:
        FileNotFoundError: If configuration files are not found.
        ValidationError: If configuration validation fails.
    """
    global _global_settings

    logger.debug(
        "Initializing multi-file configuration",
        config_dir=str(config_dir),
        domains=list(domains) if domains else "all",
    )

    try:
        _global_settings = Settings.from_multi_file(
            config_dir=config_dir,
            domains=domains,
            env_path=env_path,
            skip_validation=skip_validation,
        )
        logger.info("Multi-file configuration initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize multi-file configuration", error=str(e))
        raise


def initialize_multi_file_config_with_workspace(
    workspace_config: WorkspaceConfig,
    domains: Optional[Set[str]] = None,
    skip_validation: bool = False,
) -> None:
    """Initialize global configuration from multiple domain-specific files with workspace support.

    Args:
        workspace_config: Workspace configuration containing paths and overrides.
        domains: Set of domains to load (defaults to all domains).
        skip_validation: If True, skip directory validation and creation.

    Raises:
        FileNotFoundError: If configuration files are not found.
        ValidationError: If configuration validation fails.
    """
    global _global_settings

    logger.debug(
        "Initializing multi-file configuration with workspace",
        workspace_path=str(workspace_config.workspace_path),
        domains=list(domains) if domains else "all",
    )

    try:
        # Load configuration from workspace directory
        _global_settings = Settings.from_multi_file(
            config_dir=workspace_config.workspace_path,
            domains=domains,
            env_path=workspace_config.env_path,
            skip_validation=skip_validation,
        )

        # Override state database path from workspace config
        logger.debug(
            "Overriding state database path from workspace config",
            path=str(workspace_config.database_path),
        )
        _global_settings.global_config.state_management.database_path = str(
            workspace_config.database_path
        )

        logger.info("Multi-file configuration with workspace initialized successfully")

    except Exception as e:
        logger.error(
            "Failed to initialize multi-file configuration with workspace",
            error=str(e),
        )
        raise


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
        if not self.global_config.qdrant:
            raise ValueError("Qdrant configuration is not available")
        return self.global_config.qdrant.url

    @property
    def qdrant_api_key(self) -> str | None:
        """Get the Qdrant API key from global configuration."""
        if not self.global_config.qdrant:
            return None
        return self.global_config.qdrant.api_key

    @property
    def qdrant_collection_name(self) -> str:
        """Get the Qdrant collection name from global configuration."""
        if not self.global_config.qdrant:
            raise ValueError("Qdrant configuration is not available")
        return self.global_config.qdrant.collection_name

    @property
    def neo4j_uri(self) -> str:
        """Get the Neo4j URI from global configuration."""
        if not self.global_config.neo4j:
            raise ValueError("Neo4j configuration is not available")
        return self.global_config.neo4j.uri

    @property
    def neo4j_user(self) -> str:
        """Get the Neo4j user from global configuration."""
        if not self.global_config.neo4j:
            raise ValueError("Neo4j configuration is not available")
        return self.global_config.neo4j.user

    @property
    def neo4j_password(self) -> str:
        """Get the Neo4j password from global configuration."""
        if not self.global_config.neo4j:
            raise ValueError("Neo4j configuration is not available")
        return self.global_config.neo4j.password

    @property
    def neo4j_database(self) -> str:
        """Get the Neo4j database name from global configuration."""
        if not self.global_config.neo4j:
            raise ValueError("Neo4j configuration is not available")
        return self.global_config.neo4j.database

    @property
    def openai_api_key(self) -> str:
        """Get the OpenAI API key from embedding configuration."""
        api_key = self.global_config.embedding.api_key
        if not api_key:
            raise ValueError(
                "OpenAI API key is required but was not provided or substituted in embedding configuration"
            )
        return api_key

    @property
    def state_db_path(self) -> str:
        """Get the state database path from global configuration."""
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
        domains: Optional[Set[str]] = None,
        env_path: Path | None = None,
        skip_validation: bool = False,
    ) -> "Settings":
        """Load configuration from multiple domain-specific files.

        Args:
            config_dir: Directory containing configuration files.
            domains: Set of domains to load (defaults to all domains).
            env_path: Optional path to the .env file.
            skip_validation: If True, skip directory validation and creation.

        Returns:
            Settings: Loaded configuration.
        """
        logger.debug(
            "Loading multi-file configuration",
            config_dir=str(config_dir),
            domains=list(domains) if domains else "all",
        )

        try:
            # Use the multi-file loader to load and merge configurations
            parsed_config = load_multi_file_config(
                config_dir=config_dir,
                domains=domains,
                env_path=env_path,
                skip_validation=skip_validation,
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
