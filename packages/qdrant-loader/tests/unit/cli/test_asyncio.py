"""Tests for the CLI asyncio module."""

import asyncio
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.cli.asyncio import async_command


class TestAsyncCommand:
    """Test cases for the async_command decorator."""

    def test_async_command_decorator_with_no_running_loop(self):
        """Test async_command decorator when no event loop is running."""

        with patch("qdrant_loader.cli.asyncio.asyncio") as mock_asyncio:
            # Mock no running loop scenario
            mock_asyncio.get_running_loop.side_effect = RuntimeError("No running loop")

            # Mock loop creation
            mock_loop = Mock()
            mock_asyncio.new_event_loop.return_value = mock_loop

            def mock_run_until_complete(coro):
                # Close the coroutine to prevent warnings
                if hasattr(coro, "close"):
                    coro.close()
                return "processed_test"

            mock_loop.run_until_complete.side_effect = mock_run_until_complete

            @async_command
            async def test_function(value: str) -> str:
                """Test async function."""
                await asyncio.sleep(0.01)  # Small delay to ensure it's actually async
                return f"processed_{value}"

            # Call the decorated function
            result = test_function("test")

            # Verify behavior
            assert result == "processed_test"
            mock_asyncio.get_running_loop.assert_called_once()
            mock_asyncio.new_event_loop.assert_called_once()
            mock_asyncio.set_event_loop.assert_called_once_with(mock_loop)
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_called_once()

    def test_async_command_decorator_with_existing_loop(self):
        """Test async_command decorator when an event loop is already running."""

        with patch("qdrant_loader.cli.asyncio.asyncio") as mock_asyncio:
            # Mock existing loop scenario
            mock_loop = Mock()
            mock_asyncio.get_running_loop.return_value = mock_loop

            def mock_run_until_complete(coro):
                # Close the coroutine to prevent warnings
                if hasattr(coro, "close"):
                    coro.close()
                return "processed_test"

            mock_loop.run_until_complete.side_effect = mock_run_until_complete

            @async_command
            async def test_function(value: str) -> str:
                """Test async function."""
                return f"processed_{value}"

            # Call the decorated function
            result = test_function("test")

            # Verify behavior
            assert result == "processed_test"
            mock_asyncio.get_running_loop.assert_called_once()
            mock_asyncio.new_event_loop.assert_not_called()
            mock_asyncio.set_event_loop.assert_not_called()
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_not_called()  # Should not close existing loop

    def test_async_command_decorator_with_function_arguments(self):
        """Test async_command decorator with various function arguments."""

        with patch("qdrant_loader.cli.asyncio.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = RuntimeError("No running loop")
            mock_loop = Mock()
            mock_asyncio.new_event_loop.return_value = mock_loop
            expected_result = {"arg1": "test", "arg2": 42, "kwarg1": "custom"}

            def mock_run_until_complete(coro):
                # Close the coroutine to prevent warnings
                if hasattr(coro, "close"):
                    coro.close()
                return expected_result

            mock_loop.run_until_complete.side_effect = mock_run_until_complete

            @async_command
            async def test_function(
                arg1: str, arg2: int, kwarg1: str = "default"
            ) -> dict:
                """Test async function with arguments."""
                return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

            # Call with various arguments
            result = test_function("test", 42, kwarg1="custom")

            assert result == expected_result
            mock_loop.run_until_complete.assert_called_once()

    def test_async_command_decorator_exception_handling(self):
        """Test async_command decorator handles exceptions properly."""

        with patch("qdrant_loader.cli.asyncio.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = RuntimeError("No running loop")
            mock_loop = Mock()
            mock_asyncio.new_event_loop.return_value = mock_loop

            def mock_run_until_complete(coro):
                # Close the coroutine to prevent warnings
                if hasattr(coro, "close"):
                    coro.close()
                raise ValueError("Test error")

            mock_loop.run_until_complete.side_effect = mock_run_until_complete

            @async_command
            async def test_function() -> None:
                """Test async function that raises an exception."""
                raise ValueError("Test error")

            # Should propagate the exception
            with pytest.raises(ValueError, match="Test error"):
                test_function()

            # Should still close the loop even when exception occurs
            mock_loop.close.assert_called_once()

    def test_async_command_decorator_preserves_function_metadata(self):
        """Test that async_command decorator preserves function metadata."""

        @async_command
        async def test_function(arg: str) -> str:
            """Test function docstring."""
            return arg

        # Check that function metadata is preserved
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ is not None
        assert "Test function docstring." in test_function.__doc__

    def test_async_command_real_async_function(self):
        """Test async_command with a real async function (integration test)."""

        @async_command
        async def real_async_function(delay: float) -> str:
            """Real async function with actual await."""
            await asyncio.sleep(delay)
            return "completed"

        # This should work without mocking for a real integration test
        # Use a very small delay to keep test fast
        result = real_async_function(0.001)
        assert result == "completed"

    def test_async_command_with_coroutine_return_type(self):
        """Test async_command decorator type handling."""

        with patch("qdrant_loader.cli.asyncio.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = RuntimeError("No running loop")
            mock_loop = Mock()
            mock_asyncio.new_event_loop.return_value = mock_loop

            def mock_run_until_complete(coro):
                # Close the coroutine to prevent warnings
                if hasattr(coro, "close"):
                    coro.close()
                return "test_result"

            mock_loop.run_until_complete.side_effect = mock_run_until_complete

            @async_command
            async def test_function() -> str:
                """Test function that returns a string."""
                return "test_result"

            result = test_function()

            # Verify the coroutine was passed to run_until_complete
            assert result == "test_result"
            args, kwargs = mock_loop.run_until_complete.call_args
            # The first argument should be a coroutine
            assert len(args) == 1

    def test_async_command_multiple_calls(self):
        """Test async_command decorator with multiple sequential calls."""

        with patch("qdrant_loader.cli.asyncio.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = RuntimeError("No running loop")

            # Create separate mock loops for each call
            mock_loop1 = Mock()
            mock_loop2 = Mock()
            mock_asyncio.new_event_loop.side_effect = [mock_loop1, mock_loop2]

            def mock_run_until_complete_1(coro):
                # Close the coroutine to prevent warnings
                if hasattr(coro, "close"):
                    coro.close()
                return 10

            def mock_run_until_complete_2(coro):
                # Close the coroutine to prevent warnings
                if hasattr(coro, "close"):
                    coro.close()
                return 20

            mock_loop1.run_until_complete.side_effect = mock_run_until_complete_1
            mock_loop2.run_until_complete.side_effect = mock_run_until_complete_2

            @async_command
            async def test_function(value: int) -> int:
                """Test async function."""
                return value * 2

            # Make multiple calls
            result1 = test_function(5)
            result2 = test_function(10)

            assert result1 == 10
            assert result2 == 20

            # Verify both loops were created and closed
            assert mock_asyncio.new_event_loop.call_count == 2
            mock_loop1.close.assert_called_once()
            mock_loop2.close.assert_called_once()
