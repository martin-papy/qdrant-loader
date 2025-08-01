"""Tests for configuration parser."""

import pytest
from qdrant_loader.config.parser import MultiProjectConfigParser
from qdrant_loader.config.validator import ConfigValidator


class TestMultiProjectConfigParser:
    """Tests for MultiProjectConfigParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        self.parser = MultiProjectConfigParser(self.validator)

    def test_legacy_format_detection(self):
        """Test that legacy format is correctly detected."""
        legacy_config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333", "collection_name": "test"}
            },
            "sources": {
                "git": {
                    "test-repo": {
                        "base_url": "https://github.com/test/repo.git",
                        "token": "test-token",
                        "file_types": [".py", ".md"]
                    }
                }
            },
        }

        # Test that legacy format now raises clear error
        with pytest.raises(ValueError, match="Configuration must contain 'projects' section"):
            self.parser.parse(legacy_config)

    def test_multi_project_format_detection(self):
        """Test that multi-project format is correctly detected."""
        multi_project_config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333", "collection_name": "test"}
            },
            "projects": {
                "default": {
                    "display_name": "Default Project",
                    "description": "Test project",
                    "sources": {
                        "git": {
                            "test-repo": {
                                "source_type": "git",
                                "source": "test-repo",
                                "base_url": "https://github.com/test/repo.git",
                                "token": "test-token",
                                "file_types": [".py", ".md"]
                            }
                        }
                    },
                }
            },
        }

        # Test that multi-project format parses successfully
        result = self.parser.parse(multi_project_config, skip_validation=True)
        assert result is not None
        assert len(result.projects_config.projects) > 0

    def test_legacy_format_error_message(self):
        """Test that legacy format raises clear error message."""
        legacy_config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333", "collection_name": "test"}
            },
            "sources": {
                "git": {
                    "test-repo": {
                        "base_url": "https://github.com/test/repo.git",
                        "token": "test-token", 
                        "file_types": [".py", ".md"]
                    }
                }
            },
        }

        with pytest.raises(ValueError) as exc_info:
            self.parser.parse(legacy_config)

        error_message = str(exc_info.value)
        assert "Configuration must contain 'projects' section" in error_message

    def test_valid_multi_project_config_parsing(self):
        """Test that valid multi-project configuration is parsed correctly."""
        valid_config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333", "collection_name": "test"},
                "chunking": {"chunk_size": 500, "chunk_overlap": 50},
                "embedding": {"model": "text-embedding-3-small", "api_key": "test-key"},
                "state_management": {"database_path": ":memory:"},
            },
            "projects": {
                "test-project": {
                    "display_name": "Test Project",
                    "description": "A test project",
                    "sources": {
                        "git": {
                            "test-repo": {
                                "source_type": "git",
                                "source": "test-repo",
                                "base_url": "https://github.com/test/repo.git",
                                "branch": "main",
                                "token": "test-token",
                                "file_types": [".py", ".md"]
                            }
                        }
                    },
                    "overrides": {},
                }
            },
        }

        result = self.parser.parse(valid_config, skip_validation=True)

        assert result.global_config is not None
        assert result.projects_config is not None
        assert len(result.projects_config.projects) == 1
        assert "test-project" in result.projects_config.projects

        project = result.projects_config.projects["test-project"]
        assert project.project_id == "test-project"
        assert project.display_name == "Test Project"
        assert project.description == "A test project"
        assert project.get_effective_collection_name("test") == "test"

    def test_empty_projects_section_error(self):
        """Test that empty projects section raises validation error."""
        invalid_config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333", "collection_name": "test"}
            },
            "projects": {},
        }

        with pytest.raises(ValueError) as exc_info:
            self.parser.parse(invalid_config)

        error_message = str(exc_info.value)
        assert "'projects' section cannot be empty" in error_message

    def test_missing_required_project_fields(self):
        """Test that missing required project fields raise validation error."""
        invalid_config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333", "collection_name": "test"}
            },
            "projects": {
                "test-project": {
                    # Missing display_name
                    "description": "A test project",
                    "sources": {},
                }
            },
        }

        with pytest.raises(ValueError) as exc_info:
            self.parser.parse(invalid_config)

        error_message = str(exc_info.value)
        assert "must have a 'display_name'" in error_message
