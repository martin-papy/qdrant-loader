"""Tests for the config.py module."""

import pytest
from pydantic import ValidationError
from qdrant_loader.config import (
    ChunkingConfig,
    GlobalConfig,
    ProjectsConfig,
    SemanticAnalysisConfig,
    Settings,
)
from qdrant_loader.config.qdrant import QdrantConfig


class TestSemanticAnalysisConfig:
    """Test the SemanticAnalysisConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SemanticAnalysisConfig()
        assert config.num_topics == 3
        assert config.lda_passes == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SemanticAnalysisConfig(num_topics=5, lda_passes=20)
        assert config.num_topics == 5
        assert config.lda_passes == 20

    def test_validation_positive_values(self):
        """Test validation of positive values."""
        # Valid positive values
        config = SemanticAnalysisConfig(num_topics=1, lda_passes=1)
        assert config.num_topics == 1
        assert config.lda_passes == 1

    def test_field_descriptions(self):
        """Test that field descriptions are properly set."""
        config = SemanticAnalysisConfig()
        schema = config.model_json_schema()

        assert "num_topics" in schema["properties"]
        assert "lda_passes" in schema["properties"]
        assert (
            schema["properties"]["num_topics"]["description"]
            == "Number of topics to extract using LDA"
        )
        assert (
            schema["properties"]["lda_passes"]["description"]
            == "Number of passes for LDA training"
        )


class TestChunkingConfig:
    """Test the ChunkingConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ChunkingConfig()
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ChunkingConfig(chunk_size=2000, chunk_overlap=400)
        assert config.chunk_size == 2000
        assert config.chunk_overlap == 400

    def test_validation_positive_values(self):
        """Test validation of positive values."""
        # Valid positive values
        config = ChunkingConfig(chunk_size=100, chunk_overlap=50)
        assert config.chunk_size == 100
        assert config.chunk_overlap == 50

    def test_field_descriptions(self):
        """Test that field descriptions are properly set."""
        config = ChunkingConfig()
        schema = config.model_json_schema()

        assert "chunk_size" in schema["properties"]
        assert "chunk_overlap" in schema["properties"]
        assert (
            schema["properties"]["chunk_size"]["description"]
            == "Size of text chunks in characters"
        )
        assert (
            schema["properties"]["chunk_overlap"]["description"]
            == "Overlap between chunks in characters"
        )


