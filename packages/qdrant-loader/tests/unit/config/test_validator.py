"""Tests for the ConfigValidator class."""

from unittest.mock import patch

import pytest
from qdrant_loader.config.validator import ConfigValidator


class TestConfigValidator:
    """Test cases for ConfigValidator."""

    @pytest.fixture
    def validator(self):
        """Create a ConfigValidator instance."""
        return ConfigValidator()

    @pytest.fixture
    def valid_config(self):
        """Create a valid configuration for testing."""
        return {
            "projects": {
                "project1": {
                    "display_name": "Test Project 1",
                    "description": "A test project",
                    "collection_name": "test_collection_1",
                    "sources": {
                        "git": {
                            "repo1": {
                                "url": "https://github.com/test/repo.git",
                                "token": "test_token",
                            }
                        }
                    },
                    "overrides": {"chunk_size": 2000},
                }
            },
            "global": {"qdrant": {"collection_name": "default_collection"}},
        }

    def test_initialization(self):
        """Test ConfigValidator initialization."""
        validator = ConfigValidator()
        assert validator is not None

    def test_validate_structure_success(self, validator, valid_config):
        """Test successful structure validation."""
        with patch("qdrant_loader.config.validator.logger") as mock_logger:
            validator.validate_structure(valid_config)
            mock_logger.debug.assert_called()

    def test_validate_structure_not_dict(self, validator):
        """Test validation with non-dict config."""
        with pytest.raises(ValueError, match="Configuration must be a dictionary"):
            validator.validate_structure("not a dict")

    def test_validate_structure_missing_projects(self, validator):
        """Test validation with missing projects section."""
        config = {"global": {}}

        with pytest.raises(
            ValueError, match="Configuration must contain 'projects' section"
        ):
            validator.validate_structure(config)

    def test_validate_structure_with_global_section(self, validator):
        """Test validation with global section."""
        config = {
            "projects": {"test": {"display_name": "Test Project"}},
            "global": {"qdrant": {"collection_name": "test_collection"}},
        }

        validator.validate_structure(config)  # Should not raise

    def test_validate_projects_section_not_dict(self, validator):
        """Test projects section validation with non-dict."""
        with pytest.raises(ValueError, match="'projects' section must be a dictionary"):
            validator._validate_projects_section("not a dict")

    def test_validate_projects_section_empty(self, validator):
        """Test projects section validation with empty dict."""
        with pytest.raises(ValueError, match="'projects' section cannot be empty"):
            validator._validate_projects_section({})

    def test_validate_projects_section_duplicate_ids(self, validator):
        """Test projects section with duplicate project IDs."""
        projects_data = {
            "project1": {"display_name": "Project 1"},
            "project1": {
                "display_name": "Project 1 Duplicate"
            },  # This won't actually create a duplicate in Python dict
        }

        # Since Python dict doesn't allow duplicate keys, let's test the logic differently
        # by simulating the validation process
        validator._validate_projects_section(projects_data)  # Should work fine

    def test_validate_projects_section_duplicate_collection_names(self, validator):
        """Test projects section with duplicate collection names."""
        projects_data = {
            "project1": {
                "display_name": "Project 1",
                "collection_name": "shared_collection",
            },
            "project2": {
                "display_name": "Project 2",
                "collection_name": "shared_collection",
            },
        }

        with pytest.raises(
            ValueError, match="Duplicate collection name 'shared_collection'"
        ):
            validator._validate_projects_section(projects_data)

    def test_validate_project_config_not_dict(self, validator):
        """Test project config validation with non-dict."""
        with pytest.raises(
            ValueError, match="Project 'test' configuration must be a dictionary"
        ):
            validator._validate_project_config("test", "not a dict")

    def test_validate_project_config_missing_display_name(self, validator):
        """Test project config validation with missing display_name."""
        project_config = {"description": "Missing display name"}

        with pytest.raises(
            ValueError, match="Project 'test' must have a 'display_name'"
        ):
            validator._validate_project_config("test", project_config)

    def test_validate_project_config_invalid_display_name(self, validator):
        """Test project config validation with invalid display_name."""
        project_config = {"display_name": ""}

        with pytest.raises(
            ValueError, match="Project 'test' display_name must be a non-empty string"
        ):
            validator._validate_project_config("test", project_config)

    def test_validate_project_config_invalid_display_name_type(self, validator):
        """Test project config validation with non-string display_name."""
        project_config = {"display_name": 123}

        with pytest.raises(
            ValueError, match="Project 'test' display_name must be a non-empty string"
        ):
            validator._validate_project_config("test", project_config)

    def test_validate_project_config_invalid_description(self, validator):
        """Test project config validation with invalid description."""
        project_config = {
            "display_name": "Test Project",
            "description": 123,  # Should be string or None
        }

        with pytest.raises(
            ValueError, match="Project 'test' description must be a string or null"
        ):
            validator._validate_project_config("test", project_config)

    def test_validate_project_config_valid_description_none(self, validator):
        """Test project config validation with None description."""
        project_config = {"display_name": "Test Project", "description": None}

        validator._validate_project_config("test", project_config)  # Should not raise

    def test_validate_project_config_invalid_collection_name(self, validator):
        """Test project config validation with invalid collection_name."""
        project_config = {"display_name": "Test Project", "collection_name": ""}

        with pytest.raises(
            ValueError,
            match="Project 'test' collection_name must be a non-empty string",
        ):
            validator._validate_project_config("test", project_config)

    def test_validate_project_config_invalid_collection_name_type(self, validator):
        """Test project config validation with non-string collection_name."""
        project_config = {"display_name": "Test Project", "collection_name": 123}

        with pytest.raises(
            ValueError,
            match="Project 'test' collection_name must be a non-empty string",
        ):
            validator._validate_project_config("test", project_config)

    def test_validate_project_config_invalid_overrides(self, validator):
        """Test project config validation with invalid overrides."""
        project_config = {"display_name": "Test Project", "overrides": "not a dict"}

        with pytest.raises(
            ValueError, match="Project 'test' overrides must be a dictionary"
        ):
            validator._validate_project_config("test", project_config)

    def test_validate_project_config_with_sources(self, validator):
        """Test project config validation with sources section."""
        project_config = {
            "display_name": "Test Project",
            "sources": {"git": {"repo1": {"url": "https://github.com/test/repo.git"}}},
        }

        validator._validate_project_config("test", project_config)  # Should not raise

    def test_validate_sources_section_not_dict(self, validator):
        """Test sources section validation with non-dict."""
        with pytest.raises(ValueError, match="'sources' section must be a dictionary"):
            validator._validate_sources_section("not a dict")

    def test_validate_sources_section_empty(self, validator):
        """Test sources section validation with empty dict."""
        with patch("qdrant_loader.config.validator.logger") as mock_logger:
            validator._validate_sources_section({})
            mock_logger.debug.assert_called_with(
                "Sources section is empty - this is allowed but no data will be ingested"
            )

    def test_validate_sources_section_invalid_source_type(self, validator):
        """Test sources section with non-dict source type."""
        sources_data = {"git": "not a dict"}

        with pytest.raises(ValueError, match="Source type 'git' must be a dictionary"):
            validator._validate_sources_section(sources_data)

    def test_validate_sources_section_empty_source_type(self, validator):
        """Test sources section with empty source type."""
        sources_data = {"git": {}}

        with pytest.raises(ValueError, match="Source type 'git' cannot be empty"):
            validator._validate_sources_section(sources_data)

    def test_validate_sources_section_invalid_source_config(self, validator):
        """Test sources section with non-dict source config."""
        sources_data = {"git": {"repo1": "not a dict"}}

        with pytest.raises(
            ValueError, match="Source 'repo1' in 'git' must be a dictionary"
        ):
            validator._validate_sources_section(sources_data)

    def test_validate_global_section_not_dict(self, validator):
        """Test global section validation with non-dict."""
        with pytest.raises(ValueError, match="'global' section must be a dictionary"):
            validator._validate_global_section("not a dict")

    def test_validate_global_section_invalid_qdrant(self, validator):
        """Test global section with invalid qdrant config."""
        global_data = {"qdrant": "not a dict"}

        with pytest.raises(ValueError, match="'global.qdrant' must be a dictionary"):
            validator._validate_global_section(global_data)

    def test_validate_global_section_invalid_qdrant_collection_name(self, validator):
        """Test global section with invalid qdrant collection_name."""
        global_data = {"qdrant": {"collection_name": ""}}

        with pytest.raises(
            ValueError,
            match="'global.qdrant.collection_name' must be a non-empty string",
        ):
            validator._validate_global_section(global_data)

    def test_validate_global_section_invalid_qdrant_collection_name_type(
        self, validator
    ):
        """Test global section with non-string qdrant collection_name."""
        global_data = {"qdrant": {"collection_name": 123}}

        with pytest.raises(
            ValueError,
            match="'global.qdrant.collection_name' must be a non-empty string",
        ):
            validator._validate_global_section(global_data)

    def test_validate_project_id_not_string(self, validator):
        """Test project ID validation with non-string."""
        with pytest.raises(ValueError, match="Project ID must be a string"):
            validator._validate_project_id(123)

    def test_validate_project_id_empty(self, validator):
        """Test project ID validation with empty string."""
        with pytest.raises(ValueError, match="Project ID cannot be empty"):
            validator._validate_project_id("")

    def test_validate_project_id_whitespace_only(self, validator):
        """Test project ID validation with whitespace only."""
        with pytest.raises(ValueError, match="Project ID cannot be empty"):
            validator._validate_project_id("   ")

    def test_validate_project_id_invalid_pattern(self, validator):
        """Test project ID validation with invalid characters."""
        with pytest.raises(ValueError, match="Invalid project ID 'invalid-id!'"):
            validator._validate_project_id("invalid-id!")

    def test_validate_project_id_starts_with_number(self, validator):
        """Test project ID validation starting with number."""
        with pytest.raises(ValueError, match="Invalid project ID '123project'"):
            validator._validate_project_id("123project")

    def test_validate_project_id_reserved_id(self, validator):
        """Test project ID validation with reserved ID."""
        with patch("qdrant_loader.config.validator.logger") as mock_logger:
            validator._validate_project_id("default")
            mock_logger.warning.assert_called_with(
                "Project ID 'default' is reserved and may cause conflicts"
            )

    def test_validate_project_id_reserved_id_case_insensitive(self, validator):
        """Test project ID validation with reserved ID (case insensitive)."""
        with patch("qdrant_loader.config.validator.logger") as mock_logger:
            validator._validate_project_id("GLOBAL")
            mock_logger.warning.assert_called_with(
                "Project ID 'GLOBAL' is reserved and may cause conflicts"
            )

    def test_validate_project_id_valid(self, validator):
        """Test project ID validation with valid IDs."""
        valid_ids = ["project1", "my_project", "test-project", "ProjectABC"]

        for project_id in valid_ids:
            validator._validate_project_id(project_id)  # Should not raise

    def test_validate_source_name_not_string(self, validator):
        """Test source name validation with non-string."""
        with pytest.raises(ValueError, match="Source name must be a string"):
            validator._validate_source_name(123)

    def test_validate_source_name_empty(self, validator):
        """Test source name validation with empty string."""
        with pytest.raises(ValueError, match="Source name cannot be empty"):
            validator._validate_source_name("")

    def test_validate_source_name_whitespace_only(self, validator):
        """Test source name validation with whitespace only."""
        with pytest.raises(ValueError, match="Source name cannot be empty"):
            validator._validate_source_name("   ")

    def test_validate_source_name_invalid_pattern(self, validator):
        """Test source name validation with invalid characters."""
        with pytest.raises(ValueError, match="Invalid source name 'invalid-name!'"):
            validator._validate_source_name("invalid-name!")

    def test_validate_source_name_starts_with_number(self, validator):
        """Test source name validation starting with number."""
        with pytest.raises(ValueError, match="Invalid source name '123source'"):
            validator._validate_source_name("123source")

    def test_validate_source_name_valid(self, validator):
        """Test source name validation with valid names."""
        valid_names = ["source1", "my_source", "test-source", "SourceABC"]

        for source_name in valid_names:
            validator._validate_source_name(source_name)  # Should not raise

    def test_validate_source_config_not_dict(self, validator):
        """Test source config validation with non-dict."""
        with pytest.raises(
            ValueError,
            match="Source 'test' of type 'git' configuration must be a dictionary",
        ):
            validator._validate_source_config("git", "test", "not a dict")

    def test_validate_source_config_empty(self, validator):
        """Test source config validation with empty dict."""
        with pytest.raises(
            ValueError,
            match="Source 'test' of type 'git' configuration cannot be empty",
        ):
            validator._validate_source_config("git", "test", {})

    def test_validate_source_config_valid(self, validator):
        """Test source config validation with valid config."""
        source_config = {
            "url": "https://github.com/test/repo.git",
            "token": "test_token",
        }

        validator._validate_source_config(
            "git", "test", source_config
        )  # Should not raise

    def test_validate_collection_name_too_long(self, validator):
        """Test collection name validation with too long name."""
        long_name = "a" * 256  # Longer than 255 characters

        with pytest.raises(ValueError, match="Collection name .* is too long"):
            validator._validate_collection_name(long_name)

    def test_validate_collection_name_invalid_pattern(self, validator):
        """Test collection name validation with invalid characters."""
        with pytest.raises(ValueError, match="Invalid collection name 'invalid-name!'"):
            validator._validate_collection_name("invalid-name!")

    def test_validate_collection_name_starts_with_number(self, validator):
        """Test collection name validation starting with number."""
        with pytest.raises(ValueError, match="Invalid collection name '123collection'"):
            validator._validate_collection_name("123collection")

    def test_validate_collection_name_valid(self, validator):
        """Test collection name validation with valid names."""
        valid_names = [
            "collection1",
            "my_collection",
            "test-collection",
            "CollectionABC",
        ]

        for collection_name in valid_names:
            validator._validate_collection_name(collection_name)  # Should not raise

    def test_validate_collection_name_max_length(self, validator):
        """Test collection name validation with maximum allowed length."""
        max_length_name = "a" * 255  # Exactly 255 characters

        validator._validate_collection_name(max_length_name)  # Should not raise

    def test_validate_projects_section_duplicate_project_ids(self, validator):
        """Test validation with duplicate project IDs - covers line 75."""
        # Since Python dicts automatically deduplicate keys, we need to simulate the
        # validation logic directly to test line 75. We'll create a scenario that
        # manually triggers the duplicate check.

        # Create a custom dict-like object that can simulate duplicate keys
        class MockProjectsData(dict):
            def __bool__(self):
                # Pretend we're not empty to pass the empty check on line 65
                return True

            def __len__(self):
                # Return non-zero length to pass empty check
                return 2

            def items(self):
                # Return items with duplicate project IDs to trigger line 75
                project_config = {
                    "display_name": "Test Project",
                    "sources": {
                        "git": {
                            "repo1": {
                                "source_type": "git",
                                "source": "repo1",
                                "base_url": "https://github.com",
                                "token": "test_token",
                                "repo_path": "test/repo1",
                            }
                        }
                    },
                }
                # Return the same project_id twice to trigger duplicate check
                yield ("project1", project_config)
                yield ("project1", project_config)  # Duplicate - triggers line 75

        mock_projects_data = MockProjectsData()

        with pytest.raises(ValueError, match="Duplicate project ID: 'project1'"):
            validator._validate_projects_section(mock_projects_data)
