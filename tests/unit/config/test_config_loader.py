"""Tests for configuration loader."""

import os
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from qdrant_loader.config import initialize_config, get_settings


@pytest.fixture
def test_config_path(tmp_path: Path) -> Path:
    """Create a temporary test configuration file."""
    config_data = {
        "global": {
            "chunking": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            "embedding": {
                "model": "text-embedding-3-small",
                "vector_size": 1536,
            },
        },
        "sources": {
            "publicdocs": {
                "example": {
                    "base_url": "https://example.com",
                    "version": "1.0",
                    "content_type": "html",
                    "selectors": {
                        "content": ".content",
                        "title": "h1",
                    },
                }
            }
        },
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        import yaml

        yaml.dump(config_data, f)
    return config_path


@pytest.fixture
def test_env_path(tmp_path: Path) -> Path:
    """Create a temporary test environment file."""
    env_data = """
    QDRANT_URL=http://localhost:6333
    QDRANT_COLLECTION_NAME=test_collection
    OPENAI_API_KEY=test_key
    STATE_DB_PATH=./data/state.db
    """
    env_path = tmp_path / ".env.test"
    with open(env_path, "w") as f:
        f.write(env_data)
    return env_path


def test_config_initialization(test_config_path: Path, test_env_path: Path):
    """Test basic configuration initialization."""
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(test_env_path, override=True)

    # Initialize config
    initialize_config(test_config_path)

    # Get settings
    settings = get_settings()

    # Verify basic settings
    assert settings.QDRANT_URL == "http://localhost:6333"
    assert settings.QDRANT_COLLECTION_NAME == "test_collection"
    assert settings.OPENAI_API_KEY == "test_key"
    assert settings.STATE_DB_PATH == "./data/state.db"

    # Verify global config
    assert settings.global_config.chunking.chunk_size == 1000
    assert settings.global_config.chunking.chunk_overlap == 200
    assert settings.global_config.embedding.model == "text-embedding-3-small"
    assert settings.global_config.embedding.vector_size == 1536

    # Verify sources config
    assert "example" in settings.sources_config.publicdocs
    assert str(settings.sources_config.publicdocs["example"].base_url) == "https://example.com/"
    assert settings.sources_config.publicdocs["example"].version == "1.0"
    assert settings.sources_config.publicdocs["example"].content_type == "html"


def test_missing_required_fields(test_config_path: Path):
    """Test that missing required fields raise validation errors."""
    # Create config with missing required fields
    config_data = {
        "global": {
            "chunking": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            "embedding": {
                "model": "text-embedding-3-small",
                "vector_size": 1536,
            },
        },
        "sources": {
            "publicdocs": {
                "example": {
                    # Missing required base_url and version fields
                    "content_type": "html",
                    "selectors": {
                        "content": ".content",
                        "title": "h1",
                    },
                }
            }
        },
    }
    with open(test_config_path, "w") as f:
        import yaml

        yaml.dump(config_data, f)

    # Clear environment variables
    os.environ.pop("QDRANT_URL", None)
    os.environ.pop("QDRANT_COLLECTION_NAME", None)
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("STATE_DB_PATH", None)

    # Attempt to initialize config
    with pytest.raises(ValidationError):
        initialize_config(test_config_path)


def test_environment_variable_substitution(test_config_path: Path, test_env_path: Path):
    """Test environment variable substitution in configuration."""
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(test_env_path, override=True)

    # Modify config to include environment variables
    with open(test_config_path, "r") as f:
        import yaml

        config_data = yaml.safe_load(f)

    config_data["global"]["chunking"]["chunk_size"] = "${CHUNK_SIZE}"
    os.environ["CHUNK_SIZE"] = "2000"

    with open(test_config_path, "w") as f:
        yaml.dump(config_data, f)

    # Initialize config
    initialize_config(test_config_path)
    settings = get_settings()

    # Verify substitution
    assert settings.global_config.chunking.chunk_size == 2000


def test_invalid_yaml(test_config_path: Path):
    """Test handling of invalid YAML."""
    # Write invalid YAML
    with open(test_config_path, "w") as f:
        f.write("invalid: yaml: here")

    # Attempt to initialize config
    with pytest.raises(Exception):
        initialize_config(test_config_path)


def test_source_config_validation(test_config_path: Path, test_env_path: Path):
    """Test validation of source-specific configurations."""
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(test_env_path, override=True)

    # Add invalid source config
    with open(test_config_path, "r") as f:
        import yaml

        config_data = yaml.safe_load(f)

    config_data["sources"]["confluence"] = {
        "test_space": {
            "base_url": "https://example.com",
            "space_key": "TEST",
            # Missing required token and email
        }
    }

    with open(test_config_path, "w") as f:
        yaml.dump(config_data, f)

    # Attempt to initialize config
    with pytest.raises(ValidationError):
        initialize_config(test_config_path)


def test_config_to_dict(test_config_path: Path, test_env_path: Path):
    """Test conversion of configuration to dictionary."""
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(test_env_path, override=True)

    # Initialize config
    initialize_config(test_config_path)
    settings = get_settings()

    # Convert to dict
    config_dict = settings.to_dict()

    # Verify structure
    assert "global" in config_dict
    assert "sources" in config_dict
    assert "publicdocs" in config_dict["sources"]
    assert "example" in config_dict["sources"]["publicdocs"]
