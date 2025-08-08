"""Tests for the root config module."""


# Import directly from the root config.py file to ensure coverage
from qdrant_loader.config import (
    ChunkingConfig,
    GlobalConfig, 
    SemanticAnalysisConfig,
)


class TestSemanticAnalysisConfig:
    """Test cases for SemanticAnalysisConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SemanticAnalysisConfig()
        
        assert config.num_topics == 3
        assert config.lda_passes == 10
        assert config.spacy_model == "en_core_web_md"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SemanticAnalysisConfig(
            num_topics=5,
            lda_passes=20,
            spacy_model="en_core_web_sm"
        )
        
        assert config.num_topics == 5
        assert config.lda_passes == 20
        assert config.spacy_model == "en_core_web_sm"

    def test_validation_num_topics(self):
        """Test validation for num_topics field."""
        # Valid values
        config = SemanticAnalysisConfig(num_topics=1)
        assert config.num_topics == 1
        
        config = SemanticAnalysisConfig(num_topics=10)
        assert config.num_topics == 10

    def test_validation_lda_passes(self):
        """Test validation for lda_passes field."""
        # Valid values
        config = SemanticAnalysisConfig(lda_passes=1)
        assert config.lda_passes == 1
        
        config = SemanticAnalysisConfig(lda_passes=50)
        assert config.lda_passes == 50

    def test_spacy_model_options(self):
        """Test different spacy model options."""
        # Test small model
        config = SemanticAnalysisConfig(spacy_model="en_core_web_sm")
        assert config.spacy_model == "en_core_web_sm"
        
        # Test medium model
        config = SemanticAnalysisConfig(spacy_model="en_core_web_md")
        assert config.spacy_model == "en_core_web_md"
        
        # Test large model
        config = SemanticAnalysisConfig(spacy_model="en_core_web_lg")
        assert config.spacy_model == "en_core_web_lg"
        
        # Test custom model
        config = SemanticAnalysisConfig(spacy_model="custom_model")
        assert config.spacy_model == "custom_model"


class TestChunkingConfig:
    """Test cases for ChunkingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ChunkingConfig()
        
        assert config.chunk_size == 1500
        assert config.chunk_overlap == 200

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ChunkingConfig(
            chunk_size=2000,
            chunk_overlap=300
        )
        
        assert config.chunk_size == 2000
        assert config.chunk_overlap == 300

    def test_validation_chunk_size(self):
        """Test validation for chunk_size field."""
        # Valid values
        config = ChunkingConfig(chunk_size=500)
        assert config.chunk_size == 500
        
        config = ChunkingConfig(chunk_size=5000)
        assert config.chunk_size == 5000

    def test_validation_chunk_overlap(self):
        """Test validation for chunk_overlap field."""
        # Valid values
        config = ChunkingConfig(chunk_overlap=0)
        assert config.chunk_overlap == 0
        
        config = ChunkingConfig(chunk_overlap=100)
        assert config.chunk_overlap == 100
        
        config = ChunkingConfig(chunk_overlap=500)
        assert config.chunk_overlap == 500


