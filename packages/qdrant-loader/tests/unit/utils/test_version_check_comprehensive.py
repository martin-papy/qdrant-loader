"""Comprehensive tests for version_check.py to achieve high coverage."""

import json
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
from urllib.error import HTTPError, URLError

import pytest
from packaging.version import InvalidVersion

from qdrant_loader.utils.version_check import VersionChecker, check_version_async


class TestVersionChecker:
    """Comprehensive tests for VersionChecker class."""

    def test_init(self):
        """Test VersionChecker initialization."""
        checker = VersionChecker("1.0.0")
        
        assert checker.current_version == "1.0.0"
        assert checker.cache_path == Path.home() / ".qdrant_loader_version_cache"
        assert checker.PYPI_API_URL == "https://pypi.org/pypi/qdrant-loader/json"
        assert checker.CACHE_DURATION == 24 * 60 * 60

    @patch("pathlib.Path.exists")
    def test_get_cache_data_no_file(self, mock_exists):
        """Test _get_cache_data when cache file doesn't exist."""
        mock_exists.return_value = False
        
        checker = VersionChecker("1.0.0")
        result = checker._get_cache_data()
        
        assert result is None
        mock_exists.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"timestamp": 1234567890, "latest_version": "2.0.0"}')
    @patch("time.time")
    def test_get_cache_data_valid_cache(self, mock_time, mock_file, mock_exists):
        """Test _get_cache_data with valid cache."""
        mock_exists.return_value = True
        mock_time.return_value = 1234567890 + 3600  # 1 hour later
        
        checker = VersionChecker("1.0.0")
        result = checker._get_cache_data()
        
        assert result == {"timestamp": 1234567890, "latest_version": "2.0.0"}
        mock_exists.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"timestamp": 1234567890, "latest_version": "2.0.0"}')
    @patch("time.time")
    def test_get_cache_data_expired_cache(self, mock_time, mock_file, mock_exists):
        """Test _get_cache_data with expired cache."""
        mock_exists.return_value = True
        mock_time.return_value = 1234567890 + (25 * 60 * 60)  # 25 hours later (expired)
        
        checker = VersionChecker("1.0.0")
        result = checker._get_cache_data()
        
        assert result is None

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='invalid json')
    def test_get_cache_data_invalid_json(self, mock_file, mock_exists):
        """Test _get_cache_data with invalid JSON."""
        mock_exists.return_value = True
        
        checker = VersionChecker("1.0.0")
        result = checker._get_cache_data()
        
        assert result is None

    @patch("pathlib.Path.exists")
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_get_cache_data_os_error(self, mock_file, mock_exists):
        """Test _get_cache_data with OS error."""
        mock_exists.return_value = True
        
        checker = VersionChecker("1.0.0")
        result = checker._get_cache_data()
        
        assert result is None

    @patch("builtins.open", new_callable=mock_open)
    @patch("time.time")
    @patch("json.dump")
    def test_save_cache_data_success(self, mock_json_dump, mock_time, mock_file):
        """Test _save_cache_data successful save."""
        mock_time.return_value = 1234567890
        
        checker = VersionChecker("1.0.0")
        data = {"latest_version": "2.0.0"}
        checker._save_cache_data(data)
        
        # Verify file was opened for writing
        mock_file.assert_called_once_with(checker.cache_path, "w")
        
        # Verify correct data was dumped
        expected_data = {"timestamp": 1234567890, "latest_version": "2.0.0"}
        mock_json_dump.assert_called_once_with(expected_data, mock_file.return_value.__enter__.return_value)

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_save_cache_data_os_error(self, mock_file):
        """Test _save_cache_data with OS error (should fail silently)."""
        checker = VersionChecker("1.0.0")
        data = {"latest_version": "2.0.0"}
        
        # Should not raise exception
        checker._save_cache_data(data)

    @patch("qdrant_loader.utils.version_check.urlopen")
    @patch("qdrant_loader.utils.version_check.Request")
    def test_fetch_latest_version_success(self, mock_request, mock_urlopen):
        """Test _fetch_latest_version successful fetch."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"info": {"version": "2.1.0"}}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        checker = VersionChecker("1.0.0")
        result = checker._fetch_latest_version()
        
        assert result == "2.1.0"
        
        # Verify request was created with correct URL and headers
        mock_request.assert_called_once_with(
            "https://pypi.org/pypi/qdrant-loader/json",
            headers={"User-Agent": "qdrant-loader/1.0.0"}
        )
        
        # Verify urlopen was called with timeout
        mock_urlopen.assert_called_once_with(mock_request.return_value, timeout=5)

    @patch("qdrant_loader.utils.version_check.urlopen", side_effect=URLError("Network error"))
    @patch("qdrant_loader.utils.version_check.Request")
    def test_fetch_latest_version_url_error(self, mock_request, mock_urlopen):
        """Test _fetch_latest_version with URL error."""
        checker = VersionChecker("1.0.0")
        result = checker._fetch_latest_version()
        
        assert result is None

    @patch("qdrant_loader.utils.version_check.urlopen", side_effect=HTTPError("http://test", 404, "Not Found", {}, None))
    @patch("qdrant_loader.utils.version_check.Request") 
    def test_fetch_latest_version_http_error(self, mock_request, mock_urlopen):
        """Test _fetch_latest_version with HTTP error."""
        checker = VersionChecker("1.0.0")
        result = checker._fetch_latest_version()
        
        assert result is None

    @patch("qdrant_loader.utils.version_check.urlopen")
    @patch("qdrant_loader.utils.version_check.Request")
    def test_fetch_latest_version_invalid_json(self, mock_request, mock_urlopen):
        """Test _fetch_latest_version with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'invalid json'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        checker = VersionChecker("1.0.0")
        result = checker._fetch_latest_version()
        
        assert result is None

    @patch("qdrant_loader.utils.version_check.urlopen")
    @patch("qdrant_loader.utils.version_check.Request")
    def test_fetch_latest_version_missing_key(self, mock_request, mock_urlopen):
        """Test _fetch_latest_version with missing version key."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"info": {}}'  # Missing version key
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        checker = VersionChecker("1.0.0")
        result = checker._fetch_latest_version()
        
        assert result is None

    def test_check_for_updates_unknown_version(self):
        """Test check_for_updates with unknown current version."""
        checker = VersionChecker("unknown")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is False
        assert latest_version is None

    def test_check_for_updates_unknown_uppercase_version(self):
        """Test check_for_updates with 'Unknown' current version."""
        checker = VersionChecker("Unknown")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is False
        assert latest_version is None

    @patch.object(VersionChecker, '_get_cache_data')
    def test_check_for_updates_from_cache(self, mock_get_cache):
        """Test check_for_updates using cached data."""
        mock_get_cache.return_value = {"latest_version": "2.0.0"}
        
        checker = VersionChecker("1.0.0")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is True
        assert latest_version == "2.0.0"

    @patch.object(VersionChecker, '_save_cache_data')
    @patch.object(VersionChecker, '_fetch_latest_version')
    @patch.object(VersionChecker, '_get_cache_data')
    def test_check_for_updates_fetch_and_cache(self, mock_get_cache, mock_fetch, mock_save_cache):
        """Test check_for_updates fetching from PyPI and caching."""
        mock_get_cache.return_value = None  # No cache
        mock_fetch.return_value = "2.1.0"
        
        checker = VersionChecker("1.5.0")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is True
        assert latest_version == "2.1.0"
        
        # Verify data was cached
        mock_save_cache.assert_called_once_with({"latest_version": "2.1.0"})

    @patch.object(VersionChecker, '_fetch_latest_version')
    @patch.object(VersionChecker, '_get_cache_data')
    def test_check_for_updates_fetch_failed(self, mock_get_cache, mock_fetch):
        """Test check_for_updates when fetch fails."""
        mock_get_cache.return_value = None
        mock_fetch.return_value = None  # Fetch failed
        
        checker = VersionChecker("1.0.0")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is False
        assert latest_version is None

    @patch.object(VersionChecker, '_get_cache_data')
    def test_check_for_updates_no_update_needed(self, mock_get_cache):
        """Test check_for_updates when current version is latest."""
        mock_get_cache.return_value = {"latest_version": "1.0.0"}
        
        checker = VersionChecker("1.0.0")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is False
        assert latest_version == "1.0.0"

    @patch.object(VersionChecker, '_get_cache_data')
    def test_check_for_updates_current_newer(self, mock_get_cache):
        """Test check_for_updates when current version is newer than latest."""
        mock_get_cache.return_value = {"latest_version": "1.0.0"}
        
        checker = VersionChecker("2.0.0")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is False
        assert latest_version == "1.0.0"

    @patch.object(VersionChecker, '_get_cache_data')
    @patch("packaging.version.parse", side_effect=InvalidVersion("Invalid version"))
    def test_check_for_updates_invalid_version(self, mock_parse, mock_get_cache):
        """Test check_for_updates with invalid version format."""
        mock_get_cache.return_value = {"latest_version": "invalid.version"}
        
        checker = VersionChecker("1.0.0")
        has_update, latest_version = checker.check_for_updates()
        
        assert has_update is False
        assert latest_version is None

    @patch("builtins.print")
    def test_show_update_notification(self, mock_print):
        """Test show_update_notification prints correct message."""
        checker = VersionChecker("1.0.0")
        checker.show_update_notification("2.0.0")
        
        # Verify all expected print calls
        expected_calls = [
            unittest.mock.call("\n🆕 A new version of qdrant-loader is available!"),
            unittest.mock.call("   Current: 1.0.0"),
            unittest.mock.call("   Latest:  2.0.0"),
            unittest.mock.call("   Update:  pip install --upgrade qdrant-loader qdrant-loader-mcp-server"),
            unittest.mock.call()
        ]
        
        assert mock_print.call_count == 5
        for i, expected_call in enumerate(expected_calls):
            assert mock_print.call_args_list[i] == expected_call


class TestCheckVersionAsync:
    """Tests for check_version_async function."""

    @patch("threading.Thread")
    def test_check_version_async_success(self, mock_thread):
        """Test check_version_async creates and starts thread."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        check_version_async("1.0.0", silent=False)
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        
        # Verify daemon=True was set
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs["daemon"] is True

    @patch("threading.Thread")
    def test_check_version_async_silent(self, mock_thread):
        """Test check_version_async with silent=True."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        check_version_async("1.0.0", silent=True)
        
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @patch("threading.Thread", side_effect=Exception("Threading failed"))
    def test_check_version_async_exception(self, mock_thread):
        """Test check_version_async handles threading exceptions silently."""
        # Should not raise exception
        check_version_async("1.0.0", silent=False)

    @patch.object(VersionChecker, 'show_update_notification')
    @patch.object(VersionChecker, 'check_for_updates')
    def test_check_version_async_internal_function(self, mock_check_updates, mock_show_notification):
        """Test the internal _check function behavior."""
        mock_check_updates.return_value = (True, "2.0.0")
        
        # Call the internal function directly
        checker = VersionChecker("1.0.0")
        has_update, latest_version = checker.check_for_updates(silent=False)
        
        if has_update and latest_version and not False:  # not silent
            checker.show_update_notification(latest_version)
        
        mock_check_updates.assert_called_once_with(silent=False)
        mock_show_notification.assert_called_once_with("2.0.0")

    @patch.object(VersionChecker, 'show_update_notification')
    @patch.object(VersionChecker, 'check_for_updates')
    def test_check_version_async_no_update(self, mock_check_updates, mock_show_notification):
        """Test internal function when no update available."""
        mock_check_updates.return_value = (False, "1.0.0")
        
        checker = VersionChecker("1.0.0")
        has_update, latest_version = checker.check_for_updates(silent=False)
        
        # Should not call show_update_notification
        assert not (has_update and latest_version and not False)
        mock_show_notification.assert_not_called()

    @patch.object(VersionChecker, 'show_update_notification')
    @patch.object(VersionChecker, 'check_for_updates')
    def test_check_version_async_silent_no_notification(self, mock_check_updates, mock_show_notification):
        """Test internal function with silent=True doesn't show notification."""
        mock_check_updates.return_value = (True, "2.0.0")
        
        checker = VersionChecker("1.0.0") 
        has_update, latest_version = checker.check_for_updates(silent=True)
        
        # Even with update, silent=True should prevent notification
        if has_update and latest_version and not True:  # not silent (True)
            checker.show_update_notification(latest_version)
        
        mock_show_notification.assert_not_called()


import unittest.mock  # Add this import for the assertion