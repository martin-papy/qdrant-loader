"""Integration test configuration.

This conftest.py ensures that test environment variables are loaded
before any module-level configuration checks are performed.
"""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any


import pytest

from dotenv import load_dotenv



# Load environment variables at import time
tests_dir = Path(__file__).parent.parent
env_path = tests_dir / "config" / ".env.test"
if env_path.exists():
    load_dotenv(env_path, override=True)


class TestConfig:
    """Test configuration object with attribute access."""

    def __init__(self, config_dict: dict[str, Any]):
        for key, value in config_dict.items():
            if isinstance(value, dict):
                setattr(self, key, TestConfig(value))
            else:
                setattr(self, key, value)


@pytest.fixture
def test_config() -> TestConfig:
    """Provide test configuration for integration tests."""
    config_dict = {
        "qdrant": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "test_collection",
            "vector_size": 384,
            "distance": "Cosine",
            "api_key": None,
        },
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "test_password",
            "database": "test_db",
        },
        "graphiti": {
            "enabled": True,
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "test-key",
                "max_tokens": 4000,
                "temperature": 0.1,
            },
            "embedder": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "test-key",
                "dimensions": None,
                "batch_size": 100,
            },
            "operational": {
                "max_episode_length": 10000,
                "search_limit_default": 10,
                "search_limit_max": 100,
                "enable_auto_indexing": True,
                "enable_constraints": True,
                "timeout_seconds": 30,
            },
            "debug_mode": False,
        },
        "sync": {
            "batch_size": 10,
            "max_retries": 3,
            "timeout_seconds": 30,
            "enable_monitoring": True,
            "enable_conflict_resolution": True,
        },
        "embedding": {
            "api_key": "test-key",
            "model": "text-embedding-ada-002",
        },
    }
    return TestConfig(config_dict)











@pytest.fixture
def real_config_dir():
    """Use the actual test configuration directory with real config files.
    
    This fixture provides access to real configuration files for integration testing,
    avoiding the use of synthetic temporary configurations.
    """
    # Use the existing test config directory
    config_path = Path(__file__).parent.parent / "config"
    
    # Verify the config directory exists and has the expected files
    assert config_path.exists(), f"Config directory not found: {config_path}"
    assert (config_path / "connectivity.yaml").exists(), "connectivity.yaml not found"
    assert (config_path / "projects.yaml").exists(), "projects.yaml not found"
    assert (config_path / "fine-tuning.yaml").exists(), "fine-tuning.yaml not found"
    
    return config_path
