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
        from qdrant_loader.cli.config_loader import (
            load_config_with_workspace as _load_config_with_workspace,
        )
        from qdrant_loader.cli.config_loader import (
            setup_workspace as _setup_workspace_impl,
        )
        from qdrant_loader.config import get_settings
        from qdrant_loader.config.workspace import validate_workspace_flags
        from qdrant_loader.utils.logging import LoggingConfig

        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = _setup_workspace_impl(workspace)

        # Setup/reconfigure logging once with workspace support
        log_file = (
            str(workspace_config.logs_path) if workspace_config else "qdrant-loader.log"
        )
        if getattr(LoggingConfig, "reconfigure", None):  # Core supports reconfigure
            if getattr(LoggingConfig, "_initialized", False):  # type: ignore[attr-defined]
                LoggingConfig.reconfigure(file=log_file)  # type: ignore[attr-defined]
            else:
                LoggingConfig.setup(level=log_level, format="console", file=log_file)
        else:
            # Compatibility path when running with an older core: clear root handlers
            # to avoid duplicates, then perform a full setup once.
            import logging as _py_logging

            _py_logging.getLogger().handlers = []
            LoggingConfig.setup(level=log_level, format="console", file=log_file)

        # Emit a single set of workspace-related info logs (no duplicates)
        if workspace_config:
            logger = LoggingConfig.get_logger(__name__)
            logger.info(
                "Using workspace", workspace=str(workspace_config.workspace_path)
            )
            if getattr(workspace_config, "env_path", None):
                logger.info(
                    "Environment file found", env_path=str(workspace_config.env_path)
                )
            if getattr(workspace_config, "config_path", None):
                logger.info(
                    "Config file found", config_path=str(workspace_config.config_path)
                )

        # Load configuration (skip validation to avoid directory prompts)
        _load_config_with_workspace(workspace_config, config, env, skip_validation=True)
        settings = get_settings()
        if settings is None:
            raise ClickException("Settings not available")

        # Redact sensitive values before dumping to JSON
        def _redact_secrets(value):
            """Recursively redact sensitive keys within nested structures.

            Keys are compared case-insensitively and redacted if their name contains
            any common secret-like token.
            """
            sensitive_tokens = {
                "password",
                "secret",
                "api_key",
                "token",
                "key",
                "credentials",
                "access_token",
                "private_key",
                "client_secret",
            }

            mask = "****"

            if isinstance(value, dict):
                redacted: dict = {}
                for k, v in value.items():
                    key_lc = str(k).lower()
                    if any(token in key_lc for token in sensitive_tokens):
                        redacted[k] = mask
                    else:
                        redacted[k] = _redact_secrets(v)
                return redacted
            if isinstance(value, list):
                return [_redact_secrets(item) for item in value]
            # Primitive or unknown types are returned as-is
            return value

        config_dict = settings.model_dump(mode="json")
        safe_config = _redact_secrets(config_dict)
        return json.dumps(safe_config, indent=2, ensure_ascii=False)
    except ClickException:
        raise
    except Exception as e:
        raise ClickException(f"Failed to display configuration: {str(e)!s}") from e
