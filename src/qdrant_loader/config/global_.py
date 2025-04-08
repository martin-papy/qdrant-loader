"""Global configuration settings.

This module defines the global configuration settings that apply across the application,
including chunking, embedding, and logging configurations.
"""

from typing import Dict, Any, List
from pydantic import Field, validator

from .base import BaseConfig
from .types import GlobalConfigDict


class ChunkingConfig(BaseConfig):
    """Configuration for text chunking."""
    size: int = Field(default=500, description="Size of each chunk in characters")
    overlap: int = Field(default=50, description="Overlap between chunks in characters")

    @validator('overlap')
    def validate_overlap(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate that overlap is less than chunk size."""
        if 'size' in values and v >= values['size']:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v


class EmbeddingConfig(BaseConfig):
    """Configuration for text embedding."""
    model: str = Field(default="text-embedding-3-small", description="Name of the embedding model to use")
    batch_size: int = Field(default=100, description="Number of texts to process in each batch")


class LoggingConfig(BaseConfig):
    """Configuration for logging."""
    level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    format: str = Field(default="json", description="Log format (json or text)")
    file: str = Field(default="qdrant-loader.log", description="Path to log file")

    @validator('level')
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level. Must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @validator('format')
    def validate_format(cls, v: str) -> str:
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
            "chunking": self.chunking.dict(),
            "embedding": self.embedding.dict(),
            "logging": self.logging.dict()
        } 