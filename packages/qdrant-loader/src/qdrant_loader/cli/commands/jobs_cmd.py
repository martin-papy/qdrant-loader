"""
qdrant-loader jobs admin CLI commands.

Subcommands: list [--status], retry <id>, trigger --source-type --source --mode, cancel <id>.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click
from click.exceptions import ClickException
from click.types import Choice
from click.types import Path as ClickPath

from qdrant_loader.core.worker.job_types import JobType


def _init_queue(workspace: Path | None, config: Path | None, env: Path | None):
    """Load config, build StateManager and SQLiteJobQueue. Returns (state_manager, queue)."""
    from qdrant_loader.cli.config_loader import (
        load_config_with_workspace,
        setup_workspace,
    )
    from qdrant_loader.config import get_global_config
    from qdrant_loader.config.workspace import validate_workspace_flags
    from qdrant_loader.core.state.state_manager import StateManager

    # Validate mutually exclusive flags early
    try:
        validate_workspace_flags(workspace, config, env)
    except ValueError as e:
        raise ClickException(str(e))

    if workspace:
        ws_config = setup_workspace(workspace)
        load_config_with_workspace(workspace_config=ws_config, skip_validation=True)
    else:
        resolved_config = config
        if resolved_config is None:
            default_config = Path("config.yaml")
            resolved_config = default_config if default_config.exists() else None
        if resolved_config is None:
            raise ClickException("No config found. Use --workspace or --config.")
        load_config_with_workspace(
            workspace_config=None,
            config_path=resolved_config,
            env_path=env,
            skip_validation=True,
        )

    global_config = get_global_config()
    state_manager = StateManager(global_config.state_management)
    return state_manager


async def _run_with_queue(workspace, config, env, coro_factory):
    """Initialize queue, run coro_factory(queue), dispose state manager."""
    state_manager = _init_queue(workspace, config, env)
    await state_manager.initialize()
    queue_instance = None
    try:
        from qdrant_loader.core.worker.queue import SQLiteJobQueue

        queue_instance = SQLiteJobQueue(state_manager._session_factory)
        return await coro_factory(queue_instance)
    finally:
        await state_manager.dispose()


# ────────────────────────────────────────────────
# Click group
# ────────────────────────────────────────────────


@click.group("jobs")
def jobs_cmd():
    """Inspect and manage background ingestion jobs."""


def _common_options(fn):
    """Decorator that adds --workspace, --config, --env options."""
    fn = click.option(
        "--workspace",
        type=ClickPath(path_type=Path),
        default=None,
        help="Workspace directory.",
    )(fn)
    fn = click.option(
        "--config",
        "config_path",
        type=ClickPath(path_type=Path),
        default=None,
        help="Path to config.yaml.",
    )(fn)
    fn = click.option(
        "--env",
        "env_path",
        type=ClickPath(path_type=Path),
        default=None,
        help="Path to .env file.",
    )(fn)
    return fn


# ────────────────────────────────────────────────
# jobs list
# ────────────────────────────────────────────────


@jobs_cmd.command("list")
@click.option(
    "--status",
    type=Choice(["pending", "running", "done", "failed"], case_sensitive=False),
    default=None,
    help="Filter by job status.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1, max=1000),
    default=50,
    show_default=True,
    help="Max rows to return.",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@_common_options
def jobs_list(status, limit, output_json, workspace, config_path, env_path):
    """List jobs, optionally filtered by status."""

    async def _list(queue):
        jobs = await queue.list(status=status, limit=limit)
        if output_json:
            rows = []
            for j in jobs:
                rows.append(
                    {
                        "id": j.id,
                        "type": j.type,
                        "status": j.status,
                        "attempts": j.attempts,
                        "enqueued_at": (
                            j.enqueued_at.isoformat() if j.enqueued_at else None
                        ),
                        "started_at": (
                            j.started_at.isoformat() if j.started_at else None
                        ),
                        "finished_at": (
                            j.finished_at.isoformat() if j.finished_at else None
                        ),
                        "last_error": j.last_error,
                        "payload": json.loads(j.payload_json) if j.payload_json else {},
                    }
                )
            click.echo(json.dumps(rows, indent=2))
        else:
            if not jobs:
                click.echo("No jobs found.")
                return
            header = f"{'ID':>6}  {'STATUS':<10}  {'TYPE':<20}  {'ATTEMPTS':>8}  {'ENQUEUED_AT':<27}  LAST_ERROR"
            click.echo(header)
            click.echo("-" * len(header))
            for j in jobs:
                enq = j.enqueued_at.isoformat() if j.enqueued_at else ""
                err = (j.last_error or "")[:40]
                click.echo(
                    f"{j.id:>6}  {j.status:<10}  {j.type:<20}  {j.attempts:>8}  {enq:<27}  {err}"
                )

    asyncio.run(_run_with_queue(workspace, config_path, env_path, _list))


# ────────────────────────────────────────────────
# jobs retry
# ────────────────────────────────────────────────


@jobs_cmd.command("retry")
@click.argument("job_id", type=int)
@_common_options
def jobs_retry(job_id, workspace, config_path, env_path):
    """Reset a failed or done job back to pending."""

    async def _retry(queue):
        ok = await queue.reset_to_pending(job_id)
        if ok:
            click.echo(f"Job {job_id} reset to pending.")
        else:
            raise ClickException(
                f"Job {job_id} not found or is not in failed/done state."
            )

    asyncio.run(_run_with_queue(workspace, config_path, env_path, _retry))


# ────────────────────────────────────────────────
# jobs trigger
# ────────────────────────────────────────────────


@jobs_cmd.command("trigger")
@click.option(
    "--source-type", required=True, help="Source type (e.g. git, confluence)."
)
@click.option("--source", required=True, help="Source name as configured.")
@click.option(
    "--mode",
    type=Choice(["bulk", "incremental"], case_sensitive=False),
    required=True,
    help="Ingestion mode.",
)
@click.option("--project", "project_id", required=True, help="Project ID.")
@_common_options
def jobs_trigger(
    source_type, source, mode, project_id, workspace, config_path, env_path
):
    """Enqueue a new ingestion job immediately."""

    async def _trigger(queue):
        job_type = (
            JobType.BULK_INGEST if mode.lower() == "bulk" else JobType.INCREMENTAL_PULL
        )
        payload = {
            "project_id": project_id,
            "source_type": source_type,
            "source": source,
            "source_lock": f"{project_id}:{source_type}:{source}",
        }
        job = await queue.enqueue(job_type, payload)
        click.echo(f"Enqueued job {job.id} (type={job_type}, status={job.status}).")

    asyncio.run(_run_with_queue(workspace, config_path, env_path, _trigger))


# ────────────────────────────────────────────────
# jobs cancel
# ────────────────────────────────────────────────


@jobs_cmd.command("cancel")
@click.argument("job_id", type=int)
@_common_options
def jobs_cancel(job_id, workspace, config_path, env_path):
    """Cancel a pending or running job."""

    async def _cancel(queue):
        ok = await queue.cancel(job_id)
        if ok:
            click.echo(f"Job {job_id} cancelled.")
        else:
            raise ClickException(
                f"Job {job_id} not found or is not in pending/running state."
            )

    asyncio.run(_run_with_queue(workspace, config_path, env_path, _cancel))
