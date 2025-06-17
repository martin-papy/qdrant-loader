"""Tests for QdrantConfig class."""

import pytest
from pydantic import ValidationError
from qdrant_loader.config.qdrant import QdrantConfig


class TestQdrantConfig:
    """Test cases for QdrantConfig class."""

    def test_default_configuration(self):
        """Test QdrantConfig with minimal required fields."""
        config = QdrantConfig(
            url="http://localhost:6333", collection_name="test_collection"
        )

        assert config.url == "http://localhost:6333"
        assert config.api_key is None
        assert config.collection_name == "test_collection"

    def test_full_configuration(self):
        """Test QdrantConfig with all fields specified."""
        config = QdrantConfig(
            url="https://cloud.qdrant.io",
            api_key="test-api-key",
            collection_name="production_collection",
        )

        assert config.url == "https://cloud.qdrant.io"
        assert config.api_key == "test-api-key"
        assert config.collection_name == "production_collection"

    def test_from_dict(self):
        """Test creating QdrantConfig from dictionary."""
        config_dict = {
            "url": "http://localhost:6333",
            "api_key": "test-key",
            "collection_name": "my_collection",
        }

        config = QdrantConfig(**config_dict)

        assert config.url == "http://localhost:6333"
        assert config.api_key == "test-key"
        assert config.collection_name == "my_collection"

    def test_to_dict(self):
        """Test converting QdrantConfig to dictionary."""
        config = QdrantConfig(
            url="http://localhost:6333",
            api_key="test-key",
            collection_name="my_collection",
        )

        result = config.to_dict()

        expected = {
            "url": "http://localhost:6333",
            "api_key": "test-key",
            "collection_name": "my_collection",
        }
        assert result == expected

    def test_to_dict_with_none_api_key(self):
        """Test converting QdrantConfig to dictionary with None api_key."""
        config = QdrantConfig(
            url="http://localhost:6333", collection_name="my_collection"
        )

        result = config.to_dict()

        expected = {
            "url": "http://localhost:6333",
            "api_key": None,
            "collection_name": "my_collection",
        }
        assert result == expected

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QdrantConfig()  # type: ignore

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "url" in error_fields
        assert "collection_name" in error_fields

    def test_missing_url(self):
        """Test that missing URL raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QdrantConfig(collection_name="test")  # type: ignore

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "url" for error in errors)

    def test_missing_collection_name(self):
        """Test that missing collection name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QdrantConfig(url="http://localhost:6333")  # type: ignore

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "collection_name" for error in errors)

    # Note: Empty string validation is not implemented in the base QdrantConfig class
    # This would require custom field validators if needed in the future
