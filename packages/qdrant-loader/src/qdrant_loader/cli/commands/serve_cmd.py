"""
qdrant-loader serve CLI command
Wires config, queue, worker pool, scheduler, HTTP server. Graceful SIGTERM/SIGINT.
"""

from __future__ import annotations

import asyncio
import signal
from pathlib import Path

import click
from click.types import Choice
from click.types import Path as ClickPath

from qdrant_loader.config.workspace import validate_workspace_flags


@click.command(
    "serve", help="Run the qdrant-loader service (scheduler, workers, HTTP server)"
)
@click.option(
    "--workspace",
    type=ClickPath(path_type=Path),
    help="Workspace directory containing config.yaml and .env files.",
)
@click.option(
    "--config",
    type=ClickPath(exists=True, path_type=Path),
    help="Path to config file.",
)
@click.option(
    "--env",
    type=ClickPath(exists=True, path_type=Path),
    help="Path to .env file.",
)
@click.option(
    "--log-level",
    type=Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Set the logging level.",
)
def serve_cmd(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    log_level: str,
):
    """Run the qdrant-loader service (scheduler + worker pool)."""
    asyncio.run(_serve_main(workspace, config, env, log_level))


async def _serve_main(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    log_level: str,
):
    from qdrant_loader.cli.config_loader import (
        load_config_with_workspace,
        setup_workspace,
    )
    from qdrant_loader.config import get_global_config, get_settings
    from qdrant_loader.core.pipeline.config import PipelineConfig
    from qdrant_loader.core.pipeline.factory import PipelineComponentsFactory
    from qdrant_loader.core.pipeline.orchestrator import PipelineOrchestrator
    from qdrant_loader.core.project_manager import ProjectManager
    from qdrant_loader.core.qdrant_manager import QdrantManager
    from qdrant_loader.core.state.state_manager import StateManager
    from qdrant_loader.core.worker.handlers import IngestionJobHandler
    from qdrant_loader.core.worker.pool import QueueWorkerPool
    from qdrant_loader.core.worker.queue import SQLiteJobQueue
    from qdrant_loader.core.worker.scheduler import IncrementalPullScheduler
    from qdrant_loader.utils.logging import LoggingConfig

    # Validate flag combinations
    validate_workspace_flags(workspace, config, env)

    # Setup workspace / logging
    workspace_config = None
    if workspace:
        workspace_config = setup_workspace(workspace)

    log_file = (
        str(workspace_config.logs_path / "serve.log")
        if workspace_config
        else "qdrant-loader.log"
    )
    LoggingConfig.setup(level=log_level, format="console", file=log_file)
    logger = LoggingConfig.get_logger(__name__)

    # Load configuration (required before get_global_config / get_settings)
    load_config_with_workspace(workspace_config, config, env)

    # Setup graceful shutdown
    stop_event = asyncio.Event()

    def _handle_signal(signum, _frame):
        logger.info("serve.signal_received", signum=signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("serve.config_loaded")
    config_obj = get_global_config()
    settings = get_settings()

    state_manager = None
    logger.info("serve.state_manager_init")
    state_manager = StateManager(config_obj.state_management)
    await state_manager.initialize()

    logger.info("serve.queue_init")
    session_factory = state_manager.session_factory
    job_queue = SQLiteJobQueue(session_factory)

    logger.info("serve.qdrant_init")
    qdrant_manager = QdrantManager(settings)

    logger.info("serve.pipeline_init")
    pipeline_factory = PipelineComponentsFactory()
    pipeline_config = PipelineConfig()
    pipeline_components = pipeline_factory.create_components(
        settings,
        pipeline_config,
        qdrant_manager,
        state_manager=state_manager,
    )

    logger.info("serve.project_manager_init")
    project_manager = ProjectManager(
        projects_config=settings.projects_config,
        global_collection_name=settings.global_config.qdrant.collection_name,
    )
    async with session_factory() as session:
        await project_manager.initialize(session)

    orchestrator = PipelineOrchestrator(settings, pipeline_components, project_manager)

    logger.info("serve.handler_init")

    job_handler = IngestionJobHandler(
        orchestrator=orchestrator,
        session_factory=session_factory,
    )

    worker_runtime = config_obj.workers.runtime
    logger.info(
        "serve.pool_init",
        worker_count=worker_runtime.worker_count,
        lease_seconds=worker_runtime.lease_seconds,
        max_attempts=worker_runtime.max_attempts,
        retry_backoff_base_seconds=worker_runtime.retry_backoff_base_seconds,
    )
    worker_pool = QueueWorkerPool(
        queue=job_queue,
        handler=job_handler,
        worker_count=worker_runtime.worker_count,
        lease_seconds=worker_runtime.lease_seconds,
        max_attempts=worker_runtime.max_attempts,
        retry_backoff_base_seconds=worker_runtime.retry_backoff_base_seconds,
    )

    logger.info("serve.scheduler_init")
    schedule = config_obj.workers.schedules.incremental_pull
    scheduler = IncrementalPullScheduler(
        queue=job_queue,
        projects_config=settings.projects_config,
        schedule=schedule,
    )

    logger.info("serve.starting")

    async def scheduler_task():
        await scheduler.run(stop_event)

    async def worker_pool_task():
        """Drain queue on job arrival or visibility timeout reclaim (every ~60s lease).

        Instead of polling every 1s, await job_queue.notify() which signals when:
        - A new job is enqueued (from scheduler or trigger).
        - A job is released for retry.

        Timeout (lease_seconds) ensures expired RUNNING jobs get reclaimed.
        """
        pending_event = job_queue.notify()
        lease_seconds = worker_runtime.lease_seconds

        while not stop_event.is_set():
            processed = await worker_pool.run_until_empty()

            # If no jobs were processed, wait for notification (with timeout for reclaim)
            if processed == 0:
                pending_event.clear()
                try:
                    await asyncio.wait_for(
                        pending_event.wait(),
                        timeout=lease_seconds,
                    )
                except TimeoutError:
                    # Timeout triggers visibility timeout reclaim:
                    # claim_next() will pick up expired RUNNING jobs
                    pass

    scheduler_runner = None
    worker_runner = None
    stop_waiter = None
    try:
        scheduler_runner = asyncio.create_task(scheduler_task())
        worker_runner = asyncio.create_task(worker_pool_task())
        stop_waiter = asyncio.create_task(stop_event.wait())

        done, _ = await asyncio.wait(
            {scheduler_runner, worker_runner, stop_waiter},
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Check for background task failures
        for task in (scheduler_runner, worker_runner):
            if task in done and (exc := task.exception()) is not None:
                logger.error(
                    "serve.background_task_failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise exc
    except Exception as exc:
        logger.error("serve.loop_error", error=str(exc))
        raise
    finally:
        logger.info("serve.shutting_down")
        for task in (scheduler_runner, worker_runner, stop_waiter):
            if task is not None:
                task.cancel()
        await asyncio.gather(
            *(
                t
                for t in (scheduler_runner, worker_runner, stop_waiter)
                if t is not None
            ),
            return_exceptions=True,
        )
        if state_manager is not None:
            await state_manager.dispose()
        logger.info("serve.shutdown_complete")
