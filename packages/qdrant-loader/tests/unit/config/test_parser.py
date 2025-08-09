"""Tests for the config parser module."""

import pytest
from pydantic import ValidationError
from qdrant_loader.config.parser import MultiProjectConfigParser
from qdrant_loader.config.validator import ConfigValidator


class TestMultiProjectConfigParser:
    """Test cases for MultiProjectConfigParser."""

    @pytest.fixture
    def parser(self):
        """Create a MultiProjectConfigParser instance."""
        validator = ConfigValidator()
        return MultiProjectConfigParser(validator)

    def test_parse_global_config_validation_error(self, parser):
        """Test global config parsing with validation error - covers lines 83-85."""
        # Create invalid global config data that will trigger ValidationError
        invalid_global_data = {
            "qdrant": {
                "collection_name": "",  # Empty collection name should trigger validation error
                "vector_size": "invalid",  # Invalid vector size
            }
        }

        with pytest.raises(ValidationError):
            parser._parse_global_config(invalid_global_data)

    def test_parse_project_config_invalid_id(self, parser):
        """Test project config parsing with invalid ID - covers line 131."""
        # Test invalid project IDs that should trigger ValueError
        invalid_ids = [
            "123invalid",  # Starts with number
            "invalid.id",  # Contains dot
            "invalid id",  # Contains space
            "",  # Empty string
        ]

        for invalid_id in invalid_ids:
            project_data = {"display_name": "Test Project"}
            with pytest.raises(ValueError, match="Invalid project ID"):
                parser._parse_project_config(invalid_id, project_data, {})

    def test_inject_source_metadata_non_dict_source_configs(self, parser):
        """Test source metadata injection with non-dict source configs - covers lines 173-174."""
        # Create sources data where source_configs is not a dict
        sources_data = {
            "git": "invalid_non_dict_value",  # This should trigger lines 173-174
            "confluence": {"wiki": {"url": "https://example.com"}},
        }

        result = parser._inject_source_metadata(sources_data)

        # Non-dict value should be passed through unchanged
        assert result["git"] == "invalid_non_dict_value"
        assert "confluence" in result

    def test_inject_source_metadata_non_dict_source_config(self, parser):
        """Test source metadata injection with non-dict individual source config - covers line 188."""
        # Create sources data where individual source_config is not a dict
        sources_data = {
            "git": {
                "repo1": {"url": "https://github.com/test/repo.git"},
                "repo2": "invalid_non_dict_config",  # This should trigger line 188
            }
        }

        result = parser._inject_source_metadata(sources_data)

        # Dict config should be enhanced with metadata
        assert result["git"]["repo1"]["source_type"] == "git"
        assert result["git"]["repo1"]["source"] == "repo1"

        # Non-dict config should be passed through unchanged
        assert result["git"]["repo2"] == "invalid_non_dict_config"

    def test_deep_merge_dicts_nested_dicts(self, parser):
        """Test deep dictionary merging with nested dicts - covers lines 243, 248."""
        base = {
            "level1": {
                "level2": {"value1": "base_value1", "value2": "base_value2"},
                "simple_value": "base_simple",
            },
            "other_key": "base_other",
        }

        override = {
            "level1": {
                "level2": {
                    "value2": "override_value2",  # Should override
                    "value3": "new_value3",  # Should add
                }
                # simple_value not included, should remain from base
            },
            "new_key": "override_new",  # Should add
        }

        result = parser._deep_merge_dicts(base, override)

        # Test the nested merge (covers line 248)
        assert result["level1"]["level2"]["value1"] == "base_value1"  # From base
        assert result["level1"]["level2"]["value2"] == "override_value2"  # Overridden
        assert result["level1"]["level2"]["value3"] == "new_value3"  # Added
        assert result["level1"]["simple_value"] == "base_simple"  # Preserved from base

        # Test the top-level merge
        assert result["other_key"] == "base_other"  # From base
        assert result["new_key"] == "override_new"  # Added

    def test_deep_merge_dicts_non_dict_override(self, parser):
        """Test deep dictionary merging with non-dict override value - covers line 250."""
        base = {
            "dict_key": {"nested": "base_nested_value"},
            "simple_key": "base_simple_value",
        }

        override = {
            "dict_key": "non_dict_override",  # This should trigger line 250 (non-dict override)
            "simple_key": "override_simple_value",
            "new_key": "new_value",
        }

        result = parser._deep_merge_dicts(base, override)

        # Non-dict override should replace the entire dict (line 250)
        assert result["dict_key"] == "non_dict_override"
        assert result["simple_key"] == "override_simple_value"
        assert result["new_key"] == "new_value"

    def test_deep_merge_dicts_base_non_dict(self, parser):
        """Test deep dictionary merging when base value is not a dict - covers line 250."""
        base = {
            "simple_key": "base_simple_value",  # Not a dict
            "dict_key": {"nested": "base_nested"},
        }

        override = {
            "simple_key": {"new_nested": "override_nested"},  # Dict overriding non-dict
            "dict_key": {"nested": "override_nested"},
        }

        result = parser._deep_merge_dicts(base, override)

        # When base is not a dict, override should replace it completely (line 250)
        assert result["simple_key"] == {"new_nested": "override_nested"}
        assert result["dict_key"]["nested"] == "override_nested"

    def test_deep_merge_dicts_empty_override(self, parser):
        """Test deep dictionary merging with empty override."""
        base = {"key1": "value1", "key2": {"nested": "nested_value"}}

        override = {}

        result = parser._deep_merge_dicts(base, override)

        # Should return base unchanged
        assert result == base
        assert result is not base  # Should be a copy

    def test_is_valid_project_id_valid_cases(self, parser):
        """Test project ID validation with valid IDs."""
        valid_ids = [
            "project1",
            "my_project",
            "ProjectABC",
            "project_123",
            "project-name",  # Dashes are allowed
            "project-with-hyphens",
            "a",  # Single character
            "A",  # Single uppercase
        ]

        for valid_id in valid_ids:
            assert parser._is_valid_project_id(valid_id) is True

    def test_is_valid_project_id_edge_cases(self, parser):
        """Test project ID validation with edge cases."""
        invalid_ids = [
            "",  # Empty
            "123",  # Starts with number
            "_private_project",  # Starts with underscore (invalid per regex)
            "project.name",  # Contains dot
            "project name",  # Contains space
            "project@name",  # Contains special character
            "project/name",  # Contains slash
        ]

        for invalid_id in invalid_ids:
            assert parser._is_valid_project_id(invalid_id) is False
