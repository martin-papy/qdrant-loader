"""User-friendly configuration error formatting with Rich."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_stderr_console = Console(stderr=True)


def format_validation_errors(errors: list[dict[str, Any]]) -> Table:
    """Format Pydantic validation errors as a Rich table."""
    table = Table(title="Configuration Errors", show_lines=True)
    table.add_column("Field", style="red", no_wrap=True)
    table.add_column("Error", style="yellow")
    table.add_column("Suggestion", style="green")

    for err in errors:
        loc = " -> ".join(str(part) for part in err.get("loc", []))
        msg = err.get("msg", "Unknown error")
        suggestion = _suggest_fix(loc, msg)
        table.add_row(loc or "(root)", msg, suggestion)

    return table


def print_config_error(error: Exception) -> None:
    """Print a user-friendly configuration error to stderr using Rich."""
    try:
        from pydantic import ValidationError

        if isinstance(error, ValidationError):
            _stderr_console.print(
                Panel(
                    "[bold red]Configuration validation failed[/bold red]",
                    style="red",
                )
            )
            table = format_validation_errors(error.errors())
            _stderr_console.print(table)
            _stderr_console.print(
                "\n[dim]Tip: Run 'qdrant-loader setup' to generate a valid configuration.[/dim]"
            )
            return
    except ImportError:
        pass

    try:
        import yaml

        if isinstance(error, yaml.YAMLError):
            msg = "YAML syntax error in configuration file"
            mark = getattr(error, "problem_mark", None)
            if mark is not None:
                msg += f" at line {mark.line + 1}, column {mark.column + 1}"
            _stderr_console.print(
                Panel(
                    f"[bold red]{msg}[/bold red]\n\n"
                    f"[yellow]{str(error)}[/yellow]\n\n"
                    "[green]Suggestion:[/green] Check YAML syntax. Common issues:\n"
                    "  - Incorrect indentation (use spaces, not tabs)\n"
                    "  - Missing colons after keys\n"
                    "  - Unquoted special characters",
                    title="YAML Error",
                    style="red",
                )
            )
            return
    except ImportError:
        pass

    if isinstance(error, FileNotFoundError):
        _stderr_console.print(
            Panel(
                "[bold red]Configuration file not found[/bold red]\n\n"
                f"[yellow]{str(error)}[/yellow]\n\n"
                "[green]Suggestions:[/green]\n"
                "  - Run 'qdrant-loader setup' to generate configuration files\n"
                "  - Create config.yaml manually\n"
                "  - Specify path with --config flag",
                title="File Not Found",
                style="red",
            )
        )
        return

    if isinstance(error, ValueError):
        _stderr_console.print(
            Panel(
                "[bold red]Configuration error[/bold red]\n\n"
                f"[yellow]{str(error)}[/yellow]\n\n"
                f"[green]Suggestion:[/green] {_suggest_fix('', str(error))}",
                title="Validation Error",
                style="red",
            )
        )
        return

    # Generic fallback for any other exception type
    _stderr_console.print(
        Panel(
            "[bold red]Configuration error[/bold red]\n\n"
            f"[yellow]{type(error).__name__}: {str(error)}[/yellow]",
            title="Error",
            style="red",
        )
    )


def _suggest_fix(field: str, message: str) -> str:
    """Return a human-readable fix suggestion based on the error field and message."""
    msg_lower = message.lower()
    field_lower = field.lower()

    if "qdrant" in field_lower and "api_key" in field_lower:
        return "Set QDRANT_API_KEY in .env or environment"
    if "api_key" in field_lower or "api_key" in msg_lower:
        return "Set OPENAI_API_KEY in .env or environment"
    if "collection_name" in field_lower:
        return "Set QDRANT_COLLECTION_NAME or use default 'documents'"
    if "url" in field_lower and "qdrant" in field_lower:
        return "Set QDRANT_URL or use default http://localhost:6333"
    if "sources" in field_lower or "source" in msg_lower:
        return "Add at least one source under 'sources:' in config.yaml"
    if "database_path" in field_lower:
        return "Set STATE_DB_PATH or use default ./state.db"
    if "chunk_size" in field_lower or "chunk" in msg_lower:
        return "chunk_size must be a positive integer (recommended: 1000-2000)"
    if "required" in msg_lower:
        return f"Provide a value for '{field}' in config.yaml or .env"

    return "Check the configuration documentation"
