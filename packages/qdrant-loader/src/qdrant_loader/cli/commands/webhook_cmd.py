from __future__ import annotations

import logging
from pathlib import Path

import uvicorn

from click.exceptions import ClickException

from qdrant_loader.cli.config_loader import (
    load_config_with_workspace,
    setup_workspace,
)
from qdrant_loader.config.workspace import validate_workspace_flags
from qdrant_loader.utils.logging import LoggingConfig

from qdrant_loader.webhooks.server import app


def _setup_logging(log_level: str, workspace_config) -> None:
    log_file = (
        str(workspace_config.logs_path) if workspace_config else "qdrant-loader-webhook.log"
    )
    if getattr(LoggingConfig, "reconfigure", None):
        if getattr(LoggingConfig, "_initialized", False):
            LoggingConfig.reconfigure(file=log_file, level=log_level)
        else:
            LoggingConfig.setup(level=log_level, format="console", file=log_file)
    else:
        LoggingConfig.setup(level=log_level, format="console", file=log_file)


async def run_webhook_command(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    host: str,
    port: int,
    log_level: str,
) -> None:
    """Run the webhook server for connector events."""
    validate_workspace_flags(workspace, config, env)
    workspace_config = setup_workspace(workspace) if workspace else None

    _setup_logging(log_level, workspace_config)

    try:
        load_config_with_workspace(workspace_config, config, env)
    except Exception as exc:
        raise ClickException(f"Failed to load configuration: {exc}") from exc

    logger = LoggingConfig.get_logger(__name__)
    logger.info(
        "Starting webhook server",
        host=host,
        port=port,
        workspace=str(workspace_config.workspace_path) if workspace_config else None,
    )

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level.lower(),
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except Exception as exc:
        logger.error("Webhook server failed", error=str(exc))
        raise ClickException(f"Failed to start webhook server: {exc}") from exc
