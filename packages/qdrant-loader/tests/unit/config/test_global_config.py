"""Tests for global configuration with file conversion settings."""

import pytest
from qdrant_loader.config.global_config import GlobalConfig
from qdrant_loader.core.file_conversion import FileConversionConfig, MarkItDownConfig


class TestGlobalConfigFileConversion:
    """Test cases for global configuration file conversion integration."""

    def test_default_file_conversion_config(self):
        """Test that default file conversion config is properly initialized."""
        config = GlobalConfig()

        assert hasattr(config, "file_conversion")
        assert isinstance(config.file_conversion, FileConversionConfig)

        # Test default values
        assert config.file_conversion.max_file_size == 52428800  # 50MB
        assert config.file_conversion.conversion_timeout == 300  # 5 minutes
        assert isinstance(config.file_conversion.markitdown, MarkItDownConfig)
        assert config.file_conversion.markitdown.enable_llm_descriptions is False

    def test_custom_file_conversion_config(self):
        """Test that custom file conversion config can be provided."""
        custom_markitdown = MarkItDownConfig(
            enable_llm_descriptions=True,
            llm_model="gpt-4",
            llm_endpoint="https://custom.api.com/v1",
        )

        custom_file_conversion = FileConversionConfig(
            max_file_size=104857600,  # 100MB
            conversion_timeout=600,  # 10 minutes
            markitdown=custom_markitdown,
        )

        config = GlobalConfig(file_conversion=custom_file_conversion)

        assert config.file_conversion.max_file_size == 104857600
        assert config.file_conversion.conversion_timeout == 600
        assert config.file_conversion.markitdown.enable_llm_descriptions is True
        assert config.file_conversion.markitdown.llm_model == "gpt-4"
        assert (
            config.file_conversion.markitdown.llm_endpoint
            == "https://custom.api.com/v1"
        )

    def test_file_conversion_config_from_dict(self):
        """Test that file conversion config can be loaded from dictionary."""
        config_dict = {
            "file_conversion": {
                "max_file_size": 10485760,  # 10MB
                "conversion_timeout": 120,  # 2 minutes
                "markitdown": {
                    "enable_llm_descriptions": True,
                    "llm_model": "gpt-3.5-turbo",
                    "llm_endpoint": "https://api.openai.com/v1",
                },
            }
        }

        config = GlobalConfig(**config_dict)

        assert config.file_conversion.max_file_size == 10485760
        assert config.file_conversion.conversion_timeout == 120
        assert config.file_conversion.markitdown.enable_llm_descriptions is True
        assert config.file_conversion.markitdown.llm_model == "gpt-3.5-turbo"

    def test_global_config_to_dict_includes_file_conversion(self):
        """Test that to_dict() includes file conversion settings."""
        config = GlobalConfig()
        config_dict = config.to_dict()

        assert "file_conversion" in config_dict
        assert "max_file_size" in config_dict["file_conversion"]
        assert "conversion_timeout" in config_dict["file_conversion"]
        assert "markitdown" in config_dict["file_conversion"]

        markitdown_dict = config_dict["file_conversion"]["markitdown"]
        assert "enable_llm_descriptions" in markitdown_dict
        assert "llm_model" in markitdown_dict
        assert "llm_endpoint" in markitdown_dict

    def test_file_conversion_config_validation(self):
        """Test that file conversion config validation works."""
        # Test invalid max_file_size
        with pytest.raises(ValueError):
            GlobalConfig(file_conversion={"max_file_size": -1})

        # Test invalid conversion_timeout
        with pytest.raises(ValueError):
            GlobalConfig(file_conversion={"conversion_timeout": -1})
