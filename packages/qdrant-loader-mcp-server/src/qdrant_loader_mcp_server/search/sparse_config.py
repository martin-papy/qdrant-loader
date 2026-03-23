"""Runtime sparse/hybrid retrieval configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


@dataclass
class SparseRuntimeConfig:
    enabled: bool = True
    model: str = "bm25"
    dense_vector_name: str = "dense"
    sparse_vector_name: str = "sparse"
    use_qdrant_hybrid: bool = True
    auto_fallback: bool = True


def _parse_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def _load_llm_config_from_mcp_config(mcp_config_path: str | None) -> dict[str, Any]:
    if not mcp_config_path:
        return {}
    path = Path(mcp_config_path)
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    global_section = data.get("global") if isinstance(data, dict) else {}
    llm = (global_section or {}).get("llm") if isinstance(global_section, dict) else {}
    return llm if isinstance(llm, dict) else {}


def load_sparse_runtime_config(mcp_config_path: str | None = None) -> SparseRuntimeConfig:
    cfg = SparseRuntimeConfig()
    llm = _load_llm_config_from_mcp_config(mcp_config_path or os.getenv("MCP_CONFIG"))

    sparse_cfg: dict[str, Any] = {}
    retrieval_cfg: dict[str, Any] = {}
    if isinstance(llm.get("sparse"), dict):
        sparse_cfg.update(llm["sparse"])
    if isinstance(llm.get("retrieval"), dict):
        retrieval_cfg = llm["retrieval"]
        if isinstance(retrieval_cfg.get("sparse"), dict):
            sparse_cfg.update(retrieval_cfg["sparse"])

    cfg.enabled = _parse_bool(sparse_cfg.get("enabled"), cfg.enabled)
    cfg.model = str(sparse_cfg.get("model") or cfg.model)
    cfg.dense_vector_name = str(
        sparse_cfg.get("dense_vector_name") or cfg.dense_vector_name
    )
    cfg.sparse_vector_name = str(
        sparse_cfg.get("sparse_vector_name") or cfg.sparse_vector_name
    )
    cfg.auto_fallback = _parse_bool(sparse_cfg.get("auto_fallback"), cfg.auto_fallback)
    cfg.use_qdrant_hybrid = _parse_bool(
        retrieval_cfg.get("use_qdrant_hybrid"), cfg.use_qdrant_hybrid
    )

    cfg.enabled = _parse_bool(os.getenv("LLM_SPARSE_ENABLED"), cfg.enabled)
    cfg.model = str(os.getenv("LLM_SPARSE_MODEL") or cfg.model)
    cfg.dense_vector_name = str(
        os.getenv("LLM_DENSE_VECTOR_NAME") or cfg.dense_vector_name
    )
    cfg.sparse_vector_name = str(
        os.getenv("LLM_SPARSE_VECTOR_NAME") or cfg.sparse_vector_name
    )
    cfg.auto_fallback = _parse_bool(
        os.getenv("LLM_SPARSE_AUTO_FALLBACK"), cfg.auto_fallback
    )
    cfg.use_qdrant_hybrid = _parse_bool(
        os.getenv("SEARCH_USE_QDRANT_HYBRID"), cfg.use_qdrant_hybrid
    )
    return cfg
