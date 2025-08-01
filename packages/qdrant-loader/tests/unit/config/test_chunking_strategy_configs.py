"""Tests for chunking strategy configuration validation and behavior."""

import pytest

from qdrant_loader.config.chunking import (
    ChunkingConfig,
    DefaultStrategyConfig,
    HtmlStrategyConfig,
    CodeStrategyConfig,
    JsonStrategyConfig,
    MarkdownStrategyConfig,
    StrategySpecificConfig,
)
from qdrant_loader.config.global_config import GlobalConfig


class TestDefaultStrategyConfig:
    """Test the DefaultStrategyConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = DefaultStrategyConfig()
        assert config.min_chunk_size == 100
        assert config.enable_semantic_analysis is True
        assert config.enable_entity_extraction is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = DefaultStrategyConfig(
            min_chunk_size=50,
            enable_semantic_analysis=False,
            enable_entity_extraction=False
        )
        assert config.min_chunk_size == 50
        assert config.enable_semantic_analysis is False
        assert config.enable_entity_extraction is False

    def test_validation_min_chunk_size(self):
        """Test validation of min_chunk_size."""
        # Valid value
        config = DefaultStrategyConfig(min_chunk_size=50)
        assert config.min_chunk_size == 50

        # Invalid value (zero or negative)
        with pytest.raises(ValueError):
            DefaultStrategyConfig(min_chunk_size=0)
        
        with pytest.raises(ValueError):
            DefaultStrategyConfig(min_chunk_size=-10)


class TestHtmlStrategyConfig:
    """Test the HtmlStrategyConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HtmlStrategyConfig()
        assert config.simple_parsing_threshold == 100000
        assert config.max_html_size_for_parsing == 500000
        assert config.max_sections_to_process == 200
        assert config.max_chunk_size_for_nlp == 20000
        assert config.preserve_semantic_structure is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HtmlStrategyConfig(
            simple_parsing_threshold=50000,
            max_html_size_for_parsing=1000000,
            max_sections_to_process=100,
            max_chunk_size_for_nlp=10000,
            preserve_semantic_structure=False
        )
        assert config.simple_parsing_threshold == 50000
        assert config.max_html_size_for_parsing == 1000000
        assert config.max_sections_to_process == 100
        assert config.max_chunk_size_for_nlp == 10000
        assert config.preserve_semantic_structure is False


class TestCodeStrategyConfig:
    """Test the CodeStrategyConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CodeStrategyConfig()
        assert config.max_file_size_for_ast == 75000
        assert config.max_elements_to_process == 800
        assert config.max_recursion_depth == 8
        assert config.max_element_size == 20000
        assert config.enable_ast_parsing is True
        assert config.enable_dependency_analysis is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CodeStrategyConfig(
            max_file_size_for_ast=100000,
            max_elements_to_process=1000,
            max_recursion_depth=10,
            max_element_size=25000,
            enable_ast_parsing=False,
            enable_dependency_analysis=False
        )
        assert config.max_file_size_for_ast == 100000
        assert config.max_elements_to_process == 1000
        assert config.max_recursion_depth == 10
        assert config.max_element_size == 25000
        assert config.enable_ast_parsing is False
        assert config.enable_dependency_analysis is False


class TestJsonStrategyConfig:
    """Test the JsonStrategyConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = JsonStrategyConfig()
        assert config.max_json_size_for_parsing == 1000000
        assert config.max_objects_to_process == 200
        assert config.max_chunk_size_for_nlp == 20000
        assert config.max_recursion_depth == 5
        assert config.max_array_items_per_chunk == 50
        assert config.max_object_keys_to_process == 100
        assert config.enable_schema_inference is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = JsonStrategyConfig(
            max_json_size_for_parsing=2000000,
            max_objects_to_process=500,
            max_chunk_size_for_nlp=30000,
            max_recursion_depth=10,
            max_array_items_per_chunk=100,
            max_object_keys_to_process=200,
            enable_schema_inference=False
        )
        assert config.max_json_size_for_parsing == 2000000
        assert config.max_objects_to_process == 500
        assert config.max_chunk_size_for_nlp == 30000
        assert config.max_recursion_depth == 10
        assert config.max_array_items_per_chunk == 100
        assert config.max_object_keys_to_process == 200
        assert config.enable_schema_inference is False


