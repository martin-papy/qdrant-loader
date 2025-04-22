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
from .global_config import GlobalConfig
from .sources import SourcesConfig
from .state import StateManagementConfig

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
    "Settings",
    "SourcesConfig",
    "StateManagementConfig",
    "get_global_config",
    "get_settings",
    "initialize_config",
]

_global_settings: Optional["Settings"] = None


def get_settings() -> "Settings":
    """Get the global settings instance.

    Returns:
        Settings: The global settings instance.
    """
    if _global_settings is None:
        raise RuntimeError("Settings not initialized. Call initialize_config() first.")
    return _global_settings


def get_global_config() -> GlobalConfig:
    """Get the global configuration instance.

    Returns:
        GlobalConfig: The global configuration instance.
    """
    return get_settings().global_config


def initialize_config(yaml_path: Path, skip_validation: bool = False) -> None:
    """Initialize the global configuration.

    Args:
        yaml_path: Path to the YAML configuration file.
        skip_validation: If True, skip directory validation and creation.
    """
    global _global_settings
    try:
        # Proceed with initialization
        logger.debug("Initializing configuration", yaml_path=str(yaml_path))
        _global_settings = Settings.from_yaml(yaml_path, skip_validation=skip_validation)
        logger.debug("Successfully initialized configuration")

    except Exception as e:
        logger.error("Failed to initialize configuration", error=str(e), yaml_path=str(yaml_path))
        raise


class Settings(BaseSettings):
    """Main configuration class combining global and source-specific settings."""

    # qDrant Configuration
    QDRANT_URL: str = Field(..., description="qDrant server URL")
    QDRANT_API_KEY: str | None = Field(None, description="qDrant API key")
    QDRANT_COLLECTION_NAME: str = Field(..., description="qDrant collection name")

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")

    # State Management Configuration
    STATE_DB_PATH: str = Field(..., description="Path to state management database")

    # Source-specific environment variables
    REPO_TOKEN: str | None = Field(None, description="Repository token")
    REPO_URL: str | None = Field(None, description="Repository URL")

    CONFLUENCE_URL: str | None = Field(None, description="Confluence URL")
    CONFLUENCE_SPACE_KEY: str | None = Field(None, description="Confluence space key")
    CONFLUENCE_TOKEN: str | None = Field(None, description="Confluence API token")
    CONFLUENCE_EMAIL: str | None = Field(None, description="Confluence user email")

    JIRA_URL: str | None = Field(None, description="Jira URL")
    JIRA_PROJECT_KEY: str | None = Field(None, description="Jira project key")
    JIRA_TOKEN: str | None = Field(None, description="Jira API token")
    JIRA_EMAIL: str | None = Field(None, description="Jira user email")

    # Configuration objects
    global_config: GlobalConfig = Field(
        default_factory=GlobalConfig, description="Global configuration settings"
    )
    sources_config: SourcesConfig = Field(
        default_factory=SourcesConfig, description="Source-specific configurations"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    @field_validator("QDRANT_URL", "QDRANT_COLLECTION_NAME", "OPENAI_API_KEY", "STATE_DB_PATH")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate that required string fields are not empty."""
        if not v:
            raise ValueError("Field cannot be empty")
        return v

    @model_validator(mode="after")  # type: ignore
    def validate_source_configs(self) -> "Settings":
        """Validate that required environment variables are set for configured sources."""
        logger.debug("Validating source configurations")

        # Validate Confluence settings if Confluence sources are configured
        if self.sources_config.confluence:
            if not all([self.CONFLUENCE_TOKEN, self.CONFLUENCE_EMAIL]):
                logger.error("Missing required Confluence environment variables")
                raise ValueError(
                    "Confluence sources are configured but required environment variables "
                    "CONFLUENCE_TOKEN and/or CONFLUENCE_EMAIL are not set"
                )

        # Validate Git settings if Git sources are configured
        if self.sources_config.git:
            if not self.REPO_TOKEN and any(repo.token for repo in self.sources_config.git.values()):
                logger.error("Missing required Git repository token")
                raise ValueError(
                    "Git repositories requiring authentication are configured but "
                    "REPO_TOKEN environment variable is not set"
                )

        # Validate Jira settings if Jira sources are configured
        if self.sources_config.jira:
            if not all([self.JIRA_TOKEN, self.JIRA_EMAIL]):
                logger.error("Missing required Jira environment variables")
                raise ValueError(
                    "Jira sources are configured but required environment variables "
                    "JIRA_TOKEN and/or JIRA_EMAIL are not set"
                )

        logger.debug("Source configuration validation successful")
        return self

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
                    logger.warning("Environment variable not found", variable=var_name)
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
    def from_yaml(cls, config_path: Path, skip_validation: bool = False) -> "Settings":
        """Load configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file.
            skip_validation: If True, skip directory validation and creation.

        Returns:
            Settings: Loaded configuration.
        """
        logger.debug("Loading configuration from YAML", path=str(config_path))
        try:
            # Step 1: Load YAML config
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            # Step 2: Load environment variables
            logger.debug("Loading environment variables")
            load_dotenv(override=False)

            # Step 3: Process all environment variables in config
            logger.debug("Processing environment variables in configuration")
            config_data = cls._substitute_env_vars(config_data)

            # Step 4: Create configuration instances with processed data
            global_config = GlobalConfig(
                **config_data.get("global", {}), skip_validation=skip_validation
            )

            # Process each source type
            # Get the sources section
            sources_data = config_data.get("sources", {})

            for source_type, sources in sources_data.items():
                for source, source_config in sources.items():
                    # Add source_type and source to the config
                    source_config["source_type"] = source_type
                    source_config["source"] = source

            sources_config = SourcesConfig(**sources_data)

            # Step 5: Create settings instance with environment variables and config objects
            settings_data = {
                "global_config": global_config,
                "sources_config": sources_config,
                "QDRANT_URL": os.getenv("QDRANT_URL"),
                "QDRANT_API_KEY": os.getenv("QDRANT_API_KEY"),
                "QDRANT_COLLECTION_NAME": os.getenv("QDRANT_COLLECTION_NAME"),
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
                "STATE_DB_PATH": os.getenv("STATE_DB_PATH"),
                "REPO_TOKEN": os.getenv("REPO_TOKEN"),
                "REPO_URL": os.getenv("REPO_URL"),
                "CONFLUENCE_URL": os.getenv("CONFLUENCE_URL"),
                "CONFLUENCE_SPACE_KEY": os.getenv("CONFLUENCE_SPACE_KEY"),
                "CONFLUENCE_TOKEN": os.getenv("CONFLUENCE_TOKEN"),
                "CONFLUENCE_EMAIL": os.getenv("CONFLUENCE_EMAIL"),
                "JIRA_URL": os.getenv("JIRA_URL"),
                "JIRA_PROJECT_KEY": os.getenv("JIRA_PROJECT_KEY"),
                "JIRA_TOKEN": os.getenv("JIRA_TOKEN"),
                "JIRA_EMAIL": os.getenv("JIRA_EMAIL"),
            }

            logger.debug("Creating Settings instance with data", settings_data=settings_data)
            settings = cls(**settings_data)

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
            "sources": self.sources_config.to_dict(),
        }
