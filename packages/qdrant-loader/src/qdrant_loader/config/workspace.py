"""Workspace configuration management for QDrant Loader CLI."""

import os
from dataclasses import dataclass
from pathlib import Path

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class WorkspaceConfig:
    """Configuration for workspace mode."""

    workspace_path: Path
    config_path: Path
    env_path: Path | None
    logs_path: Path
    metrics_path: Path
    database_path: Path

    def __post_init__(self):
        """Validate workspace configuration after initialization."""
        # Ensure workspace path is absolute
        self.workspace_path = self.workspace_path.resolve()

        # Validate workspace directory exists
        if not self.workspace_path.exists():
            raise ValueError(
                f"Workspace directory does not exist: {self.workspace_path}"
            )

        if not self.workspace_path.is_dir():
            raise ValueError(
                f"Workspace path is not a directory: {self.workspace_path}"
            )

        # Validate config.yaml exists
        if not self.config_path.exists():
            raise ValueError(f"config.yaml not found in workspace: {self.config_path}")

        # Validate workspace is writable
        if not os.access(self.workspace_path, os.W_OK):
            raise ValueError(
                f"Cannot write to workspace directory: {self.workspace_path}"
            )

        logger.debug(
            "Workspace configuration validated", workspace=str(self.workspace_path)
        )


def setup_workspace(workspace_path: Path) -> WorkspaceConfig:
    """Setup and validate workspace configuration.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        WorkspaceConfig: Validated workspace configuration

    Raises:
        ValueError: If workspace validation fails
    """
    logger.debug("Setting up workspace", path=str(workspace_path))

    # Resolve to absolute path
    workspace_path = workspace_path.resolve()

    # Define workspace file paths
    config_path = workspace_path / "config.yaml"
    env_path = workspace_path / ".env"
    logs_path = workspace_path / "logs" / "qdrant-loader.log"
    metrics_path = workspace_path / "metrics"
    data_path = workspace_path / "data"
    database_path = data_path / "qdrant-loader.db"

    # Check if .env file exists (optional)
    env_path_final = env_path if env_path.exists() else None

    # Create workspace config
    workspace_config = WorkspaceConfig(
        workspace_path=workspace_path,
        config_path=config_path,
        env_path=env_path_final,
        logs_path=logs_path,
        metrics_path=metrics_path,
        database_path=database_path,
    )

    logger.debug("Workspace setup completed", workspace=str(workspace_path))
    return workspace_config


def validate_workspace(workspace_path: Path) -> bool:
    """Validate if a directory can be used as a workspace.

    Args:
        workspace_path: Path to validate

    Returns:
        bool: True if valid workspace, False otherwise
    """
    try:
        setup_workspace(workspace_path)
        return True
    except ValueError as e:
        logger.debug(
            "Workspace validation failed", path=str(workspace_path), error=str(e)
        )
        return False


def create_workspace_structure(workspace_path: Path) -> None:
    """Create the basic workspace directory structure.

    Args:
        workspace_path: Path to the workspace directory

    Raises:
        OSError: If directory creation fails
    """
    logger.debug("Creating workspace structure", path=str(workspace_path))

    # Create workspace directory if it doesn't exist
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    logs_dir = workspace_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    metrics_dir = workspace_path / "metrics"
    metrics_dir.mkdir(exist_ok=True)

    data_dir = workspace_path / "data"
    data_dir.mkdir(exist_ok=True)

    logger.debug("Workspace structure created", workspace=str(workspace_path))


def get_workspace_env_override(workspace_config: WorkspaceConfig) -> dict[str, str]:
    """Get environment variable overrides for workspace mode.

    Args:
        workspace_config: Workspace configuration

    Returns:
        dict: Environment variable overrides
    """
    overrides = {
        "STATE_DB_PATH": str(workspace_config.database_path),
    }

    logger.debug("Generated workspace environment overrides", overrides=overrides)
    return overrides


def validate_workspace_flags(
    workspace: Path | None, config: Path | None, env: Path | None
) -> None:
    """Validate that workspace flag is not used with conflicting flags.

    Args:
        workspace: Workspace path (if provided)
        config: Config path (if provided)
        env: Env path (if provided)

    Raises:
        ValueError: If conflicting flags are used
    """
    if workspace is not None:
        if config is not None:
            raise ValueError(
                "Cannot use --workspace with --config flag. Use either workspace mode or individual file flags."
            )

        if env is not None:
            raise ValueError(
                "Cannot use --workspace with --env flag. Use either workspace mode or individual file flags."
            )

        logger.debug("Workspace flag validation passed")
