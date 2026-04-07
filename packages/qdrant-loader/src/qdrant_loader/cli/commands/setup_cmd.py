"""Interactive setup wizard for qdrant-loader configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

# Heavy modules (questionary ~1.4s, rich ~0.4s) are lazy-imported via helpers
# to keep CLI startup fast.
_console = None


def _get_console():
    global _console
    if _console is None:
        from rich.console import Console

        _console = Console()
    return _console


SOURCE_TYPES: dict[str, str] = {
    "git": "Git Repository",
    "confluence": "Confluence Wiki",
    "jira": "Jira Issues",
    "publicdocs": "Public Documentation (website)",
    "localfile": "Local Files",
}

# Returned by every _collect_*_config helper: (yaml-ready dict, extra env vars dict)
_SourceResult = tuple[dict[str, Any], dict[str, str]]


SETUP_MODES: dict[str, str] = {
    "default": "Quick start with localfile source pointing to current directory",
    "normal": "Interactive wizard with simplified config format",
    "advanced": "Full control over global settings, multi-project format",
}


def run_setup(output_dir: Path | None = None, mode: str | None = None) -> None:
    """Entry point for the setup command.

    When *output_dir* is ``None`` (or ``"."``) the user is prompted to choose a
    workspace folder.  When *mode* is ``None`` a TUI mode selector is shown.

    Args:
        output_dir: Directory in which the generated files are placed.
            If ``None``, the user is prompted interactively.
        mode: One of ``"default"``, ``"normal"``, ``"advanced"`` or ``None``.
    """
    # ------------------------------------------------------------------
    # Step 0: Mode selection (before workspace, so default can skip prompt)
    # ------------------------------------------------------------------
    if mode is None:
        mode = _select_setup_mode()
        if mode is None:
            _get_console().print("[yellow]Setup cancelled.[/yellow]")
            return

    # ------------------------------------------------------------------
    # Step 1: Workspace folder
    # ------------------------------------------------------------------
    if mode == "default":
        # Default mode always uses ./workspace, no prompt
        output_dir = _resolve_workspace(
            output_dir if output_dir is not None else Path("workspace")
        )
    else:
        output_dir = _resolve_workspace(output_dir)

    dispatch = {
        "default": run_setup_default,
        "normal": run_setup_wizard,
        "advanced": run_setup_advanced,
    }
    try:
        dispatch[mode](output_dir)
    except (click.Abort, KeyboardInterrupt):
        _get_console().print("\n[yellow]Setup cancelled.[/yellow]")


def _resolve_workspace(output_dir: Path | None) -> Path:
    """Resolve and prepare the workspace directory.

    When *output_dir* is explicitly provided, uses it directly.
    Otherwise prompts the user with ``./workspace`` as the default.

    Args:
        output_dir: The value passed via ``--output-dir``, or ``None``.

    Returns:
        Resolved :class:`Path` to the workspace directory (created if needed).
    """
    # If explicitly provided via --output-dir, use it as-is.
    if output_dir is not None:
        resolved = Path(output_dir).resolve()
        if resolved.exists() and not resolved.is_dir():
            raise click.BadParameter(
                f"'{resolved}' exists but is not a directory.",
                param_hint="output_dir",
            )
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    # Interactive: prompt with default ./workspace
    default_ws = "workspace"
    raw: str = click.prompt("Workspace folder", default=default_ws)
    chosen = raw.encode("utf-8", errors="ignore").decode("utf-8").strip()
    if not chosen:
        chosen = default_ws

    ws_path = (Path.cwd() / chosen).resolve()
    if ws_path.exists() and not ws_path.is_dir():
        raise click.BadParameter(
            f"'{ws_path}' exists but is not a directory.",
            param_hint="workspace",
        )
    if not ws_path.exists():
        ws_path.mkdir(parents=True, exist_ok=True)
        _get_console().print(f"[green]Created workspace: {ws_path}[/green]")
    else:
        _get_console().print(f"[cyan]Using workspace: {ws_path}[/cyan]")

    return ws_path


def _select_setup_mode() -> str | None:
    """Present an interactive mode selector using questionary.

    Returns:
        One of the keys in :data:`SETUP_MODES`, or ``None`` if the user cancels.
    """
    import questionary
    from rich.panel import Panel

    _get_console().print(
        Panel(
            "[bold]qdrant-loader Setup[/bold]\n" "Choose a setup mode to get started.",
            style="blue",
        )
    )

    _CANCEL = "__cancel__"
    choices = [
        questionary.Choice(title=f"{key.capitalize():<10} - {desc}", value=key)
        for key, desc in SETUP_MODES.items()
    ]
    choices.append(questionary.Choice(title="Cancel", value=_CANCEL))

    try:
        result = questionary.select(
            "Select setup mode:",
            choices=choices,
            default="default",
        ).ask()
    except (EOFError, KeyboardInterrupt):
        result = None

    if result is None or result == _CANCEL:
        return None
    return result


def run_setup_default(output_dir: Path) -> None:
    """Generate a minimal default config with a localfile source pointing to the current directory.

    No interactive prompts – just writes ``config.yaml`` and ``.env`` with sensible
    defaults so the user can immediately run ``qdrant-loader init && qdrant-loader ingest``.

    Args:
        output_dir: Directory in which the generated files are placed.
    """
    from rich.panel import Panel

    output_dir = Path(output_dir).resolve()

    config_path = output_dir / "config.yaml"
    env_path = output_dir / ".env"

    # Show preview of what will be created/overwritten
    _show_file_preview(output_dir, config_path, env_path)

    if not _confirm_overwrite(config_path, env_path):
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Use workspace/docs as the localfile source directory
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    docs_path = docs_dir.as_uri()

    sources: dict[str, dict[str, Any]] = {
        "localfile": {
            "my-docs": {
                "base_url": docs_path,
                "file_types": ["*.md", "*.txt", "*.py"],
                "enable_file_conversion": True,
            }
        }
    }

    _write_env_file(
        env_path,
        openai_key="your_openai_api_key_here",
        qdrant_url="http://localhost:6333",
        qdrant_api_key="",
        collection_name="documents",
    )
    _write_config_file_multi(config_path, sources=sources)

    _get_console().print(
        Panel(
            f"[green]Created:[/green]\n"
            f"  - {config_path}\n"
            f"  - {env_path}\n"
            f"  - {docs_dir}/ (place your documents here)\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Set your OPENAI_API_KEY in {env_path}\n"
            f"  2. Place your documents in {docs_dir}/\n"
            f"  3. Run: qdrant-loader init --workspace {output_dir}\n"
            f"  4. Run: qdrant-loader ingest --workspace {output_dir}",
            title="Default Setup Complete",
            style="green",
        )
    )


def run_setup_wizard(output_dir: Path) -> None:
    """Run the interactive setup wizard (Normal mode).

    Prompts the user for core settings and source-specific details, then writes
    a ``config.yaml`` and ``.env`` file to *output_dir*.

    Args:
        output_dir: Directory in which the generated files are placed.
    """
    from rich.panel import Panel

    output_dir = Path(output_dir).resolve()

    _get_console().print(
        Panel(
            "[bold]qdrant-loader Setup Wizard[/bold] [dim](Normal mode)[/dim]\n"
            "Generate config.yaml and .env for your project.",
            style="blue",
        )
    )

    # ------------------------------------------------------------------
    # Step 1: Core settings
    # ------------------------------------------------------------------
    _get_console().print("\n[bold cyan]Step 1: Core Settings[/bold cyan]")

    openai_key: str = click.prompt("OpenAI API Key", hide_input=True)
    qdrant_url: str = click.prompt("Qdrant URL", default="http://localhost:6333")
    qdrant_api_key: str = click.prompt(
        "Qdrant API Key (leave empty for local)", default="", hide_input=True
    )
    collection_name: str = click.prompt("Collection name", default="documents")

    # ------------------------------------------------------------------
    # Step 2+3: Source type selection and config (loop for multiple)
    # ------------------------------------------------------------------
    all_sources: dict[str, dict[str, Any]] = {}
    all_extra_env: dict[str, str] = {}

    _collect_sources_loop(all_sources, all_extra_env, workspace_dir=output_dir)

    # ------------------------------------------------------------------
    # Step 4: Confirm output paths and write files
    # ------------------------------------------------------------------
    config_path = output_dir / "config.yaml"
    env_path = output_dir / ".env"

    _show_file_preview(output_dir, config_path, env_path)

    if not _confirm_overwrite(config_path, env_path):
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    _write_env_file(
        env_path,
        openai_key=openai_key,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        collection_name=collection_name,
        extra_vars=all_extra_env,
    )
    _write_config_file_multi(
        config_path,
        sources=all_sources,
    )

    # Build source summary
    source_summary = ", ".join(
        f"{st}({len(names)})" for st, names in all_sources.items()
    )

    _get_console().print(
        Panel(
            f"[green]Created:[/green]\n"
            f"  - {config_path}\n"
            f"  - {env_path}\n"
            f"  - Sources: {source_summary}\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Review the generated files\n"
            f"  2. Run: qdrant-loader init --workspace {output_dir}\n"
            f"  3. Run: qdrant-loader ingest --workspace {output_dir}",
            title="Setup Complete",
            style="green",
        )
    )


def run_setup_advanced(output_dir: Path) -> None:
    """Run the advanced setup wizard with full global settings and multi-project format.

    Args:
        output_dir: Directory in which the generated files are placed.
    """
    from rich.panel import Panel

    output_dir = Path(output_dir).resolve()

    _get_console().print(
        Panel(
            "[bold]qdrant-loader Setup Wizard[/bold] [dim](Advanced mode)[/dim]\n"
            "Full control over global settings and multi-project configuration.",
            style="blue",
        )
    )

    # ------------------------------------------------------------------
    # Step 1: Core settings
    # ------------------------------------------------------------------
    _get_console().print("\n[bold cyan]Step 1: Core Settings[/bold cyan]")

    openai_key: str = click.prompt("OpenAI API Key", hide_input=True)
    qdrant_url: str = click.prompt("Qdrant URL", default="http://localhost:6333")
    qdrant_api_key: str = click.prompt(
        "Qdrant API Key (leave empty for local)", default="", hide_input=True
    )
    collection_name: str = click.prompt("Collection name", default="documents")

    # ------------------------------------------------------------------
    # Step 2: Embedding settings
    # ------------------------------------------------------------------
    _get_console().print("\n[bold cyan]Step 2: Embedding Configuration[/bold cyan]")

    embedding_model: str = click.prompt(
        "Embedding model", default="argus-ai/pplx-embed-context-v1-0.6b:fp32"
    )
    embedding_endpoint: str = click.prompt(
        "Embedding endpoint (leave empty for OpenAI default)",
        default="http://localhost:11434",
    )
    vector_size: int = click.prompt("Vector size", default=1024, type=int)

    # ------------------------------------------------------------------
    # Step 3: Chunking settings
    # ------------------------------------------------------------------
    _get_console().print("\n[bold cyan]Step 3: Chunking Configuration[/bold cyan]")

    chunk_size: int = click.prompt("Chunk size (characters)", default=1500, type=int)
    chunk_overlap: int = click.prompt(
        "Chunk overlap (characters)", default=200, type=int
    )

    # ------------------------------------------------------------------
    # Step 4: Reranking settings
    # ------------------------------------------------------------------
    _get_console().print("\n[bold cyan]Step 4: Reranking Configuration[/bold cyan]")

    enable_reranking: bool = click.confirm(
        "Enable cross-encoder reranking?", default=True
    )

    # ------------------------------------------------------------------
    # Step 5: Projects with sources
    # ------------------------------------------------------------------
    projects: dict[str, dict[str, Any]] = {}
    all_extra_env: dict[str, str] = {}

    while True:
        _get_console().print("\n[bold cyan]Step 5: Project Configuration[/bold cyan]")

        while True:
            project_id: str = click.prompt("Project ID", default="my-project")
            if project_id in projects:
                _get_console().print(
                    f"[red]Project '{project_id}' already exists. "
                    f"Pick a different ID.[/red]"
                )
                continue
            break
        display_name: str = click.prompt("Display name", default=project_id)
        description: str = click.prompt("Description", default="")

        project_sources: dict[str, dict[str, Any]] = {}
        _collect_sources_loop(project_sources, all_extra_env, workspace_dir=output_dir)

        projects[project_id] = {
            "project_id": project_id,
            "display_name": display_name,
            "description": description,
            "sources": project_sources,
        }

        _get_console().print(f"[green]Added project: {project_id}[/green]")

        if not click.confirm("Add another project?", default=False):
            break

    # ------------------------------------------------------------------
    # Step 6: Write files
    # ------------------------------------------------------------------
    config_path = output_dir / "config.yaml"
    env_path = output_dir / ".env"

    _show_file_preview(output_dir, config_path, env_path)

    if not _confirm_overwrite(config_path, env_path):
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    _write_env_file(
        env_path,
        openai_key=openai_key,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        collection_name=collection_name,
        extra_vars=all_extra_env,
    )

    # Build global config
    global_config: dict[str, Any] = {
        "qdrant": {
            "url": qdrant_url,
            "api_key": "${QDRANT_API_KEY}" if qdrant_api_key else None,
            "collection_name": collection_name,
        },
        "embedding": {
            "model": embedding_model,
            "api_key": "${OPENAI_API_KEY}",
            "vector_size": vector_size,
        },
        "chunking": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
    }

    if embedding_endpoint:
        global_config["embedding"]["endpoint"] = embedding_endpoint

    global_config["reranking"] = {
        "enabled": enable_reranking,
    }

    _write_config_file_advanced(
        config_path,
        global_config=global_config,
        projects=projects,
    )

    project_summary = ", ".join(
        f"{pid}({sum(len(srcs) for srcs in p['sources'].values())} sources)"
        for pid, p in projects.items()
    )

    _get_console().print(
        Panel(
            f"[green]Created:[/green]\n"
            f"  - {config_path}\n"
            f"  - {env_path}\n"
            f"  - Projects: {project_summary}\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Review the generated files\n"
            f"  2. Run: qdrant-loader init --workspace {output_dir}\n"
            f"  3. Run: qdrant-loader ingest --workspace {output_dir}",
            title="Advanced Setup Complete",
            style="green",
        )
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _show_file_preview(output_dir: Path, *paths: Path) -> None:
    """Display a summary panel showing the workspace and files that will be written.

    Args:
        output_dir: The workspace directory.
        paths: File paths that will be created or overwritten.
    """
    from rich.panel import Panel

    lines = [f"[bold]Workspace:[/bold] {output_dir}"]
    for path in paths:
        status = (
            "[yellow](overwrite)[/yellow]" if path.exists() else "[green](new)[/green]"
        )
        lines.append(f"  {path.name} {status}")

    _get_console().print(
        Panel(
            "\n".join(lines),
            title="Files to write",
            style="cyan",
        )
    )


def _confirm_overwrite(*paths: Path) -> bool:
    """Ask the user to confirm before writing files.

    Always prompts for confirmation. Warns specifically about existing files
    that will be overwritten.

    Returns:
        ``True`` if it is safe to proceed, ``False`` if the user cancelled.
    """
    existing = [p for p in paths if p.exists()]
    if existing:
        names = ", ".join(p.name for p in existing)
        if not click.confirm(
            f"{names} already exist(s) and will be overwritten. Proceed?"
        ):
            _get_console().print("[yellow]Setup cancelled.[/yellow]")
            return False
    else:
        if not click.confirm("Write files?", default=True):
            _get_console().print("[yellow]Setup cancelled.[/yellow]")
            return False
    return True


def _select_source_type() -> str | None:
    """Present an interactive source type selector with arrow-key navigation.

    Returns:
        One of the keys in :data:`SOURCE_TYPES`, or ``None`` if the user
        selects Back / presses Escape.
    """
    import questionary

    choices = [
        questionary.Choice(title=f"{key:<12} - {desc}", value=key)
        for key, desc in SOURCE_TYPES.items()
    ]

    try:
        result = questionary.select(
            "Select source type:",
            choices=choices,
            default="localfile",
        ).ask()
    except (EOFError, KeyboardInterrupt):
        result = None

    return result


def _collect_sources_loop(
    all_sources: dict[str, dict[str, Any]],
    all_extra_env: dict[str, str],
    workspace_dir: Path | None = None,
) -> None:
    """Interactively collect one or more data sources from the user.

    Results are merged into *all_sources* and *all_extra_env* in-place.

    Args:
        all_sources: Accumulated source configs (mutated in-place).
        all_extra_env: Accumulated extra env vars (mutated in-place).
        workspace_dir: Workspace directory, used to derive defaults (e.g. docs path).
    """
    while True:
        _get_console().print("\n[bold cyan]Data Source[/bold cyan]")

        source_type = _select_source_type()
        if source_type is None:
            break

        _get_console().print(
            f"\n[bold cyan]Configure {SOURCE_TYPES[source_type]}[/bold cyan]"
        )
        existing_names = all_sources.get(source_type, {})
        # Collect suffixes from ALL already-registered env vars (across all
        # source types and projects) to prevent silent overwrites.
        existing_env_keys = set(all_extra_env.keys())
        while True:
            source_name = click.prompt(
                "Source name (identifier)", default=f"my-{source_type}"
            )
            suffix = _source_name_to_env_suffix(source_name)
            if source_name in existing_names:
                _get_console().print(
                    f"[red]{source_type}/{source_name} already exists. "
                    f"Pick a different name.[/red]"
                )
                continue
            # Check if any env key with this suffix already exists
            if any(k.endswith(f"_{suffix}") for k in existing_env_keys):
                _get_console().print(
                    f"[red]'{source_name}' collides with an existing "
                    f"env var suffix across projects. "
                    f"Pick a different name.[/red]"
                )
                continue
            break
        source_config, extra_env = _collect_source_config(
            source_type, source_name, workspace_dir=workspace_dir
        )

        if source_type not in all_sources:
            all_sources[source_type] = {}
        all_sources[source_type][source_name] = source_config
        all_extra_env.update(extra_env)

        _get_console().print(f"[green]Added {source_type}/{source_name}[/green]")

        if not click.confirm("Add another source?", default=False):
            break


# ---------------------------------------------------------------------------
# Source-specific config collectors
# ---------------------------------------------------------------------------


def _source_name_to_env_suffix(source_name: str) -> str:
    """Convert a source name like 'my-repo' to an env-var-safe suffix like 'MY_REPO'."""
    import re

    suffix = re.sub(r"[^A-Za-z0-9]", "_", source_name).strip("_").upper()
    return suffix if suffix else "DEFAULT"


def _collect_source_config(
    source_type: str,
    source_name: str,
    *,
    workspace_dir: Path | None = None,
) -> _SourceResult:
    """Dispatch to the correct collector based on *source_type*.

    Args:
        source_type: One of the keys in ``SOURCE_TYPES``.
        source_name: User-chosen identifier, used to create unique env var names.
        workspace_dir: Workspace directory, passed to collectors that need it.

    Returns:
        A tuple of (source yaml dict, extra env-var dict).
    """
    if source_type == "localfile":
        return _collect_localfile_config(source_name, workspace_dir=workspace_dir)

    collectors = {
        "git": _collect_git_config,
        "confluence": _collect_confluence_config,
        "jira": _collect_jira_config,
        "publicdocs": _collect_publicdocs_config,
    }
    collector = collectors.get(source_type)
    if collector is None:
        return {}, {}
    return collector(source_name)


def _collect_git_config(source_name: str) -> _SourceResult:
    """Collect Git repository source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    url: str = click.prompt("Repository URL (e.g., https://github.com/org/repo.git)")
    branch: str = click.prompt("Branch", default="main")
    token: str = click.prompt(
        "Access token (leave empty for public repos)", default="", hide_input=True
    )
    file_types_raw: str = click.prompt(
        "File types (comma-separated)", default="*.md,*.txt,*.py"
    )
    file_types = [ft.strip() for ft in file_types_raw.split(",") if ft.strip()]

    config: dict[str, Any] = {
        "base_url": url,
        "branch": branch,
        "file_types": file_types,
        "enable_file_conversion": True,
    }
    extra_env: dict[str, str] = {}

    if token:
        suffix = _source_name_to_env_suffix(source_name)
        env_key = f"GIT_TOKEN_{suffix}"
        config["token"] = f"${{{env_key}}}"
        extra_env[env_key] = token

    return config, extra_env


