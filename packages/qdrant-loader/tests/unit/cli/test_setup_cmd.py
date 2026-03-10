"""Unit tests for the setup wizard CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import call, patch

import pytest
import yaml

from qdrant_loader.cli.commands.setup_cmd import (
    _collect_git_config,
    _collect_localfile_config,
    _write_config_file_multi,
    _write_env_file,
    run_setup_wizard,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_env(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, ignoring blank lines and comments."""
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value
    return result


# ---------------------------------------------------------------------------
# run_setup_wizard integration-style tests (all I/O mocked)
# ---------------------------------------------------------------------------


class TestRunSetupWizardCreatesFiles:
    """Verify that run_setup_wizard writes both config.yaml and .env."""

    def test_run_setup_wizard_creates_files(self, tmp_path: Path) -> None:
        """Mock all prompts for a single git source and verify output files exist."""
        prompt_side_effects = [
            # Step 1 – core settings
            "sk-test-key",           # OpenAI API Key
            "http://localhost:6333", # Qdrant URL (default)
            "",                      # Qdrant API Key (empty)
            "documents",             # Collection name (default)
            # Step 2 – source type
            "git",
            # Step 3 – source name
            "my-git",
            # _collect_git_config
            "https://github.com/org/repo.git",  # url
            "main",                              # branch
            "",                                  # token (empty)
            "*.md,*.txt",                        # file types
        ]
        confirm_side_effects = [
            False,  # "Add another source?" -> no
        ]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        assert (tmp_path / "config.yaml").exists(), "config.yaml was not created"
        assert (tmp_path / ".env").exists(), ".env was not created"

    def test_run_setup_wizard_git_source(self, tmp_path: Path) -> None:
        """Test that git source is written correctly into config.yaml."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "git",
            "my-git",
            "https://github.com/org/repo.git",
            "develop",
            "",
            "*.md,*.rst",
        ]
        confirm_side_effects = [False]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        git_sources = config["sources"]["git"]
        assert "my-git" in git_sources
        src = git_sources["my-git"]
        assert src["base_url"] == "https://github.com/org/repo.git"
        assert src["branch"] == "develop"
        assert src["file_types"] == ["*.md", "*.rst"]
        assert "token" not in src  # no token provided

    def test_run_setup_wizard_confluence_source(self, tmp_path: Path) -> None:
        """Test that confluence source config and extra env vars are written."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "confluence",
            "my-confluence",
            "https://mycompany.atlassian.net/wiki",
            "DOCS",
            "user@example.com",
            "secret-confluence-token",
        ]
        confirm_side_effects = [False]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        src = config["sources"]["confluence"]["my-confluence"]
        assert src["base_url"] == "https://mycompany.atlassian.net/wiki"
        assert src["space_key"] == "DOCS"
        assert src["token"] == "${CONFLUENCE_TOKEN}"
        assert src["email"] == "${CONFLUENCE_EMAIL}"

        env = _read_env(tmp_path / ".env")
        assert env["CONFLUENCE_TOKEN"] == "secret-confluence-token"
        assert env["CONFLUENCE_EMAIL"] == "user@example.com"

    def test_run_setup_wizard_jira_source(self, tmp_path: Path) -> None:
        """Test that jira source config and extra env vars are written."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "jira",
            "my-jira",
            "https://mycompany.atlassian.net",
            "PROJ",
            "jira@example.com",
            "secret-jira-token",
        ]
        confirm_side_effects = [False]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        src = config["sources"]["jira"]["my-jira"]
        assert src["base_url"] == "https://mycompany.atlassian.net"
        assert src["project_key"] == "PROJ"
        assert src["token"] == "${JIRA_TOKEN}"
        assert src["email"] == "${JIRA_EMAIL}"

        env = _read_env(tmp_path / ".env")
        assert env["JIRA_TOKEN"] == "secret-jira-token"
        assert env["JIRA_EMAIL"] == "jira@example.com"

    def test_run_setup_wizard_publicdocs_source(self, tmp_path: Path) -> None:
        """Test that publicdocs source config is written correctly."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "publicdocs",
            "my-publicdocs",
            "https://docs.example.com/",
            "latest",
            "html",
        ]
        confirm_side_effects = [False]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        src = config["sources"]["publicdocs"]["my-publicdocs"]
        assert src["base_url"] == "https://docs.example.com/"
        assert src["version"] == "latest"
        assert src["content_type"] == "html"

    def test_run_setup_wizard_localfile_source(self, tmp_path: Path) -> None:
        """Test that localfile source gets the file:// prefix applied."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "localfile",
            "my-localfile",
            "/home/user/docs",  # no file:// prefix
            "*.md,*.txt",
        ]
        confirm_side_effects = [False]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        src = config["sources"]["localfile"]["my-localfile"]
        assert src["base_url"] == "file:///home/user/docs"

    def test_run_setup_wizard_multiple_sources(self, tmp_path: Path) -> None:
        """Test adding multiple sources in one wizard run."""
        prompt_side_effects = [
            # Core settings
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            # First source: git
            "git",
            "repo-one",
            "https://github.com/org/repo.git",
            "main",
            "",
            "*.md",
            # Second source: localfile
            "localfile",
            "local-docs",
            "file:///data/docs",
            "*.txt",
        ]
        confirm_side_effects = [
            True,   # "Add another source?" -> yes
            False,  # "Add another source?" -> no
        ]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert "git" in config["sources"]
        assert "localfile" in config["sources"]
        assert "repo-one" in config["sources"]["git"]
        assert "local-docs" in config["sources"]["localfile"]

    def test_run_setup_wizard_cancelled_on_overwrite(self, tmp_path: Path) -> None:
        """Test that setup exits without writing when user declines overwrite."""
        # Pre-create config.yaml so the overwrite prompt is triggered.
        config_path = tmp_path / "config.yaml"
        config_path.write_text("existing: true\n", encoding="utf-8")

        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "git",
            "my-git",
            "https://github.com/org/repo.git",
            "main",
            "",
            "*.md",
        ]
        confirm_side_effects = [
            False,  # "Add another source?" -> no
            False,  # "config.yaml already exists. Overwrite?" -> no (cancel)
        ]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        # The original file must be untouched.
        assert config_path.read_text(encoding="utf-8") == "existing: true\n"
        # .env must NOT have been created.
        assert not (tmp_path / ".env").exists()


# ---------------------------------------------------------------------------
# _write_env_file unit tests
# ---------------------------------------------------------------------------


class TestWriteEnvFile:
    """Tests for the _write_env_file helper."""

    def test_write_env_file_minimal(self, tmp_path: Path) -> None:
        """Only OPENAI_API_KEY is written when defaults are used."""
        env_path = tmp_path / ".env"
        _write_env_file(
            env_path,
            openai_key="sk-minimal",
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="documents",
        )

        env = _read_env(env_path)
        assert env == {"OPENAI_API_KEY": "sk-minimal"}

    def test_write_env_file_with_extras(self, tmp_path: Path) -> None:
        """All non-default values and extra_vars are written."""
        env_path = tmp_path / ".env"
        _write_env_file(
            env_path,
            openai_key="sk-full",
            qdrant_url="https://cloud.qdrant.io",
            qdrant_api_key="qdrant-secret",
            collection_name="my-docs",
            extra_vars={
                "CONFLUENCE_TOKEN": "conf-tok",
                "CONFLUENCE_EMAIL": "user@co.com",
            },
        )

        env = _read_env(env_path)
        assert env["OPENAI_API_KEY"] == "sk-full"
        assert env["QDRANT_URL"] == "https://cloud.qdrant.io"
        assert env["QDRANT_API_KEY"] == "qdrant-secret"
        assert env["QDRANT_COLLECTION_NAME"] == "my-docs"
        assert env["CONFLUENCE_TOKEN"] == "conf-tok"
        assert env["CONFLUENCE_EMAIL"] == "user@co.com"

    def test_write_env_file_default_url_not_written(self, tmp_path: Path) -> None:
        """Default Qdrant URL must not appear in the .env file."""
        env_path = tmp_path / ".env"
        _write_env_file(
            env_path,
            openai_key="sk-x",
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="documents",
        )

        env = _read_env(env_path)
        assert "QDRANT_URL" not in env
        assert "QDRANT_API_KEY" not in env
        assert "QDRANT_COLLECTION_NAME" not in env

    def test_write_env_file_ends_with_newline(self, tmp_path: Path) -> None:
        """The generated .env must end with a trailing newline."""
        env_path = tmp_path / ".env"
        _write_env_file(
            env_path,
            openai_key="sk-nl",
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="documents",
        )

        content = env_path.read_text(encoding="utf-8")
        assert content.endswith("\n")


# ---------------------------------------------------------------------------
# _write_config_file_multi unit tests
# ---------------------------------------------------------------------------


class TestWriteConfigFileMulti:
    """Tests for the _write_config_file_multi helper."""

    def test_write_config_file_multi(self, tmp_path: Path) -> None:
        """Verify YAML output structure matches input sources dict."""
        config_path = tmp_path / "config.yaml"
        sources = {
            "git": {
                "my-repo": {
                    "base_url": "https://github.com/org/repo.git",
                    "branch": "main",
                    "file_types": ["*.md"],
                }
            },
            "localfile": {
                "my-files": {
                    "base_url": "file:///data",
                    "file_types": ["*.txt"],
                }
            },
        }

        _write_config_file_multi(config_path, sources=sources)

        parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert parsed["sources"]["git"]["my-repo"]["base_url"] == "https://github.com/org/repo.git"
        assert parsed["sources"]["localfile"]["my-files"]["base_url"] == "file:///data"

    def test_write_config_file_has_header_comment(self, tmp_path: Path) -> None:
        """Generated config.yaml must start with the generator comment."""
        config_path = tmp_path / "config.yaml"
        _write_config_file_multi(config_path, sources={"git": {}})

        raw = config_path.read_text(encoding="utf-8")
        assert raw.startswith("# Generated by qdrant-loader setup")

    def test_write_config_file_empty_sources(self, tmp_path: Path) -> None:
        """Empty sources dict produces a valid YAML file with sources key."""
        config_path = tmp_path / "config.yaml"
        _write_config_file_multi(config_path, sources={})

        parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert "sources" in parsed
        assert parsed["sources"] == {}


# ---------------------------------------------------------------------------
# _collect_git_config unit tests
# ---------------------------------------------------------------------------


class TestCollectGitConfig:
    """Tests for the _collect_git_config helper."""

    def test_collect_git_config_with_token(self) -> None:
        """Token should map to ${REPO_TOKEN} in config and store real value in env."""
        prompt_side_effects = [
            "https://github.com/org/repo.git",
            "main",
            "my-secret-token",
            "*.md,*.txt",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, extra_env = _collect_git_config()

        assert config["token"] == "${REPO_TOKEN}"
        assert extra_env["REPO_TOKEN"] == "my-secret-token"
        assert config["base_url"] == "https://github.com/org/repo.git"
        assert config["branch"] == "main"
        assert config["file_types"] == ["*.md", "*.txt"]

    def test_collect_git_config_no_token(self) -> None:
        """When token is empty, no token entry should appear in config or env."""
        prompt_side_effects = [
            "https://github.com/org/public-repo.git",
            "main",
            "",
            "*.md",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, extra_env = _collect_git_config()

        assert "token" not in config
        assert extra_env == {}


# ---------------------------------------------------------------------------
# _collect_localfile_config unit tests
# ---------------------------------------------------------------------------


class TestCollectLocalfileConfig:
    """Tests for the _collect_localfile_config helper."""

    def test_collect_localfile_adds_file_prefix(self) -> None:
        """Paths without file:// prefix must have it prepended."""
        prompt_side_effects = [
            "/home/user/docs",
            "*.md,*.rst",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, extra_env = _collect_localfile_config()

        assert config["base_url"] == "file:///home/user/docs"
        assert extra_env == {}

    def test_collect_localfile_preserves_existing_prefix(self) -> None:
        """Paths already starting with file:// must not be double-prefixed."""
        prompt_side_effects = [
            "file:///data/docs",
            "*.txt",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, extra_env = _collect_localfile_config()

        assert config["base_url"] == "file:///data/docs"

    def test_collect_localfile_parses_file_types(self) -> None:
        """Comma-separated file types must be split into a list."""
        prompt_side_effects = [
            "/data",
            "*.md, *.txt, *.py",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, _ = _collect_localfile_config()

        assert config["file_types"] == ["*.md", "*.txt", "*.py"]
