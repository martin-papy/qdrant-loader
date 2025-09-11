from __future__ import annotations

import asyncio
import signal
from pathlib import Path

from click.exceptions import ClickException

from qdrant_loader.cli.async_utils import cancel_all_tasks
from qdrant_loader.cli.config_loader import (
    load_config_with_workspace,
    setup_workspace,
)
from qdrant_loader.config.workspace import validate_workspace_flags
from qdrant_loader.utils.logging import LoggingConfig

from . import run_pipeline_ingestion

# Backward-compatibility aliases for tests expecting underscored names
_load_config_with_workspace = load_config_with_workspace
_setup_workspace_impl = setup_workspace
_run_ingest_pipeline = run_pipeline_ingestion
_cancel_all_tasks_helper = cancel_all_tasks


async def run_ingest_command(
    workspace: Path | None,
    config: Path | None,
    env: Path | None,
    project: str | None,
    source_type: str | None,
    source: str | None,
    log_level: str,
    profile: bool,
    force: bool,
) -> None:
    """Implementation for the `ingest` CLI command with identical behavior."""

    try:
        # Validate flag combinations
        validate_workspace_flags(workspace, config, env)

        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = _setup_workspace_impl(workspace)

        # Setup/reconfigure logging with workspace support
        log_file = (
            str(workspace_config.logs_path) if workspace_config else "qdrant-loader.log"
        )
        if getattr(LoggingConfig, "reconfigure", None):  # type: ignore[attr-defined]
            if getattr(LoggingConfig, "_initialized", False):  # type: ignore[attr-defined]
                LoggingConfig.reconfigure(file=log_file)  # type: ignore[attr-defined]
            else:
                LoggingConfig.setup(level=log_level, format="console", file=log_file)
        else:
            import logging as _py_logging

            _py_logging.getLogger().handlers = []
            LoggingConfig.setup(level=log_level, format="console", file=log_file)

        # Load configuration
        _load_config_with_workspace(workspace_config, config, env)
        from qdrant_loader.config import get_settings

        settings = get_settings()
        if settings is None:
            LoggingConfig.get_logger(__name__).error("settings_not_available")
            raise ClickException("Settings not available")

        # Lazy import to avoid slow startup
        from qdrant_loader.core.qdrant_manager import QdrantManager

        qdrant_manager = QdrantManager(settings)

        async def _do_run():
            await _run_ingest_pipeline(
                settings,
                qdrant_manager,
                project=project,
                source_type=source_type,
                source=source,
                force=force,
                metrics_dir=(
                    str(workspace_config.metrics_path) if workspace_config else None
                ),
            )

        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def _handle_sigint():
            logger = LoggingConfig.get_logger(__name__)
            logger.debug(" SIGINT received, cancelling all tasks...")
            stop_event.set()
            # Schedule cancellation of all running tasks safely on the event loop thread
            loop.call_soon_threadsafe(
                lambda: loop.create_task(_cancel_all_tasks_helper())
            )

        try:
            loop.add_signal_handler(signal.SIGINT, _handle_sigint)
        except NotImplementedError:

            def _signal_handler(_signum, _frame):
                logger = LoggingConfig.get_logger(__name__)
                logger.debug(" SIGINT received on Windows, cancelling all tasks...")
                loop.call_soon_threadsafe(stop_event.set)
                # Ensure the coroutine runs on the correct loop without race conditions
                asyncio.run_coroutine_threadsafe(_cancel_all_tasks_helper(), loop)

            signal.signal(signal.SIGINT, _signal_handler)

        try:
            if profile:
                import cProfile

                profiler = cProfile.Profile()
                profiler.enable()
                try:
                    await _do_run()
                finally:
                    profiler.disable()
                    profiler.dump_stats("profile.out")
                    LoggingConfig.get_logger(__name__).info(
                        "Profile saved to profile.out"
                    )
            else:
                await _do_run()

            logger = LoggingConfig.get_logger(__name__)
            logger.info("Pipeline finished, awaiting cleanup.")
            pending = [
                t
                for t in asyncio.all_tasks()
                if t is not asyncio.current_task() and not t.done()
            ]
            if pending:
                logger.debug(f" Awaiting {len(pending)} pending tasks before exit...")
                results = await asyncio.gather(*pending, return_exceptions=True)
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            "Pending task failed during shutdown",
                            task_index=idx,
                            error=str(result),
                            error_type=type(result).__name__,
                            exc_info=True,
                        )
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # Preserve cancellation semantics so Ctrl+C results in a normal exit
            raise
        except Exception as e:
            logger = LoggingConfig.get_logger(__name__)
            error_msg = (
                str(e) if str(e) else f"Empty exception of type: {type(e).__name__}"
            )
            logger.error(
                "Document ingestion process failed during execution",
                error=error_msg,
                error_type=type(e).__name__,
                suggestion=(
                    "Check data sources, configuration, and system resources. "
                    "Run 'qdrant-loader project validate' to verify setup"
                ),
                exc_info=True,
            )
            raise ClickException(f"Failed to run ingestion: {error_msg}") from e
        finally:
            if stop_event.is_set():
                logger = LoggingConfig.get_logger(__name__)
                logger.debug(
                    " Cancellation already initiated by SIGINT; exiting gracefully."
                )

    except asyncio.CancelledError:
        # Bubble up cancellation to the caller/CLI, do not convert to ClickException
        raise
    except ClickException:
        raise
    except Exception as e:
        logger = LoggingConfig.get_logger(__name__)
        error_msg = str(e) if str(e) else f"Empty exception of type: {type(e).__name__}"
        logger.error(
            "Unexpected error during ingestion command execution",
            error=error_msg,
            error_type=type(e).__name__,
            suggestion="Check logs above for specific error details and verify system configuration",
            exc_info=True,
        )
        raise ClickException(f"Failed to run ingestion: {error_msg}") from e
