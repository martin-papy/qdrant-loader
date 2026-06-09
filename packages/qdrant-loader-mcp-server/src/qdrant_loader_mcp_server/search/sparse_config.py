"""Yaml-loader wrapper that produces a shared :class:`SparseRuntimeConfig`.

The dataclass and the validation rules live in
``qdrant_loader_core.config``; this module's only job is to read the
MCP server's ``MCP_CONFIG`` yaml file and delegate.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from qdrant_loader_core.config import SparseRuntimeConfig

logger = logging.getLogger(__name__)


def _load_global_section(mcp_config_path: str | None) -> dict[str, Any]:
    """Read the ``global`` block from an MCP server yaml config file.

    Returns an empty dict on any I/O or parse failure — the config layer
    treats that as "no overrides" and falls back to defaults.
    """
    if not mcp_config_path:
        return {}
    path = Path(mcp_config_path)
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to parse MCP config at %s: %s", path, e)
        return {}
    if not isinstance(data, dict):
        return {}
    global_section = data.get("global")
    return global_section if isinstance(global_section, dict) else {}


def load_sparse_runtime_config(
    mcp_config_path: str | None = None,
) -> SparseRuntimeConfig:
    """Build a :class:`SparseRuntimeConfig` from the MCP server yaml."""
    global_section = _load_global_section(mcp_config_path or os.getenv("MCP_CONFIG"))
    return SparseRuntimeConfig.from_global_config(global_section)
