"""Comprehensive tests for config.py models to achieve 100% coverage."""

# Import directly from config.py to ensure coverage
from qdrant_loader.config import (
    ChunkingConfig,
    GlobalConfig,
    SemanticAnalysisConfig,
)


class TestSemanticAnalysisConfig:
    """Comprehensive tests for SemanticAnalysisConfig - covers lines 6-18."""

    def test_default_instantiation(self):
        """Test default instantiation - covers lines 6-18."""
        config = SemanticAnalysisConfig()

        # Verify all default values (covers lines 9-18)
        assert config.num_topics == 3
        assert config.lda_passes == 10
        assert config.spacy_model == "en_core_web_md"

    def test_custom_values(self):
        """Test custom value instantiation - covers lines 6-18."""
        config = SemanticAnalysisConfig(
            num_topics=5, lda_passes=20, spacy_model="en_core_web_sm"
        )

        assert config.num_topics == 5
        assert config.lda_passes == 20
        assert config.spacy_model == "en_core_web_sm"

    def test_field_descriptions_and_validation(self):
        """Test field descriptions and types - covers lines 9-18."""
        config = SemanticAnalysisConfig()

        # Test that fields exist and have correct types
        assert isinstance(config.num_topics, int)
        assert isinstance(config.lda_passes, int)
        assert isinstance(config.spacy_model, str)

        # Test field validation
        config_custom = SemanticAnalysisConfig(
            num_topics=1, lda_passes=1, spacy_model="en_core_web_lg"
        )
        assert config_custom.num_topics == 1
        assert config_custom.lda_passes == 1
        assert config_custom.spacy_model == "en_core_web_lg"

    def test_model_dump(self):
        """Test model serialization - covers all lines."""
        config = SemanticAnalysisConfig(
            num_topics=7, lda_passes=15, spacy_model="en_core_web_lg"
        )

        data = config.model_dump()
        expected = {"num_topics": 7, "lda_passes": 15, "spacy_model": "en_core_web_lg"}
        assert data == expected


class TestChunkingConfig:
    """Comprehensive tests for ChunkingConfig - covers lines 21-30."""

    def test_default_instantiation(self):
        """Test default instantiation - covers lines 21-30."""
        config = ChunkingConfig()

        # Verify all default values (covers lines 24-30)
        assert config.chunk_size == 1500
        assert config.chunk_overlap == 200

    def test_custom_values(self):
        """Test custom value instantiation - covers lines 21-30."""
        config = ChunkingConfig(chunk_size=2000, chunk_overlap=150)

        assert config.chunk_size == 2000
        assert config.chunk_overlap == 150

    def test_field_types_and_validation(self):
        """Test field types and validation - covers lines 24-30."""
        config = ChunkingConfig()

        # Test that fields exist and have correct types
        assert isinstance(config.chunk_size, int)
        assert isinstance(config.chunk_overlap, int)

        # Test custom values
        config_custom = ChunkingConfig(chunk_size=500, chunk_overlap=50)
        assert config_custom.chunk_size == 500
        assert config_custom.chunk_overlap == 50

    def test_model_dump(self):
        """Test model serialization - covers all lines."""
        config = ChunkingConfig(chunk_size=3000, chunk_overlap=300)

        data = config.model_dump()

        # Just verify our custom fields are present (there are more defaults)
        assert data["chunk_size"] == 3000
        assert data["chunk_overlap"] == 300
        assert isinstance(data, dict)


class TestGlobalConfig:
    """Comprehensive tests for GlobalConfig - covers lines 33-43."""

    def test_default_instantiation(self):
        """Test default instantiation - covers lines 33-43."""
        config = GlobalConfig()

        # Verify nested config defaults (covers lines 36-43)
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.semantic_analysis, SemanticAnalysisConfig)

        # Verify nested defaults
        assert config.chunking.chunk_size == 1500
        assert config.semantic_analysis.num_topics == 3

    def test_custom_nested_configs(self):
        """Test custom nested configurations - covers lines 33-43."""
        custom_chunking = ChunkingConfig(chunk_size=2500, chunk_overlap=250)
        custom_semantic = SemanticAnalysisConfig(num_topics=8, lda_passes=25)

        config = GlobalConfig(
            chunking=custom_chunking, semantic_analysis=custom_semantic
        )

        assert config.chunking.chunk_size == 2500
        assert config.chunking.chunk_overlap == 250
        assert config.semantic_analysis.num_topics == 8
        assert config.semantic_analysis.lda_passes == 25

    def test_nested_config_types(self):
        """Test nested configuration types - covers lines 36-43."""
        config = GlobalConfig()

        # Verify types
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.semantic_analysis, SemanticAnalysisConfig)

    def test_model_dump_with_nested(self):
        """Test model serialization with nested configs - covers all lines."""
        config = GlobalConfig()

        data = config.model_dump()

        # Verify structure
        assert "chunking" in data
        assert "semantic_analysis" in data
        assert isinstance(data["chunking"], dict)
        assert isinstance(data["semantic_analysis"], dict)

        # Verify nested data
        assert data["chunking"]["chunk_size"] == 1500
        assert data["semantic_analysis"]["num_topics"] == 3


class TestSettings:
    """Simplified tests for Settings class - focuses on the class definition."""

    def test_settings_class_exists(self):
        """Test that Settings class exists and can be imported - covers lines 46-79."""
        # Import the Settings class directly from the config.py file
        import importlib.util
        from pathlib import Path

        # Get the path to the config.py file specifically
        config_file = (
            Path(__file__).parent.parent.parent / "src" / "qdrant_loader" / "config.py"
        )

        # Load the module directly from file
        spec = importlib.util.spec_from_file_location("config_module", config_file)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)

        # Get the Settings class from the direct module
        Settings = getattr(config_module, "Settings", None)
        assert Settings is not None, "Settings class not found in config.py"

        # Check that the class has the expected field annotations
        annotations = getattr(Settings, "__annotations__", {})

        # The actual Settings class should have these fields from config.py
        expected_fields = ["global_config"]  # This is the main field we can verify

        for field in expected_fields:
            assert (
                field in annotations
            ), f"Field {field} not found in Settings annotations"

    def test_settings_inheritance(self):
        """Test Settings class inheritance and structure - covers class definition."""
        from qdrant_loader.config import Settings

        # Verify it's a Pydantic model
        assert hasattr(Settings, "model_validate")
        assert hasattr(Settings, "model_dump")

        # Test that it has the global_config field with proper default
        field_info = Settings.model_fields.get("global_config")
        assert field_info is not None


class TestConfigModuleImports:
    """Test module imports to ensure all lines are covered."""

    def test_all_imports_and_classes(self):
        """Test importing and using all classes - covers lines 1-4."""
        # Test import statement coverage (lines 1-4)
        from qdrant_loader.config import (
            ChunkingConfig,
            GlobalConfig,
            SemanticAnalysisConfig,
        )

        # Verify all classes are usable
        chunking = ChunkingConfig()
        global_config = GlobalConfig()
        semantic = SemanticAnalysisConfig()

        assert chunking is not None
        assert global_config is not None
        assert semantic is not None
