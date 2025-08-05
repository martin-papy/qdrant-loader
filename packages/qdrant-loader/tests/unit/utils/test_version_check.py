"""Tests for the version check utility."""

import pytest
from unittest.mock import Mock, patch

from qdrant_loader.utils.version_check import (
    VersionChecker,
    check_version_async,
)


class TestVersionChecker:
    """Test cases for VersionChecker class."""

    def test_initialization(self):
        """Test VersionChecker initialization."""
        checker = VersionChecker("1.0.0")
        assert checker.current_version == "1.0.0"
        assert checker.PYPI_API_URL == "https://pypi.org/pypi/qdrant-loader/json"

    def test_check_for_updates_unknown_version(self):
        """Test checking for updates with unknown current version."""
        checker = VersionChecker("unknown")
        has_update, latest_version = checker.check_for_updates()

        assert has_update is False
        assert latest_version is None

    @patch('builtins.print')
    def test_show_update_notification(self, mock_print):
        """Test showing update notification."""
        checker = VersionChecker("1.0.0")
        checker.show_update_notification("2.0.0")

        # Verify print was called multiple times (for the notification lines)
        assert mock_print.call_count >= 4


class TestCheckVersionAsync:
    """Test cases for check_version_async function - targeting lines 144-148."""

    @patch('threading.Thread')
    def test_check_version_async_basic(self, mock_thread):
        """Test that check_version_async creates and starts a thread."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        # Call the function
        check_version_async("1.0.0")

        # Verify a thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

        # Verify the thread was created with daemon=True
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs['daemon'] is True

    @patch('threading.Thread')
    def test_check_version_async_executes_target_function(self, mock_thread):
        """Test that the thread target function is properly defined - covers lines 144-148."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        # Mock the VersionChecker to avoid actual network calls
        with patch('qdrant_loader.utils.version_check.VersionChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker.check_for_updates.return_value = (True, "2.0.0")
            mock_checker_class.return_value = mock_checker

            # Call the function
            check_version_async("1.0.0")

            # Get the target function that was passed to Thread
            thread_target = mock_thread.call_args[1]['target']
            
            # Execute the target function to cover lines 144-148
            thread_target()

            # Verify the VersionChecker was created with correct version
            mock_checker_class.assert_called_once_with("1.0.0")
            
            # Verify check_for_updates was called
            mock_checker.check_for_updates.assert_called_once_with(silent=False)
            
            # Verify show_update_notification was called (covers line 148)
            mock_checker.show_update_notification.assert_called_once_with("2.0.0")

    @patch('threading.Thread')
    def test_check_version_async_silent_mode(self, mock_thread):
        """Test check_version_async in silent mode."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        with patch('qdrant_loader.utils.version_check.VersionChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker.check_for_updates.return_value = (True, "2.0.0")
            mock_checker_class.return_value = mock_checker

            # Call the function in silent mode
            check_version_async("1.0.0", silent=True)

            # Execute the target function
            thread_target = mock_thread.call_args[1]['target']
            thread_target()

            # Verify check_for_updates was called with silent=True
            mock_checker.check_for_updates.assert_called_once_with(silent=True)
            
            # Should NOT show notification in silent mode
            mock_checker.show_update_notification.assert_not_called()

    @patch('threading.Thread')
    def test_check_version_async_no_update(self, mock_thread):
        """Test check_version_async when no update is available."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        with patch('qdrant_loader.utils.version_check.VersionChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker.check_for_updates.return_value = (False, "1.0.0")
            mock_checker_class.return_value = mock_checker

            # Call the function
            check_version_async("1.0.0")

            # Execute the target function
            thread_target = mock_thread.call_args[1]['target']
            thread_target()

            # Verify check_for_updates was called
            mock_checker.check_for_updates.assert_called_once_with(silent=False)
            
            # Should NOT show notification when no update
            mock_checker.show_update_notification.assert_not_called()

    @patch('threading.Thread')
    def test_check_version_async_no_latest_version(self, mock_thread):
        """Test check_version_async when latest_version is None."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        with patch('qdrant_loader.utils.version_check.VersionChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker.check_for_updates.return_value = (True, None)
            mock_checker_class.return_value = mock_checker

            # Call the function
            check_version_async("1.0.0")

            # Execute the target function
            thread_target = mock_thread.call_args[1]['target']
            thread_target()

            # Should NOT show notification when latest_version is None
            mock_checker.show_update_notification.assert_not_called()

    @patch('threading.Thread')
    def test_check_version_async_threading_failure(self, mock_thread):
        """Test check_version_async when threading fails."""
        mock_thread.side_effect = Exception("Threading not available")

        # Should not raise an exception - silently fails
        try:
            check_version_async("1.0.0")
        except Exception:
            pytest.fail("check_version_async should not raise exceptions when threading fails")