from __future__ import annotations

import json
from pathlib import Path

from click.exceptions import ClickException


def run_show_config(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    log_level: str,
) -> str:
    """Load configuration and return a JSON string representation.

    This function is a command helper used by the CLI wrapper to display configuration.
    It performs validation, optional workspace setup, logging setup, and settings loading.
    """
    try:
        from qdrant_loader.config.workspace import validate_workspace_flags
        from qdrant_loader.cli.config_loader import (
            setup_workspace as _setup_workspace_impl,
            load_config_with_workspace as _load_config_with_workspace,
        )
        from qdrant_loader.utils.logging import LoggingConfig
        from qdrant_loader.config import get_settings

        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = _setup_workspace_impl(workspace)

        # Setup logging with workspace support
        log_file = (
            str(workspace_config.logs_path) if workspace_config else "qdrant-loader.log"
        )
        LoggingConfig.setup(level=log_level, format="console", file=log_file)

        # Load configuration (skip validation to avoid directory prompts)
        _load_config_with_workspace(workspace_config, config, env, skip_validation=True)
        settings = get_settings()
        if settings is None:
            raise ClickException("Settings not available")

        return json.dumps(settings.model_dump(mode="json"), indent=2)
    except ClickException:
        raise
    except Exception as e:
        raise ClickException(f"Failed to display configuration: {str(e)!s}") from e