class TestGlobalConfig:
    """Test the GlobalConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GlobalConfig()
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.semantic_analysis, SemanticAnalysisConfig)

        # Check default values of nested configs
        assert config.chunking.chunk_size == 1000
        assert config.semantic_analysis.num_topics == 3

    def test_custom_nested_configs(self):
        """Test custom nested configuration values."""
        chunking = ChunkingConfig(chunk_size=1500, chunk_overlap=300)
        semantic = SemanticAnalysisConfig(num_topics=5, lda_passes=15)

        config = GlobalConfig(chunking=chunking, semantic_analysis=semantic)

        assert config.chunking.chunk_size == 1500
        assert config.chunking.chunk_overlap == 300
        assert config.semantic_analysis.num_topics == 5
        assert config.semantic_analysis.lda_passes == 15

    def test_partial_nested_config_override(self):
        """Test partial override of nested configurations."""
        config = GlobalConfig(
            chunking=ChunkingConfig(chunk_size=1500),  # Only override chunk_size
            semantic_analysis=SemanticAnalysisConfig(
                num_topics=7
            ),  # Only override num_topics
        )

        # Overridden values
        assert config.chunking.chunk_size == 1500
        assert config.semantic_analysis.num_topics == 7

        # Default values should remain
        assert config.chunking.chunk_overlap == 200
        assert config.semantic_analysis.lda_passes == 10

    def test_field_descriptions(self):
        """Test that field descriptions are properly set."""
        config = GlobalConfig()
        schema = config.model_json_schema()

        assert "chunking" in schema["properties"]
        assert "semantic_analysis" in schema["properties"]
        assert "chunking" in schema["properties"]
        assert "semantic_analysis" in schema["properties"]


class TestSettings:
    """Test the Settings class."""

    def _create_valid_global_config(self):
        """Create a valid global config with required Qdrant configuration."""
        return GlobalConfig(
            qdrant=QdrantConfig(
                url="http://localhost:6333",
                collection_name="test_collection",
                api_key=None,
            )
        )

    def test_default_settings(self):
        """Test creating settings with default values but valid Qdrant config."""
        global_config = self._create_valid_global_config()
        settings = Settings(global_config=global_config)

        # Check that configs are created
        assert isinstance(settings.global_config, GlobalConfig)
        assert isinstance(settings.projects_config, ProjectsConfig)

    def test_custom_global_config(self):
        """Test settings with custom global configuration."""
        custom_global_config = GlobalConfig(
            chunking=ChunkingConfig(chunk_size=2000, chunk_overlap=400),
            semantic_analysis=SemanticAnalysisConfig(num_topics=5, lda_passes=20),
            qdrant=QdrantConfig(
                url="http://localhost:6333",
                collection_name="test_collection",
                api_key=None,
            ),
        )

        settings = Settings(global_config=custom_global_config)

        # Check custom global config
        assert settings.global_config.chunking.chunk_size == 2000
        assert settings.global_config.chunking.chunk_overlap == 400
        assert settings.global_config.semantic_analysis.num_topics == 5
        assert settings.global_config.semantic_analysis.lda_passes == 20

    def test_field_descriptions(self):
        """Test that field descriptions are properly set."""
        global_config = self._create_valid_global_config()
        settings = Settings(global_config=global_config)
        schema = settings.model_json_schema()

        assert "global_config" in schema["properties"]
        assert "projects_config" in schema["properties"]
        assert (
            schema["properties"]["global_config"]["description"]
            == "Global configuration settings"
        )
        assert (
            schema["properties"]["projects_config"]["description"]
            == "Multi-project configurations"
        )

    def test_settings_model_config(self):
        """Test that Settings has proper model configuration."""
        global_config = self._create_valid_global_config()
        settings = Settings(global_config=global_config)

        # Check that the model config is set up correctly
        assert hasattr(settings, "model_config")

        # Check that we can access the configuration
        assert settings.global_config is not None
        assert settings.projects_config is not None

    def test_settings_validation(self):
        """Test Settings validation behavior."""
        # Test that Settings can be created with valid data
        global_config = self._create_valid_global_config()
        settings = Settings(
            global_config=global_config, projects_config=ProjectsConfig()
        )

        assert isinstance(settings.global_config, GlobalConfig)
        assert isinstance(settings.projects_config, ProjectsConfig)

    def test_settings_validation_requires_qdrant(self):
        """Test that Settings validation requires Qdrant configuration."""
        # Test that Settings fails without Qdrant config
        with pytest.raises(ValidationError, match="Qdrant configuration is required"):
            Settings(global_config=GlobalConfig())

    def test_settings_to_dict(self):
        """Test converting Settings to dictionary."""
        global_config = self._create_valid_global_config()
        settings = Settings(global_config=global_config)

        # Test that to_dict method exists and works
        settings_dict = settings.to_dict()
        assert isinstance(settings_dict, dict)
        assert "global" in settings_dict
        assert "projects" in settings_dict

    def test_settings_properties_exist(self):
        """Test that expected properties exist on Settings."""
        global_config = self._create_valid_global_config()
        settings = Settings(global_config=global_config)

        # These properties should exist based on the Settings class
        assert hasattr(settings, "global_config")
        assert hasattr(settings, "projects_config")

        # Check if property methods exist and work
        assert hasattr(Settings, "qdrant_url")
        assert hasattr(Settings, "qdrant_api_key")
        assert hasattr(Settings, "qdrant_collection_name")
        assert hasattr(Settings, "openai_api_key")
        assert hasattr(Settings, "state_db_path")

        # Test that properties work
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.qdrant_collection_name == "test_collection"
        assert settings.qdrant_api_key is None
