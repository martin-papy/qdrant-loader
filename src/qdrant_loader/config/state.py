"""State management configuration.

This module defines the configuration settings for state management,
including database path, table prefix, and connection pool settings.
"""

from typing import Dict, Any
from pathlib import Path
from pydantic import Field, field_validator, ValidationInfo
import os

from qdrant_loader.config.base import BaseConfig


class StateManagementConfig(BaseConfig):
    """Configuration for state management."""

    database_path: str = Field(..., description="Path to SQLite database file")
    table_prefix: str = Field(default="qdrant_loader_", description="Prefix for database tables")
    connection_pool: Dict[str, Any] = Field(
        default_factory=lambda: {"size": 5, "timeout": 30}, description="Connection pool settings"
    )

    @field_validator("database_path")
    def validate_database_path(cls, v: str, info: ValidationInfo) -> str:
        """Validate database path exists and is writable."""
        path = Path(v)
        if not path.parent.exists():
            raise ValueError(f"Database directory does not exist: {path.parent}")
        if not path.parent.is_dir():
            raise ValueError(f"Database path is not a directory: {path.parent}")
        if not os.access(path.parent, os.W_OK):
            raise ValueError(f"Database directory is not writable: {path.parent}")
        return str(path)

    @field_validator("table_prefix")
    def validate_table_prefix(cls, v: str, info: ValidationInfo) -> str:
        """Validate table prefix format."""
        if not v:
            raise ValueError("Table prefix cannot be empty")
        if not v.replace("_", "").isalnum():
            raise ValueError(
                "Table prefix can only contain alphanumeric characters and underscores"
            )
        return v

    @field_validator("connection_pool")
    def validate_connection_pool(cls, v: Dict[str, Any], info: ValidationInfo) -> Dict[str, Any]:
        """Validate connection pool settings."""
        if "size" not in v:
            raise ValueError("Connection pool must specify 'size'")
        if not isinstance(v["size"], int) or v["size"] < 1:
            raise ValueError("Connection pool size must be a positive integer")

        if "timeout" not in v:
            raise ValueError("Connection pool must specify 'timeout'")
        if not isinstance(v["timeout"], int) or v["timeout"] < 1:
            raise ValueError("Connection pool timeout must be a positive integer")

        return v
