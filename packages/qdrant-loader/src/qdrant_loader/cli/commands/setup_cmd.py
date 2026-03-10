"""Interactive setup wizard for qdrant-loader configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

SOURCE_TYPES: dict[str, str] = {
    "git": "Git Repository",
    "confluence": "Confluence Wiki",
    "jira": "Jira Issues",
    "publicdocs": "Public Documentation (website)",
    "localfile": "Local Files",
}

# Returned by every _collect_*_config helper: (yaml-ready dict, extra env vars dict)
_SourceResult = tuple[dict[str, Any], dict[str, str]]


def run_setup_wizard(output_dir: Path) -> None:
    """Run the interactive setup wizard.

    Prompts the user for core settings and source-specific details, then writes
    a ``config.yaml`` and ``.env`` file to *output_dir*.

    Args:
        output_dir: Directory in which the generated files are placed.
    """
    output_dir = Path(output_dir).resolve()

    console.print(
        Panel(
            "[bold]qdrant-loader Setup Wizard[/bold]\n"
            "Generate config.yaml and .env for your project.",
            style="blue",
        )
    )

    # ------------------------------------------------------------------
    # Step 1: Core settings
    # ------------------------------------------------------------------
    console.print("\n[bold cyan]Step 1: Core Settings[/bold cyan]")

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

    while True:
        console.print("\n[bold cyan]Step 2: Data Source[/bold cyan]")

        table = Table(title="Available Source Types")
        table.add_column("Key", style="green")
        table.add_column("Description")
        for key, desc in SOURCE_TYPES.items():
            table.add_row(key, desc)
        console.print(table)

        source_type: str = click.prompt(
            "Select source type",
            type=click.Choice(list(SOURCE_TYPES.keys())),
        )

        console.print(
            f"\n[bold cyan]Step 3: Configure {SOURCE_TYPES[source_type]}[/bold cyan]"
        )
        source_name: str = click.prompt(
            "Source name (identifier)", default=f"my-{source_type}"
        )
        source_config, extra_env = _collect_source_config(source_type)

        # Merge into all_sources
        if source_type not in all_sources:
            all_sources[source_type] = {}
        all_sources[source_type][source_name] = source_config
        all_extra_env.update(extra_env)

        console.print(f"[green]Added {source_type}/{source_name}[/green]")

        if not click.confirm("Add another source?", default=False):
            break

    # ------------------------------------------------------------------
    # Step 4: Confirm output paths and write files
    # ------------------------------------------------------------------
    config_path = output_dir / "config.yaml"
    env_path = output_dir / ".env"

    for path in [config_path, env_path]:
        if path.exists():
            if not click.confirm(f"{path.name} already exists. Overwrite?"):
                console.print("[yellow]Setup cancelled.[/yellow]")
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

    console.print(
        Panel(
            f"[green]Created:[/green]\n"
            f"  - {config_path}\n"
            f"  - {env_path}\n"
            f"  - Sources: {source_summary}\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  1. Review the generated files\n"
            f"  2. Run: qdrant-loader init\n"
            f"  3. Run: qdrant-loader ingest",
            title="Setup Complete",
            style="green",
        )
    )


# ---------------------------------------------------------------------------
# Source-specific config collectors
# ---------------------------------------------------------------------------


def _collect_source_config(source_type: str) -> _SourceResult:
    """Dispatch to the correct collector based on *source_type*.

    Args:
        source_type: One of the keys in ``SOURCE_TYPES``.

    Returns:
        A tuple of (source yaml dict, extra env-var dict).
    """
    collectors = {
        "git": _collect_git_config,
        "confluence": _collect_confluence_config,
        "jira": _collect_jira_config,
        "publicdocs": _collect_publicdocs_config,
        "localfile": _collect_localfile_config,
    }
    collector = collectors.get(source_type)
    if collector is None:
        return {}, {}
    return collector()


def _collect_git_config() -> _SourceResult:
    """Collect Git repository source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    url: str = click.prompt(
        "Repository URL (e.g., https://github.com/org/repo.git)"
    )
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
    }
    extra_env: dict[str, str] = {}

    if token:
        config["token"] = "${REPO_TOKEN}"
        extra_env["REPO_TOKEN"] = token

    return config, extra_env


def _collect_confluence_config() -> _SourceResult:
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

    config: dict[str, Any] = {
        "base_url": base_url,
        "space_key": space_key,
        "token": "${CONFLUENCE_TOKEN}",
        "email": "${CONFLUENCE_EMAIL}",
    }
    extra_env: dict[str, str] = {
        "CONFLUENCE_TOKEN": token,
        "CONFLUENCE_EMAIL": email,
    }
    return config, extra_env


def _collect_jira_config() -> _SourceResult:
    """Collect Jira source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    base_url: str = click.prompt(
        "Jira URL (e.g., https://mycompany.atlassian.net)"
    )
    project_key: str = click.prompt("Project key")
    email: str = click.prompt("Email")
    token: str = click.prompt("API token", hide_input=True)

    config: dict[str, Any] = {
        "base_url": base_url,
        "project_key": project_key,
        "token": "${JIRA_TOKEN}",
        "email": "${JIRA_EMAIL}",
    }
    extra_env: dict[str, str] = {
        "JIRA_TOKEN": token,
        "JIRA_EMAIL": email,
    }
    return config, extra_env


def _collect_publicdocs_config() -> _SourceResult:
    """Collect Public Documentation source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    base_url: str = click.prompt(
        "Documentation URL (e.g., https://docs.example.com/)"
    )
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


def _collect_localfile_config() -> _SourceResult:
    """Collect Local Files source configuration.

    Returns:
        Tuple of (source config dict, extra env vars).
    """
    path: str = click.prompt(
        "Directory path (e.g., /path/to/files or file:///path)"
    )
    if not path.startswith("file://"):
        path = f"file://{path}"

    file_types_raw: str = click.prompt(
        "File types (comma-separated)", default="*.md,*.txt,*.py"
    )
    file_types = [ft.strip() for ft in file_types_raw.split(",") if ft.strip()]

    config: dict[str, Any] = {
        "base_url": path,
        "file_types": file_types,
    }
    return config, {}


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------


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
    lines: list[str] = [f"OPENAI_API_KEY={openai_key}"]

    if qdrant_url and qdrant_url != "http://localhost:6333":
        lines.append(f"QDRANT_URL={qdrant_url}")

    if qdrant_api_key:
        lines.append(f"QDRANT_API_KEY={qdrant_api_key}")

    if collection_name and collection_name != "documents":
        lines.append(f"QDRANT_COLLECTION_NAME={collection_name}")

    if extra_vars:
        lines.append("")
        for key, value in extra_vars.items():
            lines.append(f"{key}={value}")

    lines.append("")  # trailing newline
    path.write_text("\n".join(lines), encoding="utf-8")


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
        fh.write(
            "# See config.template.yaml for the full multi-project format.\n\n"
        )
        yaml.dump(config, fh, default_flow_style=False, sort_keys=False)
