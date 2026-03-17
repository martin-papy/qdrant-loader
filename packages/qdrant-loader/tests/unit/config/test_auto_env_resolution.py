"""Tests for auto environment variable resolution (_auto_resolve_env_vars) in Settings
and the default state management database path."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml
from qdrant_loader.config import Settings
from qdrant_loader.config.state import StateManagementConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_minimal_config(
    *,
    qdrant_url: str = "http://localhost:6333",
    qdrant_collection: str = "documents",
    qdrant_api_key=None,
    embedding_api_key=None,
) -> Path:
    """Write a minimal valid config YAML to a temp file and return its Path."""
    qdrant_section: dict = {"url": qdrant_url, "collection_name": qdrant_collection}
    if qdrant_api_key is not None:
        qdrant_section["api_key"] = qdrant_api_key

    embedding_section: dict = {"model": "text-embedding-3-small"}
    if embedding_api_key is not None:
        embedding_section["api_key"] = embedding_api_key

    config_data = {
        "global": {
            "qdrant": qdrant_section,
            "embedding": embedding_section,
        },
        "projects": {
            "default": {
                "display_name": "Default Project",
                "sources": {},
            }
        },
    }

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(config_data, tmp)
    tmp.close()
    return Path(tmp.name)


def _clean_env(*names: str) -> dict:
    """Return a copy of os.environ with the given keys removed."""
    env = dict(os.environ)
    for name in names:
        env.pop(name, None)
    return env


# ---------------------------------------------------------------------------
# Tests for _auto_resolve_env_vars
# ---------------------------------------------------------------------------


class TestAutoEnvResolution:
    """Tests for the _auto_resolve_env_vars method in Settings."""

    def test_openai_key_auto_fills_embedding_api_key(self, tmp_path):
        """OPENAI_API_KEY env var fills embedding.api_key when not set in config."""
        config_path = _write_minimal_config()
        try:
            clean = _clean_env("OPENAI_API_KEY")
            clean["OPENAI_API_KEY"] = "sk-auto-filled-key"
            with patch.dict(os.environ, clean, clear=True):
                settings = Settings.from_yaml(config_path, skip_validation=True)
            assert settings.global_config.embedding.api_key == "sk-auto-filled-key"
        finally:
            os.unlink(config_path)

    def test_openai_key_does_not_override_config_value(self, tmp_path):
        """If embedding.api_key is set in config, OPENAI_API_KEY does not override it."""
        config_path = _write_minimal_config(embedding_api_key="sk-from-config")
        try:
            clean = _clean_env("OPENAI_API_KEY")
            clean["OPENAI_API_KEY"] = "sk-from-env"
            with patch.dict(os.environ, clean, clear=True):
                settings = Settings.from_yaml(config_path, skip_validation=True)
            assert settings.global_config.embedding.api_key == "sk-from-config"
        finally:
            os.unlink(config_path)

    def test_qdrant_url_auto_fills_from_env(self, tmp_path):
        """QDRANT_URL env var fills qdrant.url when it still holds the default value."""
        # Config uses default url so env var should take over
        config_path = _write_minimal_config(qdrant_url="http://localhost:6333")
        try:
            clean = _clean_env("QDRANT_URL")
            clean["QDRANT_URL"] = "http://remote.qdrant.example.com:6333"
            with patch.dict(os.environ, clean, clear=True):
                settings = Settings.from_yaml(config_path, skip_validation=True)
            assert (
                settings.global_config.qdrant.url
                == "http://remote.qdrant.example.com:6333"
            )
        finally:
            os.unlink(config_path)

    def test_qdrant_url_does_not_override_config_value(self, tmp_path):
        """If qdrant.url is set to a non-default value in config, env var does not override."""
        config_path = _write_minimal_config(
            qdrant_url="https://my-qdrant.internal:6333"
        )
        try:
            clean = _clean_env("QDRANT_URL")
            clean["QDRANT_URL"] = "http://should-not-win.example.com"
            with patch.dict(os.environ, clean, clear=True):
                settings = Settings.from_yaml(config_path, skip_validation=True)
            assert (
                settings.global_config.qdrant.url == "https://my-qdrant.internal:6333"
            )
        finally:
            os.unlink(config_path)

    def test_qdrant_collection_auto_fills_from_env(self, tmp_path):
        """QDRANT_COLLECTION_NAME env var fills collection_name when it is still the default."""
        config_path = _write_minimal_config(qdrant_collection="documents")
        try:
            clean = _clean_env("QDRANT_COLLECTION_NAME")
            clean["QDRANT_COLLECTION_NAME"] = "my_custom_collection"
            with patch.dict(os.environ, clean, clear=True):
                settings = Settings.from_yaml(config_path, skip_validation=True)
            assert (
                settings.global_config.qdrant.collection_name == "my_custom_collection"
            )
        finally:
            os.unlink(config_path)

    def test_qdrant_api_key_auto_fills_from_env(self, tmp_path):
        """QDRANT_API_KEY env var fills api_key when not set in config."""
        config_path = _write_minimal_config()  # api_key not in config → None
        try:
            clean = _clean_env("QDRANT_API_KEY")
            clean["QDRANT_API_KEY"] = "super-secret-qdrant-key"
            with patch.dict(os.environ, clean, clear=True):
                settings = Settings.from_yaml(config_path, skip_validation=True)
            assert settings.global_config.qdrant.api_key == "super-secret-qdrant-key"
        finally:
            os.unlink(config_path)

    def test_no_env_vars_uses_defaults(self, tmp_path):
        """Without any relevant env vars, qdrant uses its built-in defaults."""
        config_path = _write_minimal_config()
        try:
            clean = _clean_env(
                "OPENAI_API_KEY",
                "QDRANT_URL",
                "QDRANT_API_KEY",
                "QDRANT_COLLECTION_NAME",
            )
            with (
                patch.dict(os.environ, clean, clear=True),
                patch("qdrant_loader.config.load_dotenv"),
            ):
                settings = Settings.from_yaml(config_path, skip_validation=True)
            assert settings.global_config.qdrant.url == "http://localhost:6333"
            assert settings.global_config.qdrant.collection_name == "documents"
            assert (
                settings.global_config.qdrant.api_key is None
            ), "qdrant.api_key should be None when no env vars are set"
            assert (
                settings.global_config.embedding.api_key is None
            ), "embedding.api_key should be None when no env vars are set"
        finally:
            os.unlink(config_path)


# ---------------------------------------------------------------------------
# Tests for StateManagementConfig default database path
# ---------------------------------------------------------------------------


class TestStateManagementDefaultDatabasePath:
    """Tests for the default database path in StateManagementConfig."""

    def test_state_management_default_database_path(self):
        """StateManagementConfig() defaults to './state.db', not ':memory:'."""
        config = StateManagementConfig()
        assert config.database_path == "./state.db"

    def test_state_management_explicit_memory_path(self):
        """StateManagementConfig accepts ':memory:' when set explicitly."""
        config = StateManagementConfig(database_path=":memory:")
        assert config.database_path == ":memory:"

    def test_state_management_custom_path(self, tmp_path):
        """StateManagementConfig accepts a custom writable file path."""
        db_path = str(tmp_path / "custom.db")
        config = StateManagementConfig(database_path=db_path)
        assert config.database_path == db_path
