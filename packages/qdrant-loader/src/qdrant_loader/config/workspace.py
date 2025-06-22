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
    config_path: Path | None  # For legacy single-file config
    config_dir: Path | None   # For new multi-file config directory
    env_path: Path | None
    logs_path: Path
    metrics_path: Path
    database_path: Path
    is_multi_file: bool       # Whether using new multi-file format

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

        # Validate configuration exists (either legacy or new format)
        if self.is_multi_file:
            if not self.config_dir or not self.config_dir.exists():
                raise ValueError(f"Config directory not found in workspace: {self.config_dir}")
            
            # Check for required core domain config files
            # Optional files (metadata-extraction.yaml, validation.yaml) are not required
            required_files = ["connectivity.yaml", "projects.yaml", "fine-tuning.yaml"]
            missing_files = []
            for file_name in required_files:
                if not (self.config_dir / file_name).exists():
                    missing_files.append(file_name)
            
            if missing_files:
                raise ValueError(
                    f"Missing required domain configuration files in {self.config_dir}: {', '.join(missing_files)}"
                )
                
            # Log optional files if they exist
            optional_files = ["metadata-extraction.yaml", "validation.yaml"]
            found_optional = []
            for file_name in optional_files:
                if (self.config_dir / file_name).exists():
                    found_optional.append(file_name)
            
            if found_optional:
                logger.debug(
                    "Found optional configuration files",
                    files=found_optional,
                    config_dir=str(self.config_dir)
                )
        else:
            # Legacy single-file mode
            if not self.config_path or not self.config_path.exists():
                raise ValueError(f"config.yaml not found in workspace: {self.config_path}")

        # Validate workspace is writable
        if not os.access(self.workspace_path, os.W_OK):
            raise ValueError(
                f"Cannot write to workspace directory: {self.workspace_path}"
            )

        logger.debug(
            "Workspace configuration validated", 
            workspace=str(self.workspace_path),
            is_multi_file=self.is_multi_file
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
    config_dir = workspace_path / "config"
    legacy_config_path = workspace_path / "config.yaml"
    
    # Check for new multi-file format first
    is_multi_file = False
    config_path = None
    config_dir_final = None
    
    if config_dir.exists() and config_dir.is_dir():
        # Check if all required core domain files exist
        # Optional files are not required for multi-file format detection
        required_files = ["connectivity.yaml", "projects.yaml", "fine-tuning.yaml"]
        all_files_exist = all((config_dir / file_name).exists() for file_name in required_files)
        
        if all_files_exist:
            is_multi_file = True
            config_dir_final = config_dir
            logger.debug("Detected multi-file configuration format", config_dir=str(config_dir))
        else:
            # Config directory exists but missing required files - check for legacy format
            if legacy_config_path.exists():
                config_path = legacy_config_path
                logger.debug("Detected legacy configuration format", config_path=str(legacy_config_path))
            else:
                # Neither format is complete
                missing_files = [f for f in required_files if not (config_dir / f).exists()]
                raise ValueError(
                    f"Incomplete configuration found. Config directory exists but missing required files: {', '.join(missing_files)}. "
                    f"Either complete the multi-file configuration or use legacy config.yaml format."
                )
    else:
        # No config directory, check for legacy format
        if legacy_config_path.exists():
            config_path = legacy_config_path
            logger.debug("Detected legacy configuration format", config_path=str(legacy_config_path))
        else:
            raise ValueError(
                f"No configuration found in workspace. Expected either:\n"
                f"- Multi-file format: {config_dir}/{{connectivity,projects,fine-tuning}}.yaml\n"
                f"- Legacy format: {legacy_config_path}"
            )

    # Determine .env file location based on configuration format
    if is_multi_file:
        # For multi-file format, .env should be in config directory
        env_path = config_dir / ".env"
        env_path_final = env_path if env_path.exists() else None
    else:
        # For legacy format, .env is in workspace root
        env_path = workspace_path / ".env"
        env_path_final = env_path if env_path.exists() else None

    # Define other workspace paths
    logs_path = workspace_path / "logs" / "qdrant-loader.log"
    metrics_path = workspace_path / "metrics"
    data_path = workspace_path / "data"
    database_path = data_path / "qdrant-loader.db"

    # Create workspace config
    workspace_config = WorkspaceConfig(
        workspace_path=workspace_path,
        config_path=config_path,
        config_dir=config_dir_final,
        env_path=env_path_final,
        logs_path=logs_path,
        metrics_path=metrics_path,
        database_path=database_path,
        is_multi_file=is_multi_file,
    )

    logger.debug("Workspace setup completed", workspace=str(workspace_path), is_multi_file=is_multi_file)
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
