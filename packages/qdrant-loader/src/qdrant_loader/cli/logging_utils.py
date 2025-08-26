from __future__ import annotations

from logging import Logger
from typing import Any

_logger = None


def get_logger() -> Logger:
    global _logger
    if _logger is None:
        from qdrant_loader.utils.logging import LoggingConfig

        _logger = LoggingConfig.get_logger(__name__)
    return _logger


def setup_logging(log_level: str, workspace_config: Any | None = None) -> None:
    try:
        from qdrant_loader.utils.logging import LoggingConfig

        log_format = "console"
        if workspace_config:
            log_file = str(workspace_config.logs_path)
        else:
            log_file = "qdrant-loader.log"

        LoggingConfig.setup(level=log_level, format=log_format, file=log_file)

        global _logger
        _logger = LoggingConfig.get_logger(__name__)
    except Exception as e:  # pragma: no cover - delegated to CLI error handler
        from click.exceptions import ClickException

        raise ClickException(f"Failed to setup logging: {str(e)!s}") from e


def check_for_updates() -> None:
    try:
        from qdrant_loader.utils.version_check import check_version_async

        current_version = _get_version()
        check_version_async(current_version, silent=False)
    except Exception:
        # ignore failures
        pass


def _get_version() -> str:
    try:
        from importlib.metadata import version

        return version("qdrant-loader")
    except ImportError:
        return "unknown"
    except Exception:
        return "unknown"
