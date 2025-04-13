"""Shared test fixtures and configuration.

This module contains pytest fixtures that are shared across all test modules.
"""
import shutil
from pathlib import Path
from dotenv import load_dotenv

import pytest

from qdrant_loader.config import initialize_config, get_settings

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Create necessary directories
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Load test configuration
    config_path = Path("tests/config.test.yaml")
    env_path = Path("tests/.env.test")
    
    # Load environment variables first
    load_dotenv(env_path, override=True)
    
    # Initialize config using the same function as CLI
    initialize_config(config_path)
    
    yield
    
    # Clean up after all tests
    if data_dir.exists():
        shutil.rmtree(data_dir)

@pytest.fixture(scope="session")
def test_settings():
    """Get test settings."""
    settings = get_settings()
    return settings

@pytest.fixture(scope="session")
def test_global_config():
    """Get test configuration."""
    config = get_settings().global_config
    return config