def _collect_confluence_config(source_name: str) -> _SourceResult:
    """Collect Confluence source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    base_url: str = click.prompt(
        "Confluence URL (e.g., https://mycompany.atlassian.net/wiki)"
    )
    space_key: str = click.prompt("Space key")
    email: str = click.prompt("Email")
    token: str = click.prompt("API token", hide_input=True)

    suffix = _source_name_to_env_suffix(source_name)
    token_key = f"CONFLUENCE_TOKEN_{suffix}"
    email_key = f"CONFLUENCE_EMAIL_{suffix}"

    config: dict[str, Any] = {
        "base_url": base_url,
        "space_key": space_key,
        "token": f"${{{token_key}}}",
        "email": f"${{{email_key}}}",
        "enable_file_conversion": True,
    }
    extra_env: dict[str, str] = {
        token_key: token,
        email_key: email,
    }
    return config, extra_env


def _collect_jira_config(source_name: str) -> _SourceResult:
    """Collect Jira source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    base_url: str = click.prompt("Jira URL (e.g., https://mycompany.atlassian.net)")
    project_key: str = click.prompt("Project key")
    email: str = click.prompt("Email")
    token: str = click.prompt("API token", hide_input=True)

    suffix = _source_name_to_env_suffix(source_name)
    token_key = f"JIRA_TOKEN_{suffix}"
    email_key = f"JIRA_EMAIL_{suffix}"

    config: dict[str, Any] = {
        "base_url": base_url,
        "project_key": project_key,
        "token": f"${{{token_key}}}",
        "email": f"${{{email_key}}}",
        "enable_file_conversion": True,
    }
    extra_env: dict[str, str] = {
        token_key: token,
        email_key: email,
    }
    return config, extra_env


