"""Tests for source configuration with file conversion settings."""

from pydantic import AnyUrl
from qdrant_loader.config.source_config import SourceConfig


class TestSourceConfigFileConversion:
    """Test cases for source configuration file conversion integration."""

    def test_default_file_conversion_settings(self):
        """Test that default file conversion settings are properly initialized."""
        config = SourceConfig(
            source_type="git",
            source="test-repo",
            base_url=AnyUrl("https://github.com/example/repo.git"),
        )

        assert hasattr(config, "enable_file_conversion")
        assert hasattr(config, "download_attachments")

        # Test default values
        assert config.enable_file_conversion is False
        assert config.download_attachments is None

    def test_custom_file_conversion_settings(self):
        """Test that custom file conversion settings can be provided."""
        config = SourceConfig(
            source_type="confluence",
            source="test-space",
            base_url=AnyUrl("https://company.atlassian.net/wiki"),
            enable_file_conversion=True,
            download_attachments=True,
        )

        assert config.enable_file_conversion is True
        assert config.download_attachments is True

    def test_file_conversion_settings_from_dict(self):
        """Test that file conversion settings can be loaded from dictionary."""
        config_dict = {
            "source_type": "jira",
            "source": "test-project",
            "base_url": "https://company.atlassian.net",
            "enable_file_conversion": True,
            "download_attachments": False,
        }

        config = SourceConfig(**config_dict)

        assert config.enable_file_conversion is True
        assert config.download_attachments is False

    def test_file_conversion_settings_validation(self):
        """Test that file conversion settings validation works."""
        # Test valid boolean values
        config = SourceConfig(
            source_type="localfile",
            source="test-files",
            base_url=AnyUrl("file:///path/to/files"),
            enable_file_conversion=True,
            download_attachments=None,
        )

        assert config.enable_file_conversion is True
        assert config.download_attachments is None

    def test_file_conversion_settings_inheritance(self):
        """Test that file conversion settings work with inheritance."""

        # This would be used by specific connector configs that inherit from SourceConfig
        class TestConnectorConfig(SourceConfig):
            """Test connector configuration."""

            additional_field: str = "test"

        config = TestConnectorConfig(
            source_type="test",
            source="test-source",
            base_url=AnyUrl("https://example.com"),
            enable_file_conversion=True,
            download_attachments=True,
            additional_field="custom_value",
        )

        assert config.enable_file_conversion is True
        assert config.download_attachments is True
        assert config.additional_field == "custom_value"

    def test_file_conversion_settings_optional(self):
        """Test that file conversion settings are optional."""
        # Should work without specifying file conversion settings
        config = SourceConfig(
            source_type="publicdocs",
            source="test-docs",
            base_url=AnyUrl("https://docs.example.com"),
        )

        assert config.enable_file_conversion is False  # Default
        assert config.download_attachments is None  # Default
