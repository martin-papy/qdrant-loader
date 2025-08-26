from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def run_project_list(settings: Any, project_manager: Any, *, output_format: str) -> str:
    """Return project list in the requested format (json or table as text)."""
    from rich.console import Console
    from rich.table import Table

    def _gather() -> list[dict[str, str | int]]:
        projects_data = []
        contexts = project_manager.get_all_project_contexts()
        for context in contexts.values():
            sources = context.config.sources if context.config else None
            # Safely sum lengths of available source collections; treat missing/None as empty
            if sources:
                if isinstance(sources, Mapping):
                    source_count = sum(
                        len(sources.get(name, {}) or {})
                        for name in (
                            "publicdocs",
                            "git",
                            "confluence",
                            "jira",
                            "localfile",
                        )
                    )
                else:
                    source_count = sum(
                        len(getattr(sources, name, {}) or {})
                        for name in (
                            "publicdocs",
                            "git",
                            "confluence",
                            "jira",
                            "localfile",
                        )
                    )
            else:
                source_count = 0
            projects_data.append(
                {
                    "project_id": context.project_id,
                    "display_name": context.display_name or "N/A",
                    "description": context.description or "N/A",
                    "collection_name": context.collection_name or "N/A",
                    "source_count": source_count,
                }
            )
        return projects_data

    data = _gather()
    if output_format.lower() == "json":
        return json.dumps(data, indent=2)

    # table output
    table = Table(title="Configured Projects")
    table.add_column("Project ID", style="cyan", no_wrap=True)
    table.add_column("Display Name", style="magenta")
    table.add_column("Description", style="green")
    table.add_column("Collection", style="blue")
    table.add_column("Sources", justify="right", style="yellow")

    for item in data:
        table.add_row(
            str(item["project_id"]),
            str(item["display_name"]),
            str(item["description"]),
            str(item["collection_name"]),
            str(item["source_count"]),
        )
    console = Console(record=True)
    console.print(table)
    return console.export_text()
