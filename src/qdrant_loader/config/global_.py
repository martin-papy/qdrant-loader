"""Global configuration settings.

This module defines the global configuration settings that apply across the application,
including chunking, embedding, and logging configurations.
"""

from pydantic import Field, field_validator, ValidationInfo

from qdrant_loader.config.base import BaseConfig
from qdrant_loader.config.types import GlobalConfigDict
from qdrant_loader.config.chunking import ChunkingConfig
from qdrant_loader.config.embedding import EmbeddingConfig
from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.config.sources import SourcesConfig


class LoggingConfig(BaseConfig):
    """Configuration for logging."""

    level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(default="json", description="Log format (json or text)")
    file: str = Field(default="qdrant-loader.log", description="Path to log file")

    @field_validator("level")
    def validate_level(cls, v: str, info: ValidationInfo) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level. Must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator("format")
    def validate_format(cls, v: str, info: ValidationInfo) -> str:
        """Validate log format."""
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format. Must be one of: {', '.join(valid_formats)}")
        return v.lower()


class GlobalConfig(BaseConfig):
    """Global configuration settings."""

    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    state_management: StateManagementConfig = Field(
        default_factory=lambda: StateManagementConfig(database_path=":memory:"),
        description="State management configuration",
    )
    sources: SourcesConfig = Field(default_factory=SourcesConfig)

    def __init__(self, **data):
        """Initialize global configuration."""
        # If skip_validation is True, use in-memory database for state management
        skip_validation = data.pop("skip_validation", False)
        if skip_validation:
            data["state_management"] = {
                "database_path": ":memory:",
                "table_prefix": "qdrant_loader_",
                "connection_pool": {"size": 5, "timeout": 30},
            }
        super().__init__(**data)

    def to_dict(self) -> GlobalConfigDict:
        """Convert the configuration to a dictionary."""
        return {
            "chunking": {
                "chunk_size": self.chunking.chunk_size,
                "chunk_overlap": self.chunking.chunk_overlap,
            },
            "embedding": self.embedding.model_dump(),
            "logging": self.logging.model_dump(),
            "sources": self.sources.to_dict(),
        }