class TestGlobalConfig:
    """Test cases for GlobalConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GlobalConfig()
        
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.semantic_analysis, SemanticAnalysisConfig)
        
        # Test default values of nested configs
        assert config.chunking.chunk_size == 1500
        assert config.chunking.chunk_overlap == 200
        assert config.semantic_analysis.num_topics == 3
        assert config.semantic_analysis.lda_passes == 10

    def test_custom_nested_configs(self):
        """Test custom nested configuration objects."""
        chunking_config = ChunkingConfig(chunk_size=2000, chunk_overlap=300)
        semantic_config = SemanticAnalysisConfig(num_topics=5, lda_passes=15)
        
        config = GlobalConfig(
            chunking=chunking_config,
            semantic_analysis=semantic_config
        )
        
        assert config.chunking.chunk_size == 2000
        assert config.chunking.chunk_overlap == 300
        assert config.semantic_analysis.num_topics == 5
        assert config.semantic_analysis.lda_passes == 15

    def test_partial_nested_config(self):
        """Test providing partial nested configuration."""
        config = GlobalConfig(
            chunking=ChunkingConfig(chunk_size=3000)
        )
        
        # Custom chunking value
        assert config.chunking.chunk_size == 3000
        # Default chunking value
        assert config.chunking.chunk_overlap == 200
        # Default semantic analysis
        assert config.semantic_analysis.num_topics == 3


class TestConfigSerialization:
    """Test cases for configuration serialization and deserialization."""

    def test_semantic_analysis_config_serialization(self):
        """Test serialization of SemanticAnalysisConfig."""
        config = SemanticAnalysisConfig(num_topics=5, lda_passes=15, spacy_model="en_core_web_sm")
        
        # Test model_dump
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)
        assert config_dict["num_topics"] == 5
        assert config_dict["lda_passes"] == 15
        assert config_dict["spacy_model"] == "en_core_web_sm"
        
        # Test model_dump_json
        config_json = config.model_dump_json()
        assert isinstance(config_json, str)
        assert '"num_topics":5' in config_json

    def test_chunking_config_serialization(self):
        """Test serialization of ChunkingConfig."""
        config = ChunkingConfig(chunk_size=2000, chunk_overlap=300)
        
        # Test model_dump
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)
        assert config_dict["chunk_size"] == 2000
        assert config_dict["chunk_overlap"] == 300
        
        # Test model_dump_json
        config_json = config.model_dump_json()
        assert isinstance(config_json, str)
        assert '"chunk_size":2000' in config_json

    def test_global_config_serialization(self):
        """Test serialization of GlobalConfig."""
        config = GlobalConfig(
            chunking=ChunkingConfig(chunk_size=3000),
            semantic_analysis=SemanticAnalysisConfig(num_topics=8)
        )
        
        # Test model_dump
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)
        assert isinstance(config_dict["chunking"], dict)
        assert isinstance(config_dict["semantic_analysis"], dict)
        assert config_dict["chunking"]["chunk_size"] == 3000
        assert config_dict["semantic_analysis"]["num_topics"] == 8
        
        # Test model_dump_json
        config_json = config.model_dump_json()
        assert isinstance(config_json, str)
        
        # Test recreation from JSON
        new_config = GlobalConfig.model_validate_json(config_json)
        assert new_config.chunking.chunk_size == 3000
        assert new_config.semantic_analysis.num_topics == 8


class TestRootConfigModuleImports:
    """Test module-level imports to improve coverage."""

    def test_import_all_config_classes(self):
        """Test importing all classes from config module - covers import lines."""
        # This test covers the import statements in config.py
        # Import the classes that actually exist in the root config.py
        from qdrant_loader.config import (
            ChunkingConfig,
            GlobalConfig,
            SemanticAnalysisConfig,
        )
        
        # Verify all classes are importable
        assert ChunkingConfig is not None
        assert GlobalConfig is not None
        assert SemanticAnalysisConfig is not None
        
        # Create instances to ensure they work
        chunking_config = ChunkingConfig()
        global_config = GlobalConfig()
        semantic_config = SemanticAnalysisConfig()
        
        assert chunking_config.chunk_size == 1500  # default value
        assert global_config.chunking is not None
        assert semantic_config.num_topics == 3  # default value

    def test_module_level_imports_coverage(self):
        """Test module-level imports and exports to improve coverage."""
        import qdrant_loader.config as config_module
        
        # Verify the module has expected attributes
        assert hasattr(config_module, 'ChunkingConfig')
        assert hasattr(config_module, 'GlobalConfig')
        assert hasattr(config_module, 'SemanticAnalysisConfig')
        
        # Test that we can access the classes
        ChunkingConfig = getattr(config_module, 'ChunkingConfig')
        GlobalConfig = getattr(config_module, 'GlobalConfig')
        SemanticAnalysisConfig = getattr(config_module, 'SemanticAnalysisConfig')
        
        # Create instances to verify they work
        chunking_config = ChunkingConfig()
        global_config = GlobalConfig()
        semantic_config = SemanticAnalysisConfig()
        
        assert chunking_config is not None
        assert global_config is not None 
        assert semantic_config is not None