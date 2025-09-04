"""File-based configuration loader for the MCP server.

Precedence:
- CLI --config
- MCP_CONFIG environment variable
- ./config.yaml
- ~/.config/qdrant-loader/config.yaml
- /etc/qdrant-loader/config.yaml

Environment variables overlay values from file. CLI flags override env.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .config import Config, OpenAIConfig, QdrantConfig, SearchConfig
from .utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def _first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p and p.exists() and p.is_file():
            return p
    return None


def resolve_config_path(cli_config: Path | None) -> Path | None:
    if cli_config:
        return cli_config
    env_cfg = os.getenv("MCP_CONFIG")
    if env_cfg:
        p = Path(env_cfg).expanduser()
        if p.exists():
            return p
    candidates = [
        Path.cwd() / "config.yaml",
        Path.home() / ".config" / "qdrant-loader" / "config.yaml",
        Path("/etc/qdrant-loader/config.yaml"),
    ]
    return _first_existing(candidates)


def _get_section(config_data: dict[str, Any], name: str) -> dict[str, Any]:
    # Only support "global" root going forward
    return config_data.get(name, {}) or {}


def _overlay_env_llm(llm: dict[str, Any]) -> None:
    # LLM env overrides
    if os.getenv("LLM_PROVIDER"):
        llm.setdefault("provider", os.getenv("LLM_PROVIDER"))
        llm["provider"] = os.getenv("LLM_PROVIDER")
    if os.getenv("LLM_BASE_URL"):
        llm["base_url"] = os.getenv("LLM_BASE_URL")
    if os.getenv("LLM_API_KEY"):
        llm["api_key"] = os.getenv("LLM_API_KEY")
    # models
    models = dict(llm.get("models") or {})
    if os.getenv("LLM_EMBEDDING_MODEL"):
        models["embeddings"] = os.getenv("LLM_EMBEDDING_MODEL")
    if os.getenv("LLM_CHAT_MODEL"):
        models["chat"] = os.getenv("LLM_CHAT_MODEL")
    if models:
        llm["models"] = models


def _overlay_env_qdrant(qdrant: dict[str, Any]) -> None:
    if os.getenv("QDRANT_URL"):
        qdrant["url"] = os.getenv("QDRANT_URL")
    if os.getenv("QDRANT_API_KEY"):
        qdrant["api_key"] = os.getenv("QDRANT_API_KEY")
    if os.getenv("QDRANT_COLLECTION_NAME"):
        qdrant["collection_name"] = os.getenv("QDRANT_COLLECTION_NAME")


def _overlay_env_search(search: dict[str, Any]) -> None:
    # Only a subset for Phase 0; SearchConfig has its own env fallbacks as well
    if os.getenv("SEARCH_CONFLICT_USE_LLM"):
        raw = os.getenv("SEARCH_CONFLICT_USE_LLM", "true").strip().lower()
        search["conflict_use_llm"] = raw in {"1", "true", "t", "yes", "y", "on"}
    if os.getenv("SEARCH_CONFLICT_LLM_MODEL"):
        search["conflict_llm_model"] = os.getenv("SEARCH_CONFLICT_LLM_MODEL")


def load_file_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_config_from_dict(config_data: dict[str, Any]) -> Config:
    global_data = _get_section(config_data, "global")
    llm = dict(global_data.get("llm") or {})
    qdrant = dict(global_data.get("qdrant") or {})
    search = dict(config_data.get("search") or {})

    # Deprecation: detect legacy blocks and log a warning once
    legacy_embedding = global_data.get("embedding")
    legacy_markit = (
        (config_data.get("file_conversion") or {}).get("markitdown")
        if isinstance(config_data.get("file_conversion"), dict)
        else None
    )
    try:
        if legacy_embedding or legacy_markit:
            logger.warning(
                "Legacy configuration fields detected; please migrate to global.llm",
                legacy_embedding=bool(legacy_embedding),
                legacy_markitdown=bool(legacy_markit),
            )
    except Exception:
        pass

    # Apply environment overrides
    _overlay_env_llm(llm)
    _overlay_env_qdrant(qdrant)
    _overlay_env_search(search)

    # Derive OpenAIConfig for now (Phase 0); will be replaced by core LLM provider later
    api_key = llm.get("api_key") or os.getenv("OPENAI_API_KEY")
    models = dict(llm.get("models") or {})
    embedding_model = (
        models.get("embeddings")
        or os.getenv("LLM_EMBEDDING_MODEL")
        or "text-embedding-3-small"
    )
    chat_model = models.get("chat") or os.getenv("LLM_CHAT_MODEL") or "gpt-3.5-turbo"

    cfg = Config(
        qdrant=QdrantConfig(**qdrant) if qdrant else QdrantConfig(),
        openai=OpenAIConfig(
            api_key=api_key, model=embedding_model, chat_model=chat_model
        ),
        search=SearchConfig(**search) if search else SearchConfig(),
    )
    return cfg


def redact_effective_config(effective: dict[str, Any]) -> dict[str, Any]:
    def _redact(obj: Any) -> Any:
        if isinstance(obj, dict):
            redacted = {}
            for k, v in obj.items():
                if k in {"api_key", "Authorization"} and isinstance(v, str) and v:
                    redacted[k] = "***REDACTED***"
                else:
                    redacted[k] = _redact(v)
            return redacted
        if isinstance(obj, list):
            return [_redact(i) for i in obj]
        return obj

    return _redact(effective)


def load_config(cli_config: Path | None) -> tuple[Config, dict[str, Any], bool]:
    """Load effective configuration.

    Returns (config_obj, effective_dict, used_file: bool)
    """
    config_path = resolve_config_path(cli_config)
    used_file = False
    if config_path:
        try:
            data = load_file_config(config_path)
            cfg = build_config_from_dict(data)
            used_file = True
            # Effective dict for printing (merge file data with derived)
            effective = {
                "global": {
                    "llm": data.get("global", {}).get("llm"),
                    "qdrant": data.get("global", {}).get("qdrant"),
                },
                "search": data.get("search"),
                "derived": {
                    "openai": {
                        "model": cfg.openai.model,
                        "chat_model": cfg.openai.chat_model,
                        "api_key": cfg.openai.api_key,
                    }
                },
            }
            return cfg, effective, used_file
        except Exception as e:
            logger.warning(
                "Failed to load config file; falling back to env-only", error=str(e)
            )

    # Fallback to legacy env-only mode (deprecated)
    cfg = Config()
    effective = {
        "global": {
            "llm": {
                "provider": os.getenv("LLM_PROVIDER"),
                "base_url": os.getenv("LLM_BASE_URL"),
                "api_key": os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
                "models": {
                    "embeddings": os.getenv("LLM_EMBEDDING_MODEL"),
                    "chat": os.getenv("LLM_CHAT_MODEL"),
                },
            },
            "qdrant": {
                "url": os.getenv("QDRANT_URL"),
                "api_key": os.getenv("QDRANT_API_KEY"),
                "collection_name": os.getenv("QDRANT_COLLECTION_NAME"),
            },
        },
        "search": None,
        "derived": {
            "openai": {
                "model": cfg.openai.model,
                "chat_model": cfg.openai.chat_model,
                "api_key": cfg.openai.api_key,
            }
        },
        "warning": "Using legacy env-only mode; providing a config file is recommended and will be required in a future release.",
    }
    try:
        logger.warning(
            "Running in legacy env-only mode; provide --config or MCP_CONFIG file",
        )
    except Exception:
        pass
    return cfg, effective, used_file
