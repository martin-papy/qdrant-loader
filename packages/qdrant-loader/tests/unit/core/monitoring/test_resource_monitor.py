"""
Unit tests for the resource monitor.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader.core.monitoring.resource_monitor import monitor_resources


class TestResourceMonitor:
    """Test resource monitoring functionality."""

    @pytest.mark.asyncio
    async def test_monitor_resources_with_psutil(self):
        """Test resource monitoring with psutil available."""
        stop_event = asyncio.Event()

        # Mock psutil
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 50.0
        mock_virtual_memory = MagicMock()
        mock_virtual_memory.percent = 60.0
        mock_psutil.virtual_memory.return_value = mock_virtual_memory

        with patch(
            "qdrant_loader.core.monitoring.resource_monitor.psutil", mock_psutil
        ):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                # Start monitoring task
                monitor_task = asyncio.create_task(
                    monitor_resources(
                        cpu_threshold=80.0,
                        mem_threshold=80.0,
                        interval=0.1,  # Short interval for testing
                        stop_event=stop_event,
                    )
                )

                # Let it run for a short time
                await asyncio.sleep(0.2)

                # Stop the monitor
                stop_event.set()
                await monitor_task

                # Verify logging calls
                mock_logger.info.assert_called()
                mock_logger.debug.assert_called()

                # Verify psutil calls
                mock_psutil.cpu_percent.assert_called()
                mock_psutil.virtual_memory.assert_called()

    @pytest.mark.asyncio
    async def test_monitor_resources_high_cpu_warning(self):
        """Test resource monitoring with high CPU usage warning."""
        stop_event = asyncio.Event()

        # Mock psutil with high CPU usage
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 90.0  # Above threshold
        mock_virtual_memory = MagicMock()
        mock_virtual_memory.percent = 50.0  # Below threshold
        mock_psutil.virtual_memory.return_value = mock_virtual_memory

        with patch(
            "qdrant_loader.core.monitoring.resource_monitor.psutil", mock_psutil
        ):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                # Start monitoring task
                monitor_task = asyncio.create_task(
                    monitor_resources(
                        cpu_threshold=80.0,
                        mem_threshold=80.0,
                        interval=0.1,
                        stop_event=stop_event,
                    )
                )

                # Let it run for a short time
                await asyncio.sleep(0.2)

                # Stop the monitor
                stop_event.set()
                await monitor_task

                # Verify warning was logged for high CPU
                warning_calls = [
                    call
                    for call in mock_logger.warning.call_args_list
                    if "High CPU usage" in str(call)
                ]
                assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_monitor_resources_high_memory_warning(self):
        """Test resource monitoring with high memory usage warning."""
        stop_event = asyncio.Event()

        # Mock psutil with high memory usage
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 50.0  # Below threshold
        mock_virtual_memory = MagicMock()
        mock_virtual_memory.percent = 90.0  # Above threshold
        mock_psutil.virtual_memory.return_value = mock_virtual_memory

        with patch(
            "qdrant_loader.core.monitoring.resource_monitor.psutil", mock_psutil
        ):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                # Start monitoring task
                monitor_task = asyncio.create_task(
                    monitor_resources(
                        cpu_threshold=80.0,
                        mem_threshold=80.0,
                        interval=0.1,
                        stop_event=stop_event,
                    )
                )

                # Let it run for a short time
                await asyncio.sleep(0.2)

                # Stop the monitor
                stop_event.set()
                await monitor_task

                # Verify warning was logged for high memory
                warning_calls = [
                    call
                    for call in mock_logger.warning.call_args_list
                    if "High memory usage" in str(call)
                ]
                assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_monitor_resources_without_psutil(self):
        """Test resource monitoring fallback when psutil is not available."""
        stop_event = asyncio.Event()

        # Mock resource module for fallback
        mock_resource = MagicMock()
        mock_usage = MagicMock()
        mock_usage.ru_maxrss = 1024 * 1024 * 100  # 100 MB in bytes
        mock_resource.getrusage.return_value = mock_usage
        mock_resource.RUSAGE_SELF = 0

        with patch("qdrant_loader.core.monitoring.resource_monitor.psutil", None):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                with patch("builtins.__import__") as mock_import:
                    # Mock the import of resource module
                    def side_effect(name, *args, **kwargs):
                        if name == "resource":
                            return mock_resource
                        return __import__(name, *args, **kwargs)

                    mock_import.side_effect = side_effect

                    # Start monitoring task
                    monitor_task = asyncio.create_task(
                        monitor_resources(
                            cpu_threshold=80.0,
                            mem_threshold=80.0,
                            interval=0.1,
                            stop_event=stop_event,
                        )
                    )

                    # Let it run for a short time
                    await asyncio.sleep(0.2)

                    # Stop the monitor
                    stop_event.set()
                    await monitor_task

                    # Verify fallback logging
                    info_calls = [
                        call
                        for call in mock_logger.info.call_args_list
                        if "Process memory usage" in str(call)
                    ]
                    assert len(info_calls) > 0

    @pytest.mark.asyncio
    async def test_monitor_resources_exception_handling(self):
        """Test resource monitoring exception handling."""
        stop_event = asyncio.Event()

        # Mock psutil to raise an exception
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.side_effect = Exception("Test exception")

        with patch(
            "qdrant_loader.core.monitoring.resource_monitor.psutil", mock_psutil
        ):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                # Start monitoring task
                monitor_task = asyncio.create_task(
                    monitor_resources(
                        cpu_threshold=80.0,
                        mem_threshold=80.0,
                        interval=0.1,
                        stop_event=stop_event,
                    )
                )

                # Let it run for a short time
                await asyncio.sleep(0.2)

                # Stop the monitor
                stop_event.set()
                await monitor_task

                # Verify error was logged
                error_calls = [
                    call
                    for call in mock_logger.error.call_args_list
                    if "Error checking resources" in str(call)
                ]
                assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_monitor_resources_custom_thresholds(self):
        """Test resource monitoring with custom thresholds."""
        stop_event = asyncio.Event()

        # Mock psutil with values that exceed custom thresholds
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 60.0  # Above custom threshold of 50
        mock_virtual_memory = MagicMock()
        mock_virtual_memory.percent = 40.0  # Above custom threshold of 30
        mock_psutil.virtual_memory.return_value = mock_virtual_memory

        with patch(
            "qdrant_loader.core.monitoring.resource_monitor.psutil", mock_psutil
        ):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                # Start monitoring task with custom thresholds
                monitor_task = asyncio.create_task(
                    monitor_resources(
                        cpu_threshold=50.0,  # Lower threshold
                        mem_threshold=30.0,  # Lower threshold
                        interval=0.1,
                        stop_event=stop_event,
                    )
                )

                # Let it run for a short time
                await asyncio.sleep(0.2)

                # Stop the monitor
                stop_event.set()
                await monitor_task

                # Verify warnings were logged for both CPU and memory
                cpu_warning_calls = [
                    call
                    for call in mock_logger.warning.call_args_list
                    if "High CPU usage" in str(call)
                ]
                mem_warning_calls = [
                    call
                    for call in mock_logger.warning.call_args_list
                    if "High memory usage" in str(call)
                ]

                assert len(cpu_warning_calls) > 0
                assert len(mem_warning_calls) > 0

    @pytest.mark.asyncio
    async def test_monitor_resources_without_stop_event(self):
        """Test resource monitoring without stop event (infinite loop)."""
        # Mock psutil
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 50.0
        mock_virtual_memory = MagicMock()
        mock_virtual_memory.percent = 60.0
        mock_psutil.virtual_memory.return_value = mock_virtual_memory

        with patch(
            "qdrant_loader.core.monitoring.resource_monitor.psutil", mock_psutil
        ):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                # Start monitoring task without stop event
                monitor_task = asyncio.create_task(
                    monitor_resources(
                        cpu_threshold=80.0,
                        mem_threshold=80.0,
                        interval=0.1,
                        stop_event=None,  # No stop event
                    )
                )

                # Let it run for a short time
                await asyncio.sleep(0.2)

                # Cancel the task (simulates stopping the infinite loop)
                monitor_task.cancel()

                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling

                # Verify monitoring was running
                mock_logger.info.assert_called()
                mock_psutil.cpu_percent.assert_called()

    @pytest.mark.asyncio
    async def test_monitor_resources_stop_event_logging(self):
        """Test that stop event logging works correctly."""
        stop_event = asyncio.Event()

        # Mock psutil
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 50.0
        mock_virtual_memory = MagicMock()
        mock_virtual_memory.percent = 60.0
        mock_psutil.virtual_memory.return_value = mock_virtual_memory

        with patch(
            "qdrant_loader.core.monitoring.resource_monitor.psutil", mock_psutil
        ):
            with patch(
                "qdrant_loader.core.monitoring.resource_monitor.logger"
            ) as mock_logger:
                # Start monitoring task
                monitor_task = asyncio.create_task(
                    monitor_resources(
                        cpu_threshold=80.0,
                        mem_threshold=80.0,
                        interval=0.1,
                        stop_event=stop_event,
                    )
                )

                # Let it run for a short time
                await asyncio.sleep(0.1)

                # Stop the monitor
                stop_event.set()
                await monitor_task

                # Verify stop logging
                stop_calls = [
                    call
                    for call in mock_logger.info.call_args_list
                    if "Resource monitor stopping" in str(call)
                ]
                assert len(stop_calls) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
