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
        # Handle in-memory database
        if v in (":memory:", "sqlite:///:memory:"):
            return v

        # Handle SQLite URLs
        if v.startswith("sqlite://"):
            # For SQLite URLs, skip file path validation since they might be
            # in-memory or use special formats
            return v

        # For file paths, perform basic validation but allow directory creation
        try:
            # Expand environment variables, including $HOME
            expanded_path = os.path.expanduser(os.path.expandvars(v))
            path = Path(expanded_path)

            # Convert to absolute path for consistent handling
            if not path.is_absolute():
                path = path.resolve()

            # For absolute paths, use them as-is
            parent_dir = path.parent

            # Check if parent directory exists
            if not parent_dir.exists():
                # Don't fail here - let StateManager handle directory creation
                # Just validate that the path structure is reasonable
                try:
                    # Test if the path is valid by trying to resolve it
                    # Don't actually create the directory here
                    parent_dir.resolve()

                    # Basic validation: ensure the path is reasonable
                    # Note: We removed the arbitrary depth limit as it was too restrictive
                    # for legitimate use cases like nested project structures and Windows paths

                except OSError as e:
                    raise ValueError(
                        f"Invalid database path - cannot resolve directory {parent_dir}: {e}"
                    )
            else:
                # Directory exists, check if it's actually a directory and writable
                if not parent_dir.is_dir():
                    raise ValueError(
                        f"Database directory path is not a directory: {parent_dir}"
                    )

                if not os.access(str(parent_dir), os.W_OK):
                    raise ValueError(
                        f"Database directory is not writable: {parent_dir}"
                    )

        except Exception as e:
            # If any validation fails, still allow the path through
            # StateManager will provide better error handling
            if isinstance(e, ValueError):
                raise  # Re-raise validation errors
            # For other exceptions, just log and allow the path
            pass

        # Return the original value to preserve any environment variables
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
