"""Test configuration and fixtures."""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
import yaml

from qdrant_loader.config import (
    Settings,
    SourcesConfig,
    GlobalConfig,
    ChunkingConfig,
    EmbeddingConfig
)

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")

@pytest.fixture
def test_settings() -> Settings:
    """Fixture that provides test settings for all tests."""
    return Settings(
        QDRANT_URL=os.getenv("QDRANT_URL"),
        QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
        QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO")
    )

@pytest.fixture
def test_global_config() -> GlobalConfig:
    """Fixture that provides test global configuration."""
    return GlobalConfig(
        chunking={"size": 500, "overlap": 50},
        embedding=EmbeddingConfig(
            model="text-embedding-3-small",
            batch_size=100
        ),
        logging={
            "level": "INFO",
            "format": "json",
            "file": "qdrant-loader.log"
        }
    )

@pytest.fixture
def test_sources_config() -> SourcesConfig:
    """Fixture that provides test sources configuration."""
    config_path = Path(__file__).parent / "config.test.yaml"
    if not config_path.exists():
        pytest.fail("Test configuration file not found")
    
    return SourcesConfig.from_yaml(config_path)

@pytest.fixture
def test_chunking_config() -> ChunkingConfig:
    """Fixture that provides test chunking configuration."""
    return ChunkingConfig(
        chunk_size=1000,
        chunk_overlap=200
    )

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    ) 