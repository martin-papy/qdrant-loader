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
        str(workspace_config.logs_path) if workspace_config else "qdrant-loader.log"
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

    logger.info("serve.state_manager_init")
    state_manager = StateManager(config_obj.state_management)
    await state_manager.initialize()

    logger.info("serve.queue_init")
    job_queue = SQLiteJobQueue(state_manager._session_factory)

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
    session_factory = state_manager._session_factory
    if session_factory is None:
        raise RuntimeError("State manager session factory is not initialized")
    async with session_factory() as session:
        await project_manager.initialize(session)

    orchestrator = PipelineOrchestrator(settings, pipeline_components, project_manager)

    logger.info("serve.handler_init")

    def _session_context_factory():
        session_factory = state_manager._session_factory
        if session_factory is None:
            raise RuntimeError("State manager session factory is not initialized")
        return session_factory()

    job_handler = IngestionJobHandler(
        orchestrator=orchestrator,
        session_factory=_session_context_factory,
    )

    logger.info("serve.pool_init")
    worker_pool = QueueWorkerPool(
        queue=job_queue,
        handler=job_handler,
        worker_count=4,
        lease_seconds=60,
        max_attempts=1,
        retry_backoff_base_seconds=0,
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
        while not stop_event.is_set():
            await worker_pool.run_until_empty()
            await asyncio.sleep(1)

    tasks = [
        asyncio.create_task(scheduler_task()),
        asyncio.create_task(worker_pool_task()),
    ]

    try:
        await stop_event.wait()
    except Exception as exc:
        logger.error("serve.loop_error", error=str(exc))
    finally:
        logger.info("serve.shutting_down")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await state_manager.dispose()
        logger.info("serve.shutdown_complete")
