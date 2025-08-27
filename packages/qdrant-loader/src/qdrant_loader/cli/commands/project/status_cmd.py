from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


async def run_project_status(
    settings: Any,
    project_manager: Any,
    state_manager: Any,
    *,
    project_id: str | None,
    output_format: str,
) -> str:
    from rich.console import Console
    from rich.panel import Panel

    async def _get_document_count(pid: str) -> int:
        try:
            return await state_manager.get_project_document_count(pid)
        except Exception:
            return 0

    async def _get_latest_ingestion(pid: str) -> str | None:
        try:
            return await state_manager.get_project_latest_ingestion(pid)
        except Exception:
            return None

    if project_id:
        from click.exceptions import BadParameter

        context = project_manager.get_project_context(project_id)
        if context is None:
            raise BadParameter(f"Project not found: {project_id}")
        contexts = {project_id: context}
    else:
        contexts = project_manager.get_all_project_contexts()

    results = []
    for context in contexts.values():
        if not context:
            continue
        sources = context.config.sources if context.config else None
        # Safely sum lengths of available source collections; treat missing/None as empty
        if sources:
            names = ("publicdocs", "git", "confluence", "jira", "localfile")
            counts: list[int] = []
            for name in names:
                value = getattr(sources, name, None)
                if value is None:
                    counts.append(0)
                    continue
                if isinstance(value, Mapping):
                    counts.append(len(value))
                    continue
                # Any sequence/collection or object with __len__
                try:
                    counts.append(len(value))
                except Exception:
                    counts.append(0)
            source_count = sum(counts)
        else:
            source_count = 0
        document_count = await _get_document_count(context.project_id)
        latest_ingestion = await _get_latest_ingestion(context.project_id)
        results.append(
            {
                "project_id": context.project_id,
                "display_name": context.display_name or "N/A",
                "collection_name": context.collection_name or "N/A",
                "source_count": source_count,
                "document_count": document_count,
                "latest_ingestion": latest_ingestion,
            }
        )

    if output_format.lower() == "json":
        return json.dumps(results, indent=2)

    console = Console(record=True)
    for item in results:
        latest_ingestion_display = item["latest_ingestion"] or "Never"
        project_info = (
            f"[bold cyan]Project ID:[/bold cyan] {item['project_id']}\n"
            f"[bold magenta]Display Name:[/bold magenta] {item['display_name']}\n"
            f"[bold blue]Collection:[/bold blue] {item['collection_name']}\n"
            f"[bold yellow]Sources:[/bold yellow] {item['source_count']}\n"
            f"[bold red]Documents:[/bold red] {item['document_count']}\n"
            f"[bold red]Latest Ingestion:[/bold red] {latest_ingestion_display}"
        )
        console.print(Panel(project_info, title=f"Project: {item['project_id']}"))
    return console.export_text()
