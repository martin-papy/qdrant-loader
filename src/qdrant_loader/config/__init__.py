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
from .sources import (
    SourcesConfig,
    GitRepoConfig,
    ConfluenceSpaceConfig as ConfluenceConfig,
    JiraProjectConfig as JiraConfig,
    PublicDocsConfig
)

# Load environment variables from .env file
load_dotenv()

__all__ = [
    'Settings',
    'GlobalConfig',
    'SourcesConfig',
    'GitRepoConfig',
    'ConfluenceConfig',
    'JiraConfig',
    'PublicDocsConfig',
    'get_settings',
    'get_global_config',
    'initialize_config',
]

from .base import BaseConfig, ConfigProtocol, SourceConfigProtocol, BaseSourceConfig

_global_settings: Optional['Settings'] = None

def get_settings() -> 'Settings':
    """Get the global settings instance.
    
    This is an alias for get_global_config() for backward compatibility.
    
    Returns:
        Settings: The global settings instance.
        
    Raises:
        RuntimeError: If the global configuration has not been initialized.
    """
    return get_global_config()

def get_global_config() -> 'Settings':
    """Get the global configuration instance.
    
    Returns:
        Settings: The global configuration instance.
        
    Raises:
        RuntimeError: If the global configuration has not been initialized.
    """
    if _global_settings is None:
        raise RuntimeError("Global configuration has not been initialized")
    return _global_settings

def initialize_config(yaml_path: Path) -> None:
    """Initialize the global configuration.
    
    Args:
        yaml_path: Path to the YAML configuration file.
    """
    global _global_settings
    _global_settings = Settings.from_yaml(yaml_path)

class Settings(BaseConfig):
    """Main configuration class combining global and source-specific settings."""
    
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str
    OPENAI_API_KEY: str
    OPENAI_ORGANIZATION: Optional[str] = None
    
    global_config: GlobalConfig
    sources_config: SourcesConfig
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'Settings':
        """Load configuration from a YAML file.
        
        Args:
            yaml_path: Path to the YAML configuration file.
            
        Returns:
            Settings: Loaded configuration.
        """
        with open(yaml_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Create configuration instances
        global_config = GlobalConfig(**config_data.get('global', {}))
        sources_config = SourcesConfig(**config_data.get('sources', {}))
        
        # Create settings instance
        return cls(
            global_config=global_config,
            sources_config=sources_config
        )
    
    def to_dict(self) -> dict:
        """Convert the configuration to a dictionary.
        
        Returns:
            dict: Configuration as a dictionary.
        """
        return {
            'global': self.global_config.to_dict(),
            'sources': self.sources_config.to_dict()
        } 