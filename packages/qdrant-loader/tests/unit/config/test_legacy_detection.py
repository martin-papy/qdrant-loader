"""Tests for legacy configuration detection functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml

from qdrant_loader.config.legacy_detection import (
    LegacyConfigDetector,
    detect_legacy_configuration,
    get_migration_guidance,
)


class TestLegacyConfigDetector:
    """Test legacy configuration detection functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.detector = LegacyConfigDetector()

    @pytest.fixture
    def legacy_config_with_global(self):
        """Legacy configuration with global section."""
        return {
            "global": {
                "qdrant": {
                    "url": "${QDRANT_URL}",
                    "api_key": "${QDRANT_API_KEY}",
                },
                "neo4j": {
                    "uri": "${NEO4J_URI}",
                    "user": "${NEO4J_USER}",
                },
                "chunking": {
                    "chunk_size": 1500,
                    "chunk_overlap": 200,
                },
            },
            "projects": {"default": {"project_id": "default", "sources": {}}},
        }

    @pytest.fixture
    def legacy_config_mixed_domains(self):
        """Legacy configuration with mixed domains in single file."""
        return {
            "qdrant": {
                "url": "http://localhost:6333",
            },
            "projects": {"test": {"project_id": "test"}},
            "chunking": {
                "chunk_size": 1000,
            },
        }

    @pytest.fixture
    def new_format_config(self):
        """New format configuration (connectivity only)."""
        return {
            "qdrant": {
                "url": "http://localhost:6333",
                "api_key": "test-key",
            },
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
            },
        }

    def create_temp_config_file(self, config_data, filename="config.yaml"):
        """Create a temporary configuration file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=f".{filename.split('.')[-1]}", delete=False
        )
        yaml.dump(config_data, temp_file)
        temp_file.close()
        return Path(temp_file.name)

    def test_check_legacy_indicators_global_section(self, legacy_config_with_global):
        """Test detection of global section indicators."""
        indicators = self.detector._check_legacy_indicators(legacy_config_with_global)

        assert len(indicators) > 0
        assert any(
            "global section with domains" in indicator for indicator in indicators
        )
        assert any(
            "global + projects sections" in indicator for indicator in indicators
        )

    def test_check_legacy_indicators_mixed_domains(self, legacy_config_mixed_domains):
        """Test detection of mixed domain indicators."""
        indicators = self.detector._check_legacy_indicators(legacy_config_mixed_domains)

        assert len(indicators) > 0
        assert any(
            "multiple domains in single file" in indicator for indicator in indicators
        )

    def test_check_legacy_indicators_new_format(self, new_format_config):
        """Test that new format config doesn't trigger legacy indicators."""
        indicators = self.detector._check_legacy_indicators(new_format_config)

        # Should have no indicators or only single domain
        assert len(indicators) == 0

    def test_is_legacy_config_file_with_global(self, legacy_config_with_global):
        """Test legacy detection for config with global section."""
        config_file = self.create_temp_config_file(legacy_config_with_global)

        try:
            is_legacy, reason = self.detector._is_legacy_config_file(config_file)

            assert is_legacy is True
            assert "Legacy format detected" in reason
            assert "global section with domains" in reason

        finally:
            config_file.unlink()

    def test_is_legacy_config_file_mixed_domains(self, legacy_config_mixed_domains):
        """Test legacy detection for config with mixed domains."""
        config_file = self.create_temp_config_file(legacy_config_mixed_domains)

        try:
            is_legacy, reason = self.detector._is_legacy_config_file(config_file)

            assert is_legacy is True
            assert "Legacy format detected" in reason
            assert "multiple domains in single file" in reason

        finally:
            config_file.unlink()

    def test_is_legacy_config_file_new_format(self, new_format_config):
        """Test that new format config is not detected as legacy."""
        config_file = self.create_temp_config_file(new_format_config)

        try:
            is_legacy, reason = self.detector._is_legacy_config_file(config_file)

            assert is_legacy is False
            assert "Configuration appears to be in new format" in reason

        finally:
            config_file.unlink()

    def test_is_legacy_config_file_invalid_yaml(self):
        """Test handling of invalid YAML files."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        temp_file.write("invalid: yaml: content: [")
        temp_file.close()
        config_file = Path(temp_file.name)

        try:
            is_legacy, reason = self.detector._is_legacy_config_file(config_file)

            assert is_legacy is False
            assert "Invalid YAML" in reason

        finally:
            config_file.unlink()

    def test_is_legacy_config_file_nonexistent(self):
        """Test handling of non-existent files."""
        nonexistent_file = Path("/nonexistent/config.yaml")

        is_legacy, reason = self.detector._is_legacy_config_file(nonexistent_file)

        assert is_legacy is False
        assert "Error reading file" in reason

    def test_detect_legacy_config_specific_file(self, legacy_config_with_global):
        """Test detection with specific config file path."""
        config_file = self.create_temp_config_file(legacy_config_with_global)

        try:
            is_legacy, detected_path, reason = self.detector.detect_legacy_config(
                config_path=config_file
            )

            assert is_legacy is True
            assert detected_path == config_file
            assert "Legacy format detected" in reason

        finally:
            config_file.unlink()

    def test_detect_legacy_config_search_directory(self, legacy_config_with_global):
        """Test detection by searching in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            config_file = temp_dir_path / "config.yaml"

            with open(config_file, "w") as f:
                yaml.dump(legacy_config_with_global, f)

            is_legacy, detected_path, reason = self.detector.detect_legacy_config(
                search_dir=temp_dir_path
            )

            assert is_legacy is True
            assert detected_path == config_file
            assert "Legacy format detected" in reason

    def test_detect_legacy_config_new_format_files_present(
        self, legacy_config_with_global
    ):
        """Test that new format files take precedence over legacy files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Create legacy config file
            legacy_config_file = temp_dir_path / "config.yaml"
            with open(legacy_config_file, "w") as f:
                yaml.dump(legacy_config_with_global, f)

            # Create new format file
            connectivity_file = temp_dir_path / "connectivity.yaml"
            connectivity_file.write_text("qdrant:\n  url: http://localhost:6333")

            is_legacy, detected_path, reason = self.detector.detect_legacy_config(
                search_dir=temp_dir_path
            )

            assert is_legacy is False
            assert detected_path is None
            assert "New format files found" in reason

    def test_detect_legacy_config_no_files_found(self):
        """Test detection when no config files are found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            is_legacy, detected_path, reason = self.detector.detect_legacy_config(
                search_dir=temp_dir_path
            )

            assert is_legacy is False
            assert detected_path is None
            assert "No configuration files found" in reason

    def test_get_migration_guidance(self, legacy_config_with_global):
        """Test migration guidance generation."""
        config_file = self.create_temp_config_file(legacy_config_with_global)

        try:
            guidance = self.detector.get_migration_guidance(config_file)

            assert "legacy_file" in guidance
            assert "output_dir" in guidance
            assert "dry_run_command" in guidance
            assert "migration_command" in guidance
            assert "force_migration_command" in guidance

            assert str(config_file) in guidance["legacy_file"]
            assert "migrate-config" in guidance["dry_run_command"]
            assert "--dry-run" in guidance["dry_run_command"]
            assert "migrate-config" in guidance["migration_command"]
            assert "--force" in guidance["force_migration_command"]

        finally:
            config_file.unlink()

    def test_get_migration_guidance_custom_output_dir(self, legacy_config_with_global):
        """Test migration guidance with custom output directory."""
        config_file = self.create_temp_config_file(legacy_config_with_global)
        custom_output_dir = Path("/custom/output/dir")

        try:
            guidance = self.detector.get_migration_guidance(
                config_file, suggested_output_dir=custom_output_dir
            )

            assert str(custom_output_dir) in guidance["output_dir"]
            assert str(custom_output_dir) in guidance["migration_command"]

        finally:
            config_file.unlink()


