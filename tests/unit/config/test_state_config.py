"""Tests for state management configuration."""

import pytest
from pathlib import Path
import tempfile
import os
from qdrant_loader.config.state import StateManagementConfig


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for database files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_valid_config(temp_db_dir):
    """Test valid state management configuration."""
    db_path = str(Path(temp_db_dir) / "test.db")
    config = StateManagementConfig(
        database_path=db_path, table_prefix="test_", connection_pool={"size": 5, "timeout": 30}
    )
    assert config.database_path == db_path
    assert config.table_prefix == "test_"
    assert config.connection_pool == {"size": 5, "timeout": 30}


def test_default_values(temp_db_dir):
    """Test default values for state management configuration."""
    db_path = str(Path(temp_db_dir) / "test.db")
    config = StateManagementConfig(database_path=db_path)
    assert config.table_prefix == "qdrant_loader_"
    assert config.connection_pool == {"size": 5, "timeout": 30}


def test_invalid_database_path():
    """Test invalid database path validation."""
    with pytest.raises(ValueError, match="Database directory does not exist"):
        StateManagementConfig(database_path="/nonexistent/path/test.db")

    # Create a file instead of a directory
    with tempfile.NamedTemporaryFile() as temp_file:
        with pytest.raises(ValueError, match="Database path is not a directory"):
            StateManagementConfig(database_path=str(Path(temp_file.name) / "test.db"))

    # Create a read-only directory
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chmod(temp_dir, 0o444)  # Read-only permissions
        with pytest.raises(ValueError, match="Database directory is not writable"):
            StateManagementConfig(database_path=str(Path(temp_dir) / "test.db"))


def test_invalid_table_prefix(temp_db_dir):
    """Test invalid table prefix validation."""
    db_path = str(Path(temp_db_dir) / "test.db")

    with pytest.raises(ValueError, match="Table prefix cannot be empty"):
        StateManagementConfig(database_path=db_path, table_prefix="")

    with pytest.raises(
        ValueError, match="Table prefix can only contain alphanumeric characters and underscores"
    ):
        StateManagementConfig(database_path=db_path, table_prefix="test-prefix")


def test_invalid_connection_pool(temp_db_dir):
    """Test invalid connection pool validation."""
    db_path = str(Path(temp_db_dir) / "test.db")

    with pytest.raises(ValueError, match="Connection pool must specify 'size'"):
        StateManagementConfig(database_path=db_path, connection_pool={"timeout": 30})

    with pytest.raises(ValueError, match="Connection pool size must be a positive integer"):
        StateManagementConfig(database_path=db_path, connection_pool={"size": 0, "timeout": 30})

    with pytest.raises(ValueError, match="Connection pool must specify 'timeout'"):
        StateManagementConfig(database_path=db_path, connection_pool={"size": 5})
