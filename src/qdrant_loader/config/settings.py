"""Configuration settings for the QDrant Loader."""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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