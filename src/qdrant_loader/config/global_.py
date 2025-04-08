"""Global configuration settings.

This module defines the global configuration settings that apply across the application,
including chunking, embedding, and logging configurations.
"""

from typing import Dict, Any, List
from pydantic import Field, field_validator, ValidationInfo

from .base import BaseConfig
from .types import GlobalConfigDict
from .chunking import ChunkingConfig
from .embedding import EmbeddingConfig


class LoggingConfig(BaseConfig):
    """Configuration for logging."""
    level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    format: str = Field(default="json", description="Log format (json or text)")
    file: str = Field(default="qdrant-loader.log", description="Path to log file")

    @field_validator('level')
    def validate_level(cls, v: str, info: ValidationInfo) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level. Must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator('format')
    def validate_format(cls, v: str, info: ValidationInfo) -> str:
        """Validate log format."""
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format. Must be one of: {', '.join(valid_formats)}")
        return v.lower()


class GlobalConfig(BaseConfig):
    """Global configuration for all sources."""
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def to_dict(self) -> GlobalConfigDict:
        """Convert the configuration to a dictionary."""
        return {
            "chunking": {
                "size": self.chunking.chunk_size,
                "overlap": self.chunking.chunk_overlap
            },
            "embedding": self.embedding.model_dump(),
            "logging": self.logging.model_dump()
        } 