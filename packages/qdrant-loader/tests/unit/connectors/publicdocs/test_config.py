"""Tests for the publicdocs config module."""

import pytest

from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig


class TestPublicDocsSourceConfig:
    """Test cases for PublicDocsSourceConfig."""

    def test_validate_content_type_valid_html(self):
        """Test content type validation with valid 'html' type."""
        result = PublicDocsSourceConfig.validate_content_type("html")
        assert result == "html"

    def test_validate_content_type_valid_markdown(self):
        """Test content type validation with valid 'markdown' type."""
        result = PublicDocsSourceConfig.validate_content_type("markdown")
        assert result == "markdown"

    def test_validate_content_type_valid_rst(self):
        """Test content type validation with valid 'rst' type."""
        result = PublicDocsSourceConfig.validate_content_type("rst")
        assert result == "rst"

    def test_validate_content_type_case_insensitive(self):
        """Test content type validation is case insensitive."""
        result = PublicDocsSourceConfig.validate_content_type("HTML")
        assert result == "html"
        
        result = PublicDocsSourceConfig.validate_content_type("MARKDOWN")
        assert result == "markdown"
        
        result = PublicDocsSourceConfig.validate_content_type("RST")
        assert result == "rst"

    def test_validate_content_type_invalid(self):
        """Test content type validation with invalid type."""
        with pytest.raises(ValueError, match="Content type must be one of"):
            PublicDocsSourceConfig.validate_content_type("invalid")

    def test_validate_content_type_invalid_json(self):
        """Test content type validation with invalid 'json' type."""
        with pytest.raises(ValueError, match="Content type must be one of"):
            PublicDocsSourceConfig.validate_content_type("json")

    def test_validate_content_type_empty_string(self):
        """Test content type validation with empty string."""
        with pytest.raises(ValueError, match="Content type must be one of"):
            PublicDocsSourceConfig.validate_content_type("")

    def test_config_creation_with_valid_content_type(self):
        """Test creating config with valid content type."""
        config = PublicDocsSourceConfig(
            source_type="publicdocs",
            source="test_docs",
            base_url="https://example.com/docs",
            version="v1.0",
            content_type="html"
        )
        assert str(config.base_url) == "https://example.com/docs"
        assert config.content_type == "html"
        assert config.version == "v1.0"

    def test_config_creation_with_invalid_content_type(self):
        """Test creating config with invalid content type triggers validation."""
        with pytest.raises(ValueError, match="Content type must be one of"):
            PublicDocsSourceConfig(
                source_type="publicdocs",
                source="test_docs",
                base_url="https://example.com/docs",
                version="v1.0",
                content_type="invalid_type"
            )