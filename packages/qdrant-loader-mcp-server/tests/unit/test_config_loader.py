import pytest
from qdrant_loader_mcp_server.config_loader import (
    _substitute_env_vars,
    build_config_from_dict,
    load_config,
    load_file_config,
    redact_effective_config,
    resolve_config_path,
)


def test_resolve_config_path_env(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MCP_CONFIG", str(cfg))
    assert resolve_config_path(None) == cfg


def test_build_config_from_dict_minimal_global_llm(monkeypatch):
    # Clear env vars to ensure config dict values are used
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("LLM_CHAT_MODEL", raising=False)
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


def test_load_config_env_only(monkeypatch, tmp_path):
    # Change to a temporary directory to avoid finding config.yaml in the project root
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MCP_CONFIG", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    cfg, effective, used_file = load_config(None)
    assert not used_file
    assert cfg.openai.api_key == "secret"
    assert "derived" in effective


# ---------------------------------------------------------------------------
# Tests for _substitute_env_vars (Bug 1)
# ---------------------------------------------------------------------------


class TestSubstituteEnvVars:
    def test_substitute_single_var(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "hello")
        result = _substitute_env_vars("prefix_${MY_VAR}_suffix")
        assert result == "prefix_hello_suffix"

    def test_substitute_in_nested_dict(self, monkeypatch):
        monkeypatch.setenv("QDRANT_COLLECTION_NAME", "my_docs")
        data = {"global": {"qdrant": {"collection_name": "${QDRANT_COLLECTION_NAME}"}}}
        result = _substitute_env_vars(data)
        assert result["global"]["qdrant"]["collection_name"] == "my_docs"

    def test_substitute_in_list(self, monkeypatch):
        monkeypatch.setenv("VAR", "value")
        result = _substitute_env_vars(["${VAR}", "literal"])
        assert result == ["value", "literal"]

    def test_unset_var_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("UNDEFINED_VAR", raising=False)
        with pytest.raises(ValueError, match="UNDEFINED_VAR"):
            _substitute_env_vars("${UNDEFINED_VAR}")

    def test_bash_default_syntax_not_matched(self):
        """${VAR:-default} should NOT be matched — only standard env var names."""
        result = _substitute_env_vars("${VAR:-fallback}")
        # The regex won't match because of the ':-' chars, so string passes through unchanged
        assert result == "${VAR:-fallback}"

    def test_invalid_var_name_not_matched(self):
        """${123BAD} should NOT be matched — must start with letter or underscore."""
        result = _substitute_env_vars("${123BAD}")
        assert result == "${123BAD}"

    def test_no_template_passthrough(self):
        result = _substitute_env_vars({"key": "plain_value", "num": 42})
        assert result == {"key": "plain_value", "num": 42}

    def test_load_file_config_substitutes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_collection")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "global:\n  qdrant:\n    collection_name: ${QDRANT_COLLECTION_NAME}\n"
        )
        data = load_file_config(config_file)
        assert data["global"]["qdrant"]["collection_name"] == "test_collection"


# ---------------------------------------------------------------------------
# Tests for legacy embedding migration (Bug 2)
# ---------------------------------------------------------------------------


class TestLegacyEmbeddingMigration:
    def test_legacy_embedding_migrates_to_llm(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config_data = {
            "global": {
                "embedding": {
                    "model": "text-embedding-ada-002",
                    "vector_size": 1536,
                    "api_key": "sk-legacy",
                }
            }
        }
        cfg = build_config_from_dict(config_data)
        assert cfg.openai.model == "text-embedding-ada-002"
        assert cfg.openai.api_key == "sk-legacy"
        assert cfg.openai.vector_size == 1536

    def test_legacy_does_not_override_explicit_llm(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config_data = {
            "global": {
                "llm": {
                    "api_key": "sk-new",
                    "models": {"embeddings": "text-embedding-3-small"},
                },
                "embedding": {
                    "model": "text-embedding-ada-002",
                    "api_key": "sk-legacy",
                    "vector_size": 512,
                },
            }
        }
        cfg = build_config_from_dict(config_data)
        # Existing llm config takes precedence
        assert cfg.openai.api_key == "sk-new"
        assert cfg.openai.model == "text-embedding-3-small"

    def test_new_format_vector_size(self):
        config_data = {
            "global": {
                "llm": {
                    "api_key": "sk-xxx",
                    "models": {"embeddings": "text-embedding-3-small"},
                    "embeddings": {"vector_size": 1536},
                }
            }
        }
        cfg = build_config_from_dict(config_data)
        assert cfg.openai.vector_size == 1536


# ---------------------------------------------------------------------------
# Tests for ValueError propagation from load_config
# ---------------------------------------------------------------------------


class TestLoadConfigValueErrorFallback:
    def test_unresolved_env_var_falls_back_to_env_only(self, tmp_path, monkeypatch):
        """ValueError from _substitute_env_vars should trigger env-only fallback (existing business logic)."""
        monkeypatch.delenv("MISSING_VAR", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fallback")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "global:\n  qdrant:\n    url: ${MISSING_VAR}\n"
        )
        monkeypatch.setenv("MCP_CONFIG", str(config_file))
        cfg, effective, used_file = load_config(None)
        # Should NOT raise — falls back to env-only mode
        assert not used_file
        assert cfg.openai.api_key == "sk-fallback"