class TestMarkdownStrategyConfig:
    """Test the MarkdownStrategyConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MarkdownStrategyConfig()
        assert config.min_content_length_for_nlp == 100
        assert config.min_word_count_for_nlp == 20
        assert config.min_line_count_for_nlp == 3
        assert config.min_section_size == 500
        assert config.max_chunks_per_section == 1000
        assert config.max_overlap_percentage == 0.25
        assert config.max_workers == 4
        assert config.estimation_buffer == 0.2
        assert config.words_per_minute_reading == 200
        assert config.header_analysis_threshold_h1 == 3
        assert config.header_analysis_threshold_h3 == 8
        assert config.enable_hierarchical_metadata is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MarkdownStrategyConfig(
            min_content_length_for_nlp=50,
            min_word_count_for_nlp=10,
            min_line_count_for_nlp=2,
            min_section_size=300,
            max_chunks_per_section=2000,
            max_overlap_percentage=0.5,
            max_workers=8,
            estimation_buffer=0.3,
            words_per_minute_reading=250,
            header_analysis_threshold_h1=5,
            header_analysis_threshold_h3=10,
            enable_hierarchical_metadata=False
        )
        assert config.min_content_length_for_nlp == 50
        assert config.min_word_count_for_nlp == 10
        assert config.min_line_count_for_nlp == 2
        assert config.min_section_size == 300
        assert config.max_chunks_per_section == 2000
        assert config.max_overlap_percentage == 0.5
        assert config.max_workers == 8
        assert config.estimation_buffer == 0.3
        assert config.words_per_minute_reading == 250
        assert config.header_analysis_threshold_h1 == 5
        assert config.header_analysis_threshold_h3 == 10
        assert config.enable_hierarchical_metadata is False

    def test_validation_positive_values(self):
        """Test validation of positive value constraints."""
        # Test minimum constraints
        with pytest.raises(ValueError):
            MarkdownStrategyConfig(min_content_length_for_nlp=0)
        
        with pytest.raises(ValueError):
            MarkdownStrategyConfig(min_word_count_for_nlp=0)
        
        with pytest.raises(ValueError):
            MarkdownStrategyConfig(max_workers=0)

    def test_validation_percentage_bounds(self):
        """Test validation of percentage bounds."""
        # Valid percentages
        config = MarkdownStrategyConfig(max_overlap_percentage=0.0)
        assert config.max_overlap_percentage == 0.0
        
        config = MarkdownStrategyConfig(max_overlap_percentage=1.0)
        assert config.max_overlap_percentage == 1.0

        # Invalid percentages
        with pytest.raises(ValueError):
            MarkdownStrategyConfig(max_overlap_percentage=-0.1)
        
        with pytest.raises(ValueError):
            MarkdownStrategyConfig(max_overlap_percentage=1.1)

        # Test estimation_buffer bounds
        config = MarkdownStrategyConfig(estimation_buffer=0.0)
        assert config.estimation_buffer == 0.0
        
        with pytest.raises(ValueError):
            MarkdownStrategyConfig(estimation_buffer=-0.1)


class TestStrategySpecificConfig:
    """Test the StrategySpecificConfig class."""

    def test_default_values(self):
        """Test that all strategy configs are properly initialized."""
        config = StrategySpecificConfig()
        
        # Test that all strategy configs exist and have proper types
        assert isinstance(config.default, DefaultStrategyConfig)
        assert isinstance(config.html, HtmlStrategyConfig)
        assert isinstance(config.code, CodeStrategyConfig)
        assert isinstance(config.json_strategy, JsonStrategyConfig)
        assert isinstance(config.markdown, MarkdownStrategyConfig)

    def test_json_alias(self):
        """Test that json alias works for json_strategy."""
        config = StrategySpecificConfig()
        
        # Should be able to access via alias
        json_config = config.json_strategy
        assert isinstance(json_config, JsonStrategyConfig)
        assert json_config.enable_schema_inference is True

    def test_custom_strategy_configs(self):
        """Test initialization with custom strategy configurations."""
        custom_default = DefaultStrategyConfig(min_chunk_size=50)
        custom_markdown = MarkdownStrategyConfig(min_section_size=300)
        
        config = StrategySpecificConfig(
            default=custom_default,
            markdown=custom_markdown
        )
        
        assert config.default.min_chunk_size == 50
        assert config.markdown.min_section_size == 300
        # Other strategies should still have defaults
        assert config.html.simple_parsing_threshold == 100000


class TestChunkingConfigIntegration:
    """Test the complete ChunkingConfig with strategy-specific configurations."""

    def test_complete_chunking_config(self):
        """Test that ChunkingConfig properly includes strategy configurations."""
        config = ChunkingConfig()
        
        # Test main chunking settings
        assert config.chunk_size == 1500
        assert config.chunk_overlap == 200
        assert config.max_chunks_per_document == 500
        
        # Test strategy-specific configs are accessible
        assert isinstance(config.strategies, StrategySpecificConfig)
        assert isinstance(config.strategies.markdown, MarkdownStrategyConfig)
        assert config.strategies.markdown.min_section_size == 500

    def test_chunk_overlap_validation(self):
        """Test that chunk overlap validation works correctly."""
        # Valid overlap (less than chunk size)
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=500)
        assert config.chunk_overlap == 500

        # Invalid overlap (equal to chunk size)
        with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
            ChunkingConfig(chunk_size=1000, chunk_overlap=1000)

        # Invalid overlap (greater than chunk size)
        with pytest.raises(ValueError, match="Chunk overlap must be less than chunk size"):
            ChunkingConfig(chunk_size=1000, chunk_overlap=1500)

    def test_global_config_integration(self):
        """Test that GlobalConfig properly includes all chunking configurations."""
        config = GlobalConfig()
        
        # Test chunking config exists
        assert isinstance(config.chunking, ChunkingConfig)
        
        # Test strategy configs are accessible through global config
        markdown_config = config.chunking.strategies.markdown
        assert isinstance(markdown_config, MarkdownStrategyConfig)
        assert markdown_config.enable_hierarchical_metadata is True
        
        # Test all strategies are present
        strategies = config.chunking.strategies
        assert hasattr(strategies, 'default')
        assert hasattr(strategies, 'html') 
        assert hasattr(strategies, 'code')
        assert hasattr(strategies, 'json_strategy')
        assert hasattr(strategies, 'markdown')


class TestConfigurationFieldValidation:
    """Test configuration field validation and descriptions."""

    def test_field_descriptions_exist(self):
        """Test that all configuration fields have proper descriptions."""
        configs_to_test = [
            DefaultStrategyConfig,
            HtmlStrategyConfig,
            CodeStrategyConfig,
            JsonStrategyConfig,
            MarkdownStrategyConfig
        ]
        
        for config_class in configs_to_test:
            config = config_class()
            schema = config.model_json_schema()
            
            # All fields should have descriptions
            for field_name, field_info in schema.get("properties", {}).items():
                assert "description" in field_info, f"Field '{field_name}' in {config_class.__name__} missing description"
                assert len(field_info["description"]) > 10, f"Field '{field_name}' description too short"

    def test_validation_constraints(self):
        """Test that validation constraints are properly defined."""
        # Test integer constraints
        markdown_schema = MarkdownStrategyConfig().model_json_schema()
        
        # Check that positive constraints exist
        int_fields = ["min_content_length_for_nlp", "min_word_count_for_nlp", "max_workers"]
        for field in int_fields:
            field_props = markdown_schema["properties"][field]
            assert field_props.get("exclusiveMinimum") == 0 or field_props.get("minimum") == 1, \
                f"Field '{field}' should have positive constraint"

        # Check percentage constraints
        percentage_fields = ["max_overlap_percentage", "estimation_buffer"]
        for field in percentage_fields:
            field_props = markdown_schema["properties"][field]
            assert field_props.get("minimum") == 0.0, f"Field '{field}' should have minimum 0.0"
            assert field_props.get("maximum") == 1.0, f"Field '{field}' should have maximum 1.0" 