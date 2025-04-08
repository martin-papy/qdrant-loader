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
    OPENAI_ORGANIZATION: Optional[str] = Field(None, description="OpenAI organization ID")
    
    # Source-specific environment variables
    AUTH_TEST_REPO_TOKEN: Optional[str] = Field(None, description="Test repository token")
    CONFLUENCE_TOKEN: Optional[str] = Field(None, description="Confluence API token")
    CONFLUENCE_EMAIL: Optional[str] = Field(None, description="Confluence user email")
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
            'OPENAI_ORGANIZATION': os.getenv('OPENAI_ORGANIZATION'),
            'AUTH_TEST_REPO_TOKEN': os.getenv('AUTH_TEST_REPO_TOKEN'),
            'CONFLUENCE_TOKEN': os.getenv('CONFLUENCE_TOKEN'),
            'CONFLUENCE_EMAIL': os.getenv('CONFLUENCE_EMAIL'),
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