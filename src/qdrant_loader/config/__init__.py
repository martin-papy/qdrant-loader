"""Configuration module.

This module provides the main configuration interface for the application.
It combines global settings with source-specific configurations.
"""

from typing import Optional, List, Dict, Any, Tuple, Union
from pydantic import Field, field_validator, ConfigDict, ValidationError, BaseModel, model_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv
import structlog
import re

# Import consolidated configs
from .chunking import ChunkingConfig
from .embedding import EmbeddingConfig
from .global_ import GlobalConfig
from .sources import SourcesConfig
from ..connectors.git.config import GitRepoConfig, GitAuthConfig
from ..connectors.confluence.config import ConfluenceSpaceConfig
from ..connectors.jira.config import JiraProjectConfig
from ..connectors.public_docs.config import PublicDocsSourceConfig, SelectorsConfig

# Load environment variables from .env file
load_dotenv()

__all__ = [
    'Settings',
    'GlobalConfig',
    'SourcesConfig',
    'GitRepoConfig',
    'GitAuthConfig',
    'ConfluenceSpaceConfig',
    'JiraProjectConfig',
    'PublicDocsSourceConfig',
    'SelectorsConfig',
    'get_settings',
    'get_global_config',
    'initialize_config',
]

from .base import BaseConfig, ConfigProtocol, SourceConfigProtocol, BaseSourceConfig

_global_settings: Optional['Settings'] = None

def get_settings() -> 'Settings':
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

def initialize_config(yaml_path: Path) -> None:
    """Initialize the global configuration.
    
    Args:
        yaml_path: Path to the YAML configuration file.
    """
    global _global_settings
    _global_settings = Settings.from_yaml(yaml_path)

class Settings(BaseSettings):
    """Main configuration class combining global and source-specific settings."""
    
    # qDrant Configuration
    QDRANT_URL: str = Field(..., description="qDrant server URL")
    QDRANT_API_KEY: Optional[str] = Field(None, description="qDrant API key")
    QDRANT_COLLECTION_NAME: str = Field(..., description="qDrant collection name")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    
    # Source-specific environment variables
    REPO_TOKEN: Optional[str] = Field(None, description="Repository token")
    REPO_URL: Optional[str] = Field(None, description="Repository URL")
    
    CONFLUENCE_URL: Optional[str] = Field(None, description="Confluence URL")
    CONFLUENCE_SPACE_KEY: Optional[str] = Field(None, description="Confluence space key")
    CONFLUENCE_TOKEN: Optional[str] = Field(None, description="Confluence API token")
    CONFLUENCE_EMAIL: Optional[str] = Field(None, description="Confluence user email")

    JIRA_URL: Optional[str] = Field(None, description="Jira URL")
    JIRA_PROJECT_KEY: Optional[str] = Field(None, description="Jira project key")
    JIRA_TOKEN: Optional[str] = Field(None, description="Jira API token")
    JIRA_EMAIL: Optional[str] = Field(None, description="Jira user email")
    
    # Configuration objects
    global_config: GlobalConfig = Field(default_factory=GlobalConfig, description="Global configuration settings")
    sources_config: SourcesConfig = Field(default_factory=SourcesConfig, description="Source-specific configurations")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
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
            # Handle ${VAR_NAME} pattern
            return os.path.expandvars(data)
        elif isinstance(data, dict):
            return {k: Settings._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Settings._substitute_env_vars(item) for item in data]
        return data

    @classmethod
    def from_yaml(cls, config_path: Path) -> 'Settings':
        """Load configuration from a YAML file.
        
        Args:
            config_path: Path to the YAML configuration file.
            
        Returns:
            Settings: Loaded configuration.
        """
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            
        # Substitute environment variables in the config data
        config_data = cls._substitute_env_vars(config_data)
            
        # Create configuration instances
        global_config = GlobalConfig(**config_data.get('global', {}))
        sources_config = SourcesConfig(**config_data.get('sources', {}))
        
        # Create settings instance with environment variables and config objects
        settings_data = {
            'global_config': global_config,
            'sources_config': sources_config,
            'QDRANT_URL': os.getenv('QDRANT_URL'),
            'QDRANT_API_KEY': os.getenv('QDRANT_API_KEY'),
            'QDRANT_COLLECTION_NAME': os.getenv('QDRANT_COLLECTION_NAME'),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'REPO_TOKEN': os.getenv('REPO_TOKEN'),
            'REPO_URL': os.getenv('REPO_URL'),
            'CONFLUENCE_URL': os.getenv('CONFLUENCE_URL'),
            'CONFLUENCE_SPACE_KEY': os.getenv('CONFLUENCE_SPACE_KEY'),
            'CONFLUENCE_TOKEN': os.getenv('CONFLUENCE_TOKEN'),
            'CONFLUENCE_EMAIL': os.getenv('CONFLUENCE_EMAIL'),
            'JIRA_URL': os.getenv('JIRA_URL'),
            'JIRA_PROJECT_KEY': os.getenv('JIRA_PROJECT_KEY'),
            'JIRA_TOKEN': os.getenv('JIRA_TOKEN'),
            'JIRA_EMAIL': os.getenv('JIRA_EMAIL')
        }
        
        return cls(**settings_data)
    
    def to_dict(self) -> dict:
        """Convert the configuration to a dictionary.
        
        Returns:
            dict: Configuration as a dictionary.
        """
        return {
            'global': self.global_config.to_dict(),
            'sources': self.sources_config.to_dict()
        } 