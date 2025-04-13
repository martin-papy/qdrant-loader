"""Configuration settings for the QDrant Loader."""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

from .global_ import GlobalConfig
from .sources import SourcesConfig


class Settings(BaseSettings):
    """Configuration settings for the QDrant Loader."""
    
    # qDrant Configuration
    QDRANT_URL: str = Field(..., description="qDrant server URL")
    QDRANT_API_KEY: str = Field(..., description="qDrant API key")
    QDRANT_COLLECTION_NAME: str = Field(..., description="qDrant collection name")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    
    # Git Authentication Configuration
    GITHUB_TOKEN: Optional[str] = Field(None, description="GitHub Personal Access Token")
    GITLAB_TOKEN: Optional[str] = Field(None, description="GitLab Personal Access Token")
    BITBUCKET_TOKEN: Optional[str] = Field(None, description="Bitbucket Personal Access Token")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # State Database Configuration
    STATE_DB_PATH: str = Field(..., description="Path to state management database")
    
    # Optional configuration
    global_config: Optional[GlobalConfig] = None
    sources_config: Optional[SourcesConfig] = None
    
    @field_validator("QDRANT_URL", "QDRANT_API_KEY", "QDRANT_COLLECTION_NAME", "OPENAI_API_KEY")
    @classmethod
    def validate_required_string(cls, v):
        if not v:
            raise ValueError("Field is required and cannot be empty")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"  # Allow extra fields in environment variables
    ) 

    @classmethod
    def from_yaml(cls, config_path: Path) -> "Settings":
        """Create settings from a YAML file."""
        from .base import load_yaml_config
        config = load_yaml_config(config_path)
        
        # Extract global and sources config
        global_config = GlobalConfig.model_validate(config.get("global", {}))
        sources_config = SourcesConfig.model_validate(config.get("sources", {}))
        
        # Create settings with environment variables
        settings = cls()
        settings.global_config = global_config
        settings.sources_config = sources_config
        
        return settings

def get_settings() -> Settings:
    """Get the settings from environment variables."""
    return Settings()

__all__ = ['Settings', 'get_settings'] 