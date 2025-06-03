"""Version checking utility for QDrant Loader CLI."""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from packaging import version


class VersionChecker:
    """Check for new versions of qdrant-loader on PyPI."""

    PYPI_API_URL = "https://pypi.org/pypi/qdrant-loader/json"
    CACHE_FILE = ".qdrant_loader_version_cache"
    CACHE_DURATION = 24 * 60 * 60  # 24 hours in seconds

    def __init__(self, current_version: str):
        """Initialize version checker.

        Args:
            current_version: Current version of qdrant-loader
        """
        self.current_version = current_version
        self.cache_path = Path.home() / self.CACHE_FILE

    def _get_cache_data(self) -> Optional[dict]:
        """Get cached version data if still valid.

        Returns:
            Cached data if valid, None otherwise
        """
        try:
            if not self.cache_path.exists():
                return None

            with open(self.cache_path, "r") as f:
                cache_data = json.load(f)

            # Check if cache is still valid
            cache_time = cache_data.get("timestamp", 0)
            if time.time() - cache_time > self.CACHE_DURATION:
                return None

            return cache_data
        except (json.JSONDecodeError, OSError):
            return None

    def _save_cache_data(self, data: dict) -> None:
        """Save version data to cache.

        Args:
            data: Data to cache
        """
        try:
            cache_data = {"timestamp": time.time(), **data}
            with open(self.cache_path, "w") as f:
                json.dump(cache_data, f)
        except OSError:
            # Silently fail if we can't write cache
            pass

    def _fetch_latest_version(self) -> Optional[str]:
        """Fetch latest version from PyPI.

        Returns:
            Latest version string or None if fetch failed
        """
        try:
            # Create request with user agent
            req = Request(
                self.PYPI_API_URL,
                headers={"User-Agent": f"qdrant-loader/{self.current_version}"},
            )

            # Set timeout to avoid hanging
            with urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data["info"]["version"]
        except (URLError, HTTPError, json.JSONDecodeError, KeyError, OSError):
            return None

    def check_for_updates(self, silent: bool = False) -> Tuple[bool, Optional[str]]:
        """Check if a newer version is available.

        Args:
            silent: If True, don't show any output

        Returns:
            Tuple of (has_update, latest_version)
        """
        # Skip check if current version is unknown
        if self.current_version in ("unknown", "Unknown"):
            return False, None

        # Try to get from cache first
        cache_data = self._get_cache_data()
        if cache_data:
            latest_version = cache_data.get("latest_version")
        else:
            # Fetch from PyPI
            latest_version = self._fetch_latest_version()
            if latest_version:
                self._save_cache_data({"latest_version": latest_version})

        if not latest_version:
            return False, None

        try:
            # Compare versions
            current_ver = version.parse(self.current_version)
            latest_ver = version.parse(latest_version)

            has_update = latest_ver > current_ver
            return has_update, latest_version
        except version.InvalidVersion:
            return False, None

    def show_update_notification(self, latest_version: str) -> None:
        """Show update notification to user.

        Args:
            latest_version: Latest available version
        """
        print(f"\n🆕 A new version of qdrant-loader is available!")
        print(f"   Current: {self.current_version}")
        print(f"   Latest:  {latest_version}")
        print(f"   Update:  pip install --upgrade qdrant-loader")
        print()


def check_version_async(current_version: str, silent: bool = False) -> None:
    """Asynchronously check for version updates.

    Args:
        current_version: Current version of qdrant-loader
        silent: If True, don't show any output
    """

    def _check():
        checker = VersionChecker(current_version)
        has_update, latest_version = checker.check_for_updates(silent=silent)

        if has_update and latest_version and not silent:
            checker.show_update_notification(latest_version)

    # Run check in background thread to avoid blocking CLI
    try:
        import threading

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()
    except Exception:
        # Silently fail if threading doesn't work
        pass
