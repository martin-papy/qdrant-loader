"""Resource management and shutdown coordination for the pipeline."""

import asyncio
import atexit
import concurrent.futures
import signal

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ResourceManager:
    """Manages resources, cleanup, and shutdown coordination."""

    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.active_tasks: set[asyncio.Task] = set()
        self.cleanup_done = False
        self.chunk_executor: concurrent.futures.ThreadPoolExecutor | None = None
        self._signal_shutdown = (
            False  # Flag to track if shutdown was triggered by signal
        )

    def set_chunk_executor(self, executor: concurrent.futures.ThreadPoolExecutor):
        """Set the chunk executor for cleanup."""
        self.chunk_executor = executor

    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _cleanup(self):
        """Clean up resources."""
        if self.cleanup_done:
            return

        try:
            logger.info("Cleaning up resources...")

            # Only set shutdown event if this is NOT a normal atexit cleanup
            # or if we're in signal-based shutdown mode
            if (
                self._signal_shutdown
                and hasattr(self, "shutdown_event")
                and not self.shutdown_event.is_set()
            ):
                try:
                    # Try to set shutdown event via running loop if available
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(self.shutdown_event.set)
                except RuntimeError:
                    # No running loop, run async cleanup directly
                    try:
                        asyncio.run(self._async_cleanup())
                    except Exception as e:
                        logger.error(f"Error in async cleanup: {e}")

            # Shutdown thread pool executor
            if self.chunk_executor:
                logger.debug("Shutting down chunk executor")
                self.chunk_executor.shutdown(wait=True)

            self.cleanup_done = True
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    async def _async_cleanup(self):
        """Async cleanup helper."""
        self.shutdown_event.set()

        # Cancel all active tasks
        if self.active_tasks:
            logger.info(f"Cancelling {len(self.active_tasks)} active tasks")
            for task in self.active_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_tasks, return_exceptions=True),
                    timeout=10.0,
                )
            except TimeoutError:
                logger.warning("Some tasks did not complete within timeout")

    def _handle_sigint(self, signum, frame):
        """Handle SIGINT signal."""
        # Prevent multiple signal handling
        if self.shutdown_event.is_set():
            logger.warning("Multiple SIGINT received, forcing immediate exit")
            self._force_immediate_exit()
            return

        logger.info("Received SIGINT, initiating shutdown...")
        self._signal_shutdown = True  # Mark as signal-based shutdown
        self.shutdown_event.set()

        # Try to schedule graceful shutdown
        try:
            loop = asyncio.get_running_loop()
            # Cancel all running tasks immediately
            loop.call_soon_threadsafe(self._cancel_all_tasks)
            # Schedule force shutdown
            loop.call_later(3.0, self._force_immediate_exit)
        except RuntimeError:
            # No running loop, do immediate cleanup and exit
            logger.warning("No event loop found, forcing immediate exit")
            self._cleanup()
            self._force_immediate_exit()

    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM signal."""
        if self.shutdown_event.is_set():
            logger.warning("Multiple SIGTERM received, forcing immediate exit")
            self._force_immediate_exit()
            return

        logger.info("Received SIGTERM, initiating shutdown...")
        self._signal_shutdown = True  # Mark as signal-based shutdown
        self.shutdown_event.set()

        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._cancel_all_tasks)
            loop.call_later(3.0, self._force_immediate_exit)
        except RuntimeError:
            logger.warning("No event loop found, forcing immediate exit")
            self._cleanup()
            self._force_immediate_exit()

    def _cancel_all_tasks(self):
        """Cancel all active tasks."""
        if self.active_tasks:
            logger.info(f"Cancelling {len(self.active_tasks)} active tasks")
            for task in self.active_tasks:
                if not task.done():
                    task.cancel()

    def _force_immediate_exit(self):
        """Force immediate exit."""
        import os

        logger.warning("Forcing immediate exit")
        try:
            # Try to cleanup first
            self._cleanup()
        except Exception as e:
            logger.error(f"Error during forced cleanup: {e}")
        finally:
            # Force exit
            os._exit(1)

    async def cleanup(self):
        """Clean up all resources."""
        await self._async_cleanup()

    def add_task(self, task: asyncio.Task):
        """Add a task to be tracked for cleanup."""
        self.active_tasks.add(task)
        task.add_done_callback(self.active_tasks.discard)
