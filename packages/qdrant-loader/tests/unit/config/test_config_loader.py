"""Tests for configuration loader."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from qdrant_loader.config import get_settings, initialize_config


@pytest.fixture
def test_config_path(tmp_path: Path) -> Path:
    """Create a temporary test configuration file."""
    config_data = {
        "global": {
            "qdrant": {
                "url": "http://localhost:6333",
                "api_key": None,
                "collection_name": "test_collection",
            },
            "chunking": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            "embedding": {
                "model": "text-embedding-3-small",
                "api_key": "${OPENAI_API_KEY}",
                "batch_size": 100,
                "endpoint": "https://api.openai.com/v1",
                "tokenizer": "cl100k_base",
                "vector_size": 1536,
                "max_tokens_per_request": 8000,
                "max_tokens_per_chunk": 8000,
            },
            "state_management": {
                "database_path": "${STATE_DB_PATH}",
                "table_prefix": "qdrant_loader_",
                "connection_pool": {
                    "size": 5,
                    "timeout": 30,
                },
            },
            "file_conversion": {
                "max_file_size": 52428800,
                "conversion_timeout": 300,
                "markitdown": {
                    "enable_llm_descriptions": False,
                    "llm_model": "gpt-4o",
                    "llm_endpoint": "https://api.openai.com/v1",
                    "llm_api_key": "${OPENAI_API_KEY}",
                },
            },
        },
        "projects": {
            "default": {
                "display_name": "Config Loader Test Project",
                "description": "Default project for config loader testing",
                "sources": {
                    "publicdocs": {
                        "example": {
                            "source_type": "publicdocs",
                            "source": "example",
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
    initialize_config(test_config_path, skip_validation=True)

    # Get settings
    settings = get_settings()

    # Verify basic settings
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection_name == "test_collection"
    assert settings.global_config.embedding.api_key == "test_key"
    assert settings.state_db_path == "./data/state.db"

    # Verify global config
    assert settings.global_config.chunking.chunk_size == 1000
    assert settings.global_config.chunking.chunk_overlap == 200
    assert settings.global_config.embedding.model == "text-embedding-3-small"
    assert settings.global_config.embedding.vector_size == 1536

    # Verify sources config - access through projects
    default_project = settings.projects_config.projects.get("default")
    assert default_project is not None
    assert "example" in default_project.sources.publicdocs
    assert (
        str(default_project.sources.publicdocs["example"].base_url)
        == "https://example.com/"
    )
    assert default_project.sources.publicdocs["example"].version == "1.0"
    assert default_project.sources.publicdocs["example"].content_type == "html"


def test_missing_required_fields(test_config_path: Path):
    """Test that missing required fields raise validation errors."""
    # Create config with missing required fields
    config_data = {
        "global": {
            "qdrant": {
                "url": "http://localhost:6333",
                "api_key": None,
                "collection_name": "test_collection",
            },
            "chunking": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            "embedding": {
                "model": "text-embedding-3-small",
                "vector_size": 1536,
                # Missing required api_key field
            },
            "state_management": {
                "database_path": ":memory:",
            },
        },
        "projects": {
            "default": {
                "display_name": "Missing Fields Test Project",
                "description": "Default project for missing fields testing",
                "sources": {
                    "publicdocs": {
                        "example": {
                            "source_type": "publicdocs",
                            "source": "example",
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
        },
    }
    with open(test_config_path, "w") as f:
        import yaml

        yaml.dump(config_data, f)

    # Clear environment variables
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("STATE_DB_PATH", None)

    # Attempt to initialize config - should fail validation
    with pytest.raises(ValidationError):
        initialize_config(test_config_path, skip_validation=False)


def test_environment_variable_substitution(test_config_path: Path, test_env_path: Path):
    """Test environment variable substitution in configuration."""
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(test_env_path, override=True)

    # Store original environment state
    original_chunk_size = os.environ.get("CHUNK_SIZE")

    try:
        # Modify config to include environment variables
        with open(test_config_path) as f:
            import yaml

            config_data = yaml.safe_load(f)

        config_data["global"]["chunking"]["chunk_size"] = "${CHUNK_SIZE}"
        os.environ["CHUNK_SIZE"] = "2000"

        with open(test_config_path, "w") as f:
            yaml.dump(config_data, f)

        # Initialize config
        initialize_config(test_config_path, skip_validation=True)
        settings = get_settings()

        # Verify substitution
        assert settings.global_config.chunking.chunk_size == 2000
    finally:
        # Clean up environment variable
        if original_chunk_size is None:
            os.environ.pop("CHUNK_SIZE", None)
        else:
            os.environ["CHUNK_SIZE"] = original_chunk_size


def test_invalid_yaml(test_config_path: Path):
    """Test handling of invalid YAML."""
    # Write invalid YAML
    with open(test_config_path, "w") as f:
        f.write("invalid: yaml: here")

    # Attempt to initialize config
    with pytest.raises(Exception):
        initialize_config(test_config_path, skip_validation=True)


def test_source_config_validation(test_config_path: Path, test_env_path: Path):
    """Test validation of source-specific configurations."""
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(test_env_path, override=True)

    # Add invalid source config
    with open(test_config_path) as f:
        import yaml

        config_data = yaml.safe_load(f)

    # Add invalid confluence source to the default project
    config_data["projects"]["default"]["sources"]["confluence"] = {
        "test_space": {
            "source_type": "confluence",
            "source": "test_space",
            "base_url": "https://example.com",
            "space_key": "TEST",
            # Missing required token and email
        }
    }

    with open(test_config_path, "w") as f:
        yaml.dump(config_data, f)

    # Attempt to initialize config - should fail validation
    with pytest.raises(ValidationError):
        initialize_config(test_config_path, skip_validation=False)


def test_config_to_dict(test_config_path: Path, test_env_path: Path):
    """Test conversion of configuration to dictionary."""
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(test_env_path, override=True)

    # Initialize config
    initialize_config(test_config_path, skip_validation=True)
    settings = get_settings()

    # Convert to dict
    config_dict = settings.to_dict()

    # Verify structure
    assert "global" in config_dict
    assert "projects" in config_dict
    assert "default" in config_dict["projects"]
    default_project = config_dict["projects"]["default"]
    assert "sources" in default_project
    assert "publicdocs" in default_project["sources"]
    assert "example" in default_project["sources"]["publicdocs"]