def _collect_publicdocs_config(source_name: str) -> _SourceResult:
    """Collect Public Documentation source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    base_url: str = click.prompt("Documentation URL (e.g., https://docs.example.com/)")
    version: str = click.prompt("Version", default="latest")
    content_type: str = click.prompt(
        "Content type",
        default="html",
        type=click.Choice(["html", "markdown"]),
    )

    config: dict[str, Any] = {
        "base_url": base_url,
        "version": version,
        "content_type": content_type,
    }
    return config, {}


def _collect_localfile_config(
    source_name: str, *, workspace_dir: Path | None = None
) -> _SourceResult:
    """Collect Local Files source configuration.

    Args:
        source_name: User-chosen identifier for this source.
        workspace_dir: Workspace directory. When provided, defaults to ``<workspace>/docs``.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    default_path = ""
    if workspace_dir is not None:
        default_path = str(workspace_dir / "docs")

    raw_path: str = click.prompt(
        "Directory path (e.g., /path/to/files or file:///path)",
        default=default_path or None,
    )
    if raw_path.startswith("file://"):
        path = raw_path
    else:
        path = Path(raw_path).expanduser().resolve().as_uri()

    file_types_raw: str = click.prompt(
        "File types (comma-separated)", default="*.md,*.txt,*.py"
    )
    file_types = [ft.strip() for ft in file_types_raw.split(",") if ft.strip()]

    config: dict[str, Any] = {
        "base_url": path,
        "file_types": file_types,
        "enable_file_conversion": True,
    }
    return config, {}


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------


