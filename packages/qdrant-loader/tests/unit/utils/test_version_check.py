"""Tests for version checking utility."""

import json
import time
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
from urllib.error import HTTPError, URLError

from qdrant_loader.utils.version_check import (
    VersionChecker,
    check_version_async,
)


class TestVersionChecker:
    """Test VersionChecker class."""

    def test_init(self):
        """Test VersionChecker initialization."""
        checker = VersionChecker("1.0.0")
        assert checker.current_version == "1.0.0"
        assert checker.cache_path == Path.home() / ".qdrant_loader_version_cache"

    @patch("pathlib.Path.exists")
    def test_get_cache_data_no_file(self, mock_exists):
        """Test getting cache data when file doesn't exist."""
        mock_exists.return_value = False
        checker = VersionChecker("1.0.0")
        result = checker._get_cache_data()
        assert result is None

    @patch("pathlib.Path.exists")
    def test_get_cache_data_valid(self, mock_exists):
        """Test getting valid cache data."""
        mock_exists.return_value = True
        checker = VersionChecker("1.0.0")
        cache_data = {"timestamp": time.time(), "latest_version": "1.1.0"}

        with patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
            result = checker._get_cache_data()
            assert result == cache_data

    @patch("pathlib.Path.exists")
    def test_get_cache_data_expired(self, mock_exists):
        """Test getting expired cache data."""
        mock_exists.return_value = True
        checker = VersionChecker("1.0.0")
        cache_data = {
            "timestamp": time.time() - (25 * 60 * 60),  # 25 hours ago
            "latest_version": "1.1.0",
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
            result = checker._get_cache_data()
            assert result is None

    @patch("pathlib.Path.exists")
    def test_get_cache_data_invalid_json(self, mock_exists):
        """Test getting cache data with invalid JSON."""
        mock_exists.return_value = True
        checker = VersionChecker("1.0.0")

        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = checker._get_cache_data()
            assert result is None

    def test_save_cache_data(self):
        """Test saving cache data."""
        checker = VersionChecker("1.0.0")
        data = {"latest_version": "1.1.0"}

        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            checker._save_cache_data(data)

        # Verify file was opened for writing
        mock_file.assert_called_once_with(checker.cache_path, "w")

        # Verify JSON was written
        written_data = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        parsed_data = json.loads(written_data)
        assert "timestamp" in parsed_data
        assert parsed_data["latest_version"] == "1.1.0"

    def test_save_cache_data_os_error(self):
        """Test saving cache data with OS error."""
        checker = VersionChecker("1.0.0")
        data = {"latest_version": "1.1.0"}

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # Should not raise exception
            checker._save_cache_data(data)

    @patch("qdrant_loader.utils.version_check.urlopen")
    def test_fetch_latest_version_success(self, mock_urlopen):
        """Test successful version fetch from PyPI."""
        checker = VersionChecker("1.0.0")

        # Mock PyPI response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"info": {"version": "1.2.0"}}
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = checker._fetch_latest_version()
        assert result == "1.2.0"

    @patch("qdrant_loader.utils.version_check.urlopen")
    def test_fetch_latest_version_url_error(self, mock_urlopen):
        """Test version fetch with URL error."""
        checker = VersionChecker("1.0.0")
        mock_urlopen.side_effect = URLError("Network error")

        result = checker._fetch_latest_version()
        assert result is None

    @patch("qdrant_loader.utils.version_check.urlopen")
    def test_fetch_latest_version_http_error(self, mock_urlopen):
        """Test version fetch with HTTP error."""
        checker = VersionChecker("1.0.0")
        headers = EmailMessage()
        mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", headers, None)

        result = checker._fetch_latest_version()
        assert result is None

    @patch("qdrant_loader.utils.version_check.urlopen")
    def test_fetch_latest_version_invalid_json(self, mock_urlopen):
        """Test version fetch with invalid JSON response."""
        checker = VersionChecker("1.0.0")

        mock_response = Mock()
        mock_response.read.return_value = b"invalid json"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = checker._fetch_latest_version()
        assert result is None

    def test_check_for_updates_unknown_version(self):
        """Test update check with unknown current version."""
        checker = VersionChecker("unknown")

        has_update, latest_version = checker.check_for_updates()
        assert has_update is False
        assert latest_version is None

    def test_check_for_updates_with_cache(self):
        """Test update check using cached data."""
        checker = VersionChecker("1.0.0")

        with patch.object(
            checker, "_get_cache_data", return_value={"latest_version": "1.2.0"}
        ):
            has_update, latest_version = checker.check_for_updates()
            assert has_update is True
            assert latest_version == "1.2.0"

    def test_check_for_updates_no_cache_fetch_success(self):
        """Test update check without cache, successful fetch."""
        checker = VersionChecker("1.0.0")

        with (
            patch.object(checker, "_get_cache_data", return_value=None),
            patch.object(checker, "_fetch_latest_version", return_value="1.2.0"),
            patch.object(checker, "_save_cache_data") as mock_save,
        ):

            has_update, latest_version = checker.check_for_updates()
            assert has_update is True
            assert latest_version == "1.2.0"
            mock_save.assert_called_once_with({"latest_version": "1.2.0"})

    def test_check_for_updates_no_update_available(self):
        """Test update check when no update is available."""
        checker = VersionChecker("1.2.0")

        with patch.object(
            checker, "_get_cache_data", return_value={"latest_version": "1.0.0"}
        ):
            has_update, latest_version = checker.check_for_updates()
            assert has_update is False
            assert latest_version == "1.0.0"

    def test_check_for_updates_same_version(self):
        """Test update check when versions are the same."""
        checker = VersionChecker("1.0.0")

        with patch.object(
            checker, "_get_cache_data", return_value={"latest_version": "1.0.0"}
        ):
            has_update, latest_version = checker.check_for_updates()
            assert has_update is False
            assert latest_version == "1.0.0"

    def test_check_for_updates_fetch_failure(self):
        """Test update check when fetch fails."""
        checker = VersionChecker("1.0.0")

        with (
            patch.object(checker, "_get_cache_data", return_value=None),
            patch.object(checker, "_fetch_latest_version", return_value=None),
        ):

            has_update, latest_version = checker.check_for_updates()
            assert has_update is False
            assert latest_version is None

    def test_check_for_updates_invalid_version(self):
        """Test update check with invalid version format."""
        checker = VersionChecker("invalid-version")

        with patch.object(
            checker, "_get_cache_data", return_value={"latest_version": "1.0.0"}
        ):
            has_update, latest_version = checker.check_for_updates()
            assert has_update is False
            assert latest_version is None

    def test_show_update_notification(self, capsys):
        """Test showing update notification."""
        checker = VersionChecker("1.0.0")
        checker.show_update_notification("1.2.0")

        captured = capsys.readouterr()
        assert "🆕 A new version of qdrant-loader is available!" in captured.out
        assert "Current: 1.0.0" in captured.out
        assert "Latest:  1.2.0" in captured.out
        assert (
            "pip install --upgrade qdrant-loader qdrant-loader-mcp-server"
            in captured.out
        )


class TestVersionCheckAsync:
    """Test async version checking function."""

    @patch("threading.Thread")
    def test_check_version_async(self, mock_thread):
        """Test async version checking."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        check_version_async("1.0.0", silent=False)

        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @patch("threading.Thread", side_effect=Exception("Threading error"))
    def test_check_version_async_exception(self, mock_thread):
        """Test async version checking with threading exception."""
        # Should not raise exception
        check_version_async("1.0.0", silent=False)
