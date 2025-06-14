"""State management configuration.

This module defines the configuration settings for state management,
including database path, table prefix, and connection pool settings.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationInfo, field_validator

from qdrant_loader.config.base import BaseConfig


class DatabaseDirectoryError(Exception):
    """Exception raised when database directory needs to be created."""

    def __init__(self, path: Path):
        self.path = path
        super().__init__(f"Database directory does not exist: {path}")


class IngestionStatus:
    """Enum-like class for ingestion status values."""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class StateManagementConfig(BaseConfig):
    """Configuration for state management."""

    database_path: str = Field(..., description="Path to SQLite database file")
    table_prefix: str = Field(
        default="qdrant_loader_", description="Prefix for database tables"
    )
    connection_pool: dict[str, Any] = Field(
        default_factory=lambda: {"size": 5, "timeout": 30},
        description="Connection pool settings",
    )

    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, v: str, info: ValidationInfo) -> str:
        """Validate database path."""
        # Expand environment variables, including $HOME
        path = Path(os.path.expanduser(os.path.expandvars(v)))
        parent_dir = path.parent

        if not parent_dir.exists():
            raise DatabaseDirectoryError(parent_dir)

        if not parent_dir.is_dir():
            raise ValueError("Database path is not a directory")

        if not os.access(parent_dir, os.W_OK):
            raise ValueError("Database directory is not writable")

        return v

    @field_validator("table_prefix")
    @classmethod
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
    @classmethod
    def validate_connection_pool(
        cls, v: dict[str, Any], info: ValidationInfo
    ) -> dict[str, Any]:
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

    def __init__(self, **data):
        """Initialize state management configuration."""
        # If database_path is not provided, use in-memory database
        if "database_path" not in data:
            data["database_path"] = ":memory:"
        super().__init__(**data)
