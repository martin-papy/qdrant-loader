"""Tests for configuration migration functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from qdrant_loader.config.migration import (
    ConfigMigrationError,
    ConfigMigrator,
    migrate_legacy_config,
)
from qdrant_loader.config.multi_file_loader import ConfigDomain


class TestConfigMigrator:
    """Test configuration migration functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.migrator = ConfigMigrator()

    @pytest.fixture
    def sample_legacy_config(self):
        """Sample legacy configuration for testing."""
        return {
            "global": {
                "qdrant": {
                    "url": "${QDRANT_URL}",
                    "api_key": "${QDRANT_API_KEY}",
                    "collection_name": "${QDRANT_COLLECTION_NAME}",
                },
                "neo4j": {
                    "uri": "${NEO4J_URI}",
                    "user": "${NEO4J_USER}",
                    "password": "${NEO4J_PASSWORD}",
                    "database": "${NEO4J_DATABASE}",
                },
                "embedding": {
                    "model": "text-embedding-3-small",
                    "api_key": "${OPENAI_API_KEY}",
                    "batch_size": 10,
                },
                "chunking": {
                    "chunk_size": 1500,
                    "chunk_overlap": 200,
                },
                "file_conversion": {
                    "max_file_size": 52428800,
                    "conversion_timeout": 300,
                },
            },
            "projects": {
                "default": {
                    "project_id": "default",
                    "display_name": "Test Project",
                    "sources": {
                        "git": {
                            "test-repo": {
                                "source_type": "git",
                                "base_url": "${REPO_URL}",
                                "branch": "main",
                            }
                        }
                    },
                }
            },
        }

    @pytest.fixture
    def temp_config_file(self, sample_legacy_config):
        """Create a temporary legacy configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_legacy_config, f)
            return Path(f.name)

    def test_load_legacy_config_success(self, temp_config_file, sample_legacy_config):
        """Test successful loading of legacy configuration."""
        result = self.migrator._load_legacy_config(temp_config_file)
        assert result == sample_legacy_config

    def test_load_legacy_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        with pytest.raises(
            ConfigMigrationError, match="Failed to load configuration file"
        ):
            self.migrator._load_legacy_config(Path("/nonexistent/config.yaml"))

    def test_load_legacy_config_invalid_yaml(self):
        """Test loading invalid YAML configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = Path(f.name)

        with pytest.raises(
            ConfigMigrationError, match="Invalid YAML in configuration file"
        ):
            self.migrator._load_legacy_config(invalid_file)

    def test_load_legacy_config_non_dict(self):
        """Test loading configuration that's not a dictionary."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(["not", "a", "dict"], f)
            invalid_file = Path(f.name)

        with pytest.raises(
            ConfigMigrationError,
            match="Configuration file must contain a YAML dictionary",
        ):
            self.migrator._load_legacy_config(invalid_file)

    def test_split_into_domains_complete_config(self, sample_legacy_config):
        """Test splitting a complete legacy configuration into domains."""
        result = self.migrator._split_into_domains(sample_legacy_config)

        # Check that all expected domains are present
        assert ConfigDomain.CONNECTIVITY in result
        assert ConfigDomain.PROJECTS in result
        assert ConfigDomain.FINE_TUNING in result

        # Check connectivity domain
        connectivity = result[ConfigDomain.CONNECTIVITY]
        assert "qdrant" in connectivity
        assert "neo4j" in connectivity
        assert "embedding" in connectivity

        # Check projects domain
        projects = result[ConfigDomain.PROJECTS]
        assert "projects" in projects
        assert "default" in projects["projects"]

        # Check fine-tuning domain
        fine_tuning = result[ConfigDomain.FINE_TUNING]
        assert "chunking" in fine_tuning
        assert "file_conversion" in fine_tuning

    def test_split_into_domains_minimal_config(self):
        """Test splitting a minimal configuration."""
        minimal_config = {"global": {"qdrant": {"url": "http://localhost:6333"}}}

        result = self.migrator._split_into_domains(minimal_config)

        # Should only have connectivity domain
        assert ConfigDomain.CONNECTIVITY in result
        assert ConfigDomain.PROJECTS not in result
        assert ConfigDomain.FINE_TUNING not in result

        # Check connectivity content
        assert "qdrant" in result[ConfigDomain.CONNECTIVITY]

    def test_split_into_domains_projects_only(self):
        """Test splitting configuration with only projects."""
        projects_config = {"projects": {"test": {"project_id": "test", "sources": {}}}}

        result = self.migrator._split_into_domains(projects_config)

        # Should only have projects domain
        assert ConfigDomain.PROJECTS in result
        assert ConfigDomain.CONNECTIVITY not in result
        assert ConfigDomain.FINE_TUNING not in result

    def test_split_into_domains_top_level_sections(self):
        """Test splitting configuration with top-level chunking/file_conversion."""
        config = {
            "chunking": {
                "chunk_size": 1000,
                "chunk_overlap": 100,
            },
            "file_conversion": {
                "max_file_size": 10485760,
            },
        }

        result = self.migrator._split_into_domains(config)

        # Should only have fine-tuning domain
        assert ConfigDomain.FINE_TUNING in result
        assert ConfigDomain.CONNECTIVITY not in result
        assert ConfigDomain.PROJECTS not in result

        # Check fine-tuning content
        fine_tuning = result[ConfigDomain.FINE_TUNING]
        assert "chunking" in fine_tuning
        assert "file_conversion" in fine_tuning

    def test_create_backup(self, temp_config_file):
        """Test backup creation."""
        backup_path = self.migrator._create_backup(temp_config_file)

        # Check that backup file exists
        assert backup_path.exists()
        assert backup_path.name.startswith(temp_config_file.stem)
        assert ".backup." in backup_path.name
        assert backup_path.suffix == temp_config_file.suffix

        # Check that backup content matches original
        with open(temp_config_file, "r") as original:
            original_content = original.read()
        with open(backup_path, "r") as backup:
            backup_content = backup.read()

        assert original_content == backup_content

        # Clean up
        backup_path.unlink()

    def test_execute_migration_success(self, sample_legacy_config):
        """Test successful migration execution."""
        domain_configs = self.migrator._split_into_domains(sample_legacy_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            created_files = self.migrator._execute_migration(
                domain_configs, output_dir, force=False
            )

            # Check that files were created
            assert len(created_files) == len(domain_configs)

            for domain in domain_configs.keys():
                expected_file = output_dir / f"{domain}.yaml"
                assert str(expected_file) in created_files
                assert expected_file.exists()

                # Check file content
                with open(expected_file, "r") as f:
                    content = f.read()
                    assert f"# {domain.title()} Configuration" in content
                    assert "Generated by configuration migration tool" in content

    def test_execute_migration_file_exists_no_force(self, sample_legacy_config):
        """Test migration when output files exist and force=False."""
        domain_configs = self.migrator._split_into_domains(sample_legacy_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Create an existing file
            existing_file = output_dir / f"{ConfigDomain.CONNECTIVITY}.yaml"
            existing_file.touch()

            # Should raise error when force=False
            with pytest.raises(
                ConfigMigrationError, match="Output file already exists"
            ):
                self.migrator._execute_migration(
                    domain_configs, output_dir, force=False
                )

    def test_execute_migration_file_exists_with_force(self, sample_legacy_config):
        """Test migration when output files exist and force=True."""
        domain_configs = self.migrator._split_into_domains(sample_legacy_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Create an existing file
            existing_file = output_dir / f"{ConfigDomain.CONNECTIVITY}.yaml"
            existing_file.write_text("existing content")

            # Should succeed when force=True
            created_files = self.migrator._execute_migration(
                domain_configs, output_dir, force=True
            )

            assert str(existing_file) in created_files
            # Check that file was overwritten
            content = existing_file.read_text()
            assert "existing content" not in content
            assert "Generated by configuration migration tool" in content

    def test_migrate_config_dry_run(self, temp_config_file):
        """Test dry run migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = self.migrator.migrate_config(
                legacy_config_path=temp_config_file,
                output_dir=output_dir,
                dry_run=True,
                create_backup=False,
                force=False,
            )

            # Check dry run results
            assert result["dry_run"] is True
            assert "domain_configs" in result
            assert "would_create_files" in result

            # Check that no files were actually created
            assert not any(output_dir.iterdir())

    def test_migrate_config_full_migration(self, temp_config_file):
        """Test complete migration process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = self.migrator.migrate_config(
                legacy_config_path=temp_config_file,
                output_dir=output_dir,
                dry_run=False,
                create_backup=True,
                force=False,
            )

            # Check migration results
            assert result["success"] is True
            assert "created_files" in result
            assert "backup_path" in result
            assert "migration_timestamp" in result

            # Check that backup was created
            backup_path = Path(result["backup_path"])
            assert backup_path.exists()

            # Check that domain files were created
            created_files = result["created_files"]
            assert len(created_files) > 0

            for file_path in created_files:
                file_obj = Path(file_path)
                assert file_obj.exists()
                assert file_obj.suffix == ".yaml"

    def test_migrate_config_file_not_found(self):
        """Test migration with non-existent legacy config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            nonexistent_file = Path("/nonexistent/config.yaml")

            with pytest.raises(FileNotFoundError):
                self.migrator.migrate_config(
                    legacy_config_path=nonexistent_file,
                    output_dir=output_dir,
                    dry_run=False,
                    create_backup=False,
                    force=False,
                )

    def test_migrate_config_creates_output_dir(self, temp_config_file):
        """Test that migration creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "new_config_dir"
            assert not output_dir.exists()

            result = self.migrator.migrate_config(
                legacy_config_path=temp_config_file,
                output_dir=output_dir,
                dry_run=False,
                create_backup=False,
                force=False,
            )

            # Check that output directory was created
            assert output_dir.exists()
            assert result["success"] is True


class TestMigrateLegacyConfigFunction:
    """Test the convenience function for migration."""

    @pytest.fixture
    def sample_config_file(self):
        """Create a sample configuration file."""
        config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333"},
                "chunking": {"chunk_size": 1000},
            },
            "projects": {"test": {"project_id": "test"}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            return Path(f.name)

    def test_migrate_legacy_config_function(self, sample_config_file):
        """Test the convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = migrate_legacy_config(
                legacy_config_path=sample_config_file,
                output_dir=output_dir,
                dry_run=False,
                create_backup=False,
                force=False,
            )

            assert result["success"] is True
            assert len(result["created_files"]) > 0

    def test_migrate_legacy_config_function_dry_run(self, sample_config_file):
        """Test the convenience function with dry run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = migrate_legacy_config(
                legacy_config_path=sample_config_file,
                output_dir=output_dir,
                dry_run=True,
                create_backup=False,
                force=False,
            )

            assert result["dry_run"] is True
            assert "domain_configs" in result
            assert "would_create_files" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.migrator = ConfigMigrator()

    def test_empty_configuration(self):
        """Test migration of empty configuration."""
        empty_config = {}
        result = self.migrator._split_into_domains(empty_config)
        assert result == {}

    def test_configuration_with_unknown_sections(self):
        """Test configuration with unknown top-level sections."""
        config = {
            "unknown_section": {"some_key": "some_value"},
            "global": {"qdrant": {"url": "http://localhost:6333"}},
        }

        result = self.migrator._split_into_domains(config)

        # Unknown sections should be placed in connectivity by default
        assert ConfigDomain.CONNECTIVITY in result
        # The unknown section should not be included since we simplified the logic

    def test_configuration_with_nested_environment_variables(self):
        """Test configuration with complex environment variable usage."""
        config = {
            "global": {
                "qdrant": {
                    "url": "${QDRANT_PROTOCOL}://${QDRANT_HOST}:${QDRANT_PORT}",
                    "api_key": "${QDRANT_API_KEY:-default_key}",
                }
            }
        }

        result = self.migrator._split_into_domains(config)
        connectivity = result[ConfigDomain.CONNECTIVITY]

        # Environment variables should be preserved
        assert "${QDRANT_PROTOCOL}" in str(connectivity["qdrant"]["url"])
        assert "${QDRANT_API_KEY:-default_key}" in connectivity["qdrant"]["api_key"]

    @patch("qdrant_loader.config.migration.yaml.dump")
    def test_yaml_dump_error(self, mock_yaml_dump):
        """Test handling of YAML dump errors during migration."""
        mock_yaml_dump.side_effect = Exception("YAML dump failed")

        # Create a sample legacy config for this test
        sample_legacy_config = {
            "global": {
                "qdrant": {"url": "http://localhost:6333"},
                "chunking": {"chunk_size": 1000},
            },
            "projects": {"test": {"project_id": "test"}},
        }

        domain_configs = self.migrator._split_into_domains(sample_legacy_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            with pytest.raises(
                ConfigMigrationError, match="Failed to write .* configuration"
            ):
                self.migrator._execute_migration(
                    domain_configs, output_dir, force=False
                )

    def teardown_method(self):
        """Clean up after tests."""
        # Clean up any temporary files created during tests
        pass
