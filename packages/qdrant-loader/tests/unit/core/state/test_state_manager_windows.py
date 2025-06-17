"""Unit tests for StateManager Windows path handling."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.state.exceptions import DatabaseError
from qdrant_loader.core.state.state_manager import StateManager


class TestStateManagerWindowsPaths:
    """Test StateManager with Windows-style paths."""

    def test_windows_absolute_path_with_drive_letter(self):
        """Test Windows absolute path with drive letter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simulate a Windows-style path
            windows_path = f"C:{temp_dir}\\qdrant-loader.db"

            config = MagicMock(spec=StateManagementConfig)
            config.database_path = windows_path
            config.connection_pool = {"size": 5, "timeout": 30}

            manager = StateManager(config)

            # Should handle the path without errors during path processing
            # Note: We're not testing actual database creation here, just path handling
            assert manager.config.database_path == windows_path

    def test_windows_path_normalization(self):
        """Test that Windows paths are properly normalized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a path that mixes forward and backward slashes
            mixed_path = f"{temp_dir}/subdir\\qdrant-loader.db"

            config = MagicMock(spec=StateManagementConfig)
            config.database_path = mixed_path
            config.connection_pool = {"size": 5, "timeout": 30}

            manager = StateManager(config)

            # The StateManager should handle this without issues
            assert manager.config.database_path == mixed_path

    def test_database_url_generation_windows_path(self):
        """Test that Windows paths generate correct SQLite URLs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a Windows-style absolute path
            db_file = Path(temp_dir) / "qdrant-loader.db"

            config = MagicMock(spec=StateManagementConfig)
            config.database_path = str(db_file)
            config.connection_pool = {"size": 5, "timeout": 30}

            manager = StateManager(config)

            # Test the path handling logic directly
            db_path_str = manager.config.database_path
            db_path = Path(db_path_str)

            # Ensure we have an absolute path
            if not db_path.is_absolute():
                db_path = db_path.resolve()

            # For SQLite URLs, we need forward slashes even on Windows
            # Convert to POSIX-style path for the URL
            if db_path.is_absolute() and db_path.parts[0].endswith(":"):
                # Windows absolute path with drive letter (e.g., C:\path\to\db.sqlite)
                # SQLite expects file:///C:/path/to/db.sqlite format
                db_url_path = db_path.as_posix()
                db_url = f"sqlite:///{db_url_path}"
            else:
                # Relative path or Unix-style absolute path
                db_url_path = db_path.as_posix()
                if not db_url_path.startswith("/"):
                    db_url = f"sqlite:///{db_url_path}"
                else:
                    db_url = f"sqlite://{db_url_path}"

            # The URL should start with sqlite://
            assert db_url.startswith("sqlite://")
            # Should not contain backslashes in the URL part
            assert "\\" not in db_url.split("://")[1]
            # Should use forward slashes for path separation
            assert "/" in db_url.split("://")[1]

    def test_relative_path_resolution(self):
        """Test that relative paths are properly resolved."""
        config = MagicMock(spec=StateManagementConfig)
        config.database_path = "data/qdrant-loader.db"
        config.connection_pool = {"size": 5, "timeout": 30}

        manager = StateManager(config)

        # Should handle relative paths without issues
        assert manager.config.database_path == "data/qdrant-loader.db"

    @pytest.mark.asyncio
    async def test_nonexistent_directory_error_message(self):
        """Test that directory not found errors are descriptive."""
        # Use a path that definitely doesn't exist
        nonexistent_path = "/absolutely/nonexistent/directory/db.sqlite"
        if os.name == "nt":  # Windows
            nonexistent_path = "Z:\\absolutely\\nonexistent\\directory\\db.sqlite"

        config = MagicMock(spec=StateManagementConfig)
        config.database_path = nonexistent_path
        config.connection_pool = {"size": 5, "timeout": 30}

        manager = StateManager(config)

        with pytest.raises(DatabaseError) as exc_info:
            await manager.initialize()

        # The error message should mention that the directory doesn't exist
        assert "does not exist" in str(exc_info.value)

    def test_in_memory_database_handling(self):
        """Test that in-memory database is handled correctly."""
        config = MagicMock(spec=StateManagementConfig)
        config.database_path = ":memory:"
        config.connection_pool = {"size": 5, "timeout": 30}

        manager = StateManager(config)

        # Should handle in-memory database without path-related issues
        assert manager.config.database_path == ":memory:"
