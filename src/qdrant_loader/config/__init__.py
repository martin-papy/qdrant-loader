from typing import Optional
from pydantic import Field, field_validator, ConfigDict, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Configuration settings for the QDrant Loader."""
    
    # qDrant Configuration
    QDRANT_URL: str = Field(..., description="qDrant server URL")
    QDRANT_API_KEY: str = Field(..., description="qDrant API key")
    QDRANT_COLLECTION_NAME: str = Field(..., description="qDrant collection name")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="text-embedding-3-small", description="OpenAI model name")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Chunking Configuration
    CHUNK_SIZE: int = Field(default=500, description="Size of text chunks")
    CHUNK_OVERLAP: int = Field(default=50, description="Overlap between chunks")
    
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
    
    @field_validator("CHUNK_SIZE", "CHUNK_OVERLAP")
    @classmethod
    def validate_positive_integer(cls, v):
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_prefix=""
    )

_settings_instance = None

def get_settings() -> Optional[Settings]:
    """Get the settings instance, creating it if necessary and if not in test environment."""
    global _settings_instance
    if _settings_instance is None and "PYTEST_CURRENT_TEST" not in os.environ:
        try:
            _settings_instance = Settings()
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to load settings: {str(e)}")
    return _settings_instance 