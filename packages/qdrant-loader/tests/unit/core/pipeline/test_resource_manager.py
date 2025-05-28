"""Tests for ResourceManager module."""

import asyncio
import concurrent.futures
import signal
from unittest.mock import Mock, call, patch

import pytest
from qdrant_loader.core.pipeline.resource_manager import ResourceManager


class TestResourceManager:
    """Test ResourceManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resource_manager = ResourceManager()

    def test_resource_manager_initialization(self):
        """Test ResourceManager initialization."""
        assert isinstance(self.resource_manager.shutdown_event, asyncio.Event)
        assert self.resource_manager.active_tasks == set()
        assert self.resource_manager.cleanup_done is False
        assert self.resource_manager.chunk_executor is None

    def test_set_chunk_executor(self):
        """Test setting chunk executor."""
        mock_executor = Mock(spec=concurrent.futures.ThreadPoolExecutor)

        self.resource_manager.set_chunk_executor(mock_executor)

        assert self.resource_manager.chunk_executor == mock_executor

    @patch("atexit.register")
    @patch("signal.signal")
    def test_register_signal_handlers(self, mock_signal, mock_atexit):
        """Test signal handler registration."""
        self.resource_manager.register_signal_handlers()

        # Verify atexit registration
        mock_atexit.assert_called_once_with(self.resource_manager._cleanup)

        # Verify signal handler registration
        expected_calls = [
            call(signal.SIGINT, self.resource_manager._handle_sigint),
            call(signal.SIGTERM, self.resource_manager._handle_sigterm),
        ]
        mock_signal.assert_has_calls(expected_calls)

    def test_cleanup_already_done(self):
        """Test cleanup when already completed."""
        self.resource_manager.cleanup_done = True

        with patch.object(self.resource_manager, "shutdown_event") as mock_event:
            self.resource_manager._cleanup()

            # Should return early without doing anything
            mock_event.is_set.assert_not_called()

    @patch("asyncio.get_running_loop")
    def test_cleanup_with_running_loop(self, mock_get_loop):
        """Test cleanup with running event loop."""
        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        # Setup shutdown event
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = False

        # Setup chunk executor
        mock_executor = Mock(spec=concurrent.futures.ThreadPoolExecutor)
        self.resource_manager.chunk_executor = mock_executor

        self.resource_manager._cleanup()

        # Verify shutdown event is set via loop
        mock_loop.call_soon_threadsafe.assert_called_once_with(
            self.resource_manager.shutdown_event.set
        )

        # Verify executor shutdown
        mock_executor.shutdown.assert_called_once_with(wait=True)

        # Verify cleanup completion
        assert self.resource_manager.cleanup_done is True

    @patch("asyncio.get_running_loop")
    @patch("asyncio.run")
    def test_cleanup_no_running_loop(self, mock_asyncio_run, mock_get_loop):
        """Test cleanup without running event loop."""
        mock_get_loop.side_effect = RuntimeError("No running loop")

        # Setup shutdown event
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = False

        self.resource_manager._cleanup()

        # Verify async cleanup is called (check that it was called, not the exact coroutine object)
        mock_asyncio_run.assert_called_once()
        # Verify the call was made with a coroutine
        call_args = mock_asyncio_run.call_args[0][0]
        assert hasattr(call_args, "__await__")  # It's a coroutine

        assert self.resource_manager.cleanup_done is True

    @patch("asyncio.get_running_loop")
    @patch("asyncio.run")
    def test_cleanup_async_cleanup_exception(self, mock_asyncio_run, mock_get_loop):
        """Test cleanup when async cleanup raises exception."""
        mock_get_loop.side_effect = RuntimeError("No running loop")
        mock_asyncio_run.side_effect = Exception("Async cleanup failed")

        # Setup shutdown event
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = False

        # Manually mock _async_cleanup to return a regular value, not a coroutine
        self.resource_manager._async_cleanup = Mock(return_value=None)

        with patch(
            "qdrant_loader.core.pipeline.resource_manager.logger"
        ) as mock_logger:
            self.resource_manager._cleanup()

            # Verify asyncio.run was called (the exception will be caught)
            mock_asyncio_run.assert_called_once()

            # Verify error is logged
            mock_logger.error.assert_called_with(
                "Error in async cleanup: Async cleanup failed"
            )

    def test_cleanup_exception_handling(self):
        """Test cleanup exception handling."""
        # Force an exception during cleanup
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.side_effect = Exception(
            "Test exception"
        )

        with patch(
            "qdrant_loader.core.pipeline.resource_manager.logger"
        ) as mock_logger:
            # Mock asyncio.run to prevent the coroutine warning
            with patch("asyncio.run"):
                self.resource_manager._cleanup()

                # Verify error is logged
                mock_logger.error.assert_called_with(
                    "Error during cleanup: Test exception"
                )

    @pytest.mark.asyncio
    async def test_async_cleanup_success(self):
        """Test successful async cleanup."""
        # Setup shutdown event
        self.resource_manager.shutdown_event = Mock()

        # Setup active tasks
        mock_task1 = Mock(spec=asyncio.Task)
        mock_task1.done.return_value = False
        mock_task2 = Mock(spec=asyncio.Task)
        mock_task2.done.return_value = True  # Already done

        self.resource_manager.active_tasks = {mock_task1, mock_task2}

        with patch("asyncio.wait_for") as mock_wait_for:
            with patch("asyncio.gather") as mock_gather:
                await self.resource_manager._async_cleanup()

                # Verify shutdown event is set
                self.resource_manager.shutdown_event.set.assert_called_once()

                # Verify only non-done task is cancelled
                mock_task1.cancel.assert_called_once()
                mock_task2.cancel.assert_not_called()

                # Verify gather is called with all tasks (order doesn't matter for sets)
                mock_gather.assert_called_once()
                call_args = mock_gather.call_args[0]
                call_kwargs = mock_gather.call_args[1]
                assert set(call_args) == {mock_task1, mock_task2}
                assert call_kwargs == {"return_exceptions": True}
                mock_wait_for.assert_called_once_with(
                    mock_gather.return_value, timeout=10.0
                )

    @pytest.mark.asyncio
    async def test_async_cleanup_timeout(self):
        """Test async cleanup with timeout."""
        # Setup shutdown event
        self.resource_manager.shutdown_event = Mock()

        # Setup active tasks
        mock_task = Mock(spec=asyncio.Task)
        mock_task.done.return_value = False
        self.resource_manager.active_tasks = {mock_task}

        with patch("asyncio.wait_for") as mock_wait_for:
            with patch("asyncio.gather"):
                with patch(
                    "qdrant_loader.core.pipeline.resource_manager.logger"
                ) as mock_logger:
                    # Simulate timeout
                    mock_wait_for.side_effect = TimeoutError()

                    await self.resource_manager._async_cleanup()

                    # Verify warning is logged
                    mock_logger.warning.assert_called_with(
                        "Some tasks did not complete within timeout"
                    )

    @pytest.mark.asyncio
    async def test_async_cleanup_no_active_tasks(self):
        """Test async cleanup with no active tasks."""
        # Setup shutdown event
        self.resource_manager.shutdown_event = Mock()

        # No active tasks
        self.resource_manager.active_tasks = set()

        with patch("asyncio.wait_for") as mock_wait_for:
            await self.resource_manager._async_cleanup()

            # Verify shutdown event is set
            self.resource_manager.shutdown_event.set.assert_called_once()

            # Verify no wait_for call since no tasks
            mock_wait_for.assert_not_called()

    @patch("asyncio.get_running_loop")
    def test_handle_sigint_first_time(self, mock_get_loop):
        """Test SIGINT handler on first signal."""
        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        # Setup shutdown event as not set
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = False

        with patch(
            "qdrant_loader.core.pipeline.resource_manager.logger"
        ) as mock_logger:
            self.resource_manager._handle_sigint(signal.SIGINT, None)

            # Verify shutdown event is set
            self.resource_manager.shutdown_event.set.assert_called_once()

            # Verify loop calls
            mock_loop.call_soon_threadsafe.assert_called_once_with(
                self.resource_manager._cancel_all_tasks
            )
            mock_loop.call_later.assert_called_once_with(
                3.0, self.resource_manager._force_immediate_exit
            )

            # Verify log message
            mock_logger.info.assert_called_with(
                "Received SIGINT, initiating shutdown..."
            )

    def test_handle_sigint_multiple_signals(self):
        """Test SIGINT handler on multiple signals."""
        # Setup shutdown event as already set
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = True

        # Mock _cleanup to prevent async cleanup coroutine creation
        self.resource_manager._cleanup = Mock()

        with patch.object(
            self.resource_manager, "_force_immediate_exit"
        ) as mock_force_exit:
            with patch(
                "qdrant_loader.core.pipeline.resource_manager.logger"
            ) as mock_logger:
                self.resource_manager._handle_sigint(signal.SIGINT, None)

                # Verify immediate exit is forced
                mock_force_exit.assert_called_once()

                # Verify warning message
                mock_logger.warning.assert_called_with(
                    "Multiple SIGINT received, forcing immediate exit"
                )

    @patch("asyncio.get_running_loop")
    def test_handle_sigint_no_running_loop(self, mock_get_loop):
        """Test SIGINT handler with no running loop."""
        mock_get_loop.side_effect = RuntimeError("No running loop")

        # Setup shutdown event as not set
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = False

        with patch.object(self.resource_manager, "_cleanup") as mock_cleanup:
            with patch.object(
                self.resource_manager, "_force_immediate_exit"
            ) as mock_force_exit:
                with patch(
                    "qdrant_loader.core.pipeline.resource_manager.logger"
                ) as mock_logger:
                    self.resource_manager._handle_sigint(signal.SIGINT, None)

                    # Verify cleanup and force exit are called
                    mock_cleanup.assert_called_once()
                    mock_force_exit.assert_called_once()

                    # Verify warning message
                    mock_logger.warning.assert_called_with(
                        "No event loop found, forcing immediate exit"
                    )

    @patch("asyncio.get_running_loop")
    def test_handle_sigterm_first_time(self, mock_get_loop):
        """Test SIGTERM handler on first signal."""
        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop

        # Setup shutdown event as not set
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = False

        with patch(
            "qdrant_loader.core.pipeline.resource_manager.logger"
        ) as mock_logger:
            self.resource_manager._handle_sigterm(signal.SIGTERM, None)

            # Verify shutdown event is set
            self.resource_manager.shutdown_event.set.assert_called_once()

            # Verify loop calls
            mock_loop.call_soon_threadsafe.assert_called_once_with(
                self.resource_manager._cancel_all_tasks
            )
            mock_loop.call_later.assert_called_once_with(
                3.0, self.resource_manager._force_immediate_exit
            )

            # Verify log message
            mock_logger.info.assert_called_with(
                "Received SIGTERM, initiating shutdown..."
            )

    def test_handle_sigterm_multiple_signals(self):
        """Test SIGTERM handler on multiple signals."""
        # Setup shutdown event as already set
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = True

        # Mock _cleanup to prevent async cleanup coroutine creation
        self.resource_manager._cleanup = Mock()

        with patch.object(
            self.resource_manager, "_force_immediate_exit"
        ) as mock_force_exit:
            with patch(
                "qdrant_loader.core.pipeline.resource_manager.logger"
            ) as mock_logger:
                self.resource_manager._handle_sigterm(signal.SIGTERM, None)

                # Verify immediate exit is forced
                mock_force_exit.assert_called_once()

                # Verify warning message
                mock_logger.warning.assert_called_with(
                    "Multiple SIGTERM received, forcing immediate exit"
                )

    @patch("asyncio.get_running_loop")
    def test_handle_sigterm_no_running_loop(self, mock_get_loop):
        """Test SIGTERM handler with no running loop."""
        mock_get_loop.side_effect = RuntimeError("No running loop")

        # Setup shutdown event as not set
        self.resource_manager.shutdown_event = Mock()
        self.resource_manager.shutdown_event.is_set.return_value = False

        with patch.object(self.resource_manager, "_cleanup") as mock_cleanup:
            with patch.object(
                self.resource_manager, "_force_immediate_exit"
            ) as mock_force_exit:
                with patch(
                    "qdrant_loader.core.pipeline.resource_manager.logger"
                ) as mock_logger:
                    self.resource_manager._handle_sigterm(signal.SIGTERM, None)

                    # Verify cleanup and force exit are called
                    mock_cleanup.assert_called_once()
                    mock_force_exit.assert_called_once()

                    # Verify warning message
                    mock_logger.warning.assert_called_with(
                        "No event loop found, forcing immediate exit"
                    )

    def test_cancel_all_tasks_with_active_tasks(self):
        """Test cancelling all active tasks."""
        # Setup active tasks
        mock_task1 = Mock(spec=asyncio.Task)
        mock_task1.done.return_value = False
        mock_task2 = Mock(spec=asyncio.Task)
        mock_task2.done.return_value = True  # Already done

        self.resource_manager.active_tasks = {mock_task1, mock_task2}

        with patch(
            "qdrant_loader.core.pipeline.resource_manager.logger"
        ) as mock_logger:
            self.resource_manager._cancel_all_tasks()

            # Verify only non-done task is cancelled
            mock_task1.cancel.assert_called_once()
            mock_task2.cancel.assert_not_called()

            # Verify log message
            mock_logger.info.assert_called_with("Cancelling 2 active tasks")

    def test_cancel_all_tasks_no_active_tasks(self):
        """Test cancelling tasks when none are active."""
        self.resource_manager.active_tasks = set()

        with patch(
            "qdrant_loader.core.pipeline.resource_manager.logger"
        ) as mock_logger:
            self.resource_manager._cancel_all_tasks()

            # Verify no log message since no tasks
            mock_logger.info.assert_not_called()

    @patch("os._exit")
    def test_force_immediate_exit_success(self, mock_os_exit):
        """Test force immediate exit with successful cleanup."""
        with patch.object(self.resource_manager, "_cleanup") as mock_cleanup:
            with patch(
                "qdrant_loader.core.pipeline.resource_manager.logger"
            ) as mock_logger:
                # Mock asyncio.run to prevent coroutine warning
                with patch("asyncio.run"):
                    self.resource_manager._force_immediate_exit()

                    # Verify cleanup is attempted
                    mock_cleanup.assert_called_once()

                    # Verify warning message
                    mock_logger.warning.assert_called_with("Forcing immediate exit")

                    # Verify os._exit is called
                    mock_os_exit.assert_called_once_with(1)

    @patch("os._exit")
    def test_force_immediate_exit_cleanup_exception(self, mock_os_exit):
        """Test force immediate exit with cleanup exception."""
        with patch.object(self.resource_manager, "_cleanup") as mock_cleanup:
            mock_cleanup.side_effect = Exception("Cleanup failed")

            with patch(
                "qdrant_loader.core.pipeline.resource_manager.logger"
            ) as mock_logger:
                self.resource_manager._force_immediate_exit()

                # Verify cleanup is attempted
                mock_cleanup.assert_called_once()

                # Verify error is logged
                mock_logger.error.assert_called_with(
                    "Error during forced cleanup: Cleanup failed"
                )

                # Verify os._exit is still called
                mock_os_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_cleanup_method(self):
        """Test public cleanup method."""
        with patch.object(
            self.resource_manager, "_async_cleanup"
        ) as mock_async_cleanup:
            await self.resource_manager.cleanup()

            mock_async_cleanup.assert_called_once()

    def test_add_task(self):
        """Test adding task for tracking."""
        mock_task = Mock(spec=asyncio.Task)

        self.resource_manager.add_task(mock_task)

        # Verify task is added to active tasks
        assert mock_task in self.resource_manager.active_tasks

        # Verify done callback is added
        mock_task.add_done_callback.assert_called_once_with(
            self.resource_manager.active_tasks.discard
        )

    def test_add_task_callback_removes_task(self):
        """Test that task callback removes task from active set."""
        mock_task = Mock(spec=asyncio.Task)

        self.resource_manager.add_task(mock_task)

        # Get the callback that was registered
        callback = mock_task.add_done_callback.call_args[0][0]

        # Verify task is in active tasks
        assert mock_task in self.resource_manager.active_tasks

        # Call the callback (simulating task completion)
        callback(mock_task)

        # Verify task is removed from active tasks
        assert mock_task not in self.resource_manager.active_tasks
