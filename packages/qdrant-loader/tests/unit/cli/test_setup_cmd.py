"""Unit tests for the setup wizard CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
from qdrant_loader.cli.commands.setup_cmd import (
    _collect_git_config,
    _collect_localfile_config,
    _escape_env_value,
    _source_name_to_env_suffix,
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
            "sk-test-key",  # OpenAI API Key
            "http://localhost:6333",  # Qdrant URL (default)
            "",  # Qdrant API Key (empty)
            "documents",  # Collection name (default)
            # Step 2 – source type
            "git",
            # Step 3 – source name
            "my-git",
            # _collect_git_config
            "https://github.com/org/repo.git",  # url
            "main",  # branch
            "",  # token (empty)
            "*.md,*.txt",  # file types
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
        assert src["token"] == "${CONFLUENCE_TOKEN_MY_CONFLUENCE}"
        assert src["email"] == "${CONFLUENCE_EMAIL_MY_CONFLUENCE}"

        env = _read_env(tmp_path / ".env")
        assert env["CONFLUENCE_TOKEN_MY_CONFLUENCE"] == "secret-confluence-token"
        assert env["CONFLUENCE_EMAIL_MY_CONFLUENCE"] == "user@example.com"

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
        assert src["token"] == "${JIRA_TOKEN_MY_JIRA}"
        assert src["email"] == "${JIRA_EMAIL_MY_JIRA}"

        env = _read_env(tmp_path / ".env")
        assert env["JIRA_TOKEN_MY_JIRA"] == "secret-jira-token"
        assert env["JIRA_EMAIL_MY_JIRA"] == "jira@example.com"

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
        assert src["base_url"].startswith("file:///")
        assert src["base_url"].endswith("/home/user/docs")

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
            True,  # "Add another source?" -> yes
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
        assert (
            parsed["sources"]["git"]["my-repo"]["base_url"]
            == "https://github.com/org/repo.git"
        )
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
        """Token should map to a source-scoped env var."""
        prompt_side_effects = [
            "https://github.com/org/repo.git",
            "main",
            "my-secret-token",
            "*.md,*.txt",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, extra_env = _collect_git_config("my-repo")

        assert config["token"] == "${GIT_TOKEN_MY_REPO}"
        assert extra_env["GIT_TOKEN_MY_REPO"] == "my-secret-token"
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
            config, extra_env = _collect_git_config("my-repo")

        assert "token" not in config
        assert extra_env == {}


# ---------------------------------------------------------------------------
# _collect_localfile_config unit tests
# ---------------------------------------------------------------------------


class TestCollectLocalfileConfig:
    """Tests for the _collect_localfile_config helper."""

    def test_collect_localfile_adds_file_prefix(self) -> None:
        """Paths without file:// prefix get converted via Path.as_uri()."""
        prompt_side_effects = [
            "/home/user/docs",
            "*.md,*.rst",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, extra_env = _collect_localfile_config("my-local")

        assert config["base_url"].startswith("file:///")
        assert config["base_url"].endswith("/home/user/docs")
        assert extra_env == {}

    def test_collect_localfile_preserves_existing_prefix(self) -> None:
        """Paths already starting with file:// must not be double-prefixed."""
        prompt_side_effects = [
            "file:///data/docs",
            "*.txt",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, extra_env = _collect_localfile_config("my-local")

        assert config["base_url"] == "file:///data/docs"

    def test_collect_localfile_parses_file_types(self) -> None:
        """Comma-separated file types must be split into a list."""
        prompt_side_effects = [
            "/tmp/data",
            "*.md, *.txt, *.py",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, _ = _collect_localfile_config("my-local")

        assert config["file_types"] == ["*.md", "*.txt", "*.py"]

    def test_collect_localfile_resolves_relative_path(self) -> None:
        """Relative paths must be resolved to absolute file:// URIs."""
        prompt_side_effects = [
            "relative/docs",
            "*.md",
        ]

        with patch("click.prompt", side_effect=prompt_side_effects):
            config, _ = _collect_localfile_config("my-local")

        # Path.as_uri() resolves to absolute, so must start with file:///
        assert config["base_url"].startswith("file:///")
        assert config["base_url"].endswith("relative/docs")


# ---------------------------------------------------------------------------
# _source_name_to_env_suffix unit tests
# ---------------------------------------------------------------------------


class TestSourceNameToEnvSuffix:
    """Tests for the _source_name_to_env_suffix helper."""

    def test_basic_conversion(self) -> None:
        assert _source_name_to_env_suffix("my-repo") == "MY_REPO"

    def test_dots_and_special_chars(self) -> None:
        assert _source_name_to_env_suffix("my.repo@v2") == "MY_REPO_V2"

    def test_collision_detection(self) -> None:
        """Names that differ only by separator produce the same suffix."""
        assert _source_name_to_env_suffix("my-repo") == _source_name_to_env_suffix(
            "my_repo"
        )

    def test_empty_suffix_fallback(self) -> None:
        """Source name with only special chars should return 'DEFAULT'."""
        assert _source_name_to_env_suffix("---") == "DEFAULT"
        assert _source_name_to_env_suffix("...") == "DEFAULT"


# ---------------------------------------------------------------------------
# Duplicate source name rejection tests
# ---------------------------------------------------------------------------


class TestDuplicateSourceNameRejection:
    """Tests for duplicate source name/suffix detection in the wizard."""

    def test_duplicate_name_rejected_then_accepted(self, tmp_path: Path) -> None:
        """Adding two git sources with the same name should re-prompt."""
        prompt_side_effects = [
            # Core settings
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            # First source: git/my-git
            "git",
            "my-git",
            "https://github.com/org/repo1.git",
            "main",
            "",
            "*.md",
            # Second source: git — first try "my-git" (duplicate), then "my-git-2"
            "git",
            "my-git",  # duplicate → rejected
            "my-git-2",  # accepted
            "https://github.com/org/repo2.git",
            "main",
            "",
            "*.py",
        ]
        confirm_side_effects = [
            True,  # "Add another source?" → yes
            False,  # "Add another source?" → no
        ]

        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=confirm_side_effects),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        git_sources = config["sources"]["git"]
        assert "my-git" in git_sources
        assert "my-git-2" in git_sources


# ---------------------------------------------------------------------------
# .env file permissions test
# ---------------------------------------------------------------------------


class TestEnvFilePermissions:
    """Tests for .env file permission hardening."""

    def test_env_file_permissions_restricted(self, tmp_path: Path) -> None:
        """Generated .env should have 0o600 permissions on POSIX."""
        import os
        import stat

        env_path = tmp_path / ".env"
        _write_env_file(
            env_path,
            openai_key="sk-test",
            qdrant_url="http://localhost:6333",
            qdrant_api_key="",
            collection_name="documents",
        )

        mode = os.stat(env_path).st_mode
        # Owner read+write only (0o600)
        assert mode & stat.S_IRUSR  # owner read
        assert mode & stat.S_IWUSR  # owner write
        assert not (mode & stat.S_IRGRP)  # no group read
        assert not (mode & stat.S_IROTH)  # no other read


# ---------------------------------------------------------------------------
# _escape_env_value unit tests
# ---------------------------------------------------------------------------


class TestEscapeEnvValue:
    """Tests for the _escape_env_value helper."""

    def test_plain_value_unchanged(self) -> None:
        assert _escape_env_value("sk-abc123") == "sk-abc123"

    def test_value_with_equals_is_quoted(self) -> None:
        result = _escape_env_value("key=value")
        assert result == '"key=value"'

    def test_value_with_quotes_is_escaped(self) -> None:
        result = _escape_env_value('has"quote')
        assert result == '"has\\"quote"'

    def test_value_with_newline_is_quoted(self) -> None:
        result = _escape_env_value("line1\nline2")
        assert result.startswith('"') and result.endswith('"')

    def test_value_with_space_is_quoted(self) -> None:
        assert _escape_env_value("has space") == '"has space"'

    def test_value_with_hash_is_quoted(self) -> None:
        assert _escape_env_value("val#comment").startswith('"')

    def test_value_with_dollar_is_quoted(self) -> None:
        assert _escape_env_value("$HOME/path").startswith('"')


# ---------------------------------------------------------------------------
# output_dir validation tests
# ---------------------------------------------------------------------------


class TestOutputDirValidation:
    """Tests for output_dir fail-fast when it's a file."""

    def test_output_dir_is_file_raises(self, tmp_path: Path) -> None:
        """run_setup_wizard should raise BadParameter if output_dir is a file."""
        import click

        file_path = tmp_path / "not-a-dir"
        file_path.write_text("I am a file", encoding="utf-8")

        with (
            patch("click.prompt", side_effect=Exception("should not reach prompts")),
            patch("click.confirm", side_effect=Exception("should not reach confirms")),
        ):
            try:
                run_setup_wizard(file_path)
                raise AssertionError("Expected BadParameter")
            except click.BadParameter:
                pass