class TestConvenienceFunctions:
    """Test convenience functions for legacy detection."""

    @pytest.fixture
    def sample_legacy_config(self):
        """Sample legacy configuration."""
        return {
            "global": {
                "qdrant": {"url": "http://localhost:6333"},
                "chunking": {"chunk_size": 1000},
            },
            "projects": {"test": {"project_id": "test"}},
        }

    def test_detect_legacy_configuration_function(self, sample_legacy_config):
        """Test the convenience function for detection."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(sample_legacy_config, temp_file)
        temp_file.close()
        config_file = Path(temp_file.name)

        try:
            is_legacy, detected_path, reason = detect_legacy_configuration(
                config_path=config_file
            )

            assert is_legacy is True
            assert detected_path == config_file
            assert "Legacy format detected" in reason

        finally:
            config_file.unlink()

    def test_get_migration_guidance_function(self, sample_legacy_config):
        """Test the convenience function for migration guidance."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(sample_legacy_config, temp_file)
        temp_file.close()
        config_file = Path(temp_file.name)

        try:
            guidance = get_migration_guidance(config_file)

            assert isinstance(guidance, dict)
            assert "legacy_file" in guidance
            assert "migration_command" in guidance

        finally:
            config_file.unlink()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.detector = LegacyConfigDetector()

    def test_empty_configuration(self):
        """Test detection of empty configuration."""
        empty_config = {}
        indicators = self.detector._check_legacy_indicators(empty_config)
        assert indicators == []

    def test_configuration_with_only_projects(self):
        """Test configuration with only projects section."""
        projects_only_config = {"projects": {"test": {"project_id": "test"}}}
        indicators = self.detector._check_legacy_indicators(projects_only_config)
        # Should not be considered legacy if it only has projects
        assert len(indicators) == 0

    def test_configuration_with_unknown_sections(self):
        """Test configuration with unknown sections."""
        unknown_config = {
            "unknown_section": {"some_key": "some_value"},
            "another_unknown": {"other_key": "other_value"},
        }
        indicators = self.detector._check_legacy_indicators(unknown_config)
        # Unknown sections alone shouldn't trigger legacy detection
        assert len(indicators) == 0

    def test_non_dict_configuration(self):
        """Test handling of non-dictionary configuration."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(["not", "a", "dict"], temp_file)
        temp_file.close()
        config_file = Path(temp_file.name)

        try:
            is_legacy, reason = self.detector._is_legacy_config_file(config_file)

            assert is_legacy is False
            assert "Configuration is not a dictionary" in reason

        finally:
            config_file.unlink()
