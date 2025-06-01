"""Configuration module.

This module provides the main configuration interface for the application.
It combines global settings with source-specific configurations.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import (
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..connectors.confluence.config import ConfluenceSpaceConfig
from ..connectors.git.config import GitAuthConfig, GitRepoConfig
from ..connectors.jira.config import JiraProjectConfig
from ..connectors.publicdocs.config import PublicDocsSourceConfig, SelectorsConfig
from ..utils.logging import LoggingConfig
from .chunking import ChunkingConfig

# Import consolidated configs
from .global_config import GlobalConfig, SemanticAnalysisConfig
from .sources import SourcesConfig
from .state import StateManagementConfig
from .workspace import WorkspaceConfig, get_workspace_env_override

# Import multi-project support
from .models import (
    ProjectContext,
    ProjectConfig,
    ProjectsConfig,
    ParsedConfig,
    ProjectStats,
    ProjectInfo,
    ProjectDetail,
)
from .parser import MultiProjectConfigParser
from .validator import ConfigValidator

# Load environment variables from .env file
load_dotenv(override=False)

# Get logger without initializing it
logger = LoggingConfig.get_logger(__name__)

__all__ = [
    "ChunkingConfig",
    "ConfluenceSpaceConfig",
    "GitAuthConfig",
    "GitRepoConfig",
    "GlobalConfig",
    "JiraProjectConfig",
    "PublicDocsSourceConfig",
    "SelectorsConfig",
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
    # Functions
    "get_global_config",
    "get_settings",
    "initialize_config",
    "initialize_config_with_workspace",
]

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


def initialize_config(
    yaml_path: Path, env_path: Path | None = None, skip_validation: bool = False
) -> None:
    """Initialize the global configuration.

    Args:
        yaml_path: Path to the YAML configuration file.
        env_path: Optional path to the .env file.
        skip_validation: If True, skip directory validation and creation.
    """
    global _global_settings
    try:
        # Proceed with initialization
        logger.debug(
            "Initializing configuration",
            yaml_path=str(yaml_path),
            env_path=str(env_path) if env_path else None,
        )
        _global_settings = Settings.from_yaml(
            yaml_path, env_path=env_path, skip_validation=skip_validation
        )
        logger.debug("Successfully initialized configuration")

    except Exception as e:
        logger.error(
            "Failed to initialize configuration", error=str(e), yaml_path=str(yaml_path)
        )
        raise


def initialize_config_with_workspace(
    workspace_config: WorkspaceConfig, skip_validation: bool = False
) -> None:
    """Initialize configuration using workspace settings.

    Args:
        workspace_config: Workspace configuration with paths and settings
        skip_validation: If True, skip directory validation and creation
    """
    global _global_settings
    try:
        logger.debug(
            "Initializing configuration with workspace",
            workspace=str(workspace_config.workspace_path),
            config_path=str(workspace_config.config_path),
            env_path=(
                str(workspace_config.env_path) if workspace_config.env_path else None
            ),
        )

        # Load configuration using workspace paths
        _global_settings = Settings.from_yaml(
            workspace_config.config_path,
            env_path=workspace_config.env_path,
            skip_validation=skip_validation,
        )

        # Check if database_path was specified in config.yaml and warn user
        original_db_path = _global_settings.global_config.state_management.database_path
        workspace_db_path = str(workspace_config.database_path)

        # Only warn if the original path is different from the workspace path and not empty/default
        if (
            original_db_path
            and original_db_path != ":memory:"
            and original_db_path != workspace_db_path
        ):
            logger.warning(
                "Database path in config.yaml is ignored in workspace mode",
                config_database_path=original_db_path,
                workspace_database_path=workspace_db_path,
            )

        # Override the database path with workspace-specific path
        _global_settings.global_config.state_management.database_path = (
            workspace_db_path
        )

        logger.debug(
            "Set workspace database path",
            database_path=workspace_db_path,
        )

        logger.debug(
            "Successfully initialized configuration with workspace",
            workspace=str(workspace_config.workspace_path),
        )

    except Exception as e:
        logger.error(
            "Failed to initialize configuration with workspace",
            error=str(e),
            workspace=str(workspace_config.workspace_path),
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
    def from_yaml(
        cls,
        config_path: Path,
        env_path: Path | None = None,
        skip_validation: bool = False,
    ) -> "Settings":
        """Load configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file.
            env_path: Optional path to the .env file. If provided, only this file is loaded.
            skip_validation: If True, skip directory validation and creation.

        Returns:
            Settings: Loaded configuration.
        """
        logger.debug("Loading configuration from YAML", path=str(config_path))
        try:
            # Step 1: Load environment variables first
            if env_path is not None:
                # Custom env file specified - load only this file
                logger.debug("Loading custom environment file", path=str(env_path))
                if not env_path.exists():
                    raise FileNotFoundError(f"Environment file not found: {env_path}")
                load_dotenv(env_path, override=True)
            else:
                # Load default .env file if it exists
                logger.debug("Loading default environment variables")
                load_dotenv(override=False)

            # Step 2: Load YAML config
            with open(config_path) as f:
                config_data = yaml.safe_load(f)

            # Step 3: Process all environment variables in config using substitution
            logger.debug("Processing environment variables in configuration")
            config_data = cls._substitute_env_vars(config_data)

            # Step 4: Use multi-project parser to parse configuration
            validator = ConfigValidator()
            parser = MultiProjectConfigParser(validator)
            parsed_config = parser.parse(config_data, skip_validation=skip_validation)

            # Step 5: Create settings instance with parsed configuration
            settings = cls(
                global_config=parsed_config.global_config,
                projects_config=parsed_config.projects_config,
            )

            logger.debug("Successfully created Settings instance")
            return settings

        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML configuration", error=str(e))
            raise
        except ValidationError as e:
            logger.error("Configuration validation failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error loading configuration", error=str(e))
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
