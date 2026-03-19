"""Unit tests for the setup wizard CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
from qdrant_loader.cli.commands.setup_cmd import (
    _collect_git_config,
    _collect_localfile_config,
    _collect_sources_loop,
    _escape_env_value,
    _source_name_to_env_suffix,
    _write_config_file_multi,
    _write_env_file,
    run_setup,
    run_setup_advanced,
    run_setup_default,
    run_setup_wizard,
)

# Module path for patching _select_source_type inside setup_cmd
_SST = "qdrant_loader.cli.commands.setup_cmd._select_source_type"

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
            "sk-test-key",
            "http://localhost:6333",
            "",
            "documents",
            "my-git",
            "https://github.com/org/repo.git",
            "main",
            "",
            "*.md,*.txt",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="git"),
        ):
            run_setup_wizard(tmp_path)

        assert (tmp_path / "config.yaml").exists()
        assert (tmp_path / ".env").exists()

    def test_run_setup_wizard_git_source(self, tmp_path: Path) -> None:
        """Test that git source is written correctly into config.yaml."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "my-git",
            "https://github.com/org/repo.git",
            "develop",
            "",
            "*.md,*.rst",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="git"),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        git_sources = config["sources"]["git"]
        assert "my-git" in git_sources
        src = git_sources["my-git"]
        assert src["base_url"] == "https://github.com/org/repo.git"
        assert src["branch"] == "develop"
        assert src["file_types"] == ["*.md", "*.rst"]
        assert "token" not in src

    def test_run_setup_wizard_confluence_source(self, tmp_path: Path) -> None:
        """Test that confluence source config and extra env vars are written."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "my-confluence",
            "https://mycompany.atlassian.net/wiki",
            "DOCS",
            "user@example.com",
            "secret-confluence-token",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="confluence"),
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
            "my-jira",
            "https://mycompany.atlassian.net",
            "PROJ",
            "jira@example.com",
            "secret-jira-token",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="jira"),
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
            "my-publicdocs",
            "https://docs.example.com/",
            "latest",
            "html",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="publicdocs"),
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
            "my-localfile",
            "/home/user/docs",
            "*.md,*.txt",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="localfile"),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        src = config["sources"]["localfile"]["my-localfile"]
        assert src["base_url"].startswith("file:///")
        assert src["base_url"].endswith("/home/user/docs")

    def test_run_setup_wizard_multiple_sources(self, tmp_path: Path) -> None:
        """Test adding multiple sources in one wizard run."""
        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            # First source: git
            "repo-one",
            "https://github.com/org/repo.git",
            "main",
            "",
            "*.md",
            # Second source: localfile
            "local-docs",
            "file:///data/docs",
            "*.txt",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[True, False, True]),
            patch(_SST, side_effect=["git", "localfile"]),
        ):
            run_setup_wizard(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert "git" in config["sources"]
        assert "localfile" in config["sources"]
        assert "repo-one" in config["sources"]["git"]
        assert "local-docs" in config["sources"]["localfile"]

    def test_run_setup_wizard_cancelled_on_overwrite(self, tmp_path: Path) -> None:
        """Test that setup exits without writing when user declines overwrite."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("existing: true\n", encoding="utf-8")

        prompt_side_effects = [
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            "my-git",
            "https://github.com/org/repo.git",
            "main",
            "",
            "*.md",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            # "Add another source?" → False, overwrite prompt → False
            patch("click.confirm", side_effect=[False, False]),
            patch(_SST, return_value="git"),
        ):
            run_setup_wizard(tmp_path)

        assert config_path.read_text(encoding="utf-8") == "existing: true\n"
        assert not (tmp_path / ".env").exists()


# ---------------------------------------------------------------------------
# run_setup mode selector tests
# ---------------------------------------------------------------------------


