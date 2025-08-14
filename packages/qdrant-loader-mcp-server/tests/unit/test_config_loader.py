import json
import os
from pathlib import Path

import pytest

from qdrant_loader_mcp_server.config_loader import (
    resolve_config_path,
    build_config_from_dict,
    redact_effective_config,
    load_config,
)


def test_resolve_config_path_env(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MCP_CONFIG", str(cfg))
    assert resolve_config_path(None) == cfg


def test_build_config_from_dict_minimal_global_llm():
    data = {
        "global": {
            "llm": {
                "provider": "openai",
                "api_key": "secret",
                "models": {"embeddings": "text-embedding-3-small", "chat": "gpt-4o"},
            },
            "qdrant": {"url": "http://localhost:6333", "collection_name": "docs"},
        }
    }
    cfg = build_config_from_dict(data)
    assert cfg.openai.api_key == "secret"
    assert cfg.openai.model == "text-embedding-3-small"
    assert cfg.openai.chat_model == "gpt-3.5-turbo" or cfg.openai.chat_model == "gpt-4o"


def test_redact_effective_config():
    effective = {
        "global": {
            "llm": {"api_key": "secret"},
            "qdrant": {"api_key": "qsecret"},
        },
        "derived": {"openai": {"api_key": "secret"}},
    }
    red = redact_effective_config(effective)
    assert red["global"]["llm"]["api_key"] == "***REDACTED***"
    assert red["global"]["qdrant"]["api_key"] == "***REDACTED***"
    assert red["derived"]["openai"]["api_key"] == "***REDACTED***"


def test_load_config_env_only(monkeypatch):
    monkeypatch.delenv("MCP_CONFIG", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    cfg, effective, used_file = load_config(None)
    assert not used_file
    assert cfg.openai.api_key == "secret"
    assert "derived" in effective