def _escape_env_value(value: str) -> str:
    """Escape a value for .env file if it contains special characters."""
    if any(c in value for c in ("=", "\n", '"', "'", " ", "\t", "#", "$", "`")):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def _write_env_file(
    path: Path,
    *,
    openai_key: str,
    qdrant_url: str,
    qdrant_api_key: str,
    collection_name: str,
    extra_vars: dict[str, str] | None = None,
) -> None:
    """Write the ``.env`` file.

    Only non-default values are emitted so the file stays minimal.

    Args:
        path: Destination path for the ``.env`` file.
        openai_key: OpenAI API key (always written).
        qdrant_url: Qdrant URL (written only when not the default localhost).
        qdrant_api_key: Qdrant API key (written only when non-empty).
        collection_name: Collection name (written only when not "documents").
        extra_vars: Additional environment variables from source-specific config.
    """
    lines: list[str] = [f"OPENAI_API_KEY={_escape_env_value(openai_key)}"]

    if qdrant_url and qdrant_url != "http://localhost:6333":
        lines.append(f"QDRANT_URL={_escape_env_value(qdrant_url)}")

    if qdrant_api_key:
        lines.append(f"QDRANT_API_KEY={_escape_env_value(qdrant_api_key)}")

    if collection_name and collection_name != "documents":
        lines.append(f"QDRANT_COLLECTION_NAME={_escape_env_value(collection_name)}")

    if extra_vars:
        lines.append("")
        for key, value in extra_vars.items():
            lines.append(f"{key}={_escape_env_value(value)}")

    lines.append("")  # trailing newline
    content = "\n".join(lines)

    # Write with restrictive permissions from the start
    import os

    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, content.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        # Fallback for platforms that don't support os.open mode (e.g., Windows)
        path.write_text(content, encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _write_config_file_multi(
    path: Path,
    *,
    sources: dict[str, dict[str, Any]],
) -> None:
    """Write the ``config.yaml`` file using the simplified format.

    Args:
        path: Destination path for ``config.yaml``.
        sources: Dict of source_type -> {source_name: source_config}.
    """
    import yaml

    config: dict[str, Any] = {"sources": sources}

    with path.open("w", encoding="utf-8") as fh:
        fh.write("# Generated by qdrant-loader setup\n")
        fh.write("# Simplified configuration format\n")
        fh.write("# See config.template.yaml for the full multi-project format.\n\n")
        yaml.dump(config, fh, default_flow_style=False, sort_keys=False)


def _write_config_file_advanced(
    path: Path,
    *,
    global_config: dict[str, Any],
    projects: dict[str, dict[str, Any]],
) -> None:
    """Write ``config.yaml`` using the advanced multi-project format.

    Args:
        path: Destination path for ``config.yaml``.
        global_config: Global configuration dict (qdrant, embedding, chunking).
        projects: Dict of project_id -> project config dict.
    """
    import yaml

    config: dict[str, Any] = {
        "global": global_config,
        "projects": projects,
    }

    with path.open("w", encoding="utf-8") as fh:
        fh.write("# Generated by qdrant-loader setup (advanced mode)\n")
        fh.write("# Multi-project configuration format\n")
        fh.write("# See config.template.yaml for all available options.\n\n")
        yaml.dump(config, fh, default_flow_style=False, sort_keys=False)