class TestRunSetup:
    """Verify that run_setup dispatches to the correct mode."""

    def test_mode_default_creates_files(self, tmp_path: Path) -> None:
        """run_setup with explicit output_dir and mode='default'."""
        ws = tmp_path / "ws"
        with patch("click.confirm", return_value=True):
            run_setup(ws, mode="default")

        assert (ws / "config.yaml").exists()
        assert (ws / ".env").exists()

    def test_mode_default_uses_workspace_subdir(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Default mode without output_dir should use ./workspace automatically."""
        monkeypatch.chdir(tmp_path)
        with patch("click.confirm", return_value=True):
            run_setup(None, mode="default")

        assert (tmp_path / "workspace" / "config.yaml").exists()
        assert (tmp_path / "workspace" / ".env").exists()

    def test_mode_normal_dispatches_to_wizard(self, tmp_path: Path) -> None:
        """run_setup with mode='normal' should run the interactive wizard."""
        ws = tmp_path / "ws"
        prompt_side_effects = [
            "sk-test",
            "http://localhost:6333",
            "",
            "documents",
            "my-localfile",
            "file:///tmp/data",
            "*.md",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="localfile"),
        ):
            run_setup(ws, mode="normal")

        config = yaml.safe_load((ws / "config.yaml").read_text(encoding="utf-8"))
        assert "sources" in config

    def test_mode_normal_prompts_workspace(self, tmp_path: Path) -> None:
        """Normal mode without output_dir should prompt for workspace folder."""
        prompt_side_effects = [
            str(tmp_path / "my-ws"),
            "sk-test",
            "http://localhost:6333",
            "",
            "documents",
            "my-localfile",
            "file:///tmp/data",
            "*.md",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[False, True]),
            patch(_SST, return_value="localfile"),
        ):
            run_setup(None, mode="normal")

        assert (tmp_path / "my-ws" / "config.yaml").exists()

    def test_mode_advanced_dispatches(self, tmp_path: Path) -> None:
        """run_setup with mode='advanced' should run the advanced wizard."""
        ws = tmp_path / "ws"
        prompt_side_effects = [
            "sk-test",
            "http://localhost:6333",
            "",
            "documents",
            "text-embedding-3-small",
            "",
            1536,
            1500,
            200,
            "my-project",
            "My Project",
            "desc",
            "my-localfile",
            "file:///tmp/data",
            "*.md",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch(
                "click.confirm",
                side_effect=[
                    True,  # enable reranking
                    False,  # no more sources
                    False,  # no more projects
                    True,  # write files
                ],
            ),
            patch(_SST, return_value="localfile"),
        ):
            run_setup(ws, mode="advanced")

        config = yaml.safe_load((ws / "config.yaml").read_text(encoding="utf-8"))
        assert "global" in config
        assert "projects" in config

    def test_mode_none_prompts_mode_then_workspace(self, tmp_path: Path) -> None:
        """run_setup without mode should prompt mode first, then workspace."""
        with (
            patch(
                "qdrant_loader.cli.commands.setup_cmd._select_setup_mode",
                return_value="default",
            ),
            patch("click.confirm", return_value=True),
        ):
            run_setup(tmp_path / "ws", mode=None)

        assert (tmp_path / "ws" / "config.yaml").exists()

    def test_mode_cancel_exits_cleanly(self, tmp_path: Path) -> None:
        """run_setup with mode selector returning None should exit without writing."""
        with patch(
            "qdrant_loader.cli.commands.setup_cmd._select_setup_mode", return_value=None
        ):
            run_setup(tmp_path / "ws", mode=None)

        assert not (tmp_path / "ws").exists()

    def test_output_dir_is_file_raises(self, tmp_path: Path) -> None:
        """Should raise BadParameter if output_dir is a file."""
        import click

        file_path = tmp_path / "not-a-dir"
        file_path.write_text("I am a file", encoding="utf-8")

        try:
            run_setup(file_path, mode="default")
            raise AssertionError("Expected BadParameter")
        except click.BadParameter:
            pass


# ---------------------------------------------------------------------------
# run_setup_default tests
# ---------------------------------------------------------------------------


class TestRunSetupDefault:
    """Verify that run_setup_default writes minimal config without prompts."""

    def test_creates_files(self, tmp_path: Path) -> None:
        with patch("click.confirm", return_value=True):
            run_setup_default(tmp_path)

        assert (tmp_path / "config.yaml").exists()
        assert (tmp_path / ".env").exists()

    def test_config_has_localfile_source(self, tmp_path: Path) -> None:
        with patch("click.confirm", return_value=True):
            run_setup_default(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert "localfile" in config["sources"]
        assert "my-docs" in config["sources"]["localfile"]
        src = config["sources"]["localfile"]["my-docs"]
        assert src["base_url"].startswith("file:///")
        # Should point to the docs subdirectory of the workspace
        assert src["base_url"].endswith("/docs")
        assert src["file_types"] == ["*.md", "*.txt", "*.py"]
        # docs directory should be created
        assert (tmp_path / "docs").is_dir()

    def test_env_has_placeholder_key(self, tmp_path: Path) -> None:
        with patch("click.confirm", return_value=True):
            run_setup_default(tmp_path)

        env = _read_env(tmp_path / ".env")
        assert env["OPENAI_API_KEY"] == "your_openai_api_key_here"

    def test_cancelled_on_overwrite(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("existing: true\n", encoding="utf-8")

        with patch("click.confirm", return_value=False):
            run_setup_default(tmp_path)

        assert config_path.read_text(encoding="utf-8") == "existing: true\n"


# ---------------------------------------------------------------------------
# run_setup_advanced tests
# ---------------------------------------------------------------------------


class TestRunSetupAdvanced:
    """Verify that run_setup_advanced writes multi-project config."""

    def test_creates_advanced_config(self, tmp_path: Path) -> None:
        prompt_side_effects = [
            "sk-test",
            "http://localhost:6333",
            "",
            "my-collection",
            "text-embedding-3-small",
            "",
            1536,
            1500,
            200,
            "proj-1",
            "Project One",
            "A test project",
            "my-localfile",
            "file:///tmp/data",
            "*.md",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch(
                "click.confirm",
                side_effect=[
                    True,  # enable reranking
                    False,  # no more sources
                    False,  # no more projects
                    True,  # write files
                ],
            ),
            patch(_SST, return_value="localfile"),
        ):
            run_setup_advanced(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert "global" in config
        assert "projects" in config
        assert "proj-1" in config["projects"]
        proj = config["projects"]["proj-1"]
        assert proj["project_id"] == "proj-1"
        assert proj["display_name"] == "Project One"
        assert "localfile" in proj["sources"]
        assert config["global"]["reranking"]["enabled"] is True

    def test_advanced_global_settings(self, tmp_path: Path) -> None:
        prompt_side_effects = [
            "sk-test",
            "https://cloud.qdrant.io",
            "qdrant-key",
            "my-docs",
            "text-embedding-ada-002",
            "https://custom-embedding.example.com/v1",
            768,
            2000,
            300,
            "proj-1",
            "proj-1",
            "",
            "my-localfile",
            "file:///tmp/data",
            "*.md",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch(
                "click.confirm",
                side_effect=[
                    True,  # enable reranking
                    False,  # no more sources
                    False,  # no more projects
                    True,  # write files
                ],
            ),
            patch(_SST, return_value="localfile"),
        ):
            run_setup_advanced(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        g = config["global"]
        assert g["embedding"]["model"] == "text-embedding-ada-002"
        assert g["embedding"]["endpoint"] == "https://custom-embedding.example.com/v1"
        assert g["embedding"]["vector_size"] == 768
        assert g["chunking"]["chunk_size"] == 2000
        assert g["chunking"]["chunk_overlap"] == 300
        assert g["reranking"]["enabled"] is True

    def test_advanced_multiple_projects(self, tmp_path: Path) -> None:
        prompt_side_effects = [
            "sk-test",
            "http://localhost:6333",
            "",
            "documents",
            "text-embedding-3-small",
            "",
            1536,
            1500,
            200,
            "proj-a",
            "Project A",
            "",
            "local-a",
            "file:///tmp/a",
            "*.md",
            "proj-b",
            "Project B",
            "",
            "local-b",
            "file:///tmp/b",
            "*.txt",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch(
                "click.confirm",
                side_effect=[
                    True,  # enable reranking
                    False,  # no more sources for proj-a
                    True,  # add another project
                    False,  # no more sources for proj-b
                    False,  # no more projects
                    True,  # write files confirmation
                ],
            ),
            patch(_SST, side_effect=["localfile", "localfile"]),
        ):
            run_setup_advanced(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert "proj-a" in config["projects"]
        assert "proj-b" in config["projects"]

    def test_advanced_reranking_disabled(self, tmp_path: Path) -> None:
        """Test that reranking can be disabled in advanced mode."""
        prompt_side_effects = [
            "sk-test",
            "http://localhost:6333",
            "",
            "documents",
            "text-embedding-3-small",
            "",
            1536,
            1500,
            200,
            "proj-1",
            "proj-1",
            "",
            "my-localfile",
            "file:///tmp/data",
            "*.md",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch(
                "click.confirm",
                side_effect=[
                    False,  # disable reranking
                    False,  # no more sources
                    False,  # no more projects
                    True,  # write files
                ],
            ),
            patch(_SST, return_value="localfile"),
        ):
            run_setup_advanced(tmp_path)

        config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
        assert config["global"]["reranking"]["enabled"] is False


# ---------------------------------------------------------------------------
# _collect_sources_loop – cross-project env-var collision detection
# ---------------------------------------------------------------------------


class TestCollectSourcesLoopEnvCollision:
    """Verify that _collect_sources_loop rejects source names whose env-var
    suffix collides with keys already present in all_extra_env (from a
    previous project)."""

    def test_rejects_duplicate_suffix_across_projects(self, tmp_path: Path) -> None:
        """When project-1 already registered CONFLUENCE_TOKEN_MY_WIKI,
        project-2 should not be allowed to reuse the name 'my-wiki'."""
        all_sources: dict = {}
        all_extra_env: dict = {"CONFLUENCE_TOKEN_MY_WIKI": "secret-1"}

        # Simulate: user picks confluence, enters "my-wiki" (rejected),
        # then "my-wiki-2" (accepted), then stops.
        prompts = iter(
            [
                "my-wiki",
                "my-wiki-2",
                "https://x.atlassian.net/wiki",
                "SP",
                "u@c.com",
                "tok",
            ]
        )
        confirms = iter([False])  # don't add another source

        with (
            patch(_SST, side_effect=["confluence", None]),
            patch("click.prompt", side_effect=lambda *a, **kw: next(prompts)),
            patch("click.confirm", side_effect=lambda *a, **kw: next(confirms)),
        ):
            _collect_sources_loop(all_sources, all_extra_env, workspace_dir=tmp_path)

        # "my-wiki" must have been rejected; "my-wiki-2" accepted
        assert "my-wiki-2" in all_sources.get("confluence", {})
        assert "CONFLUENCE_TOKEN_MY_WIKI_2" in all_extra_env


# ---------------------------------------------------------------------------
# _write_env_file unit tests
# ---------------------------------------------------------------------------


class TestWriteEnvFile:
    """Tests for the _write_env_file helper."""

    def test_write_env_file_minimal(self, tmp_path: Path) -> None:
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
        config_path = tmp_path / "config.yaml"
        _write_config_file_multi(config_path, sources={"git": {}})

        raw = config_path.read_text(encoding="utf-8")
        assert raw.startswith("# Generated by qdrant-loader setup")

    def test_write_config_file_empty_sources(self, tmp_path: Path) -> None:
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
        with patch("click.prompt", side_effect=["/home/user/docs", "*.md,*.rst"]):
            config, extra_env = _collect_localfile_config("my-local")

        assert config["base_url"].startswith("file:///")
        assert config["base_url"].endswith("/home/user/docs")
        assert extra_env == {}

    def test_collect_localfile_preserves_existing_prefix(self) -> None:
        with patch("click.prompt", side_effect=["file:///data/docs", "*.txt"]):
            config, extra_env = _collect_localfile_config("my-local")

        assert config["base_url"] == "file:///data/docs"

    def test_collect_localfile_parses_file_types(self) -> None:
        with patch("click.prompt", side_effect=["/tmp/data", "*.md, *.txt, *.py"]):
            config, _ = _collect_localfile_config("my-local")

        assert config["file_types"] == ["*.md", "*.txt", "*.py"]

    def test_collect_localfile_resolves_relative_path(self) -> None:
        with patch("click.prompt", side_effect=["relative/docs", "*.md"]):
            config, _ = _collect_localfile_config("my-local")

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
        assert _source_name_to_env_suffix("my-repo") == _source_name_to_env_suffix(
            "my_repo"
        )

    def test_empty_suffix_fallback(self) -> None:
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
            "sk-openai",
            "http://localhost:6333",
            "",
            "documents",
            # First source
            "my-git",
            "https://github.com/org/repo1.git",
            "main",
            "",
            "*.md",
            # Second source — first try "my-git" (duplicate), then "my-git-2"
            "my-git",  # duplicate -> rejected
            "my-git-2",  # accepted
            "https://github.com/org/repo2.git",
            "main",
            "",
            "*.py",
        ]
        with (
            patch("click.prompt", side_effect=prompt_side_effects),
            patch("click.confirm", side_effect=[True, False, True]),
            patch(_SST, side_effect=["git", "git"]),
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
        assert mode & stat.S_IRUSR
        assert mode & stat.S_IWUSR
        assert not (mode & stat.S_IRGRP)
        assert not (mode & stat.S_IROTH)


# ---------------------------------------------------------------------------
# _escape_env_value unit tests
# ---------------------------------------------------------------------------


class TestEscapeEnvValue:
    """Tests for the _escape_env_value helper."""

    def test_plain_value_unchanged(self) -> None:
        assert _escape_env_value("sk-abc123") == "sk-abc123"

    def test_value_with_equals_is_quoted(self) -> None:
        assert _escape_env_value("key=value") == '"key=value"'

    def test_value_with_quotes_is_escaped(self) -> None:
        assert _escape_env_value('has"quote') == '"has\\"quote"'

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
        import click

        file_path = tmp_path / "not-a-dir"
        file_path.write_text("I am a file", encoding="utf-8")

        with (
            patch("click.prompt", side_effect=Exception("should not reach prompts")),
            patch("click.confirm", side_effect=Exception("should not reach confirms")),
        ):
            try:
                run_setup(file_path, mode="default")
                raise AssertionError("Expected BadParameter")
            except click.BadParameter:
                pass
