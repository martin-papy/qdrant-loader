from __future__ import annotations

from pathlib import Path

from click.exceptions import ClickException
from click.utils import echo

from qdrant_loader.cli.commands.config import run_show_config as _run_show_config
from qdrant_loader.cli.config_loader import setup_workspace as _setup_workspace_impl
from qdrant_loader.utils.logging import LoggingConfig


def run_config_command(
    workspace: Path | None, log_level: str, config: Path | None, env: Path | None
) -> None:
    """Implementation for the `config` CLI command."""
    try:
        # Maintain test expectation: log via workspace-logger as before
        workspace_config = _setup_workspace_impl(workspace) if workspace else None
        log_file = (
            str(workspace_config.logs_path) if workspace_config else "qdrant-loader.log"
        )
        if getattr(LoggingConfig, "reconfigure", None):  # type: ignore[attr-defined]
            if getattr(LoggingConfig, "_initialized", False):  # type: ignore[attr-defined]
                LoggingConfig.reconfigure(file=log_file)  # type: ignore[attr-defined]
            else:
                LoggingConfig.setup(level=log_level, format="console", file=log_file)
        else:
            import logging as _py_logging

            _py_logging.getLogger().handlers = []
            LoggingConfig.setup(level=log_level, format="console", file=log_file)

        echo("Current Configuration:")
        output = _run_show_config(workspace, config, env, log_level)
        echo(output)

    except Exception as e:
        LoggingConfig.get_logger(__name__).error("config_failed", error=str(e))
        raise ClickException(f"Failed to display configuration: {str(e)!s}") from e